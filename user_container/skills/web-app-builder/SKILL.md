---
name: web-app-builder
description: "Build web apps as single HTML files with Vue 3 (CDN), InstantDB (real-time DB + auth), Tailwind CSS + DaisyUI. No backend, no npm, no build step."
---

# Web App Builder

Build web applications as single HTML files - no backend, no npm, no build step:
- **Frontend**: Vue 3 (CDN) - Composition API with setup()
- **Database**: InstantDB (real-time, cloud) OR localStorage (offline)
- **Auth**: InstantDB Auth (magic codes, Google OAuth)
- **Styling**: Tailwind CSS + DaisyUI (CDN)
- **Output**: Single HTML file -> `artifacts/<name>.html`

## When to Use InstantDB vs localStorage

| Feature | InstantDB | localStorage |
|---------|-----------|-------------|
| Multi-user | Yes | No |
| Real-time sync | Yes | No |
| Authentication | Built-in | Manual |
| Cloud storage | Yes | Browser only |
| Offline support | Limited | Full |
| Setup required | App ID needed | None |

**Use InstantDB when:** multi-user apps, real-time collaboration, data persistence across devices, auth needed.
**Use localStorage when:** single-user tools, calculators, offline apps, quick prototypes, no account needed.

## Important: Editing Existing Apps

**When user asks to fix, improve, or change an existing app - MODIFY THE EXISTING FILE, do NOT create a new app!**

1. First, check if app already exists: `list_dir("artifacts")`
2. If app exists, read and edit the existing file (`read_file`, `write_file`)
3. Only create new app if user explicitly asks for a NEW app

**Examples:**
- "Fix the button" -> Edit existing HTML file
- "Add dark mode" -> Modify existing app
- "The form doesn't work" -> Debug and fix existing code
- "Create a NEW todo app" -> Create new file

## Styling Options

**For professional, unique designs** (default):
- Read `frontend-design/docs/design-principles.md` - design fundamentals
- Read `frontend-design/docs/inspiration-process.md` - how to find inspiration
- Read `frontend-design/docs/differentiation-techniques.md` - how to differentiate design
- Use custom CSS instead of DaisyUI
- `frontend-design/docs/custom-components.md` has ready-to-use CSS components

**For quick prototypes** (only when user explicitly asks):
- Use DaisyUI + Tailwind as documented below
- Faster, but generic

**Content rule - NO EMOJIS** unless user explicitly requests them. Emojis are a telltale sign of AI-generated content. Instead use:
- Icons (Lucide, Heroicons via CDN)
- Use web search to find relevant professional stock photos
- Simple SVG illustrations or nothing at all

---

## Quick Start

### Project Structure

```
artifacts/my-app.html   <-- one file, that's everything!
```

### Boilerplate - With InstantDB

```html
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My App</title>
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
</head>
<body class="min-h-screen bg-base-200 p-8">
    <div id="app" class="max-w-md mx-auto">
        <h1 class="text-3xl font-bold mb-6">Todo List</h1>

        <!-- Add form -->
        <form @submit.prevent="addTodo" class="flex gap-2 mb-6">
            <input type="text" v-model="newTitle" placeholder="What needs to be done?"
                   class="input input-bordered flex-1" required>
            <button type="submit" class="btn btn-primary">Add</button>
        </form>

        <!-- Todo list -->
        <div class="space-y-2">
            <div v-for="todo in todos" :key="todo.id" class="card bg-base-100 shadow">
                <div class="card-body p-4 flex-row items-center gap-4">
                    <input type="checkbox" :checked="todo.done"
                           @change="toggleTodo(todo)"
                           class="checkbox checkbox-primary">
                    <span class="flex-1" :class="{'line-through opacity-50': todo.done}">
                        {{ todo.title }}
                    </span>
                    <button @click="deleteTodo(todo.id)" class="btn btn-ghost btn-sm text-error">
                        Delete
                    </button>
                </div>
            </div>
        </div>

        <!-- Stats -->
        <div class="mt-6 text-sm opacity-70">
            {{ remaining }} remaining
        </div>
    </div>

    <script type="module">
    import { init, id } from 'https://unpkg.com/@instantdb/core@latest/dist/standalone/index.js';

    const db = init({ appId: 'YOUR_APP_ID' });

    const { createApp, ref, computed, onMounted, onUnmounted } = Vue;

    createApp({
        setup() {
            const todos = ref([]);
            const newTitle = ref('');
            let unsub = null;

            onMounted(() => {
                unsub = db.subscribeQuery({ todos: {} }, (resp) => {
                    if (resp.data) todos.value = resp.data.todos;
                });
            });

            onUnmounted(() => { if (unsub) unsub(); });

            function addTodo() {
                if (!newTitle.value.trim()) return;
                db.transact(db.tx.todos[id()].update({
                    title: newTitle.value.trim(),
                    done: false,
                    createdAt: Date.now()
                }));
                newTitle.value = '';
            }

            function toggleTodo(todo) {
                db.transact(db.tx.todos[todo.id].update({ done: !todo.done }));
            }

            function deleteTodo(todoId) {
                db.transact(db.tx.todos[todoId].delete());
            }

            const remaining = computed(() => todos.value.filter(t => !t.done).length);

            return { todos, newTitle, addTodo, toggleTodo, deleteTodo, remaining };
        }
    }).mount('#app');
    </script>
</body>
</html>
```

