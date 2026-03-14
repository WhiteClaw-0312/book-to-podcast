<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { apiFetch, getUser } from '../api'

const router = useRouter()
const route = useRoute()

const user = ref<any>(null)
const script = ref<any[]>([])
const loading = ref(true)

onMounted(async () => {
  user.value = getUser()
  
  // 获取文稿
  const bookId = route.params.id
  // TODO: 实现文稿加载
  loading.value = false
})
</script>

<template>
  <div class="container">
    <div class="card">
      <h2 style="color: #4caf50; margin-bottom: 20px;">📝 文稿编辑</h2>
      <p style="color: #81c784;">此功能正在开发中...</p>
      <button class="btn btn-secondary" @click="router.back()">返回</button>
    </div>
  </div>
</template>