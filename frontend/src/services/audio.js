/**
 * 音频服务
 * - 麦克风采集 → 16kHz 16bit mono PCM → Base64
 * - 模型音频播放（24kHz 16bit mono PCM）
 */

/**
 * 麦克风采集器
 */
export class MicRecorder {
  constructor() {
    this.stream = null
    this.audioContext = null
    this.processor = null
    this.isRecording = false
    this.onAudioData = null // (base64PcmChunk) => void
    this.analyser = null
  }

  /**
   * 开始采集
   * @param {function} onAudioData - 每帧回调 (base64String) => void
   */
  async start(onAudioData) {
    this.onAudioData = onAudioData
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      }
    })

    this.audioContext = new AudioContext({ sampleRate: 16000 })
    const source = this.audioContext.createMediaStreamSource(this.stream)

    // 用于音量检测
    this.analyser = this.audioContext.createAnalyser()
    this.analyser.fftSize = 256
    source.connect(this.analyser)

    // ScriptProcessor（兼容性好）采集 PCM
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1)
    this.processor.onaudioprocess = (e) => {
      if (!this.isRecording) return
      const float32 = e.inputBuffer.getChannelData(0)
      const pcm16 = float32ToInt16(float32)
      const b64 = arrayBufferToBase64(pcm16.buffer)
      if (this.onAudioData) this.onAudioData(b64)
    }

    source.connect(this.processor)
    this.processor.connect(this.audioContext.destination)
    this.isRecording = true
  }

  /**
   * 停止采集
   */
  stop() {
    this.isRecording = false
    if (this.processor) {
      this.processor.disconnect()
      this.processor = null
    }
    if (this.audioContext) {
      this.audioContext.close()
      this.audioContext = null
    }
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop())
      this.stream = null
    }
  }

  /**
   * 获取当前音量（0~1）
   */
  getVolume() {
    if (!this.analyser) return 0
    const data = new Uint8Array(this.analyser.frequencyBinCount)
    this.analyser.getByteFrequencyData(data)
    const sum = data.reduce((a, b) => a + b, 0)
    return sum / (data.length * 255)
  }
}

const PCM_SAMPLE_RATE = 24000
const WORKLET_URL = '/audio-worklet/pcm-player-processor.js'

/**
 * PCM 流式播放器（24kHz 16bit mono）
 * 使用 AudioWorklet 环形缓冲在音频线程连续拉取样本，避免每个 chunk 单独排程导致的断续感。
 */
export class PcmStreamPlayer {
  constructor({ sampleRate = PCM_SAMPLE_RATE, prebufferMs = 320 } = {}) {
    this.sampleRate = sampleRate
    this.prebufferMs = prebufferMs
    this.audioContext = null
    this.node = null
    this.readyPromise = null
    this.pendingSamples = []
    this.fallbackSources = []
    this.base64Remainder = ''
    this.byteRemainder = null
    this.fallbackNextStartTime = 0
    this.useFallback = false
    this.stopped = false
  }

  /**
   * 初始化（必须尽量在用户交互事件中调用）
   */
  init() {
    if (this.stopped) return this.readyPromise

    if (!this.audioContext) {
      this.audioContext = new AudioContext({ sampleRate: this.sampleRate })
      this.readyPromise = this.setupWorklet()
    }

    if (this.audioContext.state === 'suspended') {
      this.audioContext.resume()
    }

    registerStreamPlayer(this)
    return this.readyPromise
  }

  async setupWorklet() {
    if (!this.audioContext?.audioWorklet) {
      this.useFallback = true
      return
    }

    try {
      await this.audioContext.audioWorklet.addModule(WORKLET_URL)
      if (this.stopped || !this.audioContext) return

      this.node = new AudioWorkletNode(this.audioContext, 'pcm-player-processor', {
        numberOfInputs: 0,
        numberOfOutputs: 1,
        outputChannelCount: [1],
      })
      this.node.connect(this.audioContext.destination)
      this.node.port.postMessage({
        type: 'config',
        prebufferFrames: Math.round(this.audioContext.sampleRate * this.prebufferMs / 1000),
      })

      for (const samples of this.pendingSamples) {
        this.postSamples(samples)
      }
      this.pendingSamples = []
    } catch (e) {
      this.useFallback = true
      for (const samples of this.pendingSamples) {
        this.playFallback(samples)
      }
      this.pendingSamples = []
    }
  }

