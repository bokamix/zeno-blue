<template>
    <div v-show="activities.length > 0" class="pl-10">
        <button
            @click="showLog = !showLog"
            class="text-xs text-zinc-500 hover:text-zinc-400 flex items-center gap-1 mb-2"
        >
            <ChevronDown v-if="showLog" class="w-3 h-3" />
            <ChevronRight v-else class="w-3 h-3" />
            Activity log ({{ activities.length }})
        </button>

        <div v-show="showLog" class="activity-log bg-zinc-900/50 rounded-lg p-3 max-h-64 overflow-y-auto custom-scroll">
            <div
                v-for="activity in activities"
                :key="activity.id"
                class="activity-item"
                :class="{ 'activity-error': activity.is_error }"
            >
                <span class="activity-icon">
                    <component :is="getActivityIcon(activity.type)" class="w-3 h-3" />
                </span>
                <span class="activity-time">{{ formatTime(activity.timestamp) }}</span>
                <span class="activity-message">
                    {{ activity.message }}
                    <span
                        v-if="activity.detail"
                        class="activity-detail-btn"
                        @click="toggleDetail(activity.id)"
                    >
                        {{ expandedActivities.includes(activity.id) ? '[hide]' : '[show]' }}
                    </span>
                </span>
            </div>

            <!-- Expanded details -->
            <div
                v-for="activity in activities.filter(a => a.detail && expandedActivities.includes(a.id))"
                :key="'detail-' + activity.id"
                class="activity-detail"
            >{{ activity.detail }}</div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import {
    ChevronDown,
    ChevronRight,
    Bot,
    Terminal,
    FileText,
    Search,
    Globe,
    HelpCircle,
    AlertCircle,
    Compass
} from 'lucide-vue-next'

const props = defineProps({
    activities: {
        type: Array,
        default: () => []
    }
})

const showLog = ref(true)
const expandedActivities = ref([])

const iconMap = {
    'routing': Bot,
    'step': Bot,
    'llm_call': Bot,
    'tool_call': Terminal,
    'file_read': FileText,
    'file_write': FileText,
    'search': Search,
    'web': Globe,
    'question': HelpCircle,
    'error': AlertCircle,
    // Explore subagent activities
    'explore_start': Compass,
    'explore_step': Compass,
    'explore_end': Compass
}

const getActivityIcon = (type) => {
    return iconMap[type] || Bot
}

const formatTime = (timestamp) => {
    const date = new Date(timestamp * 1000)
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    })
}

const toggleDetail = (activityId) => {
    const index = expandedActivities.value.indexOf(activityId)
    if (index > -1) {
        expandedActivities.value.splice(index, 1)
    } else {
        expandedActivities.value.push(activityId)
    }
}
</script>
