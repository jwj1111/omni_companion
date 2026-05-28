/**
 * 沉浸模式 - WebSocket 实时通信服务
 */
import { getSessionId } from './session'

const WS_URL = 'ws://localhost:8000/api/realtime/ws'

export class RealtimeService {
  constructor() {
    this.ws = null
    this.isConnected = false
    this.onEvent = null // 外部回调：(event) => void
  }

  /**
   * 连接后端 WebSocket
   * @param {function} onEvent - 事件回调
   */
  connect(onEvent) {
    this.onEvent = onEvent
    const url = `${WS_URL}?session_id=${encodeURIComponent(getSessionId())}`
    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      this.isConnected = true
      // 发送 start 指令，后端会连接阿里云
      this.ws.send(JSON.stringify({ type: 'control', action: 'start' }))
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (this.onEvent) this.onEvent(data)
      } catch (e) {
        // 忽略
      }
    }

    this.ws.onclose = (event) => {
      this.isConnected = false
      if (this.onEvent) {
        // 如果服务端带了 reason，先作为 error 事件通知
        if (event.reason) {
          this.onEvent({ type: 'error', message: event.reason })
        }
        this.onEvent({ type: 'status', event: 'disconnected' })
      }
    }

    this.ws.onerror = () => {
      this.isConnected = false
    }
  }

  /**
   * 断开连接
   */
  disconnect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'control', action: 'stop' }))
      this.ws.close()
    }
    this.ws = null
    this.isConnected = false
  }

  /**
   * 发送音频帧（Base64 PCM）
   */
  sendAudio(audioB64) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'audio', data: audioB64 }))
    }
  }

  /**
   * 发送截屏帧（Base64 JPEG）
   */
  sendScreenshot(imageB64) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'screenshot', data: imageB64 }))
    }
  }
}
