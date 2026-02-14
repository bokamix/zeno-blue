import { ref, nextTick } from 'vue'

/**
 * Composable for @-mentions autocomplete functionality
 * Handles file and scheduler search, keyboard navigation, and mention insertion
 */
export function useMentions(inputText, inputBox, searchArtifacts, searchSchedulers = null) {
    // @-Mentions State
    const showMentions = ref(false)
    const mentionQuery = ref('')
    const mentionResults = ref([])  // Array of {type: 'file'|'scheduler', path/name, ...}
    const mentionIndex = ref(0)
    const mentionStartPos = ref(0)
    let searchDebounceTimer = null

    // Search files by query using API
    const searchFiles = async (query) => {
        if (!query || query.length < 1) {
            return []
        }
        try {
            const results = await searchArtifacts(query)
            return results.slice(0, 6).map(r => ({ ...r, type: 'file' }))
        } catch (e) {
            console.error('File search failed:', e)
            return []
        }
    }

    // Search schedulers by query
    const searchSchedulerItems = async (query) => {
        if (!searchSchedulers) return []
        try {
            const results = await searchSchedulers(query)
            return results.slice(0, 4).map(r => ({ ...r, type: 'scheduler' }))
        } catch (e) {
            console.error('Scheduler search failed:', e)
            return []
        }
    }

    // Handle input to detect @ symbol
    const onMentionInput = (e, autoResizeCallback) => {
        if (autoResizeCallback) autoResizeCallback()

        const text = e.target.value
        const cursorPos = e.target.selectionStart
        const beforeCursor = text.substring(0, cursorPos)

        const match = beforeCursor.match(/@([^\s@]*)$/)

        if (match) {
            mentionQuery.value = match[1]
            mentionStartPos.value = cursorPos - match[0].length

            // Debounce API calls
            if (searchDebounceTimer) {
                clearTimeout(searchDebounceTimer)
            }
            searchDebounceTimer = setTimeout(async () => {
                // Search both files and schedulers in parallel
                const [fileResults, schedulerResults] = await Promise.all([
                    searchFiles(match[1]),
                    searchSchedulerItems(match[1])
                ])
                // Combine results: schedulers first, then files
                mentionResults.value = [...schedulerResults, ...fileResults]
                showMentions.value = mentionResults.value.length > 0
                mentionIndex.value = 0
            }, 150)
        } else {
            showMentions.value = false
            if (searchDebounceTimer) {
                clearTimeout(searchDebounceTimer)
            }
        }
    }

    // Insert selected mention (file or scheduler)
    const insertMention = (item) => {
        const text = inputText.value
        const before = text.substring(0, mentionStartPos.value)
        const after = text.substring(mentionStartPos.value + mentionQuery.value.length + 1)

        // Use path for files, name for schedulers
        const mentionText = item.type === 'scheduler' ? `scheduler:${item.name}` : item.path

        inputText.value = before + '@' + mentionText + ' ' + after
        showMentions.value = false
        nextTick(() => {
            inputBox.value?.focus()
            const newPos = mentionStartPos.value + mentionText.length + 2
            inputBox.value?.setSelectionRange(newPos, newPos)
        })
    }

    // Handle keyboard navigation for mentions dropdown
    const handleMentionKeydown = (e) => {
        if (!showMentions.value) return false

        if (e.key === 'ArrowDown') {
            e.preventDefault()
            mentionIndex.value = Math.min(mentionIndex.value + 1, mentionResults.value.length - 1)
            return true
        }
        if (e.key === 'ArrowUp') {
            e.preventDefault()
            mentionIndex.value = Math.max(mentionIndex.value - 1, 0)
            return true
        }
        if (e.key === 'Enter' || e.key === 'Tab') {
            e.preventDefault()
            if (mentionResults.value[mentionIndex.value]) {
                insertMention(mentionResults.value[mentionIndex.value])
            }
            return true
        }
        if (e.key === 'Escape') {
            e.preventDefault()
            showMentions.value = false
            return true
        }

        return false
    }

    // Close mentions dropdown
    const closeMentions = () => {
        showMentions.value = false
    }

    return {
        // State
        showMentions,
        mentionQuery,
        mentionResults,
        mentionIndex,
        mentionStartPos,

        // Actions
        searchFiles,
        onMentionInput,
        insertMention,
        handleMentionKeydown,
        closeMentions
    }
}
