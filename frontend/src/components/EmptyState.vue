<template>
    <div class="empty-state flex flex-col h-full relative overflow-hidden">
        <!-- Subtle radial gradient background -->
        <div class="absolute inset-0 overflow-hidden pointer-events-none">
            <div class="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-gradient-radial from-blue-500/5 via-transparent to-transparent rounded-full blur-3xl"></div>
            <div class="absolute top-1/3 left-1/3 w-[400px] h-[400px] bg-gradient-radial from-sky-500/5 via-transparent to-transparent rounded-full blur-3xl"></div>
        </div>

        <!-- Scrolling capabilities (very subtle background decoration) -->
        <div class="absolute inset-0 overflow-hidden pointer-events-none" v-if="capabilities.length > 0">
            <ScrollingCapabilities :capabilities="capabilities" />
            <!-- Fade gradients overlay -->
            <div class="capabilities-fade-top"></div>
            <div class="capabilities-fade-bottom"></div>
        </div>

        <!-- Main content - hero and suggestions -->
        <div class="flex-1 flex flex-col items-center justify-center relative z-20 px-4">
            <!-- Hero text with typewriter effect -->
            <div class="text-center mb-8 md:mb-12">
                <div class="hero-text">
                    {{ $t('emptyState.heroAutomate') }}
                    <span class="hero-word">
                        <span class="typed-text">{{ displayedWord }}</span><span class="cursor">|</span>
                    </span>
                </div>
            </div>

            <!-- Capability suggestion cards -->
            <CapabilitySuggestions @select="handleSelect" />
        </div>

        <!-- Loading state -->
        <div v-if="capabilities.length === 0" class="absolute inset-0 flex items-center justify-center">
            <span class="text-[var(--text-muted)]">{{ $t('emptyState.loading') }}</span>
        </div>

        <!-- Demo prompts - HIDDEN for now (kept for potential future use) -->
        <div v-if="false" class="glass rounded-2xl p-6 max-w-xl w-full mx-auto">
            <h2 class="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-4">
                Try an example
            </h2>
            <div class="flex flex-col gap-2">
                <button
                    v-for="demo in demos"
                    :key="demo.label"
                    @click="$emit('fill-prompt', demo.prompt)"
                    class="demo-btn flex items-center gap-3 w-full p-3.5 rounded-xl bg-[var(--bg-surface)]/50 hover:bg-blue-500/10 border border-[var(--border-subtle)] hover:border-blue-500/20 text-left text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-all duration-200"
                >
                    <div class="p-1.5 rounded-lg bg-white/5 group-hover:bg-blue-500/20">
                        <component :is="demo.icon" class="w-4 h-4 text-zinc-400" />
                    </div>
                    <span>{{ demo.label }}</span>
                </button>
            </div>
        </div>

    </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
    FileSpreadsheet,
    FileText,
    Image,
    Search,
    Code,
    BarChart3
} from 'lucide-vue-next'
import ScrollingCapabilities from './ScrollingCapabilities.vue'
import CapabilitySuggestions from './CapabilitySuggestions.vue'

const { t, locale } = useI18n()
const emit = defineEmits(['fill-prompt'])

const capabilities = ref([])

// Typewriter animation state - words based on locale
const wordsMap = {
    en: ['emails', 'reports', 'meetings', 'tasks', 'anything.'],
    pl: ['maile', 'raporty', 'spotkania', 'zadania', 'wszystko.']
}
const words = computed(() => wordsMap[locale.value] || wordsMap.en)
const currentWordIndex = ref(0)
const displayedWord = ref('')
const isDeleting = ref(false)
let typewriterTimeout = null

// Typewriter timing constants
const TYPING_SPEED = 80
const DELETING_SPEED = 50
const WORD_PAUSE = 2000
const DELETE_PAUSE = 500

function typeWriter() {
    const word = words.value[currentWordIndex.value]

    if (isDeleting.value) {
        // Deleting characters
        displayedWord.value = word.substring(0, displayedWord.value.length - 1)

        if (displayedWord.value.length === 0) {
            isDeleting.value = false
            currentWordIndex.value = (currentWordIndex.value + 1) % words.value.length
            typewriterTimeout = setTimeout(typeWriter, TYPING_SPEED)
        } else {
            typewriterTimeout = setTimeout(typeWriter, DELETING_SPEED)
        }
    } else {
        // Typing characters
        displayedWord.value = word.substring(0, displayedWord.value.length + 1)

        if (displayedWord.value.length === word.length) {
            // Word complete - pause before deleting (unless it's the last word)
            if (currentWordIndex.value === words.value.length - 1) {
                // Last word - stop typing (stays on "anything/wszystko")
                return
            }
            isDeleting.value = true
            typewriterTimeout = setTimeout(typeWriter, WORD_PAUSE)
        } else {
            typewriterTimeout = setTimeout(typeWriter, TYPING_SPEED)
        }
    }
}

