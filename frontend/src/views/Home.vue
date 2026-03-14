<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const apiKey = ref('')
const backendOnline = ref(false)

// 检查后端状态
const checkBackend = async () => {
  try {
    const res = await fetch('/api/health')
    backendOnline.value = res.ok
  } catch {
    backendOnline.value = false
  }
}

// 开始使用
const start = () => {
  if (apiKey.value) {
    localStorage.setItem('apiKey', apiKey.value)
    router.push('/upload')
  }
}

onMounted(() => {
  checkBackend()
  setInterval(checkBackend, 30000)
  
  // 恢复 API Key
  const saved = localStorage.getItem('apiKey')
  if (saved) apiKey.value = saved
})
</script>

<template>
  <div class="container">
    <!-- Header -->
    <div class="card" style="display: flex; justify-content: space-between; align-items: center;">
      <div>
        <h1 style="font-size: 28px; color: #4caf50;">📚 枕边书</h1>
        <p style="font-size: 13px; color: #81c784; margin-top: 4px;">AI 图书转播客 · 按次计费</p>
      </div>
      <div :class="['status-badge', backendOnline ? 'online' : 'offline']">
        {{ backendOnline ? '● 在线' : '○ 离线' }}
      </div>
    </div>

    <!-- 产品介绍 -->
    <div class="card">
      <h2 style="margin-bottom: 20px; color: #4caf50;">✨ 功能特点</h2>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
        <div class="feature">
          <div style="font-size: 32px; margin-bottom: 8px;">📄</div>
          <h3 style="font-size: 15px; margin-bottom: 8px;">智能 OCR</h3>
          <p style="font-size: 13px; color: #a5d6a7;">自动识别扫描版 PDF，精准提取文字</p>
        </div>
        <div class="feature">
          <div style="font-size: 32px; margin-bottom: 8px;">🎙️</div>
          <h3 style="font-size: 15px; margin-bottom: 8px;">双人播客</h3>
          <p style="font-size: 13px; color: #a5d6a7;">AI 生成自然对话，像听播客一样听书</p>
        </div>
        <div class="feature">
          <div style="font-size: 32px; margin-bottom: 8px;">💰</div>
          <h3 style="font-size: 15px; margin-bottom: 8px;">按次计费</h3>
          <p style="font-size: 13px; color: #a5d6a7;">1次 = 1章，用多少付多少</p>
        </div>
      </div>
    </div>

    <!-- API Key 输入 -->
    <div class="card">
      <h2 style="margin-bottom: 16px; color: #4caf50;">🔑 输入 API Key</h2>
      <input 
        v-model="apiKey" 
        placeholder="pk_xxxxxxxxxxxxx" 
        style="margin-bottom: 16px;"
      />
      <p style="font-size: 12px; color: #81c784; margin-bottom: 16px;">
        没有 API Key？联系管理员获取
      </p>
      <button class="btn btn-primary" @click="start" :disabled="!apiKey">
        开始使用 →
      </button>
    </div>

    <!-- 价格 -->
    <div class="card">
      <h2 style="margin-bottom: 16px; color: #4caf50;">💎 价格方案</h2>
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">
        <div class="price-card">
          <div style="font-size: 24px; color: #4caf50;">¥10</div>
          <div style="font-size: 13px; color: #a5d6a7;">100 次</div>
          <div style="font-size: 11px; color: #666;">¥0.10/次</div>
        </div>
        <div class="price-card" style="border-color: #4caf50;">
          <div style="font-size: 12px; color: #4caf50; margin-bottom: 4px;">推荐</div>
          <div style="font-size: 24px; color: #4caf50;">¥45</div>
          <div style="font-size: 13px; color: #a5d6a7;">500 次</div>
          <div style="font-size: 11px; color: #666;">¥0.09/次</div>
        </div>
        <div class="price-card">
          <div style="font-size: 24px; color: #4caf50;">¥80</div>
          <div style="font-size: 13px; color: #a5d6a7;">1000 次</div>
          <div style="font-size: 11px; color: #666;">¥0.08/次</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.status-badge {
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  border: 1px solid;
}
.status-badge.online {
  background: rgba(76, 175, 80, 0.2);
  border-color: #4caf50;
  color: #81c784;
}
.status-badge.offline {
  background: rgba(244, 67, 54, 0.2);
  border-color: #f44336;
  color: #ef5350;
}
.feature {
  text-align: center;
  padding: 20px;
  background: rgba(0, 30, 20, 0.3);
  border-radius: 12px;
}
.price-card {
  text-align: center;
  padding: 20px;
  background: rgba(0, 30, 20, 0.3);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 12px;
}
</style>