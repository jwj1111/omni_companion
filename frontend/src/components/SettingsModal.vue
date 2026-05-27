<template>
  <div class="settings-overlay" @click.self="$emit('close')">
    <div class="settings-panel">
      <header class="settings-header">
        <h2>设置</h2>
        <button @click="$emit('close')">×</button>
      </header>

      <nav class="settings-nav">
        <button :class="{ active: tab === 'api' }" @click="tab = 'api'">API 配置</button>
        <button :class="{ active: tab === 'persona' }" @click="tab = 'persona'">角色管理</button>
        <button :class="{ active: tab === 'features' }" @click="tab = 'features'">功能开关</button>
        <button :class="{ active: tab === 'realtime' }" @click="tab = 'realtime'">实时模式</button>
        <button :class="{ active: tab === 'advanced' }" @click="tab = 'advanced'">高级</button>
      </nav>

      <section class="settings-content">
        <!-- TODO: 各 tab 对应的设置表单 -->
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineEmits(['close'])
const tab = ref('api')
</script>

<style scoped>
.settings-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.settings-panel {
  background: #fff;
  border-radius: 8px;
  width: 700px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e0e0e0;
}

.settings-nav {
  display: flex;
  gap: 4px;
  padding: 12px 20px;
  border-bottom: 1px solid #f0f0f0;
}

.settings-nav button {
  padding: 6px 12px;
  border: none;
  background: none;
  cursor: pointer;
  border-radius: 4px;
}

.settings-nav button.active {
  background: #e3f2fd;
  color: #1976d2;
}

.settings-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
</style>
