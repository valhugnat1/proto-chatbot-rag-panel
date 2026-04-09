<script setup>
import { ref, nextTick, watch } from "vue";

const props = defineProps({
  disabled: { type: Boolean, default: false },
  isStreaming: { type: Boolean, default: false },
});

const emit = defineEmits(["send", "stop"]);

const text = ref("");
const textarea = ref(null);

async function autoGrow() {
  await nextTick();
  if (!textarea.value) return;
  textarea.value.style.height = "auto";
  const max = 200;
  textarea.value.style.height =
    Math.min(textarea.value.scrollHeight, max) + "px";
}

watch(text, autoGrow);

function handleKeydown(e) {
  // On mobile (touch devices), Enter should insert a newline instead of sending
  const isTouch = window.matchMedia("(hover: none)").matches;
  if (e.key === "Enter" && !e.shiftKey && !isTouch) {
    e.preventDefault();
    submit();
  }
}

function submit() {
  const value = text.value.trim();
  if (!value || props.disabled) return;
  emit("send", value);
  text.value = "";
  autoGrow();
}

function stop() {
  emit("stop");
}
</script>

<template>
  <div class="input-wrapper">
    <div class="input-container">
      <textarea
        ref="textarea"
        v-model="text"
        :disabled="disabled && !isStreaming"
        rows="1"
        placeholder="Posez une question à l'assistant BNP…"
        @keydown="handleKeydown"
      />
      <button
        v-if="!isStreaming"
        class="send-btn"
        :disabled="!text.trim() || disabled"
        @click="submit"
        title="Envoyer"
        aria-label="Envoyer"
      >
        <svg
          viewBox="0 0 24 24"
          width="18"
          height="18"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M12 19V5M5 12l7-7 7 7" />
        </svg>
      </button>
      <button
        v-else
        class="stop-btn"
        @click="stop"
        title="Arrêter la génération"
        aria-label="Arrêter"
      >
        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
          <rect x="6" y="6" width="12" height="12" rx="1" />
        </svg>
      </button>
    </div>
    <div class="hint">
      L'assistant peut faire des erreurs. Vérifiez les informations importantes.
    </div>
  </div>
</template>

<style scoped>
.input-wrapper {
  max-width: 768px;
  margin: 0 auto;
  width: 100%;
  padding: 12px 16px calc(16px + env(safe-area-inset-bottom));
}

.input-container {
  position: relative;
  display: flex;
  align-items: flex-end;
  background: var(--bg-input);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-lg);
  padding: 12px 52px 12px 18px;
  transition: border-color 0.15s;
}
.input-container:focus-within {
  border-color: #5f5f5f;
}

textarea {
  flex: 1;
  min-height: 24px;
  max-height: 200px;
  line-height: 1.5;
  font-size: 16px; /* 16px prevents iOS zoom-on-focus */
  color: var(--text-primary);
  overflow-y: auto;
  width: 100%;
}
textarea::placeholder {
  color: var(--text-muted);
}
textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.send-btn,
.stop-btn {
  position: absolute;
  right: 10px;
  bottom: 10px;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition:
    background 0.15s,
    opacity 0.15s;
}
.send-btn {
  background: var(--bg-button);
  color: var(--text-button);
}
.send-btn:hover:not(:disabled) {
  background: var(--bg-button-hover);
}
.send-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.stop-btn {
  background: var(--bg-button);
  color: var(--text-button);
}
.stop-btn:hover {
  background: var(--bg-button-hover);
}

.hint {
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 10px;
}

@media (max-width: 600px) {
  .input-wrapper {
    padding: 8px 10px calc(10px + env(safe-area-inset-bottom));
  }
  .input-container {
    padding: 10px 48px 10px 14px;
  }
  .hint {
    font-size: 11px;
    margin-top: 6px;
  }
}
</style>
