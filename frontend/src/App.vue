<template>
  <div class="app-container">
    <!-- 顶部栏 -->
    <header class="app-header">
      <div class="header-left">
        <span class="app-logo">🎮</span>
        <h1 class="app-title">游戏AI陪聊</h1>
      </div>
      <button class="btn-settings" @click="showSettings = true">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
        </svg>
        <span>设置</span>
      </button>
    </header>

    <!-- 主内容区 -->
    <main class="app-main">
      <!-- 左侧：屏幕监控 -->
      <section class="panel-left">
        <ScreenMonitor ref="screenMonitorRef" />
      </section>

      <!-- 右侧：聊天面板 -->
      <section class="panel-right">
        <router-view />
      </section>
    </main>

    <!-- 状态栏 -->
    <footer class="app-status">
      <StatusBar />
    </footer>

    <!-- 设置弹窗 -->
    <SettingsModal v-if="showSettings" @close="showSettings = false" />
  </div>
</template>

<script setup>
import { ref, provide } from 'vue'
import ScreenMonitor from '@/components/ScreenMonitor.vue'
import StatusBar from '@/components/StatusBar.vue'
import SettingsModal from '@/components/SettingsModal.vue'

const showSettings = ref(false)
const screenMonitorRef = ref(null)

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
  padding: 10px 20px;
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border);
  min-height: 48px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.app-logo {
  font-size: 20px;
}

.app-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.btn-settings {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
  font-size: 13px;
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
  flex: 1;
  border-right: 1px solid var(--border);
  background: var(--bg-panel);
}

.panel-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg-deepest);
}

.app-status {
  padding: 6px 20px;
  background: var(--bg-panel);
  border-top: 1px solid var(--border);
}
</style>
