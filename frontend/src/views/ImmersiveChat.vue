<template>
  <div class="immersive-chat">
    <!-- 模式切换 Tab -->
    <ChatModeTabs active="immersive" />

    <!-- 对话区域（语音转写文字展示） -->
    <div class="transcript-area">
      <!-- TODO: 显示用户语音转写 + 模型文字回复 -->
    </div>

    <!-- 控制区域 -->
    <div class="control-area">
      <!-- TODO: 麦克风状态指示 + 开始/停止按钮 -->
    </div>
  </div>
</template>

<script setup>
import ChatModeTabs from '@/components/ChatModeTabs.vue'
</script>

<style scoped>
.immersive-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.transcript-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.control-area {
  padding: 16px;
  border-top: 1px solid #e0e0e0;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
