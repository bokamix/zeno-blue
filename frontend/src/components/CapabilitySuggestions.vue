<template>
    <div class="capability-suggestions">
        <div class="capability-grid">
            <button
                v-for="item in capabilities"
                :key="item.id"
                class="capability-card"
                @click="$emit('select', item.prompt)"
            >
                <div class="card-icon">
                    <component :is="item.icon" class="w-5 h-5" />
                </div>
                <div class="card-content">
                    <span class="card-title">{{ item.label }}</span>
                    <span class="card-desc">{{ item.description }}</span>
                </div>
            </button>
        </div>
    </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
    Rocket,
    Search,
    Type,
    Calendar,
    TrendingUp,
    Presentation
} from 'lucide-vue-next'

const { t } = useI18n()

defineEmits(['select'])

// Capability items with icons - labels, descriptions and prompts come from i18n
const capabilityItems = [
    { id: 'business', icon: Rocket },
    { id: 'social', icon: Search },
    { id: 'landing', icon: Type },
    { id: 'plan', icon: Calendar },
    { id: 'marketing', icon: TrendingUp },
    { id: 'presentation', icon: Presentation }
]

// Computed capabilities with translated labels, descriptions and prompts
const capabilities = computed(() =>
    capabilityItems.map(item => ({
        ...item,
        label: t(`capabilities.${item.id}.label`),
        description: t(`capabilities.${item.id}.description`),
        prompt: t(`capabilities.${item.id}.prompt`)
    }))
)
</script>

<style scoped>
.capability-suggestions {
    width: 100%;
    max-width: 700px;
    margin: 0 auto;
    padding: 0 1rem;
}

.capability-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
}

@media (min-width: 768px) {
    .capability-grid {
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
    }
}

.capability-card {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 1rem;
    border-radius: 1rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    color: var(--text-primary);
    text-align: left;
    cursor: pointer;
    backdrop-filter: blur(12px);
    transition: all 0.2s ease;
    min-height: 80px;
}

.capability-card:hover {
    background: var(--bg-elevated);
    border-color: rgba(37, 99, 235, 0.4);
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(37, 99, 235, 0.15);
}

.capability-card:active {
    transform: translateY(0);
}

.card-icon {
    flex-shrink: 0;
    padding: 0.5rem;
    border-radius: 0.625rem;
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.15), rgba(14, 165, 233, 0.1));
    color: var(--accent-glow, #3b82f6);
}

.card-content {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    min-width: 0;
}

.card-title {
    font-size: 0.875rem;
    font-weight: 600;
    line-height: 1.3;
    color: var(--text-primary);
}

.card-desc {
    font-size: 0.75rem;
    line-height: 1.4;
    color: var(--text-muted);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

/* Touch target size for mobile */
@media (max-width: 767px) {
    .capability-card {
        min-height: 72px;
        padding: 0.875rem;
    }

    .card-icon {
        padding: 0.375rem;
    }

    .card-icon svg {
        width: 1rem;
        height: 1rem;
    }

    .card-title {
        font-size: 0.8125rem;
    }

    .card-desc {
        font-size: 0.6875rem;
        -webkit-line-clamp: 2;
    }
}

/* Light mode - better definition and contrast */
[data-theme="light"] .capability-card {
    background: #ffffff;
    border: 1px solid rgba(0, 0, 0, 0.1);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.06);
}

[data-theme="light"] .capability-card:hover {
    background: #ffffff;
    border-color: rgba(79, 70, 229, 0.4);
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.15), 0 2px 4px rgba(0, 0, 0, 0.05);
}

[data-theme="light"] .card-icon {
    background: linear-gradient(135deg, rgba(79, 70, 229, 0.12), rgba(124, 58, 237, 0.08));
    color: #2563eb;
}
</style>
