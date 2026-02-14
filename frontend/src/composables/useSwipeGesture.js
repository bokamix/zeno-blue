import { ref, computed, onMounted, onUnmounted } from 'vue'

const EDGE_THRESHOLD = 30      // px from edge to start gesture
const SWIPE_THRESHOLD = 0.3    // 30% triggers action
const MIN_VELOCITY = 0.5       // px/ms for quick swipes

export function useSwipeGesture(options = {}) {
    const {
        sidebarWidth = 288,
        onOpenSidebar = () => {},
        onCloseSidebar = () => {},
        onOpenSettings = () => {},
        onCloseSettings = () => {},
        isSidebarOpen = ref(false),
        isSettingsOpen = ref(false),
        enabled = ref(true)
    } = options

    const touchStartX = ref(0)
    const touchStartY = ref(0)
    const touchStartTime = ref(0)
    const currentX = ref(0)
    const isDragging = ref(false)
    const dragTarget = ref(null) // 'sidebar' | 'settings'
    const dragAction = ref(null) // 'open' | 'close'

    // Sidebar position during drag (0 to sidebarWidth)
    const sidebarDragOffset = computed(() => {
        if (!isDragging.value || dragTarget.value !== 'sidebar') {
            return isSidebarOpen.value ? sidebarWidth : 0
        }
        const delta = currentX.value - touchStartX.value

        // When action not yet determined, use current state as basis
        if (dragAction.value === null) {
            return isSidebarOpen.value ? sidebarWidth : 0
        }

        if (dragAction.value === 'open') {
            return Math.max(0, Math.min(sidebarWidth, delta * 0.8))
        } else {
            return Math.max(0, sidebarWidth + delta * 0.8)
        }
    })

    // Settings position during drag (slides from right)
    const settingsDragOffset = computed(() => {
        if (!isDragging.value || dragTarget.value !== 'settings') {
            return isSettingsOpen.value ? 0 : window.innerWidth
        }
        const delta = currentX.value - touchStartX.value

        // When action not yet determined, use current state as basis
        if (dragAction.value === null) {
            return isSettingsOpen.value ? 0 : window.innerWidth
        }

        if (dragAction.value === 'open') {
            // Opening settings: swipe left (delta negative)
            return Math.max(0, window.innerWidth + delta * 0.8)
        } else {
            // Closing settings: swipe right (delta positive)
            return Math.min(window.innerWidth, delta * 0.8)
        }
    })

    const sidebarTransform = computed(() => {
        if (!isDragging.value || dragTarget.value !== 'sidebar') return null
        return `translateX(${sidebarDragOffset.value - sidebarWidth}px)`
    })

    const isMobile = () => window.innerWidth < 768

    // Check if touch target is an interactive element (buttons, links, etc.)
    const isInteractiveElement = (element) => {
        const interactiveSelectors = 'button, a, input, textarea, select, [role="button"], [onclick]'
        return element.closest(interactiveSelectors) !== null
    }

    const onTouchStart = (e) => {
        if (!enabled.value || !isMobile()) return

        // Ignore touches on interactive elements (buttons, links, etc.)
        if (isInteractiveElement(e.target)) return

        const touch = e.touches[0]
        touchStartX.value = touch.clientX
        touchStartY.value = touch.clientY
        touchStartTime.value = Date.now()
        currentX.value = touch.clientX
        dragTarget.value = null
        dragAction.value = null

        const isInLeftEdge = touch.clientX < EDGE_THRESHOLD
        const isInRightEdge = touch.clientX > window.innerWidth - EDGE_THRESHOLD

        // Determine what we're dragging based on current state
        if (isSidebarOpen.value) {
            // Sidebar open - can close it from anywhere
            isDragging.value = true
            dragTarget.value = 'sidebar'
        } else if (isSettingsOpen.value) {
            // Settings open - can close it from anywhere
            isDragging.value = true
            dragTarget.value = 'settings'
        } else if (isInLeftEdge) {
            // Nothing open, left edge - will open sidebar
            isDragging.value = true
            dragTarget.value = 'sidebar'
        } else if (isInRightEdge) {
            // Nothing open, right edge - will open settings
            isDragging.value = true
            dragTarget.value = 'settings'
        }
    }

    const onTouchMove = (e) => {
        if (!isDragging.value || !enabled.value) return

        const touch = e.touches[0]
        const deltaX = touch.clientX - touchStartX.value
        const deltaY = touch.clientY - touchStartY.value

        // Determine action on first significant move
        if (dragAction.value === null) {
            // Vertical movement dominates - cancel swipe
            if (Math.abs(deltaY) > Math.abs(deltaX) && Math.abs(deltaY) > 10) {
                isDragging.value = false
                return
            }

            if (Math.abs(deltaX) > 10) {
                // Determine intent based on target and current state
                if (dragTarget.value === 'sidebar') {
                    if (isSidebarOpen.value) {
                        dragAction.value = deltaX < 0 ? 'close' : null
                    } else {
                        dragAction.value = deltaX > 0 ? 'open' : null
                    }
                } else if (dragTarget.value === 'settings') {
                    if (isSettingsOpen.value) {
                        dragAction.value = deltaX > 0 ? 'close' : null
                    } else {
                        dragAction.value = deltaX < 0 ? 'open' : null
                    }
                }

                // Wrong direction - cancel
                if (dragAction.value === null) {
                    isDragging.value = false
                    return
                }
            }
        }

        // Prevent browser navigation
        if (dragAction.value) {
            e.preventDefault()
        }

        currentX.value = touch.clientX
    }

    const onTouchEnd = () => {
        if (!isDragging.value || !enabled.value) return

        const deltaX = currentX.value - touchStartX.value
        const elapsed = Date.now() - touchStartTime.value
        const velocity = Math.abs(deltaX) / elapsed

        const threshold = sidebarWidth * SWIPE_THRESHOLD
        const passedThreshold = Math.abs(deltaX) > threshold || velocity > MIN_VELOCITY

        if (passedThreshold && dragAction.value) {
            if (dragTarget.value === 'sidebar') {
                if (dragAction.value === 'open') onOpenSidebar()
                else onCloseSidebar()
            } else if (dragTarget.value === 'settings') {
                if (dragAction.value === 'open') onOpenSettings()
                else onCloseSettings()
            }
        }

        // Reset
        isDragging.value = false
        dragTarget.value = null
        dragAction.value = null
    }

    onMounted(() => {
        document.addEventListener('touchstart', onTouchStart, { passive: true })
        document.addEventListener('touchmove', onTouchMove, { passive: false })
        document.addEventListener('touchend', onTouchEnd, { passive: true })
    })

    onUnmounted(() => {
        document.removeEventListener('touchstart', onTouchStart)
        document.removeEventListener('touchmove', onTouchMove)
        document.removeEventListener('touchend', onTouchEnd)
    })

    return {
        isDragging,
        dragTarget,
        sidebarDragOffset,
        sidebarTransform,
        settingsDragOffset
    }
}
