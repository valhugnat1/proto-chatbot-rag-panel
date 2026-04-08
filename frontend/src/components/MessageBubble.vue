<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps({
  role: { type: String, required: true }, // 'user' | 'assistant'
  content: { type: String, required: true },
  isStreaming: { type: Boolean, default: false },
})

// Configure marked: GFM, line breaks, no header IDs
marked.setOptions({
  gfm: true,
  breaks: true,
})

const renderedHtml = computed(() => {
  if (!props.content) return ''
  const raw = marked.parse(props.content)
  return DOMPurify.sanitize(raw)
})

const isUser = computed(() => props.role === 'user')
</script>

<template>
  <div class="message" :class="{ 'message--user': isUser, 'message--assistant': !isUser }">
    <div class="avatar" :class="{ 'avatar--user': isUser, 'avatar--assistant': !isUser }">
      <template v-if="isUser">U</template>
      <template v-else>
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="3" />
          <path d="M8 12h8M12 8v8" />
        </svg>
      </template>
    </div>

    <div class="content">
      <div class="role-label">{{ isUser ? 'Vous' : 'Assistant BNP' }}</div>
      <div class="md-content" v-html="renderedHtml"></div>
      <span v-if="isStreaming" class="cursor"></span>
    </div>
  </div>
</template>

<style scoped>
.message {
  display: flex;
  gap: 16px;
  padding: 24px 0;
  max-width: 768px;
  margin: 0 auto;
  width: 100%;
}

.avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 13px;
}
.avatar--user {
  background: #5f5f5f;
  color: #fff;
}
.avatar--assistant {
  background: var(--bnp-green);
  color: #fff;
}

.content {
  flex: 1;
  min-width: 0;
  padding-top: 4px;
}

.role-label {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
  color: var(--text-primary);
}

.md-content {
  color: var(--text-primary);
  font-size: 15px;
  line-height: 1.65;
  word-wrap: break-word;
}

.cursor {
  display: inline-block;
  width: 8px;
  height: 16px;
  background: var(--text-primary);
  margin-left: 2px;
  vertical-align: middle;
  animation: blink 1s steps(2, start) infinite;
}

@keyframes blink {
  to {
    visibility: hidden;
  }
}
</style>
