<template>
  <div class="immersive-chat">
    <!-- 模式切换 Tab -->
    <ChatModeTabs active="immersive" />

    <!-- 对话转写区域 -->
    <div class="transcript-area" ref="transcriptRef">
      <div v-if="transcripts.length === 0 && !isActive" class="empty-state">
        <p class="text-muted">点击下方按钮开始语音对话</p>
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
    <div class="status-indicator" v-if="isActive">
      <div class="volume-bar">
        <div class="volume-level" :style="{ width: volumePercent + '%' }"></div>
      </div>
      <span class="status-text">{{ statusText }}</span>
    </div>

    <!-- 控制区域 -->
    <div class="control-area">
      <button
        class="btn-mic"
        :class="{ active: isActive, disconnected: isDisconnected }"
        @click="toggleSession"
      >
        <svg v-if="!isActive" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2M12 19v4M8 23h8"/>
        </svg>
        <svg v-else width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
          <rect x="6" y="6" width="12" height="12" rx="2"/>
        </svg>
      </button>
      <p class="control-hint text-muted">
        {{ isActive ? '点击停止' : (isDisconnected ? '点击重新连接' : '点击开始语音对话') }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onBeforeUnmount, inject } from 'vue'
import ChatModeTabs from '@/components/ChatModeTabs.vue'
import { RealtimeService } from '@/services/realtime'
import { MicRecorder, AudioPlayer, stopAllAudio } from '@/services/audio'

const screenMonitor = inject('screenMonitor')

const transcripts = ref([])
const isActive = ref(false)
const isDisconnected = ref(false)
const statusText = ref('')
const volumePercent = ref(0)
const transcriptRef = ref(null)

let realtimeService = null
let micRecorder = null
let audioPlayer = null
let volumeInterval = null
let screenshotInterval = null
let screenshotPushActive = false  // 是否允许推送截图（仅用户说话时为 true）
let currentAssistantText = ''

function toggleSession() {
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
function startScreenshotPush() {
  if (screenshotInterval) return

  const intervalMs = 1000
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
    startScreenshotPush()

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

  realtimeService = new RealtimeService()
  micRecorder = new MicRecorder()
  audioPlayer = new AudioPlayer()
  isDisconnected.value = false

  // 连接 WebSocket（等收到 connected 事件后再启动麦克风）
  realtimeService.connect(handleEvent)
  statusText.value = '连接中...'
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
  isActive.value = false
  volumePercent.value = 0
  statusText.value = ''
}

/**
 * 结束当前未完成的助手转写条目
 * 打断时调用：如果内容太短（碎片），直接移除；否则标记为完成
 */
function finalizeStreamingTranscript() {
  if (!currentAssistantText) return
  const last = transcripts.value[transcripts.value.length - 1]
  if (last && last.role === 'assistant' && last.streaming) {
    if (currentAssistantText.length <= 2) {
      // 碎片（如"还是"），直接移除
      transcripts.value.pop()
    } else {
      last.streaming = false
    }
  }
  currentAssistantText = ''
}

function handleEvent(event) {
  const { type } = event

  if (type === 'audio') {
    // 模型音频 → 边收边播（官方方式2）
    audioPlayer.write(event.data)
  } else if (type === 'transcript') {
    if (event.role === 'user') {
      if (event.final) {
        transcripts.value.push({ role: 'user', text: event.text })
        scrollToBottom()
      }
    } else if (event.role === 'assistant') {
      if (event.final) {
        // 替换或添加最终文本
        const last = transcripts.value[transcripts.value.length - 1]
        if (last && last.role === 'assistant' && last.streaming) {
          last.text = event.text
          last.streaming = false
        } else {
          transcripts.value.push({ role: 'assistant', text: event.text })
        }
        currentAssistantText = ''
        scrollToBottom()
      } else {
        // 流式增量
        currentAssistantText += event.text
        const last = transcripts.value[transcripts.value.length - 1]
        if (last && last.role === 'assistant' && last.streaming) {
          last.text = currentAssistantText
        } else {
          transcripts.value.push({ role: 'assistant', text: currentAssistantText, streaming: true })
        }
        scrollToBottom()
      }
    }
  } else if (type === 'status') {
    if (event.event === 'connected') {
      // WebSocket 已连接且阿里云会话已建立，现在启动麦克风
      startMicAndScreenshot()
    } else if (event.event === 'disconnected') {
      isActive.value = false
      isDisconnected.value = true
      statusText.value = '连接已断开'
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
    } else if (event.event === 'input_audio_buffer.speech_started') {
      statusText.value = '说话中...'
      screenshotPushActive = true  // 用户开始说话，允许推截图
      if (audioPlayer) audioPlayer.flush()  // 打断：清空播放缓冲（不销毁）
      // 打断时清理未完成的助手转写
      finalizeStreamingTranscript()
    } else if (event.event === 'input_audio_buffer.speech_stopped') {
      statusText.value = '思考中...'
      screenshotPushActive = false  // 用户停止说话，暂停推截图（防止 image before audio）
    } else if (event.event === 'response.done') {
      statusText.value = '聆听中...'
    }
  } else if (type === 'error') {
    statusText.value = `错误: ${event.message}`
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
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.transcript-item {
  font-size: 14px;
  line-height: 1.6;
  padding: 6px 0;
}

.transcript-role {
  font-weight: 600;
  margin-right: 8px;
}

.transcript-item.user .transcript-role {
  color: var(--accent-light);
}

.transcript-item.assistant .transcript-role {
  color: var(--success);
}

.transcript-text {
  color: var(--text-primary);
}

/* 状态指示 */
.status-indicator {
  padding: 8px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-top: 1px solid var(--border);
}

.volume-bar {
  width: 80px;
  height: 4px;
  background: var(--bg-card);
  border-radius: 2px;
  overflow: hidden;
}

.volume-level {
  height: 100%;
  background: var(--accent);
  border-radius: 2px;
  transition: width 0.1s;
}

.status-text {
  font-size: 12px;
  color: var(--text-secondary);
}

/* 控制区域 */
.control-area {
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  border-top: 1px solid var(--border);
  background: var(--bg-panel);
}

.btn-mic {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--bg-card);
  border: 2px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  transition: all var(--transition-normal);
}

.btn-mic:hover {
  border-color: var(--accent);
  color: var(--accent-light);
  transform: scale(1.05);
}

.btn-mic.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
  box-shadow: 0 0 20px rgba(124, 92, 252, 0.4);
  animation: pulse-glow 2s infinite;
}

.btn-mic.disconnected {
  border-color: var(--warning);
  color: var(--warning);
}

@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 20px rgba(124, 92, 252, 0.4); }
  50% { box-shadow: 0 0 30px rgba(124, 92, 252, 0.6); }
}

.control-hint {
  font-size: 12px;
}
</style>
