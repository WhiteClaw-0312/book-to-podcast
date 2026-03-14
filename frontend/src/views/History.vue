<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch, getUser } from '../api'

const router = useRouter()
const user = ref<any>(null)
const history = ref<any[]>([])
const loading = ref(true)

onMounted(async () => {
  user.value = getUser()
  
  if (!user.value) {
    router.push('/')
    return
  }
  
  // TODO: 获取历史记录
  loading.value = false
})
</script>

<template>
  <div class="container">
    <div class="card">
      <h2 style="color: #4caf50; margin-bottom: 20px;">📜 历史记录</h2>
      <p style="color: #81c784;">此功能正在开发中...</p>
      <button class="btn btn-secondary" @click="router.back()">返回</button>
    </div>
  </div>
</template>