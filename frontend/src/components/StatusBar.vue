<template>
  <div class="status-bar">
    <span class="connection-status">
      <span class="dot" :class="connectionClass"></span>
      {{ connectionText }}
    </span>
    <span class="model-info">{{ currentModel }}</span>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const connectionState = ref('disconnected') // disconnected | connecting | connected
const currentModel = ref('qwen3.5-omni-plus')

const connectionClass = computed(() => connectionState.value)
const connectionText = computed(() => {
  const map = { disconnected: '未连接', connecting: '连接中...', connected: '已连接' }
  return map[connectionState.value]
})
</script>

<style scoped>
.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.dot.disconnected { background: #f44336; }
.dot.connecting { background: #ff9800; }
.dot.connected { background: #4caf50; }

.model-info {
  color: #999;
}
</style>