### Boilerplate - With localStorage (no InstantDB)

```html
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My App</title>
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
</head>
<body class="min-h-screen bg-base-200 p-8">
    <div id="app" class="max-w-md mx-auto">
        <h1 class="text-3xl font-bold mb-6">Todo List</h1>

        <!-- Add form -->
        <form @submit.prevent="addTodo" class="flex gap-2 mb-6">
            <input type="text" v-model="newTitle" placeholder="What needs to be done?"
                   class="input input-bordered flex-1" required>
            <button type="submit" class="btn btn-primary">Add</button>
        </form>

        <!-- Todo list -->
        <div class="space-y-2">
            <div v-for="todo in todos" :key="todo.id" class="card bg-base-100 shadow">
                <div class="card-body p-4 flex-row items-center gap-4">
                    <input type="checkbox" :checked="todo.done"
                           @change="toggleTodo(todo.id)"
                           class="checkbox checkbox-primary">
                    <span class="flex-1" :class="{'line-through opacity-50': todo.done}">
                        {{ todo.title }}
                    </span>
                    <button @click="deleteTodo(todo.id)" class="btn btn-ghost btn-sm text-error">
                        Delete
                    </button>
                </div>
            </div>
        </div>

        <!-- Stats -->
        <div class="mt-6 text-sm opacity-70">
            {{ remaining }} remaining
        </div>
    </div>

    <script>
    const { createApp, ref, computed, watch } = Vue;

    createApp({
        setup() {
            const todos = ref(JSON.parse(localStorage.getItem('todos') || '[]'));
            const newTitle = ref('');

            // Auto-save to localStorage
            watch(todos, (val) => {
                localStorage.setItem('todos', JSON.stringify(val));
            }, { deep: true });

            function addTodo() {
                if (!newTitle.value.trim()) return;
                todos.value.push({
                    id: crypto.randomUUID(),
                    title: newTitle.value.trim(),
                    done: false,
                    createdAt: Date.now()
                });
                newTitle.value = '';
            }

            function toggleTodo(id) {
                const todo = todos.value.find(t => t.id === id);
                if (todo) todo.done = !todo.done;
            }

            function deleteTodo(id) {
                todos.value = todos.value.filter(t => t.id !== id);
            }

            const remaining = computed(() => todos.value.filter(t => !t.done).length);

            return { todos, newTitle, addTodo, toggleTodo, deleteTodo, remaining };
        }
    }).mount('#app');
    </script>
</body>
</html>
```

---

## CDN Links

```html
<!-- Vue 3 -->
<script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>

<!-- InstantDB (ESM module) -->
<script type="module">
  import { init, id } from 'https://unpkg.com/@instantdb/core@latest/dist/standalone/index.js';
</script>

<!-- Tailwind CSS + DaisyUI -->
<link href="https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css" rel="stylesheet">
<script src="https://cdn.tailwindcss.com"></script>
```

---

## Architecture

### How It Works

