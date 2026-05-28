<template>
  <div class="app-container">
    <!-- 顶部栏 -->
    <header class="app-header">
      <div class="header-left">
        <div class="app-logo-mark">O</div>
        <h1 class="app-title">Omni Companion</h1>
      </div>
      <button class="btn-settings" @click="showSettings = true" aria-label="设置">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M12.22 2h-.44a2 2 0 00-2 2v.18a2 2 0 01-1 1.73l-.43.25a2 2 0 01-2 0l-.15-.08a2 2 0 00-2.73.73l-.22.38a2 2 0 00.73 2.73l.15.1a2 2 0 011 1.72v.51a2 2 0 01-1 1.74l-.15.09a2 2 0 00-.73 2.73l.22.38a2 2 0 002.73.73l.15-.08a2 2 0 012 0l.43.25a2 2 0 011 1.73V20a2 2 0 002 2h.44a2 2 0 002-2v-.18a2 2 0 011-1.73l.43-.25a2 2 0 012 0l.15.08a2 2 0 002.73-.73l.22-.39a2 2 0 00-.73-2.73l-.15-.08a2 2 0 01-1-1.74v-.5a2 2 0 011-1.74l.15-.09a2 2 0 00.73-2.73l-.22-.38a2 2 0 00-2.73-.73l-.15.08a2 2 0 01-2 0l-.43-.25a2 2 0 01-1-1.73V4a2 2 0 00-2-2z"/><circle cx="12" cy="12" r="3"/>
        </svg>
      </button>
    </header>

    <!-- 主内容区 -->
    <main class="app-main" role="main">
      <!-- 左侧：屏幕监控（占更大比例） -->
      <section class="panel-left" aria-label="屏幕监控">
        <ScreenMonitor ref="screenMonitorRef" />
      </section>

      <!-- 右侧：聊天面板 -->
      <section class="panel-right" aria-label="对话">
        <router-view />
      </section>
    </main>

    <!-- 设置弹窗 -->
    <SettingsModal v-if="showSettings" @close="showSettings = false" />
  </div>
</template>

<script setup>
import { ref, provide, onMounted } from 'vue'
import ScreenMonitor from '@/components/ScreenMonitor.vue'
import SettingsModal from '@/components/SettingsModal.vue'
import { clearChatHistory, resetRuntimeSettings } from '@/services/api'

const showSettings = ref(false)
const screenMonitorRef = ref(null)

// 每次前端加载（刷新）= 恢复默认设置 + 新对话
onMounted(async () => {
  try {
    await resetRuntimeSettings()
  } finally {
    clearChatHistory()
  }
})

// 暴露给子组件（NonImmersiveChat / ImmersiveChat）
provide('screenMonitor', screenMonitorRef)
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-deepest);
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 48px;
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.app-logo-mark {
  width: 24px;
  height: 24px;
  border-radius: 5px;
  background: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.5px;
}

.app-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  letter-spacing: 0.3px;
}

.btn-settings {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  transition: all var(--transition-fast);
}

.btn-settings:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.app-main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.panel-left {
  flex: 3;
  border-right: 1px solid var(--border);
  background: var(--bg-deepest);
}

.panel-right {
  flex: 2;
  min-width: 340px;
  display: flex;
  flex-direction: column;
  background: var(--bg-panel);
}
</style>
