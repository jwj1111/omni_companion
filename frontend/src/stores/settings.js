import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getSettings } from '@/services/api'

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref(null)
  const loaded = ref(false)

  async function load() {
    try {
      const data = await getSettings()
      settings.value = data
      loaded.value = true
    } catch (e) {
      console.error('加载设置失败:', e)
    }
  }

  return { settings, loaded, load }
})
