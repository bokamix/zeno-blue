# InstantDB Documentation

InstantDB is a real-time database with built-in auth. Works entirely from the browser via CDN - no backend needed.

## CDN Setup

```html
<script type="module">
import { init, id } from 'https://unpkg.com/@instantdb/core@latest/dist/standalone/index.js';

const db = init({ appId: 'YOUR_APP_ID' });
</script>
```

**Getting an App ID:** Go to https://www.instantdb.com/dash, create an app, copy the App ID.

---

## Reading Data (Subscriptions)

InstantDB uses real-time subscriptions - data updates automatically when it changes.

### Basic Query
```javascript
// Subscribe to all todos
db.subscribeQuery({ todos: {} }, (resp) => {
    if (resp.error) {
        console.error('Query error:', resp.error);
        return;
    }
    if (resp.data) {
        console.log('Todos:', resp.data.todos);
    }
});
```

### With Vue 3 Integration
```javascript
// Core pattern: connect InstantDB subscriptions to Vue reactivity
const todos = ref([]);
let unsub = null;

onMounted(() => {
    unsub = db.subscribeQuery({ todos: {} }, (resp) => {
        if (resp.data) todos.value = resp.data.todos;
    });
});

onUnmounted(() => { if (unsub) unsub(); });
```

### Filtering (where)
```javascript
db.subscribeQuery({
    todos: {
        $: { where: { done: false } }
    }
}, callback);

// Multiple conditions (AND)
db.subscribeQuery({
    todos: {
        $: { where: { done: false, priority: 'high' } }
    }
}, callback);

// Comparison operators
db.subscribeQuery({
    todos: {
        $: { where: { createdAt: { $gt: someTimestamp } } }
    }
}, callback);
// Available: $gt, $gte, $lt, $lte, $ne, $in, $like
```

### Sorting (order)
```javascript
db.subscribeQuery({
    todos: {
        $: {
            where: { done: false },
            order: { serverCreatedAt: 'desc' }
        }
    }
}, callback);
```

### Limiting
```javascript
db.subscribeQuery({
    todos: {
        $: {
            order: { serverCreatedAt: 'desc' },
            limit: 10
        }
    }
}, callback);
```

### Relations (nested queries)
```javascript
// Get todos with their tags
db.subscribeQuery({
    todos: {
        tags: {}  // fetch related tags
    }
}, callback);
// Result: resp.data.todos = [{ id, title, tags: [{ id, name }] }]
```

---

## Writing Data (Transactions)

### Create
```javascript
import { id } from 'https://unpkg.com/@instantdb/core@latest/dist/standalone/index.js';

// Create a new todo
db.transact(db.tx.todos[id()].update({
    title: 'Buy groceries',
    done: false,
    createdAt: Date.now()
}));
```

### Update
```javascript
// Update a todo by ID
db.transact(db.tx.todos[todoId].update({
    done: true
}));
```

### Delete
```javascript
// Delete a todo
db.transact(db.tx.todos[todoId].delete());
```

### Merge (deep update)
```javascript
// merge() is like update() but does deep merge for nested objects
db.transact(db.tx.todos[todoId].merge({
    metadata: { updatedAt: Date.now() }
}));
```

### Batch Operations
```javascript
// Multiple operations in one transaction
db.transact([
    db.tx.todos[id()].update({ title: 'Task 1', done: false }),
    db.tx.todos[id()].update({ title: 'Task 2', done: false }),
    db.tx.todos[oldId].delete()
]);
```

---

## Relations

### Link
```javascript
// Link a todo to a tag
db.transact(db.tx.todos[todoId].link({ tags: tagId }));
```

### Unlink
```javascript
// Remove the link
db.transact(db.tx.todos[todoId].unlink({ tags: tagId }));
```

---

## Authentication

### Magic Codes (email)

```javascript
// Step 1: Send magic code to email
async function sendCode(email) {
    await db.auth.sendMagicCode({ email });
}

// Step 2: Verify the code
async function verifyCode(email, code) {
    try {
        await db.auth.signInWithMagicCode({ email, code });
        // User is now signed in
    } catch (err) {
        console.error('Invalid code:', err);
    }
}
```

### Google OAuth

```javascript
// Requires Google Client ID in InstantDB dashboard
const nonce = crypto.randomUUID();

// Load Google Sign-In button, then on callback:
async function handleGoogleSignIn(response) {
    await db.auth.signInWithIdToken({
        clientName: 'google',
        idToken: response.credential,
        nonce
    });
}
```

### Current User

```javascript
// Subscribe to auth state
const user = ref(null);

onMounted(() => {
    db.subscribeAuth((auth) => {
        if (auth.user) {
            user.value = auth.user; // { id, email }
        } else {
            user.value = null;
        }
    });
});
```

### Sign Out

```javascript
function signOut() {
    db.auth.signOut();
}
```

---

## Permissions

Permissions are configured in the InstantDB dashboard (https://www.instantdb.com/dash).

Basic example (allow authenticated users to manage their own data):
```json
{
  "todos": {
    "allow": {
      "view": "auth.id == data.creatorId",
      "create": "isOwner",
      "update": "isOwner",
      "delete": "isOwner"
    },
    "bind": ["isOwner", "auth.id == data.creatorId"]
  }
}
```

For full permissions docs, see InstantDB dashboard.

---

## localStorage Fallback Pattern

For apps that don't need cloud sync / multi-user - use localStorage instead of InstantDB.

### Storage Helper
```javascript
function useLocalStorage(key, defaultValue) {
    const data = ref(JSON.parse(localStorage.getItem(key)) || defaultValue);

    watch(data, (newVal) => {
        localStorage.setItem(key, JSON.stringify(newVal));
    }, { deep: true });

    return data;
}
```

### Usage in Vue Setup
```javascript
setup() {
    const todos = useLocalStorage('todos', []);

    function addTodo(title) {
        todos.value.push({
            id: crypto.randomUUID(),
            title,
            done: false,
            createdAt: Date.now()
        });
    }

    function toggleTodo(id) {
        const todo = todos.value.find(t => t.id === id);
        if (todo) todo.done = !todo.done;
    }

    function deleteTodo(id) {
        todos.value = todos.value.filter(t => t.id !== id);
    }

    return { todos, addTodo, toggleTodo, deleteTodo };
}
```

---

## Full Vue + InstantDB Integration Pattern

```html
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
```
