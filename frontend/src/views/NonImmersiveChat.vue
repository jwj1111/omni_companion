<template>
  <div class="non-immersive-chat">
    <!-- 模式切换 Tab -->
    <ChatModeTabs active="non-immersive" />

    <!-- 消息列表 -->
    <div class="message-list" ref="messageListRef" aria-live="polite" aria-label="消息列表">
      <div v-if="messages.length === 0" class="empty-state">
        <p class="text-muted">输入消息开始对话</p>
      </div>
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="message-item"
        :class="msg.role"
      >
        <div class="message-avatar" :class="msg.role">
          {{ msg.role === 'user' ? 'U' : 'A' }}
        </div>
        <div class="message-bubble">
          <div class="message-text">{{ msg.content }}</div>
          <div v-if="msg.imageData" class="message-attachment">
            <img :src="msg.imageData" alt="已附带的画面" />
            <span>已附带画面</span>
          </div>
          <!-- 音频播放按钮 -->
          <button
            v-if="msg.audioData && !msg.isStreaming"
            type="button"
            class="btn-play-audio"
            aria-label="播放这条语音回复"
            @click="handlePlayAudio(msg.audioData)"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 010 7.07M19.07 4.93a10 10 0 010 14.14"/></svg>
            播放语音
          </button>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="input-area">
      <!-- 附件预览 -->
      <div v-if="attachedImage" class="attachment-preview">
        <img :src="'data:image/jpeg;base64,' + attachedImage" alt="待发送的图片附件" />
        <button type="button" class="btn-remove-attachment" @click="attachedImage = null" aria-label="移除图片附件">×</button>
      </div>
      <div class="input-row">
        <button type="button" class="btn-attach" @click="attachScreenshot" aria-label="添加图片附件" title="添加图片附件">
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
          type="button"
          class="btn-send"
          :disabled="!canSend"
          @click="handleSend"
          aria-label="发送消息"
          title="发送消息"
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
import { getSettings } from '@/services/api'
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

  let outputAudio = true
  try {
    const settingsResp = await getSettings()
    outputAudio = settingsResp?.settings?.output?.modalities?.includes('audio') ?? true
  } catch (e) {
    outputAudio = true
  }
  await chatStore.send(content, outputAudio)
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
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: var(--type-label);
  line-height: var(--leading-body);
}

.message-item {
  display: flex;
  gap: 10px;
  max-width: 88%;
  animation: msg-in 0.2s ease-out;
}

@keyframes msg-in {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.message-item.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-avatar {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--type-caption);
  font-weight: 700;
  line-height: 1;
  letter-spacing: var(--tracking-label);
  flex-shrink: 0;
}

.message-avatar.user {
  background: var(--accent);
  color: var(--text-on-accent);
}

.message-avatar.assistant {
  background: var(--bg-card);
  color: var(--accent-light);
  border: 1px solid var(--border);
}

.message-bubble {
  padding: 10px 14px;
  font-size: var(--type-chat);
  line-height: var(--leading-chat);
  font-weight: 400;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-item.user .message-bubble {
  background: var(--bg-card);
  color: var(--text-primary);
  border-radius: var(--radius-md) var(--radius-md) var(--radius-xs) var(--radius-md);
  border: 1px solid var(--border);
}

.message-item.assistant .message-bubble {
  background: transparent;
  color: var(--text-primary);
  border-radius: var(--radius-md) var(--radius-md) var(--radius-md) var(--radius-xs);
  border-left: 2px solid var(--accent-subtle);
  padding-left: 12px;
}

.message-attachment {
  margin-top: 8px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 4px 8px 4px 4px;
  border-radius: var(--radius-sm);
  background: var(--bg-deepest);
  border: 1px solid var(--border-light);
  color: var(--text-secondary);
  font-size: var(--type-caption);
  line-height: 1;
  letter-spacing: var(--tracking-label);
}

.message-attachment img {
  width: 34px;
  height: 24px;
  object-fit: cover;
  border-radius: var(--radius-xs);
  border: 1px solid var(--border);
  background: var(--bg-card);
}

.btn-play-audio {
  margin-top: 8px;
  padding: 4px 10px;
  font-size: var(--type-caption);
  line-height: 1;
  letter-spacing: var(--tracking-label);
  border-radius: var(--radius-xs);
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.btn-play-audio:hover {
  border-color: var(--accent);
  color: var(--accent-light);
  background: var(--accent-subtle);
}

/* 输入区域 */
.input-area {
  padding: 10px 16px 12px;
  border-top: 1px solid var(--border);
  background: var(--bg-deepest);
}

.attachment-preview {
  margin-bottom: 8px;
  position: relative;
  display: inline-block;
}

.attachment-preview img {
  max-height: 60px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
}

.btn-remove-attachment {
  position: absolute;
  top: -5px;
  right: -5px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--error);
  color: var(--text-on-accent);
  font-size: var(--type-label);
  font-weight: 600;
  line-height: 1;
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
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-primary);
  font-size: var(--type-chat);
  line-height: var(--leading-body);
}

.btn-attach,
.btn-send {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  transition: all var(--transition-fast);
}

.btn-attach:hover {
  color: var(--text-secondary);
  background: var(--bg-hover);
}

.btn-send {
  background: var(--accent);
  color: var(--text-on-accent);
}

.btn-send:hover:not(:disabled) {
  background: var(--accent-light);
}

.btn-send:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.btn-send:active:not(:disabled),
.btn-attach:active,
.btn-play-audio:active {
  transform: translateY(1px);
}
</style>