  /**
   * 写入一个 audio chunk。
   * @param {string} audioB64 - Base64 编码的 24kHz 16bit mono PCM 片段
   */
  write(audioB64) {
    if (!audioB64 || this.stopped) return
    if (!this.audioContext) this.init()

    const samples = this.decodePcmChunk(audioB64, false)
    if (!samples.length) return

    const outputSamples = this.resampleForContext(samples)
    if (this.useFallback) {
      this.playFallback(outputSamples)
    } else if (this.node) {
      this.postSamples(outputSamples)
    } else {
      this.pendingSamples.push(outputSamples)
    }
  }

  /**
   * 解码流末尾可能残留的 Base64/PCM 字节。
   */
  finish() {
    if (this.stopped) return
    const samples = this.decodePcmChunk('', true)
    if (!samples.length) return

    const outputSamples = this.resampleForContext(samples)
    if (this.useFallback) {
      this.playFallback(outputSamples)
    } else if (this.node) {
      this.postSamples(outputSamples)
    } else {
      this.pendingSamples.push(outputSamples)
    }
  }

  decodePcmChunk(audioB64, final) {
    const cleaned = (audioB64 || '').replace(/\s/g, '')
    let combined = this.base64Remainder + cleaned

    if (!combined) return new Float32Array(0)

    let decodeLength = combined.length - (combined.length % 4)
    if (final && decodeLength !== combined.length) {
      combined = combined.padEnd(Math.ceil(combined.length / 4) * 4, '=')
      decodeLength = combined.length
    }

    if (decodeLength <= 0) {
      this.base64Remainder = combined
      return new Float32Array(0)
    }

    const part = combined.slice(0, decodeLength)
    this.base64Remainder = final ? '' : combined.slice(decodeLength)

    let bytes
    try {
      bytes = base64ToUint8Array(part)
    } catch (e) {
      this.base64Remainder = combined
      return new Float32Array(0)
    }

    if (this.byteRemainder !== null) {
      const merged = new Uint8Array(bytes.length + 1)
      merged[0] = this.byteRemainder
      merged.set(bytes, 1)
      bytes = merged
      this.byteRemainder = null
    }

    if (bytes.length % 2 === 1) {
      this.byteRemainder = bytes[bytes.length - 1]
      bytes = bytes.slice(0, -1)
    }

    return decodeInt16PcmBytes(bytes)
  }

  resampleForContext(samples) {
    const contextRate = this.audioContext?.sampleRate || this.sampleRate
    if (contextRate === this.sampleRate) return samples
    return resampleLinear(samples, this.sampleRate, contextRate)
  }

  postSamples(samples) {
    const transferable = samples.buffer.slice(samples.byteOffset, samples.byteOffset + samples.byteLength)
    this.node.port.postMessage({ type: 'audio', samples: transferable }, [transferable])
  }

  playFallback(samples) {
    if (!samples.length || !this.audioContext) return

    const buffer = createAudioBufferFromSamples(this.audioContext, samples)
    const source = this.audioContext.createBufferSource()
    source.buffer = buffer
    source.connect(this.audioContext.destination)

    const now = this.audioContext.currentTime
    if (this.fallbackNextStartTime < now + this.prebufferMs / 1000) {
      this.fallbackNextStartTime = now + this.prebufferMs / 1000
    }
    source.onended = () => {
      const index = this.fallbackSources.indexOf(source)
      if (index >= 0) this.fallbackSources.splice(index, 1)
    }
    this.fallbackSources.push(source)
    source.start(this.fallbackNextStartTime)
    this.fallbackNextStartTime += buffer.duration
  }

  /**
   * 清空播放缓冲（打断时使用），播放器仍可继续复用。
   */
  flush() {
    this.base64Remainder = ''
    this.byteRemainder = null
    this.pendingSamples = []
    for (const source of this.fallbackSources) {
      try { source.stop() } catch (e) {}
    }
    this.fallbackSources = []
    this.fallbackNextStartTime = this.audioContext?.currentTime || 0
    if (this.node) {
      this.node.port.postMessage({ type: 'flush' })
    }
  }

