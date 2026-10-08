const TARGET_RATE = 16_000
const MAX_SECONDS = 15

/** Render at the target rate with the browser's anti-aliasing resampler. */
export async function resampleMono(samples: Float32Array, sampleRate: number): Promise<Float32Array> {
  if (!Number.isFinite(sampleRate) || sampleRate < 8_000 || sampleRate > 192_000 || !samples.length) {
    throw new Error('Dữ liệu ghi âm không hợp lệ.')
  }
  const duration = samples.length / sampleRate
  if (duration < 1 || duration > MAX_SECONDS) throw new Error('Hãy ghi âm từ 1 đến 15 giây.')
  if (samples.some(sample => !Number.isFinite(sample))) throw new Error('Dữ liệu ghi âm không hợp lệ.')
  if (sampleRate === TARGET_RATE) return samples.slice()
  if (typeof OfflineAudioContext === 'undefined') throw new Error('Trình duyệt chưa hỗ trợ chuyển đổi âm thanh. Hãy tải WAV 16 kHz.')
  const frames = Math.round(samples.length * TARGET_RATE / sampleRate)
  const context = new OfflineAudioContext(1, frames, TARGET_RATE)
  const input = context.createBuffer(1, samples.length, sampleRate)
  input.getChannelData(0).set(samples)
  const source = context.createBufferSource()
  source.buffer = input
  source.connect(context.destination)
  source.start()
  const rendered = await context.startRendering()
  source.disconnect()
  return rendered.getChannelData(0).slice()
}

/** PCM16 little-endian, mono, 16 kHz WAV. Input must already be resampled. */
export function encodePcm16Wav(samples: Float32Array): ArrayBuffer {
  if (samples.length < TARGET_RATE || samples.length > TARGET_RATE * MAX_SECONDS || samples.some(sample => !Number.isFinite(sample))) {
    throw new Error('Hãy ghi âm từ 1 đến 15 giây.')
  }
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)
  const text = (offset: number, value: string) => {
    for (let i = 0; i < value.length; i++) view.setUint8(offset + i, value.charCodeAt(i))
  }
  text(0, 'RIFF')
  view.setUint32(4, buffer.byteLength - 8, true)
  text(8, 'WAVE')
  text(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, TARGET_RATE, true)
  view.setUint32(28, TARGET_RATE * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  text(36, 'data')
  view.setUint32(40, samples.length * 2, true)
  for (let i = 0; i < samples.length; i++) {
    const sample = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(44 + i * 2, Math.round(sample < 0 ? sample * 32768 : sample * 32767), true)
  }
  return buffer
}

export async function encodeWav(samples: Float32Array, sampleRate: number): Promise<File> {
  const resampled = await resampleMono(samples, sampleRate)
  return new File([encodePcm16Wav(resampled)], 'ghi-am.wav', { type: 'audio/wav' })
}

interface RecorderOptions {
  onDuration?: (seconds: number) => void
  onAutoStop?: (file: File) => void
  onError?: (error: Error) => void
}

function abortError() { return new DOMException('Đã hủy ghi âm.', 'AbortError') }

export class MicrophoneRecorder {
  private phase: 'idle' | 'starting' | 'recording' | 'stopping' = 'idle'
  private generation = 0
  private stream: MediaStream | null = null
  private context: AudioContext | null = null
  private source: MediaStreamAudioSourceNode | null = null
  private node: AudioWorkletNode | null = null
  private gain: GainNode | null = null
  private chunks: Float32Array[] = []
  private frames = 0
  private sampleRate = TARGET_RATE
  private finishing: Promise<File> | null = null
  private workletFinished: Promise<void> | null = null
  private resolveWorklet: (() => void) | null = null
  private durationListener?: (seconds: number) => void

  constructor(private readonly options: RecorderOptions = {}) {}

  get recording() { return this.phase === 'recording' }
  get duration() { return this.frames / this.sampleRate }

