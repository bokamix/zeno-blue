<template>
    <div class="input-suggestions" ref="containerRef">
        <!-- Main container that morphs -->
        <div
            class="morph-container"
            :class="{ expanded }"
        >
            <!-- Button / Hub (same element, morphs) -->
            <button
                class="hub-button"
                :class="{ expanded }"
                @click="toggle"
            >
                <Sparkles v-if="!expanded" class="w-4 h-4 icon" />
                <span class="label">{{ expanded ? $t('suggestions.buttonExpanded') : $t('suggestions.buttonCollapsed') }}</span>
            </button>

            <!-- Suggestion bubbles - circle on desktop -->
            <template v-if="expanded">
                <button
                    v-for="(item, index) in suggestions"
                    :key="item.id"
                    class="bubble desktop-bubble"
                    :style="getBubbleStyle(index)"
                    @click.stop="selectItem(item)"
                >
                    <component :is="item.icon" class="w-5 h-5" />
                    <span>{{ item.label }}</span>
                </button>
            </template>

            <!-- Suggestion list - mobile only -->
            <div v-if="expanded" class="mobile-list">
                <button
                    v-for="(item, index) in suggestions"
                    :key="item.id"
                    class="mobile-item"
                    :style="{ animationDelay: `${0.1 + index * 0.05}s` }"
                    @click.stop="selectItem(item)"
                >
                    <component :is="item.icon" class="w-5 h-5" />
                    <span>{{ item.label }}</span>
                </button>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
    Sparkles,
    Rocket,
    Search,
    Type,
    Calendar,
    TrendingUp,
    Presentation
} from 'lucide-vue-next'

const { t } = useI18n()

const emit = defineEmits(['select'])

const expanded = ref(false)
const containerRef = ref(null)

// Close on click outside
const handleClickOutside = (event) => {
    if (expanded.value && containerRef.value && !containerRef.value.contains(event.target)) {
        expanded.value = false
    }
}

// Close on Escape key
const handleKeydown = (event) => {
    if (event.key === 'Escape' && expanded.value) {
        expanded.value = false
    }
}

onMounted(() => {
    document.addEventListener('click', handleClickOutside)
    document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside)
    document.removeEventListener('keydown', handleKeydown)
})

// Suggestion items with icons - labels and prompts come from i18n
const suggestionItems = [
    { id: 'business', icon: Rocket },
    { id: 'social', icon: Search },
    { id: 'landing', icon: Type },
    { id: 'plan', icon: Calendar },
    { id: 'marketing', icon: TrendingUp },
    { id: 'presentation', icon: Presentation }
]

// Computed suggestions with translated labels and prompts
const suggestions = computed(() =>
    suggestionItems.map(item => ({
        ...item,
        label: t(`suggestions.${item.id}.label`),
        prompt: t(`suggestions.${item.id}.prompt`)
    }))
)

// Calculate bubble position in a circle
const getBubbleStyle = (index) => {
    const total = suggestions.value.length
    const radius = 210
    const startAngle = -90 // Start from top
    const angleStep = 360 / total
    const angle = startAngle + (index * angleStep)
    const radian = (angle * Math.PI) / 180

    const x = Math.cos(radian) * radius
    const y = Math.sin(radian) * radius

    return {
        '--bubble-x': `${x}px`,
        '--bubble-y': `${y}px`,
        '--delay': `${0.1 + index * 0.05}s`
    }
}

const toggle = () => {
    expanded.value = !expanded.value
}

const selectItem = (item) => {
    emit('select', item)
    expanded.value = false
}
</script>

<style scoped>
.input-suggestions {
    position: absolute;
    bottom: calc(100% + 40px);
    left: 50%;
    transform: translateX(-50%);
    z-index: 30;
}

.morph-container {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.8s cubic-bezier(0.34, 1.2, 0.64, 1);
}

.morph-container.expanded {
    transform: translateY(-80px);
}

/* The button that morphs into hub */
.hub-button {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 180px;
    height: 44px;
    padding: 12px 20px;
    border-radius: 999px;
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.15), rgba(14, 165, 233, 0.1));
    border: 1px solid rgba(37, 99, 235, 0.3);
    color: var(--text-primary);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    backdrop-filter: blur(12px);
    box-shadow: 0 4px 24px rgba(37, 99, 235, 0.15);
    transition: all 0.8s cubic-bezier(0.34, 1.2, 0.64, 1);
    white-space: nowrap;
    overflow: hidden;
}

.hub-button:hover {
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.25), rgba(14, 165, 233, 0.2));
    border-color: rgba(37, 99, 235, 0.5);
    box-shadow: 0 6px 32px rgba(37, 99, 235, 0.25);
}

