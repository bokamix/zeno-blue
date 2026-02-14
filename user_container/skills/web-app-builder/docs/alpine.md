# Alpine.js Documentation

Alpine.js is a lightweight JavaScript framework for adding reactivity to HTML. It requires no build step and works directly in the browser.

## Installation (CDN)
```html
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js"></script>
```

---

## Core Directives

### x-data
Defines reactive data for a component.

```html
<!-- Object data -->
<div x-data="{ open: false, count: 0 }">
    <p x-text="count"></p>
</div>

<!-- Function data (for complex components) -->
<div x-data="dropdown()">
    ...
</div>

<script>
function dropdown() {
    return {
        open: false,
        toggle() { this.open = !this.open }
    }
}
</script>

<!-- Nested components -->
<div x-data="{ name: 'outer' }">
    <div x-data="{ name: 'inner' }">
        <p x-text="name"></p>  <!-- Shows "inner" -->
    </div>
</div>
```

### x-init
Runs code when component initializes.

```html
<div x-data="{ items: [] }" x-init="items = await fetchItems()">
    ...
</div>

<!-- With async -->
<div x-data="myComponent()" x-init="await init()">
    ...
</div>

<script>
function myComponent() {
    return {
        data: [],
        async init() {
            this.data = await fetch('/api/data').then(r => r.json());
        }
    }
}
</script>
```

### x-show
Toggle visibility (uses CSS display).

```html
<div x-show="open">This is visible when open is true</div>

<!-- With transition -->
<div x-show="open" x-transition>Smooth fade</div>

<!-- Custom transition -->
<div x-show="open"
     x-transition:enter="transition ease-out duration-300"
     x-transition:enter-start="opacity-0 scale-90"
     x-transition:enter-end="opacity-100 scale-100"
     x-transition:leave="transition ease-in duration-300"
     x-transition:leave-start="opacity-100 scale-100"
     x-transition:leave-end="opacity-0 scale-90">
    Animated content
</div>
```

### x-if
Conditionally render elements (removes from DOM).

```html
<template x-if="loggedIn">
    <p>Welcome back!</p>
</template>

<!-- Note: x-if must be on a <template> tag -->
```

### x-for
Loop over arrays.

```html
<template x-for="item in items" :key="item.id">
    <div x-text="item.name"></div>
</template>

<!-- With index -->
<template x-for="(item, index) in items" :key="item.id">
    <div>
        <span x-text="index + 1"></span>.
        <span x-text="item.name"></span>
    </div>
</template>

<!-- Iterate range -->
<template x-for="i in 10">
    <span x-text="i"></span>
</template>
```

### x-bind
Bind attribute values reactively.

```html
<!-- Shorthand : -->
<div :class="{ 'active': isActive }"></div>

<!-- Full syntax -->
<div x-bind:class="{ 'active': isActive }"></div>

<!-- Multiple classes -->
<div :class="{ 'bg-red-500': hasError, 'bg-green-500': success }"></div>

<!-- Array of classes -->
<div :class="[baseClass, isActive ? 'active' : '']"></div>

<!-- Style binding -->
<div :style="{ color: textColor, fontSize: size + 'px' }"></div>

<!-- Any attribute -->
<input :disabled="isLoading">
<a :href="url">Link</a>
<img :src="imageUrl" :alt="imageAlt">
```

### x-on
Listen to events.

```html
<!-- Shorthand @ -->
<button @click="count++">Increment</button>

<!-- Full syntax -->
<button x-on:click="count++">Increment</button>

<!-- Call method -->
<button @click="handleClick">Click me</button>

<!-- With argument -->
<button @click="handleClick($event)">Click</button>

<!-- Prevent default -->
<form @submit.prevent="save">
    <button type="submit">Save</button>
</form>

<!-- Stop propagation -->
<div @click="outer">
    <button @click.stop="inner">Won't trigger outer</button>
</div>

<!-- Key modifiers -->
<input @keydown.enter="submit">
<input @keydown.escape="cancel">
<input @keydown.arrow-up="prev">

<!-- Mouse modifiers -->
<button @click.right="contextMenu">Right click</button>

<!-- Once -->
<button @click.once="init">Run once</button>

<!-- Debounce -->
<input @input.debounce.500ms="search">

<!-- Throttle -->
<div @scroll.throttle.100ms="handleScroll">

<!-- Self (only if event target is this element) -->
<div @click.self="close">
    <button>Won't close</button>
</div>

<!-- Window/Document events -->
<div @resize.window="handleResize">
<div @keydown.escape.window="closeModal">
```

