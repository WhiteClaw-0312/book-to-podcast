import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

// 动态确定 base 路径
const getBasePath = () => {
  // 如果设置了环境变量，使用环境变量
  if (import.meta.env.VITE_BASE_PATH) {
    return import.meta.env.VITE_BASE_PATH
  }
  // GitHub Pages 使用 /book-to-podcast/
  if (window.location.hostname.includes('github.io')) {
    return '/book-to-podcast/'
  }
  // 其他环境（服务器直接部署）使用 /
  return '/'
}

// 路由
const router = createRouter({
  history: createWebHistory(getBasePath()),
  routes: [
    { path: '/', component: () => import('./views/Home.vue') },
    { path: '/book/:id', component: () => import('./views/BookDetail.vue') },
    { path: '/book/:id/chapters', component: () => import('./views/ChapterManager.vue') },
    { path: '/book/:id/script', component: () => import('./views/ScriptEditor.vue') },
    { path: '/prompts', component: () => import('./views/PromptEditor.vue') },
    { path: '/balance', component: () => import('./views/Balance.vue') }
  ]
})

const app = createApp(App)
app.use(router)
app.mount('#app')