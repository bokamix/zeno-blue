# Vue 3 CDN Documentation

Vue 3 via CDN - no build step, no npm. Composition API with `setup()` directly in the browser.

## Installation (CDN)
```html
<script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
```

---

## App Setup

```html
<div id="app">
    <h1>{{ title }}</h1>
    <button @click="count++">Count: {{ count }}</button>
</div>

<script>
const { createApp, ref, reactive, computed, watch, onMounted, onUnmounted } = Vue;

createApp({
    setup() {
        const title = ref('My App');
        const count = ref(0);

        return { title, count };
    }
}).mount('#app');
</script>
```

---

## Reactivity

### ref() - primitive values
```javascript
const count = ref(0);
const name = ref('');
const loading = ref(false);

// Read/write via .value in JS
count.value++;
console.log(count.value); // 1

// In template - no .value needed
// {{ count }}
```

### reactive() - objects
```javascript
const state = reactive({
    user: null,
    items: [],
    filters: { search: '', category: 'all' }
});

// Direct property access (no .value)
state.items.push({ id: 1, name: 'Item' });
state.user = { name: 'John' };
```

### computed() - derived values
```javascript
const todos = ref([]);
const doneCount = computed(() => todos.value.filter(t => t.done).length);
const remaining = computed(() => todos.value.length - doneCount.value);

// In template: {{ doneCount }}, {{ remaining }}
```

### watch() - react to changes
```javascript
// Watch single ref
watch(count, (newVal, oldVal) => {
    console.log(`Changed from ${oldVal} to ${newVal}`);
});

// Watch reactive object (deep by default)
watch(() => state.filters, (newFilters) => {
    fetchData(newFilters);
}, { deep: true });

// Watch multiple sources
watch([count, name], ([newCount, newName]) => {
    console.log(newCount, newName);
});
```

---

## Lifecycle Hooks

```javascript
setup() {
    onMounted(() => {
        // DOM is ready, fetch data, init libraries
        console.log('Component mounted');
    });

    onUnmounted(() => {
        // Cleanup: remove listeners, clear intervals
        console.log('Component destroyed');
    });
}
```

---

## Template Syntax

### Text Interpolation
```html
<span>{{ message }}</span>
<span>{{ count + 1 }}</span>
<span>{{ ok ? 'YES' : 'NO' }}</span>
<span>{{ items.length }} items</span>
```

### Attribute Binding (v-bind / :)
```html
<div :class="{ active: isActive, 'text-bold': isBold }"></div>
<div :class="[baseClass, errorClass]"></div>
<div :style="{ color: textColor, fontSize: size + 'px' }"></div>
<input :disabled="loading">
<a :href="url">Link</a>
<img :src="imageUrl" :alt="imageAlt">
```

### Event Handling (v-on / @)
```html
<button @click="count++">Increment</button>
<button @click="handleClick">Click me</button>
<button @click="handleClick($event)">With event</button>
<form @submit.prevent="save">Submit</form>
<div @click.stop="inner">Stop propagation</div>
<input @keydown.enter="submit">
<input @keydown.escape="cancel">
<input @input="onInput">
<button @click.once="initOnce">Run once</button>
```

### Two-way Binding (v-model)
```html
<input type="text" v-model="name">
<textarea v-model="content"></textarea>
<input type="checkbox" v-model="agreed">
<input type="radio" value="yes" v-model="answer">
<select v-model="country">
    <option value="">Select...</option>
    <option value="us">United States</option>
</select>

<!-- Modifiers -->
<input v-model.number="age">
<input v-model.trim="name">
<input v-model.lazy="name">  <!-- Update on change, not input -->
```

### Conditional Rendering
```html
<!-- v-if: adds/removes from DOM -->
<div v-if="loading">Loading...</div>
<div v-else-if="error">Error: {{ error }}</div>
<div v-else>Content here</div>

<!-- v-show: toggles CSS display (better for frequent toggling) -->
<div v-show="visible">Toggled with CSS</div>
```

### List Rendering (v-for)
```html
<div v-for="item in items" :key="item.id">
    {{ item.name }}
</div>

<!-- With index -->
<div v-for="(item, index) in items" :key="item.id">
    {{ index + 1 }}. {{ item.name }}
</div>

<!-- Object iteration -->
<div v-for="(value, key) in object" :key="key">
    {{ key }}: {{ value }}
</div>

<!-- Range -->
<span v-for="n in 10" :key="n">{{ n }}</span>
```

### Template Refs
```html
<input ref="inputRef" type="text">
<canvas ref="chartRef"></canvas>

<script>
setup() {
    const inputRef = ref(null);
    const chartRef = ref(null);

    onMounted(() => {
        inputRef.value.focus();
        // chartRef.value is the canvas element
    });

    return { inputRef, chartRef };
}
</script>
```

---

## Migration from Alpine.js