### x-model
Two-way data binding for form inputs.

```html
<!-- Text input -->
<input type="text" x-model="name">
<p x-text="name"></p>

<!-- Textarea -->
<textarea x-model="content"></textarea>

<!-- Checkbox (boolean) -->
<input type="checkbox" x-model="agreed">

<!-- Checkbox (array) -->
<input type="checkbox" value="apple" x-model="fruits">
<input type="checkbox" value="banana" x-model="fruits">
<!-- fruits = ['apple'] when apple is checked -->

<!-- Radio -->
<input type="radio" value="yes" x-model="answer">
<input type="radio" value="no" x-model="answer">

<!-- Select -->
<select x-model="country">
    <option value="">Select...</option>
    <option value="us">United States</option>
    <option value="uk">United Kingdom</option>
</select>

<!-- Modifiers -->
<input x-model.number="age">          <!-- Cast to number -->
<input x-model.debounce.500ms="search">  <!-- Debounce -->
<input x-model.lazy="name">           <!-- Update on change (not input) -->
<input x-model.fill="name">           <!-- Initialize from input value -->
```

### x-text
Set text content.

```html
<span x-text="message"></span>
<span x-text="count + ' items'"></span>
<span x-text="formatDate(date)"></span>
```

### x-html
Set HTML content (use carefully - XSS risk).

```html
<div x-html="htmlContent"></div>
```

### x-ref
Get reference to DOM element.

```html
<input x-ref="input" type="text">
<button @click="$refs.input.focus()">Focus</button>

<!-- Multiple refs -->
<div x-ref="container">
    <input x-ref="input">
</div>
<script>
// Access via this.$refs.container, this.$refs.input
</script>
```

### x-cloak
Hide element until Alpine initializes.

```html
<style>[x-cloak] { display: none !important; }</style>

<div x-cloak x-data="{ loading: true }">
    <!-- Won't flash unstyled content -->
</div>
```

### x-ignore
Ignore Alpine processing in a subtree.

```html
<div x-data="{ name: 'John' }">
    <div x-ignore>
        <span x-text="name"></span> <!-- Won't be processed -->
    </div>
</div>
```

### x-effect
Run code reactively when dependencies change.

```html
<div x-data="{ count: 0 }" x-effect="console.log('Count is:', count)">
    <button @click="count++">Increment</button>
</div>
```

### x-teleport
Move element to another location in DOM.

```html
<div x-data="{ open: false }">
    <button @click="open = true">Open Modal</button>

    <template x-teleport="body">
        <div x-show="open" class="modal">
            Modal content
            <button @click="open = false">Close</button>
        </div>
    </template>
</div>
```

---

## Magic Properties

### $el
Reference to current DOM element.

```html
<button @click="$el.classList.toggle('active')">Toggle</button>
```

### $refs
Access elements with x-ref.

```html
<input x-ref="input">
<button @click="$refs.input.focus()">Focus</button>
```

### $store
Access global stores.

```html
<!-- Define store -->
<script>
document.addEventListener('alpine:init', () => {
    Alpine.store('user', {
        name: 'John',
        loggedIn: false,
        login() { this.loggedIn = true; }
    });
});
</script>

<!-- Use store -->
<div x-data>
    <p x-text="$store.user.name"></p>
    <button @click="$store.user.login()">Login</button>
</div>
```

### $watch
Watch for changes.

```html
<div x-data="{ count: 0 }" x-init="$watch('count', value => console.log(value))">
    <button @click="count++">Increment</button>
</div>

<!-- Deep watch -->
<div x-data="{ user: { name: '' } }"
     x-init="$watch('user', value => console.log(value), { deep: true })">
```

### $dispatch
Dispatch custom events.

```html
<!-- Dispatch event -->
<button @click="$dispatch('notify', { message: 'Hello!' })">
    Notify
</button>

<!-- Listen to event -->
<div @notify.window="alert($event.detail.message)">
    ...
</div>
```

