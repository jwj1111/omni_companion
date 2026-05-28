<template>
  <div class="screen-monitor-container">
    <div class="monitor-header">
      <div class="header-info">
        <span class="dot" :class="{ active: isCapturing }"></span>
        <span class="label">屏幕监控</span>
      </div>
      <button class="btn-capture" @click="isCapturing ? stopCapture() : startCapture()">
        {{ isCapturing ? '停止' : '开始采集' }}
      </button>
    </div>
    <div class="monitor-preview">
      <video
        v-show="isCapturing"
        ref="videoRef"
        autoplay
        muted
        playsinline
      ></video>
      <canvas ref="canvasRef" style="display: none;"></canvas>
      <div v-if="!isCapturing" class="placeholder">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
          <rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
        </svg>
        <p>点击"开始采集"共享游戏画面</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onBeforeUnmount } from 'vue'

const isCapturing = ref(false)
const videoRef = ref(null)
const canvasRef = ref(null)

let mediaStream = null
let frameInterval = null

async function startCapture() {
  try {
    mediaStream = await navigator.mediaDevices.getDisplayMedia({
      video: true,  // 不限帧率，预览丝滑；抽帧频率由定时器另外控制
      audio: false
    })
    videoRef.value.srcObject = mediaStream
    isCapturing.value = true

    mediaStream.getVideoTracks()[0].addEventListener('ended', () => {
      stopCapture()
    })
  } catch (err) {
    console.error('屏幕采集失败:', err)
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
  padding: 10px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
}

.header-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
  transition: background var(--transition-normal);
}

.dot.active {
  background: var(--success);
  box-shadow: 0 0 6px var(--success);
}

.btn-capture {
  padding: 5px 12px;
  font-size: 12px;
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.btn-capture:hover {
  background: var(--bg-hover);
  border-color: var(--accent);
  color: var(--accent-light);
}

.monitor-preview {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  overflow: hidden;
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
  gap: 12px;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
