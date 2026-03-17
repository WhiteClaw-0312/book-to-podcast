import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

// 路由
const router = createRouter({
  history: createWebHistory('/book-to-podcast/'),
  routes: [
    { path: '/', component: () => import('./views/Home.vue') },
    { path: '/book/:id', component: () => import('./views/BookDetail.vue') },
    { path: '/book/:id/script', component: () => import('./views/ScriptEditor.vue') },
    { path: '/prompts', component: () => import('./views/PromptEditor.vue') },
    { path: '/balance', component: () => import('./views/Balance.vue') }
  ]
})

const app = createApp(App)
app.use(router)
app.mount('#app')