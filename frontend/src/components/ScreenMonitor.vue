<template>
  <div class="screen-monitor-container">
    <div class="monitor-header">
      <div class="header-info">
        <span class="dot" :class="{ active: isCapturing }"></span>
        <span class="label">屏幕监控</span>
      </div>
      <button
        type="button"
        class="btn-capture"
        :disabled="isRequesting"

        @click="isCapturing ? stopCapture() : startCapture()"
        :aria-label="isCapturing ? '停止屏幕采集' : '开始屏幕采集'"
      >
        {{ isRequesting ? '等待授权...' : (isCapturing ? '停止' : '开始采集') }}
      </button>
    </div>
    <div class="monitor-preview">
      <video
        v-show="isCapturing"
        ref="videoRef"
        autoplay
        muted
        playsinline
        aria-hidden="true"
      ></video>
      <canvas ref="canvasRef" style="display: none;"></canvas>
      <div v-if="!isCapturing" class="placeholder">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
          <rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
        </svg>
        <p v-if="errorMsg" class="error-text">{{ errorMsg }}</p>
        <p v-else>共享屏幕后，AI 可以看到你的画面</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onBeforeUnmount } from 'vue'

const isCapturing = ref(false)
const isRequesting = ref(false)
const errorMsg = ref('')
const videoRef = ref(null)
const canvasRef = ref(null)

let mediaStream = null
let frameInterval = null

async function startCapture() {
  errorMsg.value = ''
  isRequesting.value = true
  try {
    mediaStream = await navigator.mediaDevices.getDisplayMedia({
      video: true,
      audio: false
    })
    videoRef.value.srcObject = mediaStream
    isCapturing.value = true

    mediaStream.getVideoTracks()[0].addEventListener('ended', () => {
      stopCapture()
    })
  } catch (err) {
    if (err.name === 'NotAllowedError') {
      errorMsg.value = '屏幕共享权限被拒绝'
    } else {
      errorMsg.value = `采集失败: ${err.message}`
    }
  } finally {
    isRequesting.value = false
  }
}

function stopCapture() {
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop())
    mediaStream = null
  }
  if (frameInterval) {
    clearInterval(frameInterval)
    frameInterval = null
  }
  if (videoRef.value) {
    videoRef.value.srcObject = null
  }
  isCapturing.value = false
}

/**
 * 从视频流抽取一帧，转为 JPEG base64
 */
function captureFrame() {
  if (!videoRef.value || !canvasRef.value) return null
  const video = videoRef.value
  const canvas = canvasRef.value
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  const ctx = canvas.getContext('2d')
  ctx.drawImage(video, 0, 0)
  const dataUrl = canvas.toDataURL('image/jpeg', 0.7)
  return dataUrl.split(',')[1]
}

onBeforeUnmount(() => {
  stopCapture()
})

defineExpose({ captureFrame, isCapturing })
</script>

<style scoped>
.screen-monitor-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.monitor-header {
  padding: 8px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border);
}

.header-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--type-label);
  font-weight: 500;
  line-height: var(--leading-tight);
  color: var(--text-secondary);
  letter-spacing: var(--tracking-label);
}

.dot {

  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
  transition: all var(--transition-normal);
}

.dot.active {
  background: var(--success);
  box-shadow: 0 0 6px var(--success);
}

.btn-capture {
  padding: 4px 10px;
  font-size: var(--type-caption);
  font-weight: 600;
  line-height: 1;
  border-radius: var(--radius-xs);
  background: transparent;
  border: 1px solid var(--border-light);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
  letter-spacing: var(--tracking-label);
}

.btn-capture:hover:not(:disabled) {

  background: var(--accent-subtle);
  border-color: var(--accent);
  color: var(--accent-light);
}

.btn-capture:disabled {
  opacity: 0.5;
  cursor: wait;
}

.btn-capture:active:not(:disabled) {
  transform: translateY(1px);
}


.monitor-preview {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-deepest);
  overflow: hidden;
  position: relative;
}

.monitor-preview video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: var(--text-muted);
  font-size: var(--type-label);
  opacity: 0.7;
}

.placeholder p {
  max-width: 200px;
  text-align: center;
  line-height: var(--leading-body);
}

.placeholder .error-text {

  color: var(--error);
  opacity: 1;
}
</style>
