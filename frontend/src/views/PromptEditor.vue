<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch, getUser, getToken } from '../api'

const router = useRouter()
const user = ref<any>(null)
const prompts = ref<any[]>([])
const loading = ref(true)
const editing = ref(false)
const currentPrompt = ref<any>(null)
const saving = ref(false)

// 表单
const form = ref({
  name: '',
  description: '',
  content: '',
  is_public: false
})

// 筛选
const filter = ref<'all' | 'public' | 'mine'>('all')
const filteredPrompts = computed(() => {
  if (filter.value === 'public') {
    return prompts.value.filter(p => p.is_public || p.is_system)
  }
  if (filter.value === 'mine') {
    return prompts.value.filter(p => p.user_id === user.value?.id)
  }
  return prompts.value
})

// 默认 Prompt
const defaultPrompt = `你是一位专业的播客编剧，擅长将图书内容转换为引人入胜的双人对话式播客。

主持人设定：
- 小北：活泼好奇，善于提问，用"诶~"、"哇"、"真的吗"等语气词增加互动感
- 阿南：沉稳博学，善于总结和解释，用"没错"、"其实"、"可以说"等连接词

对话风格：
1. 自然口语化，避免书面语
2. 适当加入感叹、停顿、思考
3. 每段对话 1-3 句话，不宜过长
4. 保留关键信息，但要用聊天的方式表达

输出格式：JSON
{
  "dialogues": [
    {"speaker": "小北", "content": "..."},
    {"speaker": "阿南", "content": "..."}
  ]
}

请根据以下内容生成播客文稿：`

// 获取 Prompt 列表
const fetchPrompts = async () => {
  try {
    const res = await apiFetch('/api/prompts')
    if (res.ok) {
      prompts.value = await res.json()
    }
  } catch (e) {
    console.error(e)
  }
  loading.value = false
}

// 新建
const createNew = () => {
  currentPrompt.value = null
  form.value = {
    name: '我的 Prompt',
    description: '',
    content: defaultPrompt,
    is_public: false
  }
  editing.value = true
}

// 编辑
const editPrompt = (prompt: any) => {
  currentPrompt.value = prompt
  form.value = {
    name: prompt.name,
    description: prompt.description || '',
    content: prompt.content,
    is_public: prompt.is_public
  }
  editing.value = true
}

// 使用
const usePrompt = async (prompt: any) => {
  if (!user.value) {
    alert('请先登录')
    return
  }
  // 跳转到首页
  router.push('/')
}

// 保存
const save = async () => {
  if (!form.value.name || !form.value.content) {
    alert('请填写名称和内容')
    return
  }
  
  saving.value = true
  try {
    const token = getToken()
    const url = currentPrompt.value 
      ? `/api/prompts/${currentPrompt.value.id}`
      : '/api/prompts'
    const method = currentPrompt.value ? 'PUT' : 'POST'
    
    const res = await apiFetch(url, {
      method,
      headers: { 'Authorization': `Bearer ${token}` },
      body: JSON.stringify(form.value)
    })
    
    if (res.ok) {
      await fetchPrompts()
      editing.value = false
      alert('保存成功！')
    } else {
      const err = await res.json()
      throw new Error(err.detail || '保存失败')
    }
  } catch (e: any) {
    alert('保存失败: ' + e.message)
  }
  saving.value = false
}

