import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import { sendChatMessage, clearChatHistory } from '@/services/api'
import { PcmStreamPlayer, stopAllAudio } from '@/services/audio'

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

    // 添加用户消息到列表
    const userMsg = reactive({
      id: Date.now(),
      role: 'user',
      content: typeof content === 'string' ? content : '[多模态消息]',
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

    // 在用户点击上下文中初始化流式播放器（官方方式2：边收边播）
    if (outputAudio) {
      currentPlayer = new PcmStreamPlayer()
      currentPlayer.init()
    }

    try {
      await sendChatMessage(content, outputAudio, (chunk) => {
        if (chunk.type === 'text') {
          assistantMsg.content += chunk.data
        } else if (chunk.type === 'audio') {
          assistantMsg.audioData += chunk.data
          // 官方方式2：每收到一个 chunk 立即解码播放
          if (currentPlayer) {
            currentPlayer.write(chunk.data)
          }
        } else if (chunk.type === 'done') {
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