1. **Vue 3** provides reactivity and component structure via CDN
2. **InstantDB** handles real-time data sync and auth from the browser
3. **Tailwind + DaisyUI** provide styling without build step
4. Single HTML file - open directly in browser, no server needed

### Why This Stack?

- **No build step**: Just open the HTML file
- **No backend**: InstantDB handles data and auth
- **Real-time by default**: Data syncs automatically across all clients
- **Single file**: Easy to create, share, and modify
- **Zero deployment**: Open in browser and it works

---

## Frontend Reference

### Vue 3 Basics

See `docs/vue-cdn.md` for full Vue 3 CDN documentation:
- Composition API: `ref()`, `reactive()`, `computed()`, `watch()`
- Template syntax: `{{ }}`, `v-bind`/`:`, `v-on`/`@`, `v-model`, `v-for`, `v-if`
- Lifecycle: `onMounted()`, `onUnmounted()`
- Migration table from Alpine.js

### Tailwind + DaisyUI

See `docs/tailwind-daisyui.md` for full styling documentation.

**DaisyUI components:**
- `btn`, `btn-primary`, `btn-ghost` - Buttons
- `card`, `card-body` - Cards
- `input`, `input-bordered` - Inputs
- `modal` - Modals
- `navbar` - Navigation
- `alert` - Alerts
- `badge` - Badges

**Themes:**
```html
<html data-theme="light">  <!-- or "dark", "cupcake", "dracula", etc. -->
```

---

## Database Reference

See `docs/instantdb.md` for full InstantDB documentation:
- Real-time subscriptions
- CRUD operations (transact)
- Relations (link/unlink)
- Authentication (magic codes, Google OAuth)
- localStorage fallback pattern

---

## Common Patterns

### Authentication (InstantDB Magic Codes)

```html
<div id="app">
    <!-- Login form -->
    <div v-if="!user" class="max-w-sm mx-auto mt-20">
        <div class="card bg-base-100 shadow-xl">
            <div class="card-body">
                <h2 class="card-title">Login</h2>
                <div v-if="!codeSent">
                    <input type="email" v-model="email" placeholder="Email"
                           class="input input-bordered w-full mb-4" required>
                    <button @click="sendCode" class="btn btn-primary w-full"
                            :disabled="sending">
                        {{ sending ? 'Sending...' : 'Send Login Code' }}
                    </button>
                </div>
                <div v-else>
                    <p class="mb-4 text-sm">Code sent to {{ email }}</p>
                    <input type="text" v-model="code" placeholder="Enter code"
                           class="input input-bordered w-full mb-4" required>
                    <button @click="verifyCode" class="btn btn-primary w-full">
                        Verify
                    </button>
                </div>
                <p v-if="error" class="text-error mt-2">{{ error }}</p>
            </div>
        </div>
    </div>

    <!-- Main app (when logged in) -->
    <div v-else>
        <div class="navbar bg-base-100 shadow mb-4">
            <div class="flex-1"><span class="text-xl font-bold">My App</span></div>
            <div class="flex-none gap-2">
                <span class="text-sm">{{ user.email }}</span>
                <button @click="signOut" class="btn btn-ghost btn-sm">Logout</button>
            </div>
        </div>
        <!-- App content here -->
    </div>
</div>

<script type="module">
import { init, id } from 'https://unpkg.com/@instantdb/core@latest/dist/standalone/index.js';
const db = init({ appId: 'YOUR_APP_ID' });
const { createApp, ref, onMounted } = Vue;

createApp({
    setup() {
        const user = ref(null);
        const email = ref('');
        const code = ref('');
        const codeSent = ref(false);
        const sending = ref(false);
        const error = ref('');

        onMounted(() => {
            db.subscribeAuth((auth) => {
                user.value = auth.user || null;
            });
        });

        async function sendCode() {
            sending.value = true;
            error.value = '';
            try {
                await db.auth.sendMagicCode({ email: email.value });
                codeSent.value = true;
            } catch (e) { error.value = e.message; }
            finally { sending.value = false; }
        }

        async function verifyCode() {
            error.value = '';
            try {
                await db.auth.signInWithMagicCode({ email: email.value, code: code.value });
            } catch (e) { error.value = 'Invalid code'; }
        }

        function signOut() { db.auth.signOut(); }

        return { user, email, code, codeSent, sending, error, sendCode, verifyCode, signOut };
    }
}).mount('#app');
</script>
```

