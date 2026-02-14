import { computed, isRef } from 'vue'

/**
 * Composable for grouping conversations by date
 * Groups: today, yesterday, thisWeek, older
 *
 * @param {Array|Ref<Array>|Function} conversationsSource - conversations array, ref, or getter function
 */
export function useConversationGrouping(conversationsSource) {
    const groupedConversations = computed(() => {
        const now = new Date()
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
        const yesterday = new Date(today.getTime() - 86400000)
        const weekAgo = new Date(today.getTime() - 7 * 86400000)

        const groups = {
            today: [],
            yesterday: [],
            thisWeek: [],
            older: []
        }

        // Handle different input types: ref, getter function, or plain array
        let convList
        if (isRef(conversationsSource)) {
            convList = conversationsSource.value || []
        } else if (typeof conversationsSource === 'function') {
            convList = conversationsSource() || []
        } else {
            convList = conversationsSource || []
        }

        for (const conv of convList) {
            const date = conv.last_user_message_at
                ? new Date(conv.last_user_message_at)
                : new Date(conv.created_at)

            if (date >= today) {
                groups.today.push(conv)
            } else if (date >= yesterday) {
                groups.yesterday.push(conv)
            } else if (date >= weekAgo) {
                groups.thisWeek.push(conv)
            } else {
                groups.older.push(conv)
            }
        }

        // Sort each group by last_user_message_at DESC (newest first)
        const sortByDate = (a, b) => {
            const dateA = a.last_user_message_at ? new Date(a.last_user_message_at) : new Date(a.created_at)
            const dateB = b.last_user_message_at ? new Date(b.last_user_message_at) : new Date(b.created_at)
            return dateB - dateA
        }
        groups.today.sort(sortByDate)
        groups.yesterday.sort(sortByDate)
        groups.thisWeek.sort(sortByDate)
        groups.older.sort(sortByDate)

        return groups
    })

    return {
        groupedConversations
    }
}
