<script setup>
const emit = defineEmits(['suggest'])

const suggestions = [
  {
    title: 'Frais bancaires',
    prompt: 'Quels sont les frais d\'une carte Visa Premier ?',
  },
  {
    title: 'Information compte',
    prompt: 'Quel est le solde de Jean Dupont ?',
  },
  {
    title: 'Produits BNP',
    prompt: 'Quels sont les avantages d\'un Livret A ?',
  },
  {
    title: 'Investissement',
    prompt: 'Comment ouvrir un PEA chez BNP Paribas ?',
  },
]
</script>

<template>
  <div class="welcome">
    <div class="welcome-header">
      <div class="logo">B</div>
      <h1>Comment puis-je vous aider ?</h1>
      <p class="subtitle">Assistant virtuel BNP Paribas</p>
    </div>

    <div class="suggestions">
      <button
        v-for="s in suggestions"
        :key="s.title"
        class="suggestion"
        @click="emit('suggest', s.prompt)"
      >
        <div class="suggestion-title">{{ s.title }}</div>
        <div class="suggestion-prompt">{{ s.prompt }}</div>
      </button>
    </div>
  </div>
</template>

<style scoped>
.welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  max-width: 768px;
  margin: 0 auto;
  width: 100%;
}

.welcome-header {
  text-align: center;
  margin-bottom: 40px;
}

.logo {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: var(--bnp-green);
  color: #fff;
  font-weight: 700;
  font-size: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
}

h1 {
  font-size: 28px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: var(--text-primary);
}

.subtitle {
  color: var(--text-muted);
  font-size: 15px;
  margin: 0;
}

.suggestions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
  width: 100%;
  max-width: 640px;
}

.suggestion {
  text-align: left;
  padding: 16px 18px;
  background: var(--bg-input);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-md);
  transition: background 0.15s, border-color 0.15s;
}
.suggestion:hover {
  background: var(--bg-input-hover);
  border-color: var(--bnp-green);
}

.suggestion-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
  margin-bottom: 4px;
}
.suggestion-prompt {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.4;
}
</style>
