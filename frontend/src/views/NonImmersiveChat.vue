<template>
  <div class="non-immersive-chat">
    <!-- 模式切换 Tab -->
    <ChatModeTabs active="non-immersive" />

    <!-- 消息列表 -->
    <div class="message-list" ref="messageListRef">
      <div v-if="messages.length === 0" class="empty-state">
        <p class="text-muted">开始聊天吧</p>
      </div>
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="message-item"
        :class="msg.role"
      >
        <div class="message-avatar">
          {{ msg.role === 'user' ? '🎮' : '💜' }}
        </div>
        <div class="message-bubble">
          <div class="message-text">{{ msg.content }}<span v-if="msg.isStreaming" class="cursor-blink">|</span></div>
          <!-- 音频播放按钮 -->
          <button
            v-if="msg.audioData && !msg.isStreaming"
            class="btn-play-audio"
            @click="handlePlayAudio(msg.audioData)"
          >
            🔊 播放语音
          </button>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="input-area">
      <!-- 附件预览 -->
      <div v-if="attachedImage" class="attachment-preview">
        <img :src="'data:image/jpeg;base64,' + attachedImage" alt="附件" />
        <button class="btn-remove-attachment" @click="attachedImage = null">×</button>
      </div>
      <div class="input-row">
        <button class="btn-attach" @click="attachScreenshot" title="附带截图">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/>
          </svg>
        </button>
        <textarea
          ref="inputRef"
          v-model="inputText"
          placeholder="输入消息..."
          rows="1"
          @keydown.enter.exact.prevent="handleSend"
          @input="autoResize"
        ></textarea>
        <button
          class="btn-send"
          :disabled="!canSend"
          @click="handleSend"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, inject } from 'vue'
import { useChatStore } from '@/stores/chat'
import { playPcmAudio } from '@/services/audio'
import ChatModeTabs from '@/components/ChatModeTabs.vue'

const chatStore = useChatStore()
const messages = computed(() => chatStore.messages)

function handlePlayAudio(audioB64) {
  chatStore.stopCurrentAudio()
  playPcmAudio(audioB64)
}

const screenMonitor = inject('screenMonitor')

const inputText = ref('')
const attachedImage = ref(null)
const messageListRef = ref(null)
const inputRef = ref(null)

const canSend = computed(() => {
  return (inputText.value.trim() || attachedImage.value) && !chatStore.isLoading
})

async function handleSend() {
  if (!canSend.value) return

  let content
  let imageB64 = null

  if (attachedImage.value) {
    // 用户手动附了图 → 优先用附件（覆盖屏幕监控截图）
    imageB64 = attachedImage.value
  } else if (screenMonitor.value?.isCapturing) {
    // 屏幕监控开着 + 没手动附图 → 自动取当前帧
    imageB64 = screenMonitor.value.captureFrame()
  }

  if (imageB64) {
    content = [
      { type: 'text', text: inputText.value.trim() || '请描述这张图片' },
      { type: 'image_url', image_url: { url: `data:image/jpeg;base64,${imageB64}` } },
    ]
  } else {
    content = inputText.value.trim()
  }

  inputText.value = ''
  attachedImage.value = null
  resetTextareaHeight()

  await chatStore.send(content, true)
  scrollToBottom()
}

function attachScreenshot() {
  // 点击按钮 → 弹文件选择器上传自定义图片
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.onchange = (e) => {
    const file = e.target.files[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      attachedImage.value = reader.result.split(',')[1]
    }
    reader.readAsDataURL(file)
  }
  input.click()
}

function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

function autoResize() {
  const el = inputRef.value
  if (el) {
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }
}

function resetTextareaHeight() {
  nextTick(() => {
    if (inputRef.value) {
      inputRef.value.style.height = 'auto'
    }
  })
}

// 自动滚动
watch(() => chatStore.messages.length, scrollToBottom)
</script>

<style scoped>
.non-immersive-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.message-item {
  display: flex;
  gap: 10px;
  max-width: 85%;
}

.message-item.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.message-bubble {
  padding: 10px 14px;
  border-radius: var(--radius-lg);
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-item.user .message-bubble {
  background: var(--accent-dark);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message-item.assistant .message-bubble {
  background: var(--bg-card);
  color: var(--text-primary);
  border-bottom-left-radius: 4px;
}

.cursor-blink {
  animation: blink 1s infinite;
  color: var(--accent-light);
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.btn-play-audio {
  margin-top: 8px;
  padding: 4px 10px;
  font-size: 12px;
  border-radius: var(--radius-sm);
  background: var(--bg-hover);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.btn-play-audio:hover {
  background: var(--accent-dark);
  color: #fff;
}

/* 输入区域 */
.input-area {
  padding: 12px 16px;
  border-top: 1px solid var(--border);
  background: var(--bg-panel);
}

.attachment-preview {
  margin-bottom: 8px;
  position: relative;
  display: inline-block;
}

.attachment-preview img {
  max-height: 80px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
}

.btn-remove-attachment {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--error);
  color: #fff;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.input-row textarea {
  flex: 1;
  min-height: 36px;
  max-height: 120px;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-primary);
  line-height: 1.4;
  transition: border-color var(--transition-fast);
}

.input-row textarea:focus {
  border-color: var(--accent);
}

.btn-attach,
.btn-send {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.btn-attach:hover {
  background: var(--bg-hover);
  color: var(--accent-light);
}

.btn-send {
  background: var(--accent);
  color: #fff;
}

.btn-send:hover:not(:disabled) {
  background: var(--accent-light);
}

.btn-send:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
