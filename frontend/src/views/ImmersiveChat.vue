<template>
  <div class="immersive-chat">
    <!-- 模式切换 Tab -->
    <ChatModeTabs active="immersive" />

    <!-- 对话转写区域 -->
    <div class="transcript-area" ref="transcriptRef" aria-live="polite" aria-label="对话记录">
      <div v-if="transcripts.length === 0 && !isActive" class="empty-state">
        <p class="text-muted">准备好后，点击下方按钮开始</p>
      </div>
      <div
        v-for="(item, idx) in transcripts"
        :key="idx"
        class="transcript-item"
        :class="item.role"
      >
        <span class="transcript-role">{{ item.role === 'user' ? '你' : '助手' }}:</span>
        <span class="transcript-text">{{ item.text }}</span>
      </div>
    </div>

    <!-- 状态指示 -->
    <div class="status-indicator" v-if="isActive || statusText">
      <div class="volume-bar" v-if="isActive">
        <div class="volume-level" :style="{ width: volumePercent + '%' }"></div>
      </div>
      <span class="status-text">{{ statusText }}</span>
    </div>

    <!-- 控制区域 -->
    <div class="control-area">
      <button
        class="btn-mic"
        :class="{ active: isActive, disconnected: isDisconnected, connecting: isConnecting }"
        @click="toggleSession"
        :aria-label="isActive ? '停止语音' : (isDisconnected ? '重新连接' : '开始语音对话')"
      >
        <svg v-if="!isActive" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2M12 19v4M8 23h8"/>
        </svg>
        <svg v-else width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
          <rect x="6" y="6" width="12" height="12" rx="2"/>
        </svg>
      </button>
      <p class="control-hint text-muted">
        {{ isActive ? '停止' : (isDisconnected ? '重新连接' : '开始语音对话') }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onBeforeUnmount, inject } from 'vue'
import ChatModeTabs from '@/components/ChatModeTabs.vue'
import { RealtimeService } from '@/services/realtime'
import { MicRecorder, AudioPlayer, stopAllAudio } from '@/services/audio'
import { getSettings } from '@/services/api'

const screenMonitor = inject('screenMonitor')

const transcripts = ref([])
const isActive = ref(false)
const isDisconnected = ref(false)
const isConnecting = ref(false)  // 连接中，禁止重复操作
const statusText = ref('')
const volumePercent = ref(0)
const transcriptRef = ref(null)

let realtimeService = null
let micRecorder = null
let audioPlayer = null
let volumeInterval = null
let screenshotInterval = null
let screenshotPushActive = false  // 是否允许推送截图（仅用户说话时为 true）

// 当前语音轮次的转写状态。
// Realtime 事件可能出现“助手文本先于用户最终转写到达”，所以不能靠消息列表最后一项判断归属。
let waitingForUserFinal = false
let currentUserTranscript = null
let currentAssistantTranscript = null
let pendingAssistantText = ''
let pendingAssistantFinalText = ''

function toggleSession() {
  if (isConnecting.value) return  // 连接中，忽略点击
  if (isActive.value) {
    stopSession()
  } else {
    startSession()
  }
}

/**
 * 启动截屏推送定时器
 * 定时器启动后常驻，内部动态检测屏幕监控状态和 screenshotPushActive 标志
 * 支持中途开启/关闭屏幕监控
 */
async function startScreenshotPush() {
  if (screenshotInterval) return

  let intervalMs = 1000
  try {
    const settingsResp = await getSettings()
    intervalMs = settingsResp?.settings?.screen_capture?.interval_ms || 1000
  } catch (e) {
    intervalMs = 1000
  }

  screenshotInterval = setInterval(() => {
    if (!screenshotPushActive) return
    if (!screenMonitor.value?.isCapturing) return
    if (!realtimeService?.isConnected) return
    const frame = screenMonitor.value.captureFrame()
    if (frame) {
      realtimeService.sendScreenshot(frame)
    }
  }, intervalMs)
}

/**
 * 连接就绪后启动麦克风和截屏推送
 */
async function startMicAndScreenshot() {
  try {
    await micRecorder.start((audioB64) => {
      realtimeService.sendAudio(audioB64)
    })
    isActive.value = true
    statusText.value = '聆听中...'

    // 启动截屏推送定时器（实际推送由 screenshotPushActive 门控）
    await startScreenshotPush()

    // 音量检测
    volumeInterval = setInterval(() => {
      volumePercent.value = Math.round(micRecorder.getVolume() * 100)
    }, 100)
  } catch (e) {
    statusText.value = '麦克风权限被拒绝'
    realtimeService.disconnect()
  }
}

