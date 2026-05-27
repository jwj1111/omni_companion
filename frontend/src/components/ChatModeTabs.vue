<template>
  <div class="mode-tabs">
    <router-link to="/chat" class="tab" :class="{ active: active === 'non-immersive' }">
      非沉浸
    </router-link>
    <router-link to="/immersive" class="tab" :class="{ active: active === 'immersive' }">
      沉浸
    </router-link>
  </div>
</template>

<script setup>
defineProps({
  active: { type: String, required: true }
})
</script>

<style scoped>
.mode-tabs {
  display: flex;
  border-bottom: 1px solid #e0e0e0;
}

.tab {
  flex: 1;
  padding: 10px;
  text-align: center;
  text-decoration: none;
  color: #666;
  font-size: 14px;
  transition: all 0.2s;
}

.tab.active {
  color: #1976d2;
  border-bottom: 2px solid #1976d2;
}
</style>