.hub-button .icon {
    color: var(--accent-glow, #3b82f6);
    transition: opacity 0.3s ease;
}

.hub-button .label {
    transition: opacity 0.2s ease;
}

/* Expanded state - morphs into circle */
.hub-button.expanded {
    width: 140px;
    height: 140px;
    padding: 16px;
    border-radius: 50%;
    font-size: 13px;
    text-align: center;
    color: var(--text-secondary);
    box-shadow:
        0 0 60px rgba(37, 99, 235, 0.25),
        inset 0 0 30px rgba(255, 255, 255, 0.05);
    animation: hub-pulse 2.5s ease-in-out infinite;
}

.hub-button.expanded .label {
    max-width: 110px;
    white-space: normal;
    line-height: 1.3;
}

@keyframes hub-pulse {
    0%, 100% {
        box-shadow:
            0 0 60px rgba(37, 99, 235, 0.25),
            inset 0 0 30px rgba(255, 255, 255, 0.05);
    }
    50% {
        box-shadow:
            0 0 80px rgba(37, 99, 235, 0.35),
            inset 0 0 30px rgba(255, 255, 255, 0.08);
    }
}

/* Suggestion bubbles */
.bubble {
    position: absolute;
    left: calc(50% + var(--bubble-x));
    top: calc(50% + var(--bubble-y));
    translate: -50% -50%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    width: 200px;
    height: 56px;
    padding: 12px 16px;
    border-radius: 14px;
    background: linear-gradient(135deg, var(--bg-surface) 0%, rgba(37, 99, 235, 0.08) 100%);
    border: 1px solid rgba(37, 99, 235, 0.35);
    color: var(--text-primary);
    font-size: 13px;
    font-weight: 500;
    text-align: center;
    line-height: 1.3;
    cursor: pointer;
    backdrop-filter: blur(16px);
    box-shadow:
        0 4px 24px rgba(0, 0, 0, 0.12),
        0 0 0 1px rgba(255, 255, 255, 0.05) inset;
    opacity: 0;
    scale: 0.5;
    animation: bubble-appear 0.5s ease-out forwards;
    animation-delay: var(--delay);
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.bubble:hover {
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.15) 0%, rgba(14, 165, 233, 0.12) 100%);
    border-color: rgba(37, 99, 235, 0.6);
    box-shadow:
        0 8px 32px rgba(37, 99, 235, 0.25),
        0 0 0 1px rgba(255, 255, 255, 0.1) inset;
    scale: 1.05;
    z-index: 10;
}

.bubble svg {
    color: var(--accent-glow, #3b82f6);
    flex-shrink: 0;
}

.bubble span {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
}

@keyframes bubble-appear {
    to {
        opacity: 1;
        scale: 1;
    }
}

/* Mobile list - hidden on desktop */
.mobile-list {
    display: none;
}

/* Responsive */
@media (max-width: 768px) {
    .input-suggestions {
        bottom: calc(100% + 20px);
        width: 100vw;
        left: 50%;
        transform: translateX(-50%);
        padding: 0 16px;
        box-sizing: border-box;
    }

    .morph-container.expanded {
        transform: translateY(-20px);
        flex-direction: column;
        align-items: center;
    }

    .hub-button {
        width: 160px;
        height: 40px;
        padding: 10px 16px;
        font-size: 13px;
    }

    .hub-button.expanded {
        width: 100px;
        height: 100px;
        font-size: 11px;
        padding: 12px;
        margin-bottom: 16px;
    }

    /* Hide circle bubbles on mobile */
    .desktop-bubble {
        display: none;
    }

    /* Show mobile list */
    .mobile-list {
        display: flex;
        flex-direction: column;
        gap: 10px;
        width: 100%;
        max-width: 320px;
        max-height: 45vh;
        overflow-y: auto;
        padding: 4px;
        scrollbar-width: none; /* Firefox */
        -ms-overflow-style: none; /* IE/Edge */
    }

    .mobile-list::-webkit-scrollbar {
        display: none; /* Chrome/Safari */
    }

    .mobile-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 14px 18px;
        border-radius: 14px;
        background: linear-gradient(135deg, var(--bg-surface) 0%, rgba(37, 99, 235, 0.08) 100%);
        border: 1px solid rgba(37, 99, 235, 0.35);
        color: var(--text-primary);
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        backdrop-filter: blur(16px);
        box-shadow:
            0 4px 20px rgba(0, 0, 0, 0.12),
            0 0 0 1px rgba(255, 255, 255, 0.05) inset;
        transition: all 0.2s ease;
        opacity: 0;
        transform: translateY(10px);
        animation: mobile-item-appear 0.3s ease-out forwards;
    }

    .mobile-item:hover,
    .mobile-item:active {
        background: linear-gradient(135deg, rgba(37, 99, 235, 0.15) 0%, rgba(14, 165, 233, 0.12) 100%);
        border-color: rgba(37, 99, 235, 0.5);
    }

    .mobile-item svg {
        color: var(--accent-glow, #3b82f6);
        flex-shrink: 0;
    }

    @keyframes mobile-item-appear {
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
}
</style>