### Data Table with Sorting

```html
<div class="overflow-x-auto">
    <table class="table">
        <thead>
            <tr>
                <th @click="sortBy('name')" class="cursor-pointer">
                    Name {{ sortKey === 'name' ? (sortAsc ? '↑' : '↓') : '' }}
                </th>
                <th @click="sortBy('email')" class="cursor-pointer">
                    Email {{ sortKey === 'email' ? (sortAsc ? '↑' : '↓') : '' }}
                </th>
                <th>Status</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            <tr v-for="user in sortedUsers" :key="user.id">
                <td>{{ user.name }}</td>
                <td>{{ user.email }}</td>
                <td>
                    <span class="badge" :class="user.active ? 'badge-success' : 'badge-ghost'">
                        {{ user.active ? 'Active' : 'Inactive' }}
                    </span>
                </td>
                <td>
                    <button @click="editUser(user)" class="btn btn-ghost btn-xs">Edit</button>
                    <button @click="deleteUser(user.id)" class="btn btn-ghost btn-xs text-error">Delete</button>
                </td>
            </tr>
        </tbody>
    </table>
</div>

<script>
setup() {
    const users = ref([]);
    const sortKey = ref('name');
    const sortAsc = ref(true);

    const sortedUsers = computed(() => {
        return [...users.value].sort((a, b) => {
            const valA = a[sortKey.value];
            const valB = b[sortKey.value];
            const cmp = String(valA).localeCompare(String(valB));
            return sortAsc.value ? cmp : -cmp;
        });
    });

    function sortBy(key) {
        if (sortKey.value === key) {
            sortAsc.value = !sortAsc.value;
        } else {
            sortKey.value = key;
            sortAsc.value = true;
        }
    }

    return { users, sortKey, sortAsc, sortedUsers, sortBy };
}
</script>
```

### Modal Dialog

```html
<!-- Trigger -->
<button @click="showModal = true" class="btn btn-primary">Open Modal</button>

<!-- Modal -->
<div v-show="showModal" class="modal modal-open">
    <div class="modal-box">
        <h3 class="font-bold text-lg">Modal Title</h3>
        <p class="py-4">Modal content goes here.</p>
        <div class="modal-action">
            <button @click="showModal = false" class="btn btn-ghost">Cancel</button>
            <button @click="saveAndClose()" class="btn btn-primary">Save</button>
        </div>
    </div>
    <div class="modal-backdrop" @click="showModal = false"></div>
</div>

<script>
setup() {
    const showModal = ref(false);

    function saveAndClose() {
        // save logic
        showModal.value = false;
    }

    return { showModal, saveAndClose };
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

---

## InstantDB App ID

When the app needs InstantDB (multi-user, real-time, auth), **ask the user** for their App ID using `ask_user`.

Provide these instructions:
1. Go to https://www.instantdb.com/dash
2. Create a new app (or select existing)
3. Copy the App ID from the dashboard
4. Paste it here

---

## Additional Libraries

See `docs/libraries.md` for integration guides:
- **Chart.js** - Simple charts
- **Leaflet** - Maps
- **Quill** - Rich text editor
- **SortableJS** - Drag & drop
- **Day.js** - Date formatting
- **jsPDF** - PDF export

---

## Docs References

- `docs/vue-cdn.md` - Vue 3 CDN reference (Composition API, template syntax, patterns)
- `docs/instantdb.md` - InstantDB CRUD, auth, permissions, localStorage fallback
- `docs/tailwind-daisyui.md` - Styling (Tailwind utilities + DaisyUI components)
- `docs/libraries.md` - Chart.js, Leaflet, Quill, SortableJS, Day.js etc.
- `docs/skill-api.md` - AI features (requires separate Python backend)

---

## Skill API - AI in Applications

Apps can use AI (transcription, image analysis, LLM) via the Skill API.

**Documentation:** See `docs/skill-api.md`

**Important:** The Skill API requires a Python backend. If your app needs AI features, write a separate Python script with FastAPI and have the frontend communicate with it via fetch. The HTML app and the Python script are separate files.
