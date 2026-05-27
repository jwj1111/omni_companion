<template>
  <div class="screen-monitor-container">
    <div class="monitor-header">
      <span>屏幕监控</span>
      <span class="status-dot" :class="{ active: isCapturing }"></span>
      <button v-if="!isCapturing" @click="startCapture">开始采集</button>
      <button v-else @click="stopCapture">停止采集</button>
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
      <p v-if="!isCapturing" class="placeholder">点击"开始采集"共享屏幕画面</p>
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

/**
 * 开始屏幕采集
 * 使用 getDisplayMedia 让用户选择共享的屏幕/窗口
 */
async function startCapture() {
  try {
    mediaStream = await navigator.mediaDevices.getDisplayMedia({
      video: { frameRate: { max: 5 } },
      audio: false
    })
    videoRef.value.srcObject = mediaStream
    isCapturing.value = true

    // 监听用户手动停止共享
    mediaStream.getVideoTracks()[0].addEventListener('ended', () => {
      stopCapture()
    })

    // TODO: 按配置频率抽帧并上传后端
    // frameInterval = setInterval(() => captureFrame(), intervalMs)
  } catch (err) {
    console.error('屏幕采集失败:', err)
  }
}

/**
 * 停止屏幕采集
 */
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
 * TODO: 调用后端上传接口或通过 WebSocket 发送
 */
function captureFrame() {
  if (!videoRef.value || !canvasRef.value) return null
  const video = videoRef.value
  const canvas = canvasRef.value
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  const ctx = canvas.getContext('2d')
  ctx.drawImage(video, 0, 0)
  // 输出 JPEG base64（去掉 data:image/jpeg;base64, 前缀）
  const dataUrl = canvas.toDataURL('image/jpeg', 0.7)
  return dataUrl.split(',')[1]
}

onBeforeUnmount(() => {
  stopCapture()
})

// 暴露给父组件使用
defineExpose({ captureFrame, isCapturing })
</script>

<style scoped>
.screen-monitor-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.monitor-header {
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
}

.monitor-header button {
  margin-left: auto;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ccc;
}

.status-dot.active {
  background: #4caf50;
}

.monitor-preview {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1a1a1a;
  overflow: hidden;
}

.monitor-preview video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.placeholder {
  color: #666;
}
</style>