// Load capabilities from JSON based on current locale
const loadCapabilities = async () => {
    const lang = locale.value || 'en'

    try {
        const res = await fetch(`/what-you-can-do-${lang}.json`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        capabilities.value = await res.json()
    } catch (e) {
        // Fallback to English
        try {
            const res = await fetch('/what-you-can-do-en.json')
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            capabilities.value = await res.json()
        } catch (e2) {
            console.error('Failed to load capabilities:', e2)
        }
    }
}

// Reset typewriter when locale changes
watch(locale, () => {
    if (typewriterTimeout) clearTimeout(typewriterTimeout)
    currentWordIndex.value = 0
    displayedWord.value = ''
    isDeleting.value = false
    typeWriter()
    // Also reload capabilities for the new locale
    loadCapabilities()
})

// Load capabilities from JSON
onMounted(async () => {
    await loadCapabilities()
    // Start typewriter animation
    typeWriter()
})

onUnmounted(() => {
    if (typewriterTimeout) {
        clearTimeout(typewriterTimeout)
    }
})

// Handle click on capability - directly fill prompt
const handleSelect = (text) => {
    emit('fill-prompt', text)
}

// Demo prompts - kept for future use
const demos = [
    {
        icon: FileSpreadsheet,
        label: 'Analyze messy budget spreadsheet',
        prompt: 'Open the file demo/budzet-2024.xlsx. This budget has some issues - duplicates, inconsistent naming, missing data. Find all the problems, clean it up, and create a summary report with monthly totals and recommendations.'
    },
    {
        icon: FileText,
        label: 'Extract data from invoices',
        prompt: 'I have 4 invoices in demo/faktury/ folder. Extract all invoice numbers, dates, client names, and total amounts from each PDF. Create a summary table and calculate the total revenue.'
    },
    {
        icon: Image,
        label: 'Read data from whiteboard photo',
        prompt: 'Look at the image demo/tablica-sprint.png - it\'s a photo of our sprint planning board. Read all the tasks, assignees, estimates and statuses. Calculate the total hours and identify any risks or blockers.'
    },
    {
        icon: BarChart3,
        label: 'Analyze user churn risk',
        prompt: 'Analyze the file demo/user-analytics.csv. Find users with high churn risk and create a report: who are they, what plan are they on, when did they last login? Suggest actions to retain them.'
    },
    {
        icon: Search,
        label: 'Research AI coding assistants',
        prompt: 'Search the web for the latest AI coding assistants and tools in 2024. Compare Cursor, GitHub Copilot, and Claude Code. What are the pros and cons of each? Which one would you recommend for a Python developer?'
    },
    {
        icon: Code,
        label: 'Build a simple web app',
        prompt: 'Create a simple expense tracker web application. It should have: a form to add expenses (amount, category, date, description), a list of all expenses, filtering by category, and a chart showing spending by category. Use HTML, CSS, and vanilla JavaScript.'
    }
]
</script>

<style scoped>
.demo-btn:hover {
    transform: translateX(4px);
}

.bg-gradient-radial {
    background: radial-gradient(circle, var(--tw-gradient-stops));
}

/* Disable expensive blur effects on mobile */
@media (max-width: 768px) {
    .blur-3xl {
        filter: none !important;
        -webkit-filter: none !important;
    }
}

/* Hero text styles - single line, clean design */
.hero-text {
    font-family: 'Orbitron', sans-serif;
    font-weight: 700;
    font-size: 2.5rem;
    line-height: 1.2;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    background: linear-gradient(180deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.6) 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 2px 20px rgba(255, 255, 255, 0.1));
}

/* Light mode hero text - solid dark color for contrast */
[data-theme="light"] .hero-text {
    background: linear-gradient(180deg, #1e293b 0%, #334155 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: none;
}

.hero-word {
    display: inline-block;
    min-width: 120px;
    text-align: left;
}

.typed-text {
    font-family: 'Playfair Display', serif;
    font-style: italic;
    font-weight: 400;
    text-transform: none;
    letter-spacing: 0;
}

.cursor {
    font-family: 'Orbitron', sans-serif;
    font-weight: 300;
    animation: blink 0.7s infinite;
    margin-left: 2px;
}

@keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
}

/* Light mode typed text - solid blue for visibility */
[data-theme="light"] .typed-text {
    background: linear-gradient(180deg, #1d4ed8 0%, #0284c7 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* Responsive sizing */
@media (max-width: 768px) {
    .hero-text {
        font-size: 1.75rem;
    }
    .hero-word {
        min-width: 80px;
    }
}

/* Capabilities fade gradients */
.capabilities-fade-top {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 80px;
    background: linear-gradient(to bottom, var(--bg-base), transparent);
    pointer-events: none;
    z-index: 10;
}

.capabilities-fade-bottom {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 100px;
    background: linear-gradient(to top, var(--bg-base), transparent);
    pointer-events: none;
    z-index: 10;
}

</style>
