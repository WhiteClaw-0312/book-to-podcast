# 架构变更记录

## 2026-03-12: 采用 pdf2skills 方案

### 变更原因
用户发现 pdf2skills 项目可以一步完成 PDF → Skill 转换，优于原先的 OCR + 知识库构建两步方案。

### 新架构
```
PDF/EPUB → pdf2skills → Skill (含知识库) → 播客文稿 → TTS → 音频播客
```

### 旧架构（已废弃）
```
PDF → OCR → 知识库构建 → 播客文稿 → TTS → 音频播客
```

### pdf2skills 优势
1. **一步到位**: PDF/EPUB 直接转换为可执行 Skill
2. **知识库内置**: Skill 的 references/ 目录包含结构化知识库
3. **交互功能**: Skill 具备交互能力，可直接用于 AI Agent
4. **效率提升**: 30分钟内完成一本书的转换
5. **专业输出**: 包含 SKILL.md、scripts/、references/、templates/

### 保留模块
- `src/parser/` - 备选方案，当 pdf2skills 不可用时使用
- `src/knowledge/` - 备选方案，当 pdf2skills 不可用时使用
- `src/script/` - 播客文稿生成（核心模块）
- `src/tts/` - TTS 语音合成（核心模块）

### 文件变更
- 更新 README.md
- 更新 MEMORY.md
- 创建 docs/ARCHITECTURE.md
- 标记旧模块为备选方案

---
*记录者: 白 (HandFoot 首席程序员)*