// 删除
const deletePrompt = async (prompt: any) => {
  if (!confirm('确定删除此 Prompt？')) return
  
  try {
    const token = getToken()
    const res = await apiFetch(`/api/prompts/${prompt.id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    
    if (res.ok) {
      await fetchPrompts()
    }
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  user.value = getUser()
  fetchPrompts()
})
</script>

<template>
  <div class="container">
    <!-- Header -->
    <div class="card header-card">
      <h1 style="color: #4caf50; font-size: 22px; margin: 0;">✏️ Prompt 编辑器</h1>
      <div class="header-actions">
        <button class="btn btn-secondary" @click="router.push('/')">← 返回首页</button>
        <button class="btn btn-primary" @click="createNew">+ 新建 Prompt</button>
      </div>
    </div>

    <!-- 编辑模式 -->
    <div v-if="editing" class="card editor-card">
      <h2 style="color: #4caf50; margin-bottom: 20px;">
        {{ currentPrompt ? '编辑 Prompt' : '新建 Prompt' }}
      </h2>
      
      <div class="form-group">
        <label>名称</label>
        <input v-model="form.name" type="text" placeholder="给 Prompt 起个名字" />
      </div>
      
      <div class="form-group">
        <label>描述（可选）</label>
        <input v-model="form.description" type="text" placeholder="简单描述这个 Prompt 的用途" />
      </div>
      
      <div class="form-group">
        <label>Prompt 内容</label>
        <textarea 
          v-model="form.content" 
          placeholder="输入 Prompt 内容..."
          rows="15"
        ></textarea>
      </div>
      
      <div class="form-group checkbox-group">
        <label>
          <input type="checkbox" v-model="form.is_public" />
          公开分享给其他用户
        </label>
      </div>
      
      <div class="editor-actions">
        <button class="btn btn-secondary" @click="editing = false">取消</button>
        <button class="btn btn-primary" @click="save" :disabled="saving">
          {{ saving ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>

    <!-- 列表模式 -->
    <template v-else>
      <!-- 筛选 -->
      <div class="card filter-card">
        <div class="filter-tabs">
          <button 
            :class="['filter-tab', { active: filter === 'all' }]"
            @click="filter = 'all'"
          >全部</button>
          <button 
            :class="['filter-tab', { active: filter === 'public' }]"
            @click="filter = 'public'"
          >公开模版</button>
          <button 
            :class="['filter-tab', { active: filter === 'mine' }]"
            @click="filter = 'mine'"
          >我的</button>
        </div>
      </div>

      <!-- Prompt 列表 -->
      <div class="card">
        <div v-if="loading" class="loading">加载中...</div>
        
        <div v-else-if="filteredPrompts.length === 0" class="empty">
          <p>暂无 Prompt</p>
          <button class="btn btn-primary" @click="createNew">创建第一个 Prompt</button>
        </div>
        
        <div v-else class="prompt-list">
          <div 
            v-for="prompt in filteredPrompts" 
            :key="prompt.id" 
            class="prompt-item"
          >
            <div class="prompt-header">
              <h3>
                {{ prompt.name }}
                <span v-if="prompt.is_default" class="badge default">默认</span>
                <span v-if="prompt.is_system" class="badge system">系统</span>
                <span v-if="prompt.is_public && !prompt.is_system" class="badge public">公开</span>
              </h3>
              <div class="prompt-stats">
                使用 {{ prompt.use_count }} 次
              </div>
            </div>
            
            <p class="prompt-desc">{{ prompt.description || '暂无描述' }}</p>
            
            <div class="prompt-preview">
              {{ prompt.content.substring(0, 100) }}...
            </div>
            
            <div class="prompt-actions">
              <button class="btn btn-primary btn-sm" @click="usePrompt(prompt)">使用</button>
              <button class="btn btn-secondary btn-sm" @click="editPrompt(prompt)">编辑</button>
              <button 
                v-if="!prompt.is_system" 
                class="btn btn-danger btn-sm" 
                @click="deletePrompt(prompt)"
              >删除</button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.header-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.filter-card {
  padding: 12px 20px;
}

.filter-tabs {
  display: flex;
  gap: 8px;
}

.filter-tab {
  background: none;
  border: 1px solid rgba(76, 175, 80, 0.3);
  color: #81c784;
  padding: 8px 16px;
  border-radius: 20px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.3s;
}

.filter-tab.active {
  background: #4caf50;
  border-color: #4caf50;
  color: white;
}

.editor-card {
  max-width: 800px;
  margin: 0 auto;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  color: #a5d6a7;
  font-size: 13px;
  margin-bottom: 8px;
}

.form-group input[type="text"],
.form-group textarea {
  width: 100%;
  padding: 12px;
  background: rgba(0, 30, 20, 0.8);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 8px;
  color: #e8f5e9;
  font-size: 14px;
  font-family: inherit;
}

.form-group textarea {
  resize: vertical;
  min-height: 200px;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #4caf50;
}

.checkbox-group {
  margin-top: 16px;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #81c784;
}

.checkbox-group input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.editor-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
}

.loading, .empty {
  text-align: center;
  padding: 40px;
  color: #81c784;
}

.prompt-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.prompt-item {
  background: rgba(0, 30, 20, 0.4);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 12px;
  padding: 20px;
}

.prompt-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.prompt-header h3 {
  color: #e8f5e9;
  font-size: 16px;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: normal;
}

.badge.default {
  background: #4caf50;
  color: white;
}

.badge.system {
  background: #2196f3;
  color: white;
}

.badge.public {
  background: rgba(76, 175, 80, 0.2);
  color: #81c784;
}

.prompt-stats {
  font-size: 12px;
  color: #666;
}

.prompt-desc {
  color: #a5d6a7;
  font-size: 13px;
  margin: 0 0 12px 0;
}

.prompt-preview {
  background: rgba(0, 0, 0, 0.3);
  padding: 12px;
  border-radius: 8px;
  font-size: 12px;
  color: #666;
  margin-bottom: 16px;
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.prompt-actions {
  display: flex;
  gap: 8px;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.btn-danger {
  background: rgba(244, 67, 54, 0.2);
  border: 1px solid rgba(244, 67, 54, 0.3);
  color: #ef5350;
}
</style>