  async start(onDuration?: (seconds: number) => void): Promise<void> {
    if (this.phase !== 'idle') throw new Error('Một phiên ghi âm đang hoạt động.')
    if (!navigator.mediaDevices?.getUserMedia || typeof AudioContext === 'undefined' || typeof AudioWorkletNode === 'undefined') {
      throw new Error('Trình duyệt chưa hỗ trợ microphone. Hãy dùng Chrome trên localhost hoặc tải tệp WAV.')
    }
    this.phase = 'starting'
    const token = ++this.generation
    this.frames = 0
    this.chunks = []
    this.finishing = null
    this.durationListener = onDuration ?? this.options.onDuration
    let stream: MediaStream | null = null
    let context: AudioContext | null = null
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } })
      if (token !== this.generation) {
        stream.getTracks().forEach(track => track.stop())
        throw abortError()
      }
      this.stream = stream
      context = new AudioContext({ latencyHint: 'interactive' })
      this.context = context
      this.sampleRate = context.sampleRate
      await context.audioWorklet.addModule('/pcm-capture-worklet.js')
      if (token !== this.generation) throw abortError()
      await context.resume()
      if (token !== this.generation) throw abortError()
      this.workletFinished = new Promise(resolve => { this.resolveWorklet = resolve })
      this.source = context.createMediaStreamSource(stream)
      this.node = new AudioWorkletNode(context, 'pcm-capture', {
        processorOptions: { maxSeconds: MAX_SECONDS, batchSize: 2048 },
      })
      this.gain = context.createGain()
      this.gain.gain.value = 0
      this.node.port.onmessage = (event: MessageEvent<{ type: string; samples?: Float32Array; reason?: string }>) => {
        if (token !== this.generation) return
        if (event.data.type === 'samples' && event.data.samples) {
          const remaining = this.sampleRate * MAX_SECONDS - this.frames
          const chunk = event.data.samples.slice(0, remaining)
          if (chunk.length) {
            this.chunks.push(chunk)
            this.frames += chunk.length
            this.durationListener?.(this.duration)
          }
        }
        if (event.data.type === 'done') {
          this.resolveWorklet?.()
          if (event.data.reason === 'limit' && this.phase === 'recording') {
            void this.stop().then(file => {
              if (token === this.generation) this.options.onAutoStop?.(file)
            }).catch(error => {
              if (token === this.generation) this.options.onError?.(error instanceof Error ? error : new Error('Không thể hoàn tất ghi âm.'))
            })
          }
        }
      }
      this.source.connect(this.node)
      this.node.connect(this.gain)
      this.gain.connect(context.destination)
      this.phase = 'recording'
      this.durationListener?.(0)
    } catch (error) {
      stream?.getTracks().forEach(track => track.stop())
      if (context && context.state !== 'closed') await context.close().catch(() => undefined)
      if (token === this.generation) {
        await this.releaseResources()
        this.phase = 'idle'
      }
      if (token !== this.generation) throw abortError()
      if (error instanceof DOMException && error.name === 'NotAllowedError') throw new Error('Bạn chưa cho phép dùng microphone. Hãy cấp quyền hoặc tải tệp WAV.')
      if (error instanceof DOMException && error.name === 'NotFoundError') throw new Error('Không tìm thấy microphone. Hãy kết nối thiết bị hoặc tải tệp WAV.')
      throw error
    }
  }

  stop(): Promise<File> {
    if (this.finishing) return this.finishing
    if (this.phase !== 'recording') return Promise.reject(new Error('Chưa có phiên ghi âm để dừng.'))
    const token = this.generation
    this.phase = 'stopping'
    this.node?.port.postMessage({ type: 'stop' })
    this.finishing = this.finalize(token)
    return this.finishing
  }

  private async finalize(token: number): Promise<File> {
    let flushTimer: ReturnType<typeof setTimeout> | undefined
    try {
      await Promise.race([this.workletFinished, new Promise<void>(resolve => { flushTimer = setTimeout(resolve, 250) })])
      if (token !== this.generation) throw abortError()
      const samples = new Float32Array(this.frames)
      let offset = 0
      for (const chunk of this.chunks) { samples.set(chunk, offset); offset += chunk.length }
      const rate = this.sampleRate
      this.chunks = []
      await this.releaseResources()
      if (token !== this.generation) throw abortError()
      const file = await encodeWav(samples, rate)
      if (token !== this.generation) throw abortError()
      return file
    } finally {
      clearTimeout(flushTimer)
      if (token === this.generation) {
        await this.releaseResources()
        this.chunks = []
        this.phase = 'idle'
      }
    }
  }

  async cancel(): Promise<void> {
    ++this.generation
    this.resolveWorklet?.()
    await this.releaseResources()
    this.chunks = []
    this.frames = 0
    this.finishing = null
    this.phase = 'idle'
  }

  private async releaseResources(): Promise<void> {
    const node = this.node
    const context = this.context
    const stream = this.stream
    this.node = null
    this.context = null
    this.stream = null
    this.source?.disconnect()
    this.gain?.disconnect()
    this.source = null
    this.gain = null
    if (node) {
      node.port.onmessage = null
      node.port.postMessage({ type: 'stop' })
      node.disconnect()
      node.port.close()
    }
    stream?.getTracks().forEach(track => track.stop())
    if (context && context.state !== 'closed') await context.close().catch(() => undefined)
  }
}
