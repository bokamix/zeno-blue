<template>
    <div v-show="question" class="w-full">
        <div class="flex flex-col gap-3">
            <div class="flex items-center gap-2.5">
                <div class="w-7 h-7 rounded-lg bg-gradient-to-br from-amber-500 to-amber-600 flex items-center justify-center shadow-sm">
                    <HelpCircle class="w-4 h-4 text-white" />
                </div>
                <span class="question-prompt-title text-sm font-semibold text-amber-600 dark:text-amber-400">{{ $t('prompts.question.needsInput') }}</span>
            </div>

            <div class="pl-10 space-y-4">
                <div
                    class="question-prompt-content prose prose-zinc dark:prose-invert prose-sm max-w-none text-zinc-700 dark:text-zinc-200"
                    v-html="renderedQuestion"
                ></div>

                <!-- Options (if provided) -->
                <div v-if="question?.options?.length" class="flex flex-wrap gap-2">
                    <button
                        v-for="opt in question.options"
                        :key="opt"
                        @click="submit(opt)"
                        class="question-prompt-option px-4 py-2 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-200 text-sm rounded-lg border border-zinc-300 dark:border-zinc-700 hover:border-zinc-400 dark:hover:border-zinc-600 transition-colors"
                    >
                        {{ opt }}
                    </button>
                </div>

                <!-- Free-form input -->
                <div class="flex gap-2">
                    <input
                        v-model="response"
                        @keydown.enter="submit(response)"
                        type="text"
                        :placeholder="question?.options ? $t('prompts.question.customAnswer') : $t('prompts.question.typeAnswer')"
                        class="question-prompt-input flex-1 bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-zinc-700 dark:text-zinc-200 text-sm rounded-lg px-4 py-2 focus:outline-none focus:border-zinc-400 dark:focus:border-zinc-600 placeholder-zinc-400 dark:placeholder-zinc-500"
                    />
                    <button
                        @click="submit(response)"
                        :disabled="!response.trim()"
                        class="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white text-sm rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                        {{ $t('common.send') }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { HelpCircle } from 'lucide-vue-next'
import { marked } from 'marked'

const props = defineProps({
    question: {
        type: Object,
        default: null
    }
})

const emit = defineEmits(['submit'])

const response = ref('')

const renderedQuestion = computed(() => {
    if (!props.question?.question) return ''
    return marked.parse(props.question.question)
})

const submit = (answer) => {
    if (!answer?.trim()) return
    emit('submit', answer)
    response.value = ''
}
</script>
