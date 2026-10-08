import { afterEach, describe, expect, it, vi } from 'vitest'
import { encodePcm16Wav, encodeWav, MicrophoneRecorder, resampleMono } from './voice'

afterEach(() => { vi.unstubAllGlobals() })

describe('WAV encoder and browser-resampler contract', () => {
  it('writes actual signed PCM samples and an exact mono 16kHz WAV header', () => {
    const samples = new Float32Array(16_000)
    samples.set([-2, -.5, 0, .5, 2])
    const buffer = encodePcm16Wav(samples)
    const header = new DataView(buffer)
    expect(buffer.byteLength).toBe(32_044)
    expect(header.getUint32(4, true)).toBe(buffer.byteLength - 8)
    expect(header.getUint16(20, true)).toBe(1)
    expect(header.getUint16(22, true)).toBe(1)
    expect(header.getUint32(24, true)).toBe(16_000)
    expect(header.getUint32(28, true)).toBe(32_000)
    expect(header.getUint16(34, true)).toBe(16)
    expect(header.getUint32(40, true)).toBe(32_000)
    expect(header.getInt16(44, true)).toBe(-32_768)
    expect(header.getInt16(46, true)).toBe(-16_384)
    expect(header.getInt16(52, true)).toBe(32_767)
  })

  it.each([44_100, 48_000])('renders %iHz input into a 16000-frame mono buffer without changing duration', async (rate) => {
    const calls: number[][] = []
    class OfflineContextDouble {
      destination = {}
      constructor(channels: number, length: number, sampleRate: number) { calls.push([channels, length, sampleRate]) }
      createBuffer(channels: number, length: number, sampleRate: number) {
        calls.push([channels, length, sampleRate])
        return { getChannelData: () => new Float32Array(length) }
      }
      createBufferSource() { return { buffer: null, connect: vi.fn(), start: vi.fn(), disconnect: vi.fn() } }
      async startRendering() { return { getChannelData: () => new Float32Array(16_000).fill(.25) } }
    }
    vi.stubGlobal('OfflineAudioContext', OfflineContextDouble)
    const samples = await resampleMono(new Float32Array(rate).fill(.25), rate)
    expect(calls).toEqual([[1,16_000,16_000],[1,rate,rate]])
    expect(samples.length / 16_000).toBe(1)
    const wav = new DataView(encodePcm16Wav(samples))
    expect(wav.getUint32(40,true)).toBe(32_000)
  })

  it('rejects short, too long, and nonfinite audio before upload', async () => {
    await expect(encodeWav(new Float32Array(15_999),16_000)).rejects.toThrow('1 đến 15')
    await expect(encodeWav(new Float32Array(240_001),16_000)).rejects.toThrow('1 đến 15')
    const bad = new Float32Array(16_000)
    bad[0] = NaN
    await expect(encodeWav(bad,16_000)).rejects.toThrow('không hợp lệ')
  })

  it('accepts 15 seconds and exports a WAV File rather than renamed WebM', async () => {
    const file = await encodeWav(new Float32Array(240_000),16_000)
    expect(file.type).toBe('audio/wav')
    expect(file.size).toBe(480_044)
    expect(file.name).toBe('ghi-am.wav')
  })

  it('stops late microphone permission streams after cancellation', async () => {
    let allow!: (stream: unknown) => void
    const stop = vi.fn()
    const getUserMedia = vi.fn().mockImplementation(() => new Promise(resolve => { allow = resolve }))
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } })
    vi.stubGlobal('AudioContext', class {})
    vi.stubGlobal('AudioWorkletNode', class {})
    const recorder = new MicrophoneRecorder()
    const start = recorder.start().catch(error => error)
    await recorder.cancel()
    allow({ getTracks: () => [{ stop }] })
    expect(await start).toMatchObject({ name: 'AbortError' })
    expect(stop).toHaveBeenCalled()
    expect(recorder.recording).toBe(false)
  })
})
