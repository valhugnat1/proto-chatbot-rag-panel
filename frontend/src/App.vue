<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import Sidebar from './components/Sidebar.vue'
import MessageBubble from './components/MessageBubble.vue'
import ChatInput from './components/ChatInput.vue'
import WelcomeScreen from './components/WelcomeScreen.vue'
import { streamChatCompletion } from './services/api.js'

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const STORAGE_KEY = 'bnp-chatbot-conversations'

// Each conversation: { id, title, messages: [{role, content}], createdAt }
const conversations = ref([])
const currentId = ref(null)
const isStreaming = ref(false)
const error = ref(null)
const messagesContainer = ref(null)

let abortController = null

const currentConversation = computed(() =>
  conversations.value.find((c) => c.id === currentId.value) || null,
)
const currentMessages = computed(() => currentConversation.value?.messages ?? [])

// ---------------------------------------------------------------------------
// Persistence
// ---------------------------------------------------------------------------

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed)) {
      conversations.value = parsed
      if (parsed.length > 0) {
        currentId.value = parsed[0].id
      }
    }
  } catch (err) {
    console.warn('Failed to load conversations from storage:', err)
  }
}

function saveToStorage() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations.value))
  } catch (err) {
    console.warn('Failed to save conversations to storage:', err)
  }
}

watch(conversations, saveToStorage, { deep: true })

// ---------------------------------------------------------------------------
// Conversation lifecycle
// ---------------------------------------------------------------------------

function newConversation() {
  const id = `conv-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  const conv = {
    id,
    title: 'Nouvelle conversation',
    messages: [],
    createdAt: new Date().toISOString(),
  }
  conversations.value.unshift(conv)
  currentId.value = id
  error.value = null
}

function selectConversation(id) {
  if (isStreaming.value) return
  currentId.value = id
  error.value = null
}

function deleteConversation(id) {
  const idx = conversations.value.findIndex((c) => c.id === id)
  if (idx === -1) return
  conversations.value.splice(idx, 1)
  if (currentId.value === id) {
    currentId.value = conversations.value[0]?.id ?? null
  }
}

// ---------------------------------------------------------------------------
// Streaming
// ---------------------------------------------------------------------------

async function scrollToBottom() {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

async function sendMessage(text) {
  if (!text.trim() || isStreaming.value) return

  // Make sure we have a conversation
  if (!currentConversation.value) {
    newConversation()
  }

  const conv = currentConversation.value
  error.value = null

  // Append the user message
  conv.messages.push({ role: 'user', content: text })

  // Auto-title from the first user message
  if (conv.title === 'Nouvelle conversation') {
    conv.title = text.slice(0, 40) + (text.length > 40 ? '…' : '')
  }

  // Append a placeholder assistant message we'll fill in
  conv.messages.push({ role: 'assistant', content: '' })
  await scrollToBottom()

  isStreaming.value = true
  abortController = new AbortController()

  // Build the history we send to the backend (without the empty placeholder).
  const historyForBackend = conv.messages
    .slice(0, -1)
    .map((m) => ({ role: m.role, content: m.content }))

  try {
    for await (const token of streamChatCompletion(
      historyForBackend,
      abortController.signal,
    )) {
      const last = conv.messages[conv.messages.length - 1]
      last.content += token
      await scrollToBottom()
    }
  } catch (err) {
    if (err.name === 'AbortError') {
      const last = conv.messages[conv.messages.length - 1]
      if (last && last.role === 'assistant') {
        last.content += '\n\n_(Génération interrompue)_'
      }
    } else {
      console.error('Stream error:', err)
      error.value = err.message || 'Une erreur est survenue'
      // Remove the empty placeholder if nothing was streamed
      const last = conv.messages[conv.messages.length - 1]
      if (last && last.role === 'assistant' && !last.content) {
        conv.messages.pop()
      }
    }
  } finally {
    isStreaming.value = false
    abortController = null
  }
}

function stopStreaming() {
  if (abortController) {
    abortController.abort()
  }
}

function handleSuggestion(prompt) {
  sendMessage(prompt)
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

onMounted(() => {
  loadFromStorage()
  if (conversations.value.length === 0) {
    newConversation()
  }
})
</script>

<template>
  <div class="app">
    <Sidebar
      :conversations="conversations"
      :current-id="currentId"
      @new="newConversation"
      @select="selectConversation"
      @delete="deleteConversation"
    />

    <main class="main">
      <div class="messages-container" ref="messagesContainer">
        <WelcomeScreen
          v-if="currentMessages.length === 0"
          @suggest="handleSuggestion"
        />
        <template v-else>
          <MessageBubble
            v-for="(msg, i) in currentMessages"
            :key="i"
            :role="msg.role"
            :content="msg.content"
            :is-streaming="
              isStreaming &&
              i === currentMessages.length - 1 &&
              msg.role === 'assistant'
            "
          />
          <div v-if="error" class="error-bubble">
            <strong>Erreur :</strong> {{ error }}
          </div>
        </template>
      </div>

      <ChatInput
        :disabled="isStreaming"
        :is-streaming="isStreaming"
        @send="sendMessage"
        @stop="stopStreaming"
      />
    </main>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  height: 100vh;
  width: 100vw;
  background: var(--bg-app);
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.error-bubble {
  max-width: 768px;
  margin: 16px auto;
  padding: 12px 16px;
  background: rgba(255, 107, 107, 0.1);
  border: 1px solid rgba(255, 107, 107, 0.3);
  border-radius: 8px;
  color: #ff8a8a;
  font-size: 14px;
  width: calc(100% - 32px);
}

@media (max-width: 768px) {
  .app {
    flex-direction: column;
  }
  :deep(.sidebar) {
    width: 100%;
    height: auto;
    max-height: 200px;
  }
}
</style>
