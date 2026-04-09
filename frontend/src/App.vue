<script setup>
import { ref, computed, onMounted, nextTick, watch } from "vue";
import Sidebar from "./components/Sidebar.vue";
import MessageBubble from "./components/MessageBubble.vue";
import ChatInput from "./components/ChatInput.vue";
import WelcomeScreen from "./components/WelcomeScreen.vue";
import { streamChatCompletion } from "./services/api.js";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const STORAGE_KEY = "bnp-chatbot-conversations";

// Each conversation: { id, title, messages: [{role, content}], createdAt }
const conversations = ref([]);
const currentId = ref(null);
const isStreaming = ref(false);
const error = ref(null);
const messagesContainer = ref(null);
const sidebarOpen = ref(false);

let abortController = null;

const currentConversation = computed(
  () => conversations.value.find((c) => c.id === currentId.value) || null,
);
const currentMessages = computed(
  () => currentConversation.value?.messages ?? [],
);

// ---------------------------------------------------------------------------
// Persistence
// ---------------------------------------------------------------------------

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      conversations.value = parsed;
      if (parsed.length > 0) {
        currentId.value = parsed[0].id;
      }
    }
  } catch (err) {
    console.warn("Failed to load conversations from storage:", err);
  }
}

function saveToStorage() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations.value));
  } catch (err) {
    console.warn("Failed to save conversations to storage:", err);
  }
}

watch(conversations, saveToStorage, { deep: true });

// ---------------------------------------------------------------------------
// Conversation lifecycle
// ---------------------------------------------------------------------------

function newConversation() {
  const id = `conv-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const conv = {
    id,
    title: "Nouvelle conversation",
    messages: [],
    createdAt: new Date().toISOString(),
  };
  conversations.value.unshift(conv);
  currentId.value = id;
  error.value = null;
  sidebarOpen.value = false;
}

function selectConversation(id) {
  if (isStreaming.value) return;
  currentId.value = id;
  error.value = null;
  sidebarOpen.value = false;
}

function deleteConversation(id) {
  const idx = conversations.value.findIndex((c) => c.id === id);
  if (idx === -1) return;
  conversations.value.splice(idx, 1);
  if (currentId.value === id) {
    currentId.value = conversations.value[0]?.id ?? null;
  }
}

function deleteAllConversations() {
  if (isStreaming.value) stopStreaming();
  conversations.value = [];
  currentId.value = null;
  error.value = null;
  newConversation();
}

// ---------------------------------------------------------------------------
// Streaming
// ---------------------------------------------------------------------------

async function scrollToBottom() {
  await nextTick();
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
}

async function runStream(conv) {
  error.value = null;
  await scrollToBottom();

  isStreaming.value = true;
  abortController = new AbortController();

  // Build the history we send to the backend (without the empty placeholder).
  const historyForBackend = conv.messages
    .slice(0, -1)
    .map((m) => ({ role: m.role, content: m.content }));

  try {
    for await (const token of streamChatCompletion(
      historyForBackend,
      abortController.signal,
    )) {
      const last = conv.messages[conv.messages.length - 1];
      last.content += token;
      await scrollToBottom();
    }
  } catch (err) {
    if (err.name === "AbortError") {
      const last = conv.messages[conv.messages.length - 1];
      if (last && last.role === "assistant") {
        last.content += "\n\n_(Génération interrompue)_";
      }
    } else {
      console.error("Stream error:", err);
      error.value = err.message || "Une erreur est survenue";
      const last = conv.messages[conv.messages.length - 1];
      if (last && last.role === "assistant" && !last.content) {
        conv.messages.pop();
      }
    }
  } finally {
    isStreaming.value = false;
    abortController = null;
  }
}

async function sendMessage(text) {
  if (!text.trim() || isStreaming.value) return;

  if (!currentConversation.value) {
    newConversation();
  }

  const conv = currentConversation.value;

  // Append the user message
  conv.messages.push({ role: "user", content: text });

  // Auto-title from the first user message
  if (conv.title === "Nouvelle conversation") {
    conv.title = text.slice(0, 40) + (text.length > 40 ? "…" : "");
  }

  // Append a placeholder assistant message we'll fill in
  conv.messages.push({ role: "assistant", content: "" });

  await runStream(conv);
}

async function regenerateLast() {
  if (isStreaming.value) return;
  const conv = currentConversation.value;
  if (!conv || conv.messages.length === 0) return;

  // Drop the last assistant message; there must be a preceding user message.
  const last = conv.messages[conv.messages.length - 1];
  if (!last || last.role !== "assistant") return;

  conv.messages.pop();

  // Push a fresh empty assistant placeholder
  conv.messages.push({ role: "assistant", content: "" });

  await runStream(conv);
}

function stopStreaming() {
  if (abortController) {
    abortController.abort();
  }
}

function handleSuggestion(prompt) {
  sendMessage(prompt);
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

onMounted(() => {
  loadFromStorage();
  if (conversations.value.length === 0) {
    newConversation();
  }
});
</script>

<template>
  <div class="app">
    <Sidebar
      :conversations="conversations"
      :current-id="currentId"
      :is-open="sidebarOpen"
      @new="newConversation"
      @select="selectConversation"
      @delete="deleteConversation"
      @delete-all="deleteAllConversations"
      @close="sidebarOpen = false"
    />

    <main class="main">
      <!-- Mobile top bar -->
      <header class="mobile-topbar">
        <button
          class="menu-btn"
          @click="sidebarOpen = true"
          title="Ouvrir le menu"
          aria-label="Ouvrir le menu"
        >
          <svg
            viewBox="0 0 24 24"
            width="22"
            height="22"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M3 12h18M3 6h18M3 18h18" />
          </svg>
        </button>
        <div class="mobile-title">
          <div class="mobile-logo">B</div>
          <span>BNP Paribas</span>
        </div>
        <button
          class="menu-btn"
          @click="newConversation"
          title="Nouvelle conversation"
          aria-label="Nouvelle conversation"
        >
          <svg
            viewBox="0 0 24 24"
            width="20"
            height="20"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path
              d="M12 20h9M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4 12.5-12.5z"
            />
          </svg>
        </button>
      </header>

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
            :can-regenerate="
              !isStreaming &&
              i === currentMessages.length - 1 &&
              msg.role === 'assistant' &&
              msg.content.length > 0
            "
            @regenerate="regenerateLast"
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
  height: 100dvh;
  width: 100vw;
  background: var(--bg-app);
  overflow: hidden;
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
  -webkit-overflow-scrolling: touch;
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

/* Mobile top bar — hidden on desktop */
.mobile-topbar {
  display: none;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
  padding-top: calc(10px + env(safe-area-inset-top));
  background: var(--bg-sidebar);
  border-bottom: 1px solid #000;
  flex-shrink: 0;
}
.menu-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-primary);
  border-radius: 8px;
}
.menu-btn:hover {
  background: #2a2a2a;
}
.mobile-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 15px;
  color: var(--text-primary);
}
.mobile-logo {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  background: var(--bnp-green);
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 768px) {
  .mobile-topbar {
    display: flex;
  }
}
</style>
