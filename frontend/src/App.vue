<template>
  <div class="app-container">
    <!-- 顶部栏 -->
    <header class="app-header">
      <h1 class="app-title">游戏AI陪聊</h1>
      <button class="settings-btn" @click="openSettings">设置</button>
    </header>

    <!-- 主内容区 -->
    <main class="app-main">
      <!-- 左侧：屏幕监控 -->
      <section class="screen-monitor">
        <ScreenMonitor />
      </section>

      <!-- 右侧：聊天面板 -->
      <section class="chat-panel">
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
import { ref } from 'vue'
import ScreenMonitor from '@/components/ScreenMonitor.vue'
import StatusBar from '@/components/StatusBar.vue'
import SettingsModal from '@/components/SettingsModal.vue'

const showSettings = ref(false)

function openSettings() {
  showSettings.value = true
}
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-bottom: 1px solid #e0e0e0;
}

.app-main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.screen-monitor {
  flex: 1;
  border-right: 1px solid #e0e0e0;
}

.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.app-status {
  padding: 4px 16px;
  border-top: 1px solid #e0e0e0;
  font-size: 12px;
}
</style>