### $nextTick
Wait for DOM to update.

```html
<div x-data="{ items: [] }">
    <button @click="items.push('new'); $nextTick(() => $refs.list.scrollTop = $refs.list.scrollHeight)">
        Add
    </button>
    <ul x-ref="list">
        <template x-for="item in items">
            <li x-text="item"></li>
        </template>
    </ul>
</div>
```

### $root
Reference to root x-data element.

```html
<div x-data="{ name: 'Parent' }">
    <div x-data="{ name: 'Child' }">
        <p x-text="$root.name"></p>  <!-- Shows "Parent" -->
    </div>
</div>
```

### $data
Reference to current component data.

```html
<div x-data="{ name: 'John', age: 30 }">
    <button @click="console.log($data)">Log Data</button>
</div>
```

### $id
Generate unique IDs.

```html
<div x-data>
    <input :id="$id('input')" type="text">
    <label :for="$id('input')">Name</label>
</div>
```

---

## Common Patterns

### Dropdown/Modal
```html
<div x-data="{ open: false }" @click.outside="open = false">
    <button @click="open = !open">Toggle</button>

    <div x-show="open" x-transition class="dropdown">
        <a href="#">Item 1</a>
        <a href="#">Item 2</a>
    </div>
</div>
```

### Tabs
```html
<div x-data="{ tab: 'tab1' }">
    <div class="tabs">
        <button :class="{ 'active': tab === 'tab1' }" @click="tab = 'tab1'">Tab 1</button>
        <button :class="{ 'active': tab === 'tab2' }" @click="tab = 'tab2'">Tab 2</button>
    </div>

    <div x-show="tab === 'tab1'">Content 1</div>
    <div x-show="tab === 'tab2'">Content 2</div>
</div>
```

### Form Validation
```html
<div x-data="{
    email: '',
    error: '',
    validate() {
        if (!this.email.includes('@')) {
            this.error = 'Invalid email';
            return false;
        }
        this.error = '';
        return true;
    }
}">
    <input type="email" x-model="email" @blur="validate">
    <p x-show="error" x-text="error" class="text-red-500"></p>
</div>
```

### Loading State
```html
<div x-data="{ loading: false, data: null }">
    <button @click="loading = true; data = await fetchData(); loading = false"
            :disabled="loading">
        <span x-show="!loading">Load</span>
        <span x-show="loading">Loading...</span>
    </button>

    <div x-show="data" x-text="JSON.stringify(data)"></div>
</div>
```

### Infinite Scroll
```html
<div x-data="{ items: [], page: 1, loading: false }"
     x-init="items = await loadPage(1)"
     @scroll.window.throttle.100ms="
         if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 100 && !loading) {
             loading = true;
             page++;
             items = [...items, ...await loadPage(page)];
             loading = false;
         }
     ">
    <template x-for="item in items" :key="item.id">
        <div x-text="item.title"></div>
    </template>
    <div x-show="loading">Loading more...</div>
</div>
```

### Dark Mode Toggle
```html
<div x-data="{
    dark: localStorage.getItem('dark') === 'true',
    toggle() {
        this.dark = !this.dark;
        localStorage.setItem('dark', this.dark);
    }
}" x-init="$watch('dark', val => document.documentElement.setAttribute('data-theme', val ? 'dark' : 'light'))">
    <button @click="toggle">
        <span x-show="!dark">Dark Mode</span>
        <span x-show="dark">Light Mode</span>
    </button>
</div>
```

---

## Tips

### Async in x-init
```html
<div x-data="{ data: [] }" x-init="data = await fetch('/api').then(r => r.json())">
```

### Access event in handler
```html
<button @click="handleClick($event)">Click</button>
```

### Conditional classes with Tailwind
```html
<div :class="{
    'bg-green-500': status === 'success',
    'bg-red-500': status === 'error',
    'bg-gray-500': status === 'pending'
}"></div>
```

### Dynamic component data
```html
<div x-data="components[type]">
    <!-- type determines which component to render -->
</div>
```

### Cleanup on component destroy
```html
<div x-data="{
    interval: null,
    init() {
        this.interval = setInterval(() => console.log('tick'), 1000);
    },
    destroy() {
        clearInterval(this.interval);
    }
}" @remove="destroy">
```
