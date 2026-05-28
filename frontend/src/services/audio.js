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

/**
 * PCM 流式播放器（24kHz 16bit mono）
 * 模仿 pyaudio 的 stream.write() 方式：
 * 每收到一个 chunk 就解码写入缓冲区，底层连续播放
 */
export class PcmStreamPlayer {
  constructor() {
    this.audioContext = null
    this.nextStartTime = 0
    this.stopped = false
  }

  /**
   * 初始化（必须在用户交互事件中调用）
   */
  init() {
    if (!this.audioContext) {
      this.audioContext = new AudioContext({ sampleRate: 24000 })
      this.nextStartTime = 0
    }
    if (this.audioContext.state === 'suspended') {
      this.audioContext.resume()
    }
    registerStreamPlayer(this)
  }

  /**
   * 写入一个 audio chunk 并立即排队播放
   * 等同于 pyaudio 的 stream.write(pcm_bytes)
   * @param {string} audioB64 - 单个 Base64 编码的 PCM chunk
   */
  write(audioB64) {
    if (!audioB64 || this.stopped) return
    if (!this.audioContext) this.init()

    const bytes = base64ToArrayBuffer(audioB64)
    const samples = bytes.byteLength / 2
    if (samples === 0) return

    // 解码 PCM → float32
    const buffer = this.audioContext.createBuffer(1, samples, 24000)
    const channelData = buffer.getChannelData(0)
    const view = new DataView(bytes)
    for (let i = 0; i < samples; i++) {
      channelData[i] = view.getInt16(i * 2, true) / 32768
    }

    // 排队播放（无缝衔接）
    const source = this.audioContext.createBufferSource()
    source.buffer = buffer
    source.connect(this.audioContext.destination)

    const now = this.audioContext.currentTime
    if (this.nextStartTime < now) {
      this.nextStartTime = now
    }
    source.start(this.nextStartTime)
    this.nextStartTime += buffer.duration
  }

  /**
   * 清空播放缓冲（打断时使用）
   * 关闭旧 context 以立刻静音，下次 write 时自动重新初始化
   */
  flush() {
    unregisterStreamPlayer(this)
    if (this.audioContext) {
      this.audioContext.close()
      this.audioContext = null
    }
    this.nextStartTime = 0
    // 注意：不设 stopped=true，播放器仍可继续使用
  }

  /**
   * 停止播放并释放资源（彻底销毁，不可复用）
   */
  stop() {
    this.stopped = true
    unregisterStreamPlayer(this)
    if (this.audioContext) {
      this.audioContext.close()
      this.audioContext = null
    }
    this.nextStartTime = 0
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

  // 停掉之前的播放
  stopAllAudio()

  const bytes = base64ToArrayBuffer(audioB64)
  const samples = bytes.byteLength / 2
  if (samples === 0) return

  _activeContext = new AudioContext({ sampleRate: 24000 })
  if (_activeContext.state === 'suspended') {
    _activeContext.resume()
  }

  const buffer = _activeContext.createBuffer(1, samples, 24000)
  const channelData = buffer.getChannelData(0)
  const view = new DataView(bytes)

  for (let i = 0; i < samples; i++) {
    channelData[i] = view.getInt16(i * 2, true) / 32768
  }

  _activeSource = _activeContext.createBufferSource()
  _activeSource.buffer = buffer
  _activeSource.connect(_activeContext.destination)
  _activeSource.start()

  _activeSource.onended = () => {
    _activeSource = null
    if (_activeContext) {
      _activeContext.close()
      _activeContext = null
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

function base64ToArrayBuffer(base64) {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes.buffer
}
