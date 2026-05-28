<template>
  <div class="mode-tabs">
    <router-link to="/chat" class="tab" :class="{ active: active === 'non-immersive' }">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
      </svg>
      <span>非沉浸</span>
    </router-link>
    <router-link to="/immersive" class="tab" :class="{ active: active === 'immersive' }">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2M12 19v4M8 23h8"/>
      </svg>
      <span>沉浸</span>
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
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border);
}

.tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 12px;
  text-decoration: none;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 500;
  transition: all var(--transition-fast);
  border-bottom: 2px solid transparent;
}

.tab:hover {
  color: var(--text-secondary);
  background: var(--bg-hover);
}

.tab.active {
  color: var(--accent-light);
  border-bottom-color: var(--accent);
}
</style>
