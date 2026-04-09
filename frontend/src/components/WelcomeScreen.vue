<script setup>
import { ref, onMounted } from "vue";

const emit = defineEmits(["suggest"]);

const ALL_SUGGESTIONS = [
  {
    title: "Frais bancaires",
    prompt: "Quels sont les frais d'une carte Visa Premier ?",
  },
  { title: "Information compte", prompt: "Quel est le solde de Jean Dupont ?" },
  { title: "Produits BNP", prompt: "Quels sont les avantages d'un Livret A ?" },
  {
    title: "Investissement",
    prompt: "Comment ouvrir un PEA chez BNP Paribas ?",
  },
  {
    title: "Crédit immobilier",
    prompt: "Quelles sont les conditions pour obtenir un prêt immobilier ?",
  },
  {
    title: "Assurance vie",
    prompt:
      "Quelle est la différence entre une assurance vie en euros et en unités de compte ?",
  },
  {
    title: "Carte bleue",
    prompt: "Comment faire opposition à ma carte bancaire ?",
  },
  {
    title: "Virement international",
    prompt: "Combien coûte un virement SEPA vers l'Allemagne ?",
  },
  {
    title: "Découvert autorisé",
    prompt: "Comment demander une augmentation de mon découvert autorisé ?",
  },
  { title: "Épargne", prompt: "Quel est le plafond du LDDS en 2025 ?" },
  {
    title: "Assistance",
    prompt: "Comment contacter mon conseiller BNP Paribas ?",
  },
  {
    title: "Prêt étudiant",
    prompt: "Quelles sont les offres de prêt étudiant disponibles ?",
  },
  {
    title: "Changement RIB",
    prompt: "Comment obtenir un RIB de mon compte courant ?",
  },
  {
    title: "Fiscalité",
    prompt: "Comment sont imposés les intérêts d'un PEL ?",
  },
  {
    title: "Application mobile",
    prompt: "Comment activer l'authentification biométrique sur l'app BNP ?",
  },
  {
    title: "Bourse",
    prompt: "Comment passer un ordre de bourse depuis mon compte-titres ?",
  },
];

const suggestions = ref([]);

function pickRandom() {
  const shuffled = [...ALL_SUGGESTIONS].sort(() => Math.random() - 0.5);
  suggestions.value = shuffled.slice(0, 4);
}

onMounted(pickRandom);
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

    <button class="shuffle-btn" @click="pickRandom" title="Autres suggestions">
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
        <path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5" />
      </svg>
      Autres suggestions
    </button>

    <div class="powered-by">
      <span>Propulsé par</span>
      <img class="mistral-mark" src="/mistral_logo.png" alt="Mistral AI" />
      <span class="mistral-name">Mistral AI</span>
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
  padding: 24px 16px;
  max-width: 768px;
  margin: 0 auto;
  width: 100%;
}

.welcome-header {
  text-align: center;
  margin-bottom: 32px;
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
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
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
  transition:
    background 0.15s,
    border-color 0.15s;
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

.shuffle-btn {
  margin-top: 16px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: 12px;
  color: var(--text-secondary);
  background: transparent;
  border: 1px solid var(--border-input);
  border-radius: 999px;
  transition:
    color 0.15s,
    border-color 0.15s;
}
.shuffle-btn:hover {
  color: var(--text-primary);
  border-color: var(--bnp-green);
}

.powered-by {
  margin-top: 28px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
}
.mistral-mark {
  height: 18px;
  width: auto;
  display: block;
  object-fit: contain;
}
.mistral-name {
  font-weight: 600;
  color: var(--text-secondary);
}

@media (max-width: 600px) {
  h1 {
    font-size: 22px;
  }
  .welcome-header {
    margin-bottom: 24px;
  }
  .suggestions {
    grid-template-columns: 1fr;
  }
  .suggestion {
    padding: 14px 16px;
  }
}
</style>
