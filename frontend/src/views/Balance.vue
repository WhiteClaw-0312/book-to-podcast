<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../api'

const router = useRouter()
const apiKey = ref('')
const balance = ref<number | null>(null)
const totalUsed = ref(0)
const loading = ref(false)

// 查询余额
const checkBalance = async () => {
  if (!apiKey.value) return
  
  loading.value = true
  
  try {
    const res = await apiFetch(`/api/keys/${apiKey.value}/balance`)
    const data = await res.json()
    balance.value = data.balance
    totalUsed.value = data.total_used
  } catch (e) {
    alert('查询失败，请检查 API Key')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  const saved = localStorage.getItem('apiKey')
  if (saved) apiKey.value = saved
})
</script>

<template>
  <div class="container">
    <!-- Header -->
    <div class="card" style="display: flex; justify-content: space-between; align-items: center;">
      <h1 style="font-size: 20px; color: #4caf50; cursor: pointer;" @click="router.push('/')">
        ← 余额查询
      </h1>
      <button class="btn btn-secondary" @click="router.push('/upload')">
        上传书籍
      </button>
    </div>

    <!-- 查询 -->
    <div class="card">
      <h2 style="margin-bottom: 16px; color: #4caf50;">🔑 输入 API Key</h2>
      <div style="display: flex; gap: 12px;">
        <input 
          v-model="apiKey" 
          placeholder="pk_xxxxxxxxxxxxx"
          style="flex: 1;"
        />
        <button class="btn btn-primary" @click="checkBalance" :disabled="loading || !apiKey">
          {{ loading ? '查询中...' : '查询' }}
        </button>
      </div>
    </div>

    <!-- 结果 -->
    <div class="card" v-if="balance !== null">
      <h2 style="margin-bottom: 20px; color: #4caf50;">💰 账户信息</h2>
      
      <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
        <div class="stat-card">
          <div style="font-size: 32px; color: #4caf50;">{{ balance }}</div>
          <div style="font-size: 13px; color: #a5d6a7;">剩余次数</div>
        </div>
        <div class="stat-card">
          <div style="font-size: 32px; color: #81c784;">{{ totalUsed }}</div>
          <div style="font-size: 13px; color: #a5d6a7;">累计使用</div>
        </div>
      </div>
      
      <p style="text-align: center; margin-top: 20px; font-size: 12px; color: #666;">
        余额不足？联系管理员充值
      </p>
    </div>
  </div>
</template>

<style scoped>
.stat-card {
  text-align: center;
  padding: 24px;
  background: rgba(0, 30, 20, 0.3);
  border-radius: 12px;
}
</style>