async function startSession() {
  // 停掉非沉浸模式可能还在播放的音频
  stopAllAudio()

  isConnecting.value = true
  isDisconnected.value = false
  statusText.value = '连接中...'

  realtimeService = new RealtimeService()
  micRecorder = new MicRecorder()
  audioPlayer = new AudioPlayer()
  audioPlayer.init()

  // 连接 WebSocket（等收到 connected 事件后再启动麦克风）
  realtimeService.connect(handleEvent)
}

function stopSession() {
  if (micRecorder) {
    micRecorder.stop()
    micRecorder = null
  }
  if (realtimeService) {
    realtimeService.disconnect()
    realtimeService = null
  }
  if (audioPlayer) {
    audioPlayer.stop()
    audioPlayer = null
  }
  if (volumeInterval) {
    clearInterval(volumeInterval)
    volumeInterval = null
  }
  if (screenshotInterval) {
    clearInterval(screenshotInterval)
    screenshotInterval = null
  }
  screenshotPushActive = false
  isConnecting.value = false
  isActive.value = false
  volumePercent.value = 0
  statusText.value = ''
  finalizeStreamingTranscript()
  resetTurnTranscriptState()
}

/**
 * 创建一条转写消息，并返回可持续更新的引用。
 */
function createTranscript(role, text = '', streaming = false) {
  const item = { role, text, streaming }
  transcripts.value.push(item)
  scrollToBottom()
  return item
}

function removeTranscript(item) {
  const index = transcripts.value.indexOf(item)
  if (index >= 0) {
    transcripts.value.splice(index, 1)
  }
}

function resetTurnTranscriptState() {
  waitingForUserFinal = false
  currentUserTranscript = null
  currentAssistantTranscript = null
  pendingAssistantText = ''
  pendingAssistantFinalText = ''
}

function startUserTurn() {
  finalizeStreamingTranscript()
  resetTurnTranscriptState()
  waitingForUserFinal = true
}

function updateUserTranscript(text, final) {
  const normalizedText = text || ''

  if (!currentUserTranscript && !normalizedText) {
    if (final) {
      waitingForUserFinal = false
      flushPendingAssistantTranscript()
    }
    return
  }

  if (!currentUserTranscript) {
    currentUserTranscript = createTranscript('user', normalizedText, !final)
  } else {
    currentUserTranscript.text = normalizedText
    currentUserTranscript.streaming = !final
    scrollToBottom()
  }

  if (final) {
    waitingForUserFinal = false
    flushPendingAssistantTranscript()
  }
}

function ensureUserTranscriptBeforeAssistant() {
  if (!currentUserTranscript) {
    currentUserTranscript = createTranscript('user', '正在识别...', true)
  }
}

function appendAssistantTranscript(deltaText) {
  if (!deltaText) return
  if (!currentAssistantTranscript) {
    currentAssistantTranscript = createTranscript('assistant', '', true)
  }
  currentAssistantTranscript.text += deltaText
  currentAssistantTranscript.streaming = true
  scrollToBottom()
}

function setAssistantTranscript(text, streaming) {
  if (!text) return
  if (!currentAssistantTranscript) {
    currentAssistantTranscript = createTranscript('assistant', text, streaming)
  } else {
    currentAssistantTranscript.text = text
    currentAssistantTranscript.streaming = streaming
    scrollToBottom()
  }
}

function flushPendingAssistantTranscript() {
  if (!pendingAssistantText && !pendingAssistantFinalText) return

  if (waitingForUserFinal) {
    ensureUserTranscriptBeforeAssistant()
  }

  if (pendingAssistantFinalText) {
    setAssistantTranscript(pendingAssistantFinalText, false)
  } else {
    appendAssistantTranscript(pendingAssistantText)
  }

  pendingAssistantText = ''
  pendingAssistantFinalText = ''
}

function handleUserTranscript(event) {
  updateUserTranscript(event.text || '', event.final)
}

function handleAssistantTranscript(event) {
  const text = event.text || ''

  if (event.final) {
    pendingAssistantFinalText = text || pendingAssistantText
    if (!waitingForUserFinal) {
      flushPendingAssistantTranscript()
    }
    return
  }

  if (waitingForUserFinal) {
    pendingAssistantText += text
    return
  }

  appendAssistantTranscript(text)
}

/**
 * 结束当前未完成的助手转写条目。
 * 打断时调用：如果内容太短（碎片），直接移除；否则标记为完成。
 */
function finalizeStreamingTranscript() {
  if (currentAssistantTranscript?.streaming) {
    const text = currentAssistantTranscript.text || ''
    if (text.trim().length <= 2) {
      removeTranscript(currentAssistantTranscript)
    } else {
      currentAssistantTranscript.streaming = false
    }
  }
  currentAssistantTranscript = null
  pendingAssistantText = ''
  pendingAssistantFinalText = ''
}

