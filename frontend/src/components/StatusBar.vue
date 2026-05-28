<template>
  <div class="status-bar">
    <div class="status-left">
      <span class="connection-status">
        <span class="dot" :class="connectionState"></span>
        <span class="mono">{{ connectionText }}</span>
      </span>
    </div>
    <div class="status-right">
      <span class="mono text-muted">{{ currentModel }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const connectionState = ref('disconnected') // disconnected | connecting | connected
const currentModel = ref('qwen3.5-omni-plus')

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
  font-size: 11px;
}

.status-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  transition: background var(--transition-normal);
}

.dot.disconnected { background: var(--text-muted); }
.dot.connecting { background: var(--warning); animation: pulse 1.5s infinite; }
.dot.connected { background: var(--success); }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