| Alpine.js | Vue 3 CDN | Notes |
|-----------|-----------|-------|
| `x-data="{ count: 0 }"` | `setup() { return { count: ref(0) } }` | State in setup() |
| `x-init="loadData()"` | `onMounted(() => loadData())` | Lifecycle hook |
| `x-model="title"` | `v-model="title"` | Same concept |
| `x-text="message"` | `{{ message }}` | Text interpolation |
| `x-html="content"` | `v-html="content"` | Raw HTML |
| `x-show="visible"` | `v-show="visible"` | Same concept |
| `x-if="condition"` | `v-if="condition"` | No `<template>` required |
| `x-for="item in items"` | `v-for="item in items"` | Same syntax |
| `@click="handle"` | `@click="handle"` | Identical |
| `@submit.prevent` | `@submit.prevent` | Identical |
| `:class="{ active: on }"` | `:class="{ active: on }"` | Identical |
| `x-ref="input"` | `ref="input"` + `const input = ref(null)` | Needs setup() ref |
| `$nextTick(() => ...)` | `nextTick(() => ...)` | Import from Vue |
| `$watch('x', cb)` | `watch(x, cb)` | Import from Vue |
| `$store.user` | Use `reactive()` global | No built-in store |
| `$dispatch('event')` | Custom events or shared state | No direct equivalent |

---

## Common Patterns

### Dropdown
```html
<div id="app">
    <div style="position: relative;">
        <button @click="open = !open" class="btn">Toggle</button>
        <div v-show="open" @click.stop class="dropdown-menu">
            <a href="#">Item 1</a>
            <a href="#">Item 2</a>
        </div>
    </div>
</div>

<script>
createApp({
    setup() {
        const open = ref(false);

        onMounted(() => {
            document.addEventListener('click', () => { open.value = false; });
        });

        return { open };
    }
}).mount('#app');
</script>
```

### Tabs
```html
<div>
    <div class="tabs tabs-boxed">
        <button v-for="tab in tabs" :key="tab"
                :class="['tab', { 'tab-active': activeTab === tab }]"
                @click="activeTab = tab">
            {{ tab }}
        </button>
    </div>
    <div v-show="activeTab === 'Tab 1'">Content 1</div>
    <div v-show="activeTab === 'Tab 2'">Content 2</div>
</div>

<script>
setup() {
    const tabs = ['Tab 1', 'Tab 2', 'Tab 3'];
    const activeTab = ref('Tab 1');
    return { tabs, activeTab };
}
</script>
```

### Loading State
```html
<button @click="load" :disabled="loading" class="btn btn-primary">
    <span v-if="loading" class="loading loading-spinner"></span>
    <span v-else>Load Data</span>
</button>
<div v-if="data">{{ data }}</div>

<script>
setup() {
    const loading = ref(false);
    const data = ref(null);

    async function load() {
        loading.value = true;
        try {
            const res = await fetch('/api/data');
            data.value = await res.json();
        } finally {
            loading.value = false;
        }
    }

    return { loading, data, load };
}
</script>
```

### Form Validation
```html
<form @submit.prevent="submit">
    <input v-model="email" @blur="validateEmail" class="input input-bordered"
           :class="{ 'input-error': errors.email }">
    <p v-if="errors.email" class="text-error text-sm">{{ errors.email }}</p>
    <button type="submit" class="btn btn-primary" :disabled="!isValid">Submit</button>
</form>

<script>
setup() {
    const email = ref('');
    const errors = reactive({});

    function validateEmail() {
        errors.email = email.value.includes('@') ? '' : 'Invalid email';
    }

    const isValid = computed(() => email.value && !errors.email);

    function submit() {
        validateEmail();
        if (isValid.value) {
            // submit form
        }
    }

    return { email, errors, validateEmail, isValid, submit };
}
</script>
```

### Dark Mode Toggle
```html
<label class="swap swap-rotate">
    <input type="checkbox" :checked="dark" @change="toggleDark">
    <span class="swap-on">Dark</span>
    <span class="swap-off">Light</span>
</label>

<script>
setup() {
    const dark = ref(localStorage.getItem('theme') === 'dark');

    function toggleDark() {
        dark.value = !dark.value;
        localStorage.setItem('theme', dark.value ? 'dark' : 'light');
        document.documentElement.setAttribute('data-theme', dark.value ? 'dark' : 'light');
    }

    onMounted(() => {
        document.documentElement.setAttribute('data-theme', dark.value ? 'dark' : 'light');
    });

    return { dark, toggleDark };
}
</script>
```

### Fetch Data on Mount
```javascript
setup() {
    const items = ref([]);
    const loading = ref(true);

    onMounted(async () => {
        try {
            const res = await fetch('/api/items');
            items.value = await res.json();
        } finally {
            loading.value = false;
        }
    });

    return { items, loading };
}
```

---

## Tips

### Multiple Components on One Page
```html
<div id="header-app">
    <nav>{{ title }}</nav>
</div>

<div id="main-app">
    <p>{{ content }}</p>
</div>

<script>
createApp({
    setup() { return { title: ref('My Site') }; }
}).mount('#header-app');

createApp({
    setup() { return { content: ref('Hello') }; }
}).mount('#main-app');
</script>
```

### Shared State Between Apps
```javascript
// Global state
const globalState = Vue.reactive({ user: null, theme: 'light' });

// Use in any app
createApp({
    setup() {
        return { state: globalState };
    }
}).mount('#app');
```

### Using nextTick
```javascript
const { nextTick } = Vue;

async function addItem() {
    items.value.push(newItem);
    await nextTick();
    // DOM is now updated
    container.value.scrollTop = container.value.scrollHeight;
}
```
