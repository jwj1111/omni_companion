import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/chat'
  },
  {
    path: '/chat',
    name: 'NonImmersive',
    component: () => import('@/views/NonImmersiveChat.vue')
  },
  {
    path: '/immersive',
    name: 'Immersive',
    component: () => import('@/views/ImmersiveChat.vue')
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
