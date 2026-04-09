<script setup>
import { ref } from "vue";

defineProps({
  conversations: { type: Array, required: true },
  currentId: { type: String, default: null },
  isOpen: { type: Boolean, default: false },
});

const emit = defineEmits(["new", "select", "delete", "delete-all", "close"]);

function confirmDeleteAll() {
  if (
    window.confirm(
      "Supprimer toutes les conversations ? Cette action est irréversible.",
    )
  ) {
    emit("delete-all");
  }
}
</script>

<template>
  <div
    class="sidebar-backdrop"
    :class="{ 'sidebar-backdrop--visible': isOpen }"
    @click="emit('close')"
  ></div>
  <aside class="sidebar" :class="{ 'sidebar--open': isOpen }">
    <div class="sidebar-header">
      <div class="brand">
        <div class="brand-logo">B</div>
        <div class="brand-text">
          <div class="brand-title">BNP Paribas</div>
          <div class="brand-sub">Assistant virtuel</div>
        </div>
        <button
          class="close-btn"
          @click="emit('close')"
          title="Fermer"
          aria-label="Fermer le menu"
        >
          <svg
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>
      <button
        class="new-chat-btn"
        @click="emit('new')"
        title="Nouvelle conversation"
      >
        <svg
          viewBox="0 0 24 24"
          width="16"
          height="16"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M12 5v14M5 12h14" />
        </svg>
        Nouvelle conversation
      </button>
    </div>

    <div class="conversations">
      <div v-if="conversations.length === 0" class="empty">
        Aucune conversation
      </div>
      <div
        v-for="conv in conversations"
        :key="conv.id"
        class="conv-item"
        :class="{ 'conv-item--active': conv.id === currentId }"
        @click="emit('select', conv.id)"
      >
        <span class="conv-title">{{
          conv.title || "Nouvelle conversation"
        }}</span>
        <button
          class="delete-btn"
          @click.stop="emit('delete', conv.id)"
          title="Supprimer"
          aria-label="Supprimer la conversation"
        >
          <svg
            viewBox="0 0 24 24"
            width="14"
            height="14"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path
              d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"
            />
          </svg>
        </button>
      </div>
    </div>

    <div class="sidebar-footer">
      <button
        v-if="conversations.length > 0"
        class="delete-all-btn"
        @click="confirmDeleteAll"
        title="Supprimer toutes les conversations"
      >
        <svg
          viewBox="0 0 24 24"
          width="14"
          height="14"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path
            d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"
          />
        </svg>
        Tout supprimer
      </button>

      <div class="powered-by">
        <span>Propulsé par</span>
        <img class="mistral-mark" src="/mistral_logo.png" alt="Mistral AI" />
        <span class="mistral-name">Mistral AI</span>
      </div>

      <div class="disclaimer">Démo — Non affilié à BNP Paribas</div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 280px;
  background: var(--bg-sidebar);
  display: flex;
  flex-direction: column;
  height: 100%;
  border-right: 1px solid #000;
  flex-shrink: 0;
}

.sidebar-backdrop {
  display: none;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #000;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.brand-logo {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: var(--bnp-green);
  color: #fff;
  font-weight: 700;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.brand-text {
  flex: 1;
  min-width: 0;
}
.brand-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
}
.brand-sub {
  font-size: 12px;
  color: var(--text-muted);
}

.close-btn {
  display: none;
  color: var(--text-secondary);
  padding: 6px;
  border-radius: 6px;
}
.close-btn:hover {
  color: var(--text-primary);
  background: #2a2a2a;
}

.new-chat-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--bnp-green);
  color: #fff;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.15s;
}
.new-chat-btn:hover {
  background: var(--bnp-green-hover);
}

.conversations {
  flex: 1;
  overflow-y: auto;
  padding: 12px 8px;
}

.empty {
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
  padding: 24px 0;
}

.conv-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 2px;
}
.conv-item:hover {
  background: #2a2a2a;
}
.conv-item--active {
  background: #2f2f2f;
}

.conv-title {
  flex: 1;
  font-size: 14px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.delete-btn {
  opacity: 0;
  color: var(--text-muted);
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition:
    opacity 0.15s,
    color 0.15s;
}
.conv-item:hover .delete-btn,
.conv-item--active .delete-btn {
  opacity: 1;
}
.delete-btn:hover {
  color: #ff6b6b;
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid #000;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.delete-all-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: 12px;
  color: var(--text-secondary);
  background: transparent;
  border: 1px solid var(--border-input);
  border-radius: 8px;
  transition:
    color 0.15s,
    border-color 0.15s,
    background 0.15s;
}
.delete-all-btn:hover {
  color: #ff6b6b;
  border-color: #ff6b6b;
  background: rgba(255, 107, 107, 0.08);
}

.powered-by {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-muted);
}
.mistral-mark {
  height: 16px;
  width: auto;
  display: block;
  object-fit: contain;
}
.mistral-name {
  font-weight: 600;
  color: var(--text-secondary);
}

.disclaimer {
  font-size: 11px;
  color: var(--text-muted);
  text-align: center;
}

/* Mobile: sidebar becomes an off-canvas drawer */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    height: 100%;
    width: 82%;
    max-width: 320px;
    z-index: 1000;
    transform: translateX(-100%);
    transition: transform 0.25s ease;
    box-shadow: 2px 0 24px rgba(0, 0, 0, 0.5);
  }
  .sidebar--open {
    transform: translateX(0);
  }
  .sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 999;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.25s ease;
  }
  .sidebar-backdrop--visible {
    opacity: 1;
    pointer-events: auto;
  }
  .close-btn {
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .delete-btn {
    opacity: 1;
  }
}
</style>