function completeAssistantResponse() {
  if (waitingForUserFinal && (pendingAssistantText || pendingAssistantFinalText)) {
    ensureUserTranscriptBeforeAssistant()
  }
  waitingForUserFinal = false
  flushPendingAssistantTranscript()
  if (currentAssistantTranscript) {
    currentAssistantTranscript.streaming = false
  }
  pendingAssistantText = ''
  pendingAssistantFinalText = ''
}

function handleEvent(event) {
  const { type } = event

  if (type === 'audio') {
    if (audioPlayer) audioPlayer.write(event.data)
  } else if (type === 'transcript') {
    if (event.role === 'user') {
      handleUserTranscript(event)
    } else if (event.role === 'assistant') {
      handleAssistantTranscript(event)
    }
  } else if (type === 'status') {
    if (event.event === 'connected') {
      // WebSocket 已连接且阿里云会话已建立，现在启动麦克风
      isConnecting.value = false
      startMicAndScreenshot()
    } else if (event.event === 'disconnected') {
      isActive.value = false
      isConnecting.value = false
      isDisconnected.value = true
      // 如果之前已经有错误提示（如"服务繁忙"），保留它；否则显示通用断连文案
      if (!statusText.value || statusText.value === '连接中...' || statusText.value === '聆听中...') {
        statusText.value = '连接已断开'
      }
      screenshotPushActive = false
      if (audioPlayer) {
        audioPlayer.stop()
        audioPlayer = null
      }
      if (screenshotInterval) {
        clearInterval(screenshotInterval)
        screenshotInterval = null
      }
      if (micRecorder) {
        micRecorder.stop()
        micRecorder = null
      }
      if (volumeInterval) {
        clearInterval(volumeInterval)
        volumeInterval = null
      }
      finalizeStreamingTranscript()
      resetTurnTranscriptState()
    } else if (event.event === 'input_audio_buffer.speech_started') {
      statusText.value = '说话中...'
      screenshotPushActive = true  // 用户开始说话，允许推截图
      if (audioPlayer) audioPlayer.flush()  // 打断：清空播放缓冲（不销毁）
      startUserTurn()
    } else if (event.event === 'input_audio_buffer.speech_stopped') {
      statusText.value = '思考中...'
      screenshotPushActive = false  // 用户停止说话，暂停推截图（防止 image before audio）
    } else if (event.event === 'response.done') {
      completeAssistantResponse()
      statusText.value = '聆听中...'
    }
  } else if (type === 'error') {
    isConnecting.value = false
    const msg = event.message || ''
    if (msg.includes('Too many requests') || msg.includes('throttled') || msg.includes('capacity')) {
      statusText.value = '服务繁忙，请稍后再试'
    } else if (msg.includes('401') || msg.includes('Unauthorized')) {
      statusText.value = 'API Key 无效，请检查设置'
    } else {
      statusText.value = `连接异常: ${msg.slice(0, 50)}`
    }
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (transcriptRef.value) {
      transcriptRef.value.scrollTop = transcriptRef.value.scrollHeight
    }
  })
}

onBeforeUnmount(() => {
  stopSession()
})
</script>

<style scoped>
.immersive-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.transcript-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 13px;
}

.transcript-item {
  font-size: 13px;
  line-height: 1.7;
  padding: 4px 0;
  animation: msg-in 0.15s ease-out;
}

@keyframes msg-in {
  from { opacity: 0; transform: translateY(3px); }
  to { opacity: 1; transform: translateY(0); }
}

.transcript-role {
  font-weight: 500;
  margin-right: 6px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.transcript-item.user .transcript-role {
  color: var(--text-secondary);
}

.transcript-item.assistant .transcript-role {
  color: var(--accent);
}

.transcript-text {
  color: var(--text-primary);
}

/* 状态指示 */
.status-indicator {
  padding: 6px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  border-top: 1px solid var(--border);
  background: var(--bg-deepest);
}

.volume-bar {
  width: 60px;
  height: 3px;
  background: var(--bg-card);
  border-radius: 2px;
  overflow: hidden;
}

.volume-level {
  height: 100%;
  background: var(--accent);
  border-radius: 2px;
  transition: width 0.1s linear;
}

.status-text {
  font-size: 11px;
  color: var(--text-muted);
  letter-spacing: 0.2px;
}

/* 控制区域 */
.control-area {
  padding: 24px 20px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  border-top: 1px solid var(--border);
  background: var(--bg-deepest);
}

.btn-mic {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--bg-card);
  border: 1.5px solid var(--border-light);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  transition: all var(--transition-normal);
}

.btn-mic:hover {
  border-color: var(--accent);
  color: var(--accent-light);
  background: var(--accent-subtle);
}

.btn-mic.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
  box-shadow: var(--shadow-accent);
}

.btn-mic.disconnected {
  border-color: var(--accent-dark);
  color: var(--accent-dark);
}

.btn-mic.connecting {
  opacity: 0.5;
  cursor: wait;
}

.control-hint {
  font-size: 11px;
  color: var(--text-muted);
}
</style>
