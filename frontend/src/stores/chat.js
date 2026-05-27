import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * 非沉浸模式聊天状态
 */
export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const isLoading = ref(false)

  function addMessage(role, content) {
    // TODO
  }

  function clearMessages() {
    messages.value = []
  }

  return { messages, isLoading, addMessage, clearMessages }
})

/**
 * 沉浸模式状态
 */
export const useRealtimeStore = defineStore('realtime', () => {
  const isConnected = ref(false)
  const isListening = ref(false)
  const transcripts = ref([])  // 对话转写记录

  function connect() {
    // TODO
  }

  function disconnect() {
    // TODO
  }

  return { isConnected, isListening, transcripts, connect, disconnect }
})
