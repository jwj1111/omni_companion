import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import { sendChatMessage, clearChatHistory } from '@/services/api'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const isLoading = ref(false)

  /**
   * 发送消息
   * @param {string|Array} content - 文本或多模态
   * @param {boolean} outputAudio - 是否要音频回复
   */
  async function send(content, outputAudio = false) {
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

    try {
      await sendChatMessage(content, outputAudio, (chunk) => {
        if (chunk.type === 'text') {
          assistantMsg.content += chunk.data
        } else if (chunk.type === 'audio') {
          assistantMsg.audioData += chunk.data
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

  return { messages, isLoading, send, clear }
})
