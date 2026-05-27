<template>
  <div class="non-immersive-chat">
    <!-- 模式切换 Tab -->
    <ChatModeTabs active="non-immersive" />

    <!-- 消息列表 -->
    <div class="message-list">
      <!-- TODO: 渲染对话消息 -->
    </div>

    <!-- 输入区域 -->
    <div class="input-area">
      <!-- TODO: 文本输入框 + 附件按钮（截图） + 发送按钮 -->
    </div>
  </div>
</template>

<script setup>
import ChatModeTabs from '@/components/ChatModeTabs.vue'
</script>

<style scoped>
.non-immersive-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.input-area {
  padding: 12px 16px;
  border-top: 1px solid #e0e0e0;
}
</style>