  /**
   * 停止播放并释放资源（彻底销毁，不可复用）。
   */
  stop() {
    this.stopped = true
    unregisterStreamPlayer(this)
    this.pendingSamples = []
    for (const source of this.fallbackSources) {
      try { source.stop() } catch (e) {}
    }
    this.fallbackSources = []
    this.base64Remainder = ''
    this.byteRemainder = null
    if (this.node) {
      this.node.disconnect()
      this.node = null
    }
    if (this.audioContext) {
      this.audioContext.close()
      this.audioContext = null
    }
    this.fallbackNextStartTime = 0
  }
}

// 保留旧名兼容沉浸模式
export const AudioPlayer = PcmStreamPlayer

// ==================== 全局播放管理器 ====================

// 全局唯一，确保同时只有一个音频在播放
let _activeContext = null
let _activeSource = null
let _activeStreamPlayer = null  // 当前活跃的流式播放器

/**
 * 注册当前活跃的流式播放器（内部使用）
 */
function registerStreamPlayer(player) {
  _activeStreamPlayer = player
}

/**
 * 注销流式播放器（内部使用）
 */
function unregisterStreamPlayer(player) {
  if (_activeStreamPlayer === player) {
    _activeStreamPlayer = null
  }
}

/**
 * 停止当前正在播放的任何音频（切换模式或新播放时调用）
 */
export function stopAllAudio() {
  // 停掉流式播放器
  if (_activeStreamPlayer) {
    _activeStreamPlayer.stop()
    _activeStreamPlayer = null
  }
  // 停掉一次性播放
  if (_activeSource) {
    try { _activeSource.stop() } catch (e) {}
    _activeSource = null
  }
  if (_activeContext) {
    try { _activeContext.close() } catch (e) {}
    _activeContext = null
  }
}

/**
 * 一次性播放完整的 PCM 音频（24kHz 16bit mono）
 * 会先停掉任何正在播放的音频，确保不冲突
 * @param {string} audioB64 - 完整的 Base64 编码 PCM 数据
 */
export function playPcmAudio(audioB64) {
  if (!audioB64) return

  stopAllAudio()

  const sourceSamples = decodeInt16PcmBytes(base64ToUint8Array(audioB64))
  if (!sourceSamples.length) return

  const context = new AudioContext({ sampleRate: PCM_SAMPLE_RATE })
  if (context.state === 'suspended') {
    context.resume()
  }

  const outputSamples = context.sampleRate === PCM_SAMPLE_RATE
    ? sourceSamples
    : resampleLinear(sourceSamples, PCM_SAMPLE_RATE, context.sampleRate)
  const buffer = createAudioBufferFromSamples(context, outputSamples)
  const source = context.createBufferSource()

  _activeContext = context
  _activeSource = source

  source.buffer = buffer
  source.connect(context.destination)
  source.start()

  source.onended = () => {
    if (_activeSource === source) {
      _activeSource = null
    }
    if (_activeContext === context) {
      _activeContext = null
      context.close()
    }
  }
}

// ==================== 工具函数 ====================

function float32ToInt16(float32Array) {
  const int16 = new Int16Array(float32Array.length)
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]))
    int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
  }
  return int16
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}

function base64ToUint8Array(base64) {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes
}

function decodeInt16PcmBytes(bytes) {
  const samples = bytes.byteLength / 2
  if (samples === 0) return new Float32Array(0)

  const output = new Float32Array(samples)
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  for (let i = 0; i < samples; i++) {
    output[i] = view.getInt16(i * 2, true) / 32768
  }
  return output
}

function createAudioBufferFromSamples(audioContext, samples) {
  const buffer = audioContext.createBuffer(1, samples.length, audioContext.sampleRate)
  buffer.getChannelData(0).set(samples)
  return buffer
}

function resampleLinear(input, fromRate, toRate) {
  if (!input.length || fromRate === toRate) return input

  const ratio = toRate / fromRate
  const outputLength = Math.max(1, Math.round(input.length * ratio))
  const output = new Float32Array(outputLength)

  for (let i = 0; i < outputLength; i++) {
    const sourceIndex = i / ratio
    const index = Math.floor(sourceIndex)
    const fraction = sourceIndex - index
    const current = input[index] || 0
    const next = input[Math.min(index + 1, input.length - 1)] || current
    output[i] = current + (next - current) * fraction
  }

  return output
}

