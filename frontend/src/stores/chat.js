import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import { sendChatMessage, clearChatHistory } from '@/services/api'
import { PcmStreamPlayer, stopAllAudio } from '@/services/audio'

function getUserMessageText(content) {
  if (typeof content === 'string') return content
  const textPart = content.find(item => item.type === 'text')
  return textPart?.text || '请描述这张图片'
}

function getUserMessageImage(content) {
  if (!Array.isArray(content)) return ''
  const imagePart = content.find(item => item.type === 'image_url')
  const imageUrl = imagePart?.image_url?.url || ''
  return imageUrl.startsWith('data:image/') ? imageUrl : ''
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const isLoading = ref(false)
  let currentPlayer = null

  /**
   * 发送消息
   * @param {string|Array} content - 文本或多模态
   * @param {boolean} outputAudio - 是否要音频回复
   */
  async function send(content, outputAudio = false) {
    // 停掉所有正在播放的音频
    if (currentPlayer) {
      currentPlayer.stop()
      currentPlayer = null
    }
    stopAllAudio()  // 停掉 playPcmAudio 的一次性播放

    // 添加用户消息到列表。多模态消息展示用户原话，并用紧凑附件标记提示已带图。
    const userMsg = reactive({
      id: Date.now(),
      role: 'user',
      content: getUserMessageText(content),
      imageData: getUserMessageImage(content),
      rawContent: content,
      timestamp: new Date(),
    })
    messages.value.push(userMsg)

    // 准备助手消息占位
    const assistantMsg = reactive({
      id: Date.now() + 1,
      role: 'assistant',
      content: '',
      audioData: '',
      timestamp: new Date(),
      isStreaming: true,
    })
    messages.value.push(assistantMsg)
    isLoading.value = true

    // 在用户点击上下文中初始化流式播放器。非实时模式多留一点启动缓冲，优先保证自动播放连续性。
    if (outputAudio) {
      currentPlayer = new PcmStreamPlayer({ prebufferMs: 450 })
      currentPlayer.init()
    }

    try {
      await sendChatMessage(content, outputAudio, (chunk) => {
        if (chunk.type === 'text') {
          assistantMsg.content += chunk.data
        } else if (chunk.type === 'audio') {
          assistantMsg.audioData += chunk.data
          // 自动播放走 AudioWorklet 环形缓冲，减少 chunk 拼接导致的断续感。
          if (currentPlayer) {
            currentPlayer.write(chunk.data)
          }
        } else if (chunk.type === 'done') {
          if (currentPlayer) currentPlayer.finish()
          assistantMsg.isStreaming = false
        } else if (chunk.type === 'error') {
          assistantMsg.content += `\n[错误: ${chunk.data}]`
          assistantMsg.isStreaming = false
        }
      })
    } catch (e) {
      assistantMsg.content += `\n[请求失败: ${e.message}]`
      assistantMsg.isStreaming = false
    } finally {
      isLoading.value = false
    }
  }

  async function clear() {
    stopCurrentAudio()
    stopAllAudio()
    await clearChatHistory()
    messages.value = []
  }

  /**
   * 停止当前正在流式播放的音频
   */
  function stopCurrentAudio() {
    if (currentPlayer) {
      currentPlayer.stop()
      currentPlayer = null
    }
  }

  return { messages, isLoading, send, clear, stopCurrentAudio }
})
