<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../api'
import AuthModal from '../components/AuthModal.vue'

const router = useRouter()

// 用户状态
const user = ref<any>(null)
const showAuthModal = ref(false)
const authMode = ref<'login' | 'register'>('login')

// 后端状态
const backendOnline = ref(false)
const showCertHint = ref(false)

// 文件上传
const file = ref<File | null>(null)
const uploading = ref(false)
const bookId = ref('')

// 检查后端状态
const checkBackend = async () => {
  try {
    const res = await apiFetch('/health')
    backendOnline.value = res.ok
    if (res.ok) {
      showCertHint.value = false
    }
  } catch {
    backendOnline.value = false
  }
}

// 接受证书 - 直接切换到服务器版本
const acceptCertificate = async () => {
  // 如果在 GitHub Pages，直接跳转到服务器
  if (isGitHubPages) {
    window.location.href = 'http://139.196.211.206/'
  } else {
    // 非GitHub Pages，尝试刷新
    await refreshStatus()
  }
}

// 切换到服务器版本
const switchToServer = () => {
  window.location.href = 'http://139.196.211.206/'
}

// 刷新状态
const refreshStatus = async () => {
  showCertHint.value = false
  backendOnline.value = false
  await checkBackend()
}

// 检测是否在 GitHub Pages 上
const isGitHubPages = window.location.hostname.includes('github.io')

// 检查用户登录状态
const checkUser = () => {
  const token = localStorage.getItem('token')
  const userData = localStorage.getItem('user')
  
  if (token && userData) {
    try {
      user.value = JSON.parse(userData)
    } catch {
      user.value = null
    }
  }
}

// 文件选择
const onFileSelect = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files?.length) {
    file.value = target.files[0]
  }
}

const onDrop = (e: DragEvent) => {
  e.preventDefault()
  const dropped = e.dataTransfer?.files[0]
  if (dropped && (dropped.name.endsWith('.pdf') || dropped.name.endsWith('.txt') || dropped.name.endsWith('.md'))) {
    file.value = dropped
  }
}

// 上传
const upload = async () => {
  if (!file.value) return
  
  // 检查是否登录
  if (!user.value) {
    authMode.value = 'login'
    showAuthModal.value = true
    return
  }
  
  uploading.value = true
  
  const form = new FormData()
  form.append('file', file.value)
  
  try {
    const token = localStorage.getItem('token')
    const res = await apiFetch('/api/books', {
      method: 'POST',
      body: form,
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    })
    
    if (res.status === 401) {
      // 未登录
      authMode.value = 'login'
      showAuthModal.value = true
      uploading.value = false
      return
    }
    
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '上传失败')
    }
    
    const data = await res.json()
    bookId.value = data.id
    router.push(`/book/${bookId.value}`)
    
  } catch (e: any) {
    alert('上传失败: ' + e.message)
  } finally {
    uploading.value = false
  }
}

// 登录成功
const onAuthSuccess = (userData: any) => {
  user.value = userData
  // 自动继续上传
  if (file.value) {
    upload()
  }
}

// 登出
const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  user.value = null
}

// 显示登录/注册
const showLogin = () => {
  authMode.value = 'login'
  showAuthModal.value = true
}

const showRegister = () => {
  authMode.value = 'register'
  showAuthModal.value = true
}

onMounted(() => {
  checkBackend()
  checkUser()
  setInterval(checkBackend, 30000)
})
</script>

