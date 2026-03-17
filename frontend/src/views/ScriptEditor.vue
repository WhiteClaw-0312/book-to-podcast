<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { apiFetch, getUser, getToken } from '../api'

const router = useRouter()
const route = useRoute()

const user = ref<any>(null)
const loading = ref(true)
const saving = ref(false)
const book = ref<any>(null)
const chapter = ref<any>(null)
const dialogues = ref<any[]>([])

// 编辑模式
const editingIndex = ref(-1)
const editContent = ref('')

// 音色选择
const showVoiceSelector = ref(false)
const voices = ref<any[]>([])
const voiceMapping = ref<Record<string, string>>({
  '小北': 'zh-CN-XiaoxiaoNeural',
  '阿南': 'zh-CN-YunxiNeural'
})

// 角色列表（从文稿中提取）
const speakers = computed(() => {
  return [...new Set(dialogues.value.map(d => d.speaker))]
})

// 获取音色列表
const fetchVoices = async () => {
  try {
    const res = await apiFetch('/api/voices')
    if (res.ok) {
      voices.value = await res.json()
    }
  } catch (e) {
    console.error('获取音色失败', e)
  }
}

const femaleVoices = computed(() => voices.value.filter(v => v.gender === 'female'))
const maleVoices = computed(() => voices.value.filter(v => v.gender === 'male'))

// 获取数据
const fetchData = async () => {
  const bookId = route.params.id
  const chapterNum = route.query.chapter || 1
  
  try {
    // 获取书籍信息
    const bookRes = await apiFetch(`/api/books/${bookId}`)
    if (bookRes.ok) {
      book.value = await bookRes.json()
      
      // 获取指定章节的文稿
      if (book.value.chapters?.length > 0) {
        const ch = book.value.chapters.find((c: any) => c.number == chapterNum) || book.value.chapters[0]
        chapter.value = ch
        
        // 获取文稿详情
        const scriptRes = await apiFetch(`/api/books/${bookId}/chapters/${ch.number}/script`)
        if (scriptRes.ok) {
          const data = await scriptRes.json()
          dialogues.value = data.dialogues || []
        }
      }
    }
  } catch (e) {
    console.error(e)
  }
  loading.value = false
}

// 添加对话
const addDialogue = (afterIndex: number) => {
  const newDialogue = {
    speaker: speakers.value[0] || '小北',
    content: ''
  }
  dialogues.value.splice(afterIndex + 1, 0, newDialogue)
  startEdit(afterIndex + 1)
}

// 删除对话
const deleteDialogue = (index: number) => {
  if (confirm('确定删除这段对话？')) {
    dialogues.value.splice(index, 1)
  }
}

// 开始编辑
const startEdit = (index: number) => {
  editingIndex.value = index
  editContent.value = dialogues.value[index]?.content || ''
}

// 保存编辑
const saveEdit = () => {
  if (editingIndex.value >= 0) {
    dialogues.value[editingIndex.value].content = editContent.value
  }
  editingIndex.value = -1
  editContent.value = ''
}

// 取消编辑
const cancelEdit = () => {
  editingIndex.value = -1
  editContent.value = ''
}

// 更改角色
const changeSpeaker = (index: number, speaker: string) => {
  dialogues.value[index].speaker = speaker
}

// 保存文稿
const saveScript = async () => {
  if (!dialogues.value.length) {
    alert('文稿内容为空')
    return false
  }
  
  saving.value = true
  try {
    const token = getToken()
    const res = await apiFetch(`/api/books/${route.params.id}/chapters/${chapter.value.number}/script`, {
      method: 'PUT',
      headers: { 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({
        dialogues: dialogues.value
      })
    })
    
    if (res.ok) {
      saving.value = false
      return true
    } else {
      const err = await res.json()
      throw new Error(err.detail || '保存失败')
    }
  } catch (e: any) {
    alert('保存失败: ' + e.message)
    saving.value = false
    return false
  }
}

// 显示音色选择器
const openVoiceSelector = async () => {
  // 先保存文稿
  const saved = await saveScript()
  if (!saved) return
  
  showVoiceSelector.value = true
}

// 确认生成音频
const confirmGenerateAudio = async () => {
  showVoiceSelector.value = false
  
  try {
    const token = getToken()
    const res = await apiFetch(`/api/books/${route.params.id}/generate-audio`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({
        chapters: [chapter.value.number],
        voice_mapping: voiceMapping.value
      })
    })
    
    if (res.ok) {
      // 跳转回首页查看进度
      router.push('/')
    } else {
      const err = await res.json()
      throw new Error(err.detail || '生成失败')
    }
  } catch (e: any) {
    alert('生成音频失败: ' + e.message)
  }
}

// 返回
const goBack = () => {
  router.push('/')
}

