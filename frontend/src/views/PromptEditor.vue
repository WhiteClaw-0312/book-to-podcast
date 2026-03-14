<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch, getUser } from '../api'

const router = useRouter()
const user = ref<any>(null)
const prompts = ref<any[]>([])
const loading = ref(true)

onMounted(async () => {
  user.value = getUser()
  
  // 获取Prompt列表
  try {
    const res = await apiFetch('/api/prompts')
    if (res.ok) {
      prompts.value = await res.json()
    }
  } catch (e) {
    console.error(e)
  }
  
  loading.value = false
})
</script>

<template>
  <div class="container">
    <div class="card">
      <h2 style="color: #4caf50; margin-bottom: 20px;">✏️ Prompt 编辑器</h2>
      <p style="color: #81c784;">此功能正在开发中...</p>
      <button class="btn btn-secondary" @click="router.back()">返回</button>
    </div>
  </div>
</template>