<template>
  <div class="container">
    <!-- Header -->
    <div class="card header-card">
      <div class="header-left">
        <h1 class="site-title">📚 枕边书</h1>
        <p class="site-subtitle">AI 图书转播客 · 一键生成</p>
      </div>
      <div class="header-right">
        <div 
          class="status-badge" 
          :class="backendOnline ? 'online' : 'offline'"
          @click="backendOnline ? null : (showCertHint = true)"
          :title="backendOnline ? '后端服务正常运行' : '点击查看解决方案'"
        >
          {{ backendOnline ? '● 在线' : '○ 离线' }}
        </div>
        <div v-if="user" class="user-info">
          <span class="user-name">{{ user.nickname || user.email }}</span>
          <span class="user-balance">{{ user.balance + user.free_quota }}次</span>
          <button class="logout-btn" @click="logout">退出</button>
        </div>
        <div v-else class="auth-buttons">
          <button class="btn-text" @click="showLogin">登录</button>
          <button class="btn-secondary" @click="showRegister">注册</button>
        </div>
      </div>
    </div>

    <!-- 上传区域 -->
    <div class="card upload-card">
      <h2 class="card-title">📤 上传文件</h2>
      
      <div 
        class="upload-zone" 
        @click="($refs.fileInput as HTMLInputElement).click()"
        @dragover.prevent
        @drop="onDrop"
      >
        <input 
          type="file" 
          ref="fileInput" 
          accept=".pdf,.txt,.md" 
          @change="onFileSelect" 
          style="display: none"
        />
        <div class="upload-icon">📄</div>
        <p class="upload-text">{{ file ? file.name : '拖拽文件到这里或点击选择' }}</p>
        <p class="upload-hint">支持 PDF、TXT、MD 格式</p>
      </div>
      
      <button 
        class="btn btn-primary upload-btn"
        @click="upload" 
        :disabled="!file || uploading"
      >
        {{ uploading ? '⏳ 上传中...' : '🚀 开始生成播客' }}
      </button>
      
      <p class="upload-tip" v-if="!user">
        💡 新用户注册即送 <strong>3次</strong> 免费体验
      </p>
    </div>

    <!-- 功能介绍 -->
    <div class="card features-card">
      <h2 class="card-title">✨ 功能特点</h2>
      <div class="features-grid">
        <div class="feature-item">
          <div class="feature-icon">📄</div>
          <h3>智能解析</h3>
          <p>PDF/文本自动识别，提取章节</p>
        </div>
        <div class="feature-item">
          <div class="feature-icon">🎙️</div>
          <h3>AI播客</h3>
          <p>双人对话，像听节目一样听书</p>
        </div>
        <div class="feature-item">
          <div class="feature-icon">🎭</div>
          <h3>多音色</h3>
          <p>多种音色可选，角色自由搭配</p>
        </div>
        <div class="feature-item">
          <div class="feature-icon">✏️</div>
          <h3>可编辑</h3>
          <p>文稿可编辑，Prompt可自定义</p>
        </div>
      </div>
    </div>

    <!-- 价格 -->
    <div class="card pricing-card">
      <h2 class="card-title">💎 价格方案</h2>
      <div class="pricing-grid">
        <div class="price-item">
          <div class="price-amount">¥10</div>
          <div class="price-count">100次</div>
          <div class="price-unit">¥0.10/次</div>
        </div>
        <div class="price-item featured">
          <div class="price-badge">推荐</div>
          <div class="price-amount">¥45</div>
          <div class="price-count">500次</div>
          <div class="price-unit">¥0.09/次</div>
        </div>
        <div class="price-item">
          <div class="price-amount">¥80</div>
          <div class="price-count">1000次</div>
          <div class="price-unit">¥0.08/次</div>
        </div>
      </div>
    </div>

    <!-- 登录/注册对话框 -->
    <AuthModal 
      v-if="showAuthModal"
      :mode="authMode"
      @close="showAuthModal = false"
      @success="onAuthSuccess"
    />
    
    <!-- 离线提示对话框 -->
    <div v-if="showCertHint" class="modal-overlay" @click.self="showCertHint = false">
      <div class="modal-content cert-hint-modal">
        <div class="modal-header">
          <h2>🔒 无法连接服务器</h2>
          <button class="close-btn" @click="showCertHint = false">×</button>
        </div>
        <div class="cert-hint-body">
          <p class="hint-title">后端服务暂时无法访问</p>
          <p class="hint-desc" v-if="isGitHubPages">
            GitHub Pages 使用 HTTPS，无法直接访问 HTTP 接口。<br>
            请点击下方按钮切换到服务器版本：
          </p>
          <p class="hint-desc" v-else>
            服务器可能暂时离线，请稍后重试。
          </p>
          
          <div class="hint-actions">
            <button class="btn-primary big-btn" @click="switchToServer" v-if="isGitHubPages">
              🚀 切换到服务器版本
            </button>
            <button class="btn-secondary big-btn" @click="refreshStatus" v-else>
              🔄 刷新状态
            </button>
          </div>
          
          <p class="hint-note" v-if="isGitHubPages">
            💡 点击后将跳转到 http://139.196.211.206<br>
            推荐使用服务器版本获得最佳体验
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Header */
.header-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.header-left {
  flex: 1;
}

.site-title {
  font-size: 28px;
  color: #4caf50;
  margin: 0;
}

.site-subtitle {
  font-size: 13px;
  color: #81c784;
  margin: 4px 0 0 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

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

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-name {
  color: #e8f5e9;
  font-size: 14px;
}

.user-balance {
  background: rgba(76, 175, 80, 0.2);
  padding: 4px 10px;
  border-radius: 12px;
  color: #4caf50;
  font-size: 12px;
}

.logout-btn {
  background: none;
  border: 1px solid rgba(76, 175, 80, 0.3);
  color: #81c784;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

.auth-buttons {
  display: flex;
  gap: 8px;
}

.btn-text {
  background: none;
  border: none;
  color: #81c784;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 14px;
}

.btn-secondary {
  background: rgba(76, 175, 80, 0.2);
  border: 1px solid rgba(76, 175, 80, 0.3);
  color: #81c784;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

/* Card */
.card-title {
  margin-bottom: 20px;
  color: #4caf50;
  font-size: 18px;
}

/* Upload */
.upload-card {
  margin-bottom: 20px;
}

.upload-zone {
  border: 2px dashed rgba(76, 175, 80, 0.4);
  border-radius: 16px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: 20px;
}

.upload-zone:hover {
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.05);
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.upload-text {
  color: #e8f5e9;
  margin: 0 0 8px 0;
}

.upload-hint {
  font-size: 12px;
  color: #81c784;
  margin: 0;
}

.upload-btn {
  width: 100%;
}

.upload-tip {
  text-align: center;
  color: #81c784;
  font-size: 13px;
  margin: 12px 0 0 0;
}

.upload-tip strong {
  color: #4caf50;
}

/* Features */
.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 16px;
}

.feature-item {
  text-align: center;
  padding: 20px;
  background: rgba(0, 30, 20, 0.4);
  border-radius: 12px;
}

.feature-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.feature-item h3 {
  font-size: 14px;
  color: #e8f5e9;
  margin: 0 0 6px 0;
}

.feature-item p {
  font-size: 12px;
  color: #81c784;
  margin: 0;
}

/* Pricing */
.pricing-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.price-item {
  text-align: center;
  padding: 20px;
  background: rgba(0, 30, 20, 0.4);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 12px;
  position: relative;
}

.price-item.featured {
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.1);
}

.price-badge {
  position: absolute;
  top: -10px;
  left: 50%;
  transform: translateX(-50%);
  background: #4caf50;
  color: white;
  padding: 4px 12px;
  border-radius: 10px;
  font-size: 11px;
}

.price-amount {
  font-size: 24px;
  color: #4caf50;
  font-weight: 600;
}

.price-count {
  font-size: 13px;
  color: #a5d6a7;
  margin: 4px 0;
}

.price-unit {
  font-size: 11px;
  color: #666;
}

@media (max-width: 600px) {
  .pricing-grid {
    grid-template-columns: 1fr;
  }
  
  .header-card {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .header-right {
    width: 100%;
    justify-content: space-between;
  }
}

/* 离线提示弹窗 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: linear-gradient(135deg, #1a3a2a 0%, #0f2419 100%);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 16px;
  padding: 24px;
  width: 100%;
  max-width: 400px;
  margin: 20px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.modal-header h2 {
  color: #4caf50;
  margin: 0;
  font-size: 20px;
}

.close-btn {
  background: none;
  border: none;
  color: #81c784;
  font-size: 28px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.close-btn:hover {
  color: #4caf50;
}

.cert-hint-modal {
  max-width: 420px;
}

.cert-hint-body {
  padding: 10px 0;
}

.hint-title {
  color: #ef5350;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
}

.hint-desc {
  color: #a5d6a7;
  font-size: 14px;
  margin-bottom: 20px;
  line-height: 1.6;
}

.hint-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.hint-actions .big-btn {
  width: 100%;
  padding: 16px;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.hint-actions .btn-primary {
  background: linear-gradient(135deg, #4caf50, #2e7d32);
  border: none;
  color: white;
}

.hint-actions .btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(76, 175, 80, 0.4);
}

.hint-actions .btn-secondary {
  background: rgba(76, 175, 80, 0.2);
  border: 1px solid rgba(76, 175, 80, 0.3);
  color: #81c784;
}

.hint-actions .btn-secondary:hover {
  background: rgba(76, 175, 80, 0.3);
}

.hint-note {
  color: #81c784;
  font-size: 12px;
  text-align: center;
  background: rgba(76, 175, 80, 0.1);
  padding: 12px;
  border-radius: 8px;
  margin: 0;
  line-height: 1.6;
}

.status-badge.offline {
  cursor: pointer;
  transition: all 0.3s;
}

.status-badge.offline:hover {
  transform: scale(1.05);
  box-shadow: 0 0 12px rgba(244, 67, 54, 0.4);
}
</style>