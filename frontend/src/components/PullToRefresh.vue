<template>
    <div
        ref="containerRef"
        class="pull-to-refresh-container"
        @touchstart.passive="onTouchStart"
        @touchmove="onTouchMove"
        @touchend="onTouchEnd"
    >
        <!-- Pull indicator -->
        <div
            class="pull-indicator"
            :class="{ 'refreshing': isRefreshing, 'visible': indicatorY > 0 || countdown > 0 }"
            :style="{ transform: `translateY(${(indicatorY || (countdown > 0 ? 48 : 0)) - 48}px)` }"
        >
            <template v-if="countdown > 0">
                <span class="text-lg font-bold text-[var(--text-primary)]">{{ countdown }}</span>
            </template>
            <template v-else>
                <RefreshCw
                    class="w-5 h-5 text-[var(--text-secondary)]"
                    :class="{ 'animate-spin': isRefreshing }"
                    :style="{ transform: `rotate(${rotation}deg)` }"
                />
            </template>
        </div>

        <!-- Content -->
        <slot />
    </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'
import { RefreshCw } from 'lucide-vue-next'

const THRESHOLD = 80 // px to trigger refresh
const MAX_PULL = 120 // max pull distance
const COUNTDOWN_START = 3 // seconds

const containerRef = ref(null)
const startY = ref(0)
const startX = ref(0)
const isPulling = ref(false)
const isRefreshing = ref(false)
const touchStartElement = ref(null)
const countdown = ref(0)
const countdownInterval = ref(null)
const shouldRefresh = ref(false)

const indicatorY = ref(0)
const rotation = ref(0)

// Start countdown when threshold is reached while holding
const startCountdown = () => {
    if (countdownInterval.value) return // Already running

    countdown.value = COUNTDOWN_START
    countdownInterval.value = setInterval(() => {
        countdown.value--
        if (countdown.value <= 0) {
            clearInterval(countdownInterval.value)
            countdownInterval.value = null
            shouldRefresh.value = true
            // Reload immediately when countdown finishes while holding
            window.location.reload()
        }
    }, 1000)
}

// Cancel countdown when user releases early or pulls back
const cancelCountdown = () => {
    if (countdownInterval.value) {
        clearInterval(countdownInterval.value)
        countdownInterval.value = null
    }
    countdown.value = 0
    shouldRefresh.value = false
}

// Cleanup on unmount to prevent reload after navigation
onUnmounted(() => {
    cancelCountdown()
})

// Check if an element or any of its ancestors is scrollable and not at top
const hasScrollableAncestorNotAtTop = (element) => {
    let el = element
    while (el && el !== document.body) {
        const style = window.getComputedStyle(el)
        const overflowY = style.overflowY
        const isScrollable = overflowY === 'auto' || overflowY === 'scroll'

        if (isScrollable && el.scrollHeight > el.clientHeight) {
            // This element is scrollable - check if it's at top
            if (el.scrollTop > 0) {
                return true // Has scrollable ancestor that is NOT at top
            }
        }
        el = el.parentElement
    }
    return false
}

const onTouchStart = (e) => {
    if (isRefreshing.value) return

    // Store the element where touch started
    touchStartElement.value = e.target

    // Check if touch started on a scrollable element that's not at top
    if (hasScrollableAncestorNotAtTop(e.target)) {
        isPulling.value = false
        return
    }

    startY.value = e.touches[0].clientY
    startX.value = e.touches[0].clientX
    isPulling.value = true
}

const onTouchMove = (e) => {
    if (!isPulling.value || isRefreshing.value) return

    const currentY = e.touches[0].clientY
    const currentX = e.touches[0].clientX
    const diffY = currentY - startY.value
    const diffX = currentX - startX.value

    // If horizontal movement is greater, it's a swipe - cancel pull
    if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 10) {
        isPulling.value = false
        indicatorY.value = 0
        rotation.value = 0
        return
    }

    // Only activate when pulling down
    if (diffY > 0) {
        // Double-check scrollable ancestors at move time too
        if (hasScrollableAncestorNotAtTop(touchStartElement.value)) {
            isPulling.value = false
            indicatorY.value = 0
            rotation.value = 0
            cancelCountdown()
            return
        }

        // Apply resistance
        const pull = Math.min(diffY * 0.4, MAX_PULL)
        indicatorY.value = pull
        rotation.value = (pull / THRESHOLD) * 180

        // Start countdown when threshold is reached while holding
        if (pull >= THRESHOLD) {
            startCountdown()
        } else {
            // Pulled back below threshold - cancel countdown
            cancelCountdown()
        }

        // Prevent default scroll when actively pulling
        if (pull > 5) {
            e.preventDefault()
        }
    } else {
        // Scrolling up - cancel pull and countdown
        indicatorY.value = 0
        rotation.value = 0
        cancelCountdown()
    }
}

const onTouchEnd = () => {
    if (!isPulling.value) return

    isPulling.value = false
    touchStartElement.value = null

    // User released - cancel countdown and reset
    cancelCountdown()
    indicatorY.value = 0
    rotation.value = 0
}
</script>

<style scoped>
.pull-to-refresh-container {
    position: relative;
    min-height: 100%;
}

.pull-indicator {
    position: fixed;
    top: 0;
    left: 50%;
    margin-left: -20px;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    opacity: 0;
    transition: opacity 0.15s ease;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    pointer-events: none;
}

.pull-indicator.visible {
    opacity: 1;
}

.pull-indicator.refreshing {
    opacity: 1;
}

/* Only enable on touch devices */
@media (hover: hover) {
    .pull-indicator {
        display: none;
    }
}
</style>
