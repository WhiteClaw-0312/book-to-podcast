<script setup lang="ts">
import { ref, computed } from 'vue'
import { apiFetch } from '../api'

const props = defineProps<{
  mode: 'login' | 'register'
}>()

const emit = defineEmits<{
  close: []
  success: [user: any]
}>()

const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const nickname = ref('')
const loading = ref(false)
const error = ref('')

const isRegister = computed(() => props.mode === 'register')

const submit = async () => {
  error.value = ''
  
  if (!email.value || !password.value) {
    error.value = '请填写邮箱和密码'
    return
  }
  
  if (isRegister.value) {
    if (password.value !== confirmPassword.value) {
      error.value = '两次密码不一致'
      return
    }
    if (password.value.length < 6) {
      error.value = '密码至少6位'
      return
    }
  }
  
  loading.value = true
  
  try {
    const endpoint = isRegister.value ? '/api/auth/register' : '/api/auth/login'
    const body = isRegister.value 
      ? { email: email.value, password: password.value, nickname: nickname.value }
      : { email: email.value, password: password.value }
    
    const res = await apiFetch(endpoint, {
      method: 'POST',
      body: JSON.stringify(body)
    })
    
    const data = await res.json()
    
    if (!res.ok) {
      error.value = data.detail || '操作失败'
      return
    }
    
    // 保存token
    if (data.token) {
      localStorage.setItem('token', data.token)
      localStorage.setItem('user', JSON.stringify(data.user))
    }
    
    emit('success', data.user || data)
    emit('close')
    
  } catch (e: any) {
    error.value = e.message || '网络错误'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="modal-overlay" @click.self="emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2>{{ isRegister ? '注册账号' : '登录' }}</h2>
        <button class="close-btn" @click="emit('close')">×</button>
      </div>
      
      <form @submit.prevent="submit" class="form">
        <div class="form-group">
          <label>邮箱</label>
          <input 
            v-model="email" 
            type="email" 
            placeholder="请输入邮箱"
            autocomplete="email"
          />
        </div>
        
        <div class="form-group">
          <label>密码</label>
          <input 
            v-model="password" 
            type="password" 
            placeholder="请输入密码"
            autocomplete="current-password"
          />
        </div>
        
        <template v-if="isRegister">
          <div class="form-group">
            <label>确认密码</label>
            <input 
              v-model="confirmPassword" 
              type="password" 
              placeholder="再次输入密码"
            />
          </div>
          
          <div class="form-group">
            <label>昵称（可选）</label>
            <input 
              v-model="nickname" 
              type="text" 
              placeholder="给自己起个名字"
            />
          </div>
          
          <div class="register-tip">
            🎁 新用户注册即送 <strong>3次</strong> 免费体验额度
          </div>
        </template>
        
        <div v-if="error" class="error-msg">{{ error }}</div>
        
        <button type="submit" class="submit-btn" :disabled="loading">
          {{ loading ? '处理中...' : (isRegister ? '注册' : '登录') }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
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
  margin-bottom: 24px;
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

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  color: #a5d6a7;
  font-size: 13px;
  margin-bottom: 6px;
}

.form-group input {
  width: 100%;
  padding: 12px;
  background: rgba(0, 30, 20, 0.8);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 8px;
  color: #e8f5e9;
  font-size: 14px;
}

.form-group input:focus {
  outline: none;
  border-color: #4caf50;
}

.register-tip {
  background: rgba(76, 175, 80, 0.1);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
  color: #81c784;
  font-size: 13px;
  text-align: center;
}

.register-tip strong {
  color: #4caf50;
}

.error-msg {
  color: #ef5350;
  font-size: 13px;
  margin-bottom: 16px;
  text-align: center;
}

.submit-btn {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, #4caf50, #2e7d32);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>