onMounted(() => {
  user.value = getUser()
  if (!user.value) {
    alert('请先登录')
    router.push('/')
    return
  }
  fetchVoices()
  fetchData()
})
</script>

<template>
  <div class="container">
    <!-- Header -->
    <div class="card header-card">
      <div class="header-left">
        <button class="btn btn-secondary" @click="goBack">← 返回</button>
        <div class="title-info">
          <h1>📝 文稿编辑</h1>
          <p v-if="book">{{ book.title }} - 第{{ chapter?.number }}章</p>
        </div>
      </div>
      <div class="header-actions">
        <button class="btn btn-secondary" @click="saveScript" :disabled="saving">
          {{ saving ? '保存中...' : '保存文稿' }}
        </button>
        <button class="btn btn-primary" @click="openVoiceSelector">
          🎙️ 生成音频
        </button>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="card loading-card">
      <div class="loading">加载中...</div>
    </div>

    <!-- 编辑区域 -->
    <div v-else class="card editor-card">
      <!-- 角色提示 -->
      <div class="speakers-info">
        <span class="label">当前角色：</span>
        <span v-for="speaker in speakers" :key="speaker" class="speaker-tag">
          {{ speaker }}
        </span>
        <span v-if="speakers.length === 0" class="no-speakers">暂无角色</span>
      </div>

      <!-- 对话列表 -->
      <div class="dialogues-list">
        <div 
          v-for="(d, i) in dialogues" 
          :key="i" 
          class="dialogue-item"
          :class="{ editing: editingIndex === i }"
        >
          <div class="dialogue-header">
            <select 
              :value="d.speaker" 
              @change="changeSpeaker(i, ($event.target as HTMLSelectElement).value)"
              class="speaker-select"
            >
              <option v-for="s in speakers" :key="s" :value="s">{{ s }}</option>
              <option value="小北">小北</option>
              <option value="阿南">阿南</option>
            </select>
            <div class="dialogue-actions">
              <button class="btn-icon" @click="startEdit(i)" title="编辑">✏️</button>
              <button class="btn-icon" @click="addDialogue(i)" title="在下方添加">➕</button>
              <button class="btn-icon danger" @click="deleteDialogue(i)" title="删除">🗑️</button>
            </div>
          </div>
          
          <!-- 显示模式 -->
          <div v-if="editingIndex !== i" class="dialogue-content" @click="startEdit(i)">
            {{ d.content || '点击编辑内容...' }}
          </div>
          
          <!-- 编辑模式 -->
          <div v-else class="dialogue-edit">
            <textarea 
              v-model="editContent" 
              placeholder="输入对话内容..."
              rows="3"
              autofocus
            ></textarea>
            <div class="edit-actions">
              <button class="btn btn-secondary btn-sm" @click="cancelEdit">取消</button>
              <button class="btn btn-primary btn-sm" @click="saveEdit">确定</button>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="dialogues.length === 0" class="empty-state">
          <p>暂无文稿内容</p>
          <p class="hint">请先生成文稿，或手动添加对话</p>
          <button class="btn btn-primary" @click="dialogues.push({ speaker: '小北', content: '' })">
            添加第一段对话
          </button>
        </div>
      </div>

      <!-- 底部操作 -->
      <div class="bottom-actions" v-if="dialogues.length > 0">
        <button class="btn btn-secondary" @click="dialogues.push({ speaker: speakers[0] || '小北', content: '' })">
          ➕ 添加对话
        </button>
      </div>
    </div>

    <!-- 统计信息 -->
    <div class="card stats-card" v-if="dialogues.length > 0">
      <div class="stat-item">
        <span class="stat-label">对话数量</span>
        <span class="stat-value">{{ dialogues.length }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">总字数</span>
        <span class="stat-value">{{ dialogues.reduce((sum, d) => sum + (d.content?.length || 0), 0) }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">预估时长</span>
        <span class="stat-value">{{ Math.ceil(dialogues.reduce((sum, d) => sum + (d.content?.length || 0), 0) / 200) }} 分钟</span>
      </div>
    </div>
    
    <!-- 音色选择弹窗 -->
    <div v-if="showVoiceSelector" class="modal-overlay" @click.self="showVoiceSelector = false">
      <div class="modal-content voice-modal">
        <div class="modal-header">
          <h2>🎭 选择音色</h2>
          <button class="close-btn" @click="showVoiceSelector = false">×</button>
        </div>
        
        <div class="voice-selector-body">
          <p class="voice-hint">为播客中的角色选择合适的音色</p>
          
          <!-- 小北（女声） -->
          <div class="voice-group" v-if="speakers.includes('小北')">
            <h3>👩 小北（女主持）</h3>
            <div class="voice-options">
              <div 
                v-for="v in femaleVoices" 
                :key="v.id"
                :class="['voice-option', { selected: voiceMapping['小北'] === v.voice_id }]"
                @click="voiceMapping['小北'] = v.voice_id"
              >
                <div class="voice-header">
                  <div class="voice-name">{{ v.speaker_name }}</div>
                </div>
                <div class="voice-desc">{{ v.description }}</div>
              </div>
            </div>
          </div>
          
          <!-- 阿南（男声） -->
          <div class="voice-group" v-if="speakers.includes('阿南')">
            <h3>👨 阿南（男主持）</h3>
            <div class="voice-options">
              <div 
                v-for="v in maleVoices" 
                :key="v.id"
                :class="['voice-option', { selected: voiceMapping['阿南'] === v.voice_id }]"
                @click="voiceMapping['阿南'] = v.voice_id"
              >
                <div class="voice-header">
                  <div class="voice-name">{{ v.speaker_name }}</div>
                </div>
                <div class="voice-desc">{{ v.description }}</div>
              </div>
            </div>
          </div>
          
          <div class="voice-actions">
            <button class="btn btn-secondary" @click="showVoiceSelector = false">取消</button>
            <button class="btn btn-primary" @click="confirmGenerateAudio">
              🎙️ 开始生成
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.header-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.title-info h1 {
  color: #4caf50;
  font-size: 20px;
  margin: 0;
}

.title-info p {
  color: #81c784;
  font-size: 13px;
  margin: 4px 0 0 0;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.loading-card {
  text-align: center;
  padding: 40px;
}

.loading {
  color: #81c784;
}

.editor-card {
  padding: 24px;
}

.speakers-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
  padding: 12px;
  background: rgba(76, 175, 80, 0.1);
  border-radius: 8px;
}

.speakers-info .label {
  color: #81c784;
  font-size: 13px;
}

.speaker-tag {
  background: #4caf50;
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
}

.no-speakers {
  color: #666;
  font-size: 13px;
}

.dialogues-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dialogue-item {
  background: rgba(0, 30, 20, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.3s;
}

.dialogue-item.editing {
  border-color: #4caf50;
  box-shadow: 0 0 12px rgba(76, 175, 80, 0.3);
}

.dialogue-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.speaker-select {
  background: rgba(76, 175, 80, 0.2);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 6px;
  padding: 6px 12px;
  color: #e8f5e9;
  font-size: 13px;
  cursor: pointer;
}

.dialogue-actions {
  display: flex;
  gap: 8px;
}

.btn-icon {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  opacity: 0.6;
  transition: opacity 0.3s;
}

.btn-icon:hover {
  opacity: 1;
}

.btn-icon.danger:hover {
  opacity: 1;
  filter: brightness(0.8) sepia(1) hue-rotate(-50deg);
}

.dialogue-content {
  color: #e8f5e9;
  font-size: 14px;
  line-height: 1.6;
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
  min-height: 40px;
}

.dialogue-content:hover {
  background: rgba(76, 175, 80, 0.1);
}

.dialogue-edit textarea {
  width: 100%;
  padding: 12px;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 8px;
  color: #e8f5e9;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  min-height: 80px;
}

.dialogue-edit textarea:focus {
  outline: none;
  border-color: #4caf50;
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}

.btn-sm {
  padding: 6px 16px;
  font-size: 13px;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #81c784;
}

.empty-state .hint {
  font-size: 13px;
  color: #666;
  margin-bottom: 20px;
}

.bottom-actions {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid rgba(76, 175, 80, 0.2);
  text-align: center;
}

.stats-card {
  display: flex;
  justify-content: space-around;
  padding: 16px;
}

.stat-item {
  text-align: center;
}

.stat-label {
  display: block;
  color: #81c784;
  font-size: 12px;
  margin-bottom: 4px;
}

.stat-value {
  display: block;
  color: #4caf50;
  font-size: 20px;
  font-weight: 600;
}

/* Modal */
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

/* Voice selector */
.voice-modal {
  max-width: 500px;
}

.voice-selector-body {
  padding: 10px 0;
}

.voice-hint {
  color: #81c784;
  font-size: 14px;
  margin-bottom: 20px;
}

.voice-group {
  margin-bottom: 20px;
}

.voice-group h3 {
  color: #e8f5e9;
  font-size: 14px;
  margin: 0 0 10px 0;
}

.voice-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.voice-option {
  background: rgba(0, 30, 20, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 8px;
  padding: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.voice-option:hover {
  border-color: rgba(76, 175, 80, 0.5);
}

.voice-option.selected {
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.15);
}

.voice-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.voice-name {
  color: #e8f5e9;
  font-size: 13px;
  font-weight: 500;
}

.voice-desc {
  color: #81c784;
  font-size: 11px;
}

.voice-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid rgba(76, 175, 80, 0.2);
}
</style>