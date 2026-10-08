/* Native-rate floating PCM capture; the main thread resamples before WAV export. */
class PcmCaptureProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super()
    this.limit = Math.floor(sampleRate * (options.processorOptions?.maxSeconds ?? 15))
    this.batchSize = options.processorOptions?.batchSize ?? 2048
    this.buffer = new Float32Array(this.batchSize)
    this.position = 0
    this.frames = 0
    this.finished = false
    this.port.onmessage = event => {
      if (event.data.type === 'stop') this.finish('stop')
    }
  }

  flush() {
    if (!this.position) return
    const samples = this.buffer.slice(0, this.position)
    this.port.postMessage({ type: 'samples', samples }, [samples.buffer])
    this.position = 0
  }

  finish(reason) {
    if (this.finished) return
    this.flush()
    this.finished = true
    this.port.postMessage({ type: 'done', reason })
  }

  process(inputs) {
    if (this.finished) return false
    const channels = inputs[0]
    if (!channels?.length) return true
    const count = Math.min(channels[0].length, this.limit - this.frames)
    for (let frame = 0; frame < count; frame++) {
      let mono = 0
      for (const channel of channels) mono += channel[frame]
      this.buffer[this.position++] = mono / channels.length
      this.frames++
      if (this.position === this.batchSize) this.flush()
    }
    if (this.frames >= this.limit) this.finish('limit')
    return !this.finished
  }
}

registerProcessor('pcm-capture', PcmCaptureProcessor)
