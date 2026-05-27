import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * 全局设置状态
 */
export const useSettingsStore = defineStore('settings', () => {
  const settings = ref(null)
  const currentPersona = ref(null)

  async function loadSettings() {
    // TODO: 从后端 GET /api/settings/all 加载
  }

  async function saveSettings(data) {
    // TODO: PUT /api/settings/update
  }

  async function loadPersonas() {
    // TODO: GET /api/settings/personas
  }

  return { settings, currentPersona, loadSettings, saveSettings, loadPersonas }
})
