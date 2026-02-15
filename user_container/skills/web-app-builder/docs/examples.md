# Example Applications

Complete working examples using Vue 3 + InstantDB / localStorage.

---

## 1. Todo App (InstantDB - Real-time CRUD)

A todo app with real-time cloud sync. Open in multiple tabs - changes sync instantly.

```html
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Todo App</title>
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
</head>
<body class="min-h-screen bg-base-200 p-8">
    <div id="app" class="max-w-md mx-auto">
        <h1 class="text-3xl font-bold mb-6">Todo List</h1>

        <form @submit.prevent="addTodo" class="flex gap-2 mb-6">
            <input type="text" v-model="newTitle" placeholder="What needs to be done?"
                   class="input input-bordered flex-1" required>
            <button type="submit" class="btn btn-primary">Add</button>
        </form>

        <!-- Filter tabs -->
        <div class="tabs tabs-boxed mb-4">
            <button v-for="f in ['all', 'active', 'done']" :key="f"
                    :class="['tab', { 'tab-active': filter === f }]"
                    @click="filter = f">
                {{ f.charAt(0).toUpperCase() + f.slice(1) }}
            </button>
        </div>

        <div class="space-y-2">
            <div v-for="todo in filteredTodos" :key="todo.id" class="card bg-base-100 shadow">
                <div class="card-body p-4 flex-row items-center gap-4">
                    <input type="checkbox" :checked="todo.done"
                           @change="toggleTodo(todo)" class="checkbox checkbox-primary">
                    <span class="flex-1" :class="{'line-through opacity-50': todo.done}">
                        {{ todo.title }}
                    </span>
                    <button @click="deleteTodo(todo.id)" class="btn btn-ghost btn-sm text-error">
                        Delete
                    </button>
                </div>
            </div>
        </div>

        <div class="stats shadow mt-6 w-full">
            <div class="stat">
                <div class="stat-title">Total</div>
                <div class="stat-value text-sm">{{ todos.length }}</div>
            </div>
            <div class="stat">
                <div class="stat-title">Done</div>
                <div class="stat-value text-sm text-success">{{ todos.filter(t => t.done).length }}</div>
            </div>
            <div class="stat">
                <div class="stat-title">Remaining</div>
                <div class="stat-value text-sm text-warning">{{ remaining }}</div>
            </div>
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
            const filter = ref('all');
            let unsub = null;

            onMounted(() => {
                unsub = db.subscribeQuery({
                    todos: { $: { order: { serverCreatedAt: 'desc' } } }
                }, (resp) => {
                    if (resp.data) todos.value = resp.data.todos;
                });
            });

            onUnmounted(() => { if (unsub) unsub(); });

            const filteredTodos = computed(() => {
                if (filter.value === 'active') return todos.value.filter(t => !t.done);
                if (filter.value === 'done') return todos.value.filter(t => t.done);
                return todos.value;
            });

            const remaining = computed(() => todos.value.filter(t => !t.done).length);

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

            return { todos, newTitle, filter, filteredTodos, remaining, addTodo, toggleTodo, deleteTodo };
        }
    }).mount('#app');
    </script>
</body>
</html>
```

---

## 2. Dashboard with Charts (localStorage)

A sales dashboard with Chart.js - no database needed, sample data generated locally.

```html
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sales Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
</head>
<body class="min-h-screen bg-base-200 p-8">
    <div id="app" class="container mx-auto max-w-6xl">
        <h1 class="text-3xl font-bold mb-8">Sales Dashboard</h1>

        <!-- Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div class="stat bg-base-100 rounded-box shadow">
                <div class="stat-title">Total Revenue</div>
                <div class="stat-value text-primary">${{ totalRevenue.toLocaleString() }}</div>
            </div>
            <div class="stat bg-base-100 rounded-box shadow">
                <div class="stat-title">Products</div>
                <div class="stat-value">{{ products.length }}</div>
            </div>
            <div class="stat bg-base-100 rounded-box shadow">
                <div class="stat-title">Avg Daily</div>
                <div class="stat-value text-secondary">${{ avgDaily.toLocaleString() }}</div>
            </div>
        </div>

        <!-- Charts -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div class="card bg-base-100 shadow">
                <div class="card-body">
                    <h2 class="card-title">Sales by Product</h2>
                    <canvas ref="pieChart"></canvas>
                </div>
            </div>
            <div class="card bg-base-100 shadow">
                <div class="card-body">
                    <h2 class="card-title">Daily Sales (Last 7 Days)</h2>
                    <canvas ref="lineChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Product Table -->
        <div class="card bg-base-100 shadow mt-6">
            <div class="card-body">
                <h2 class="card-title">Product Breakdown</h2>
                <div class="overflow-x-auto">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Product</th>
                                <th>Total Sales</th>
                                <th>Share</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="item in productStats" :key="item.name">
                                <td>{{ item.name }}</td>
                                <td>${{ item.total.toLocaleString() }}</td>
                                <td>
                                    <progress class="progress progress-primary w-20"
                                              :value="item.total" :max="totalRevenue"></progress>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
    const { createApp, ref, computed, onMounted, nextTick } = Vue;

    createApp({
        setup() {
            const pieChart = ref(null);
            const lineChart = ref(null);
            const products = ['Laptop', 'Phone', 'Tablet', 'Watch', 'Headphones'];
            const salesData = ref([]);

            // Generate sample data
            function generateData() {
                const data = [];
                for (let i = 0; i < 30; i++) {
                    const date = new Date();
                    date.setDate(date.getDate() - (29 - i));
                    for (const product of products) {
                        data.push({
                            product,
                            amount: Math.floor(Math.random() * 4000) + 100,
                            date: date.toISOString().split('T')[0]
                        });
                    }
                }
                return data;
            }

            const productStats = computed(() => {
                const stats = {};
                salesData.value.forEach(s => {
                    stats[s.product] = (stats[s.product] || 0) + s.amount;
                });
                return Object.entries(stats)
                    .map(([name, total]) => ({ name, total }))
                    .sort((a, b) => b.total - a.total);
            });

            const totalRevenue = computed(() =>
                salesData.value.reduce((sum, s) => sum + s.amount, 0)
            );

            const avgDaily = computed(() => {
                const last7 = salesData.value.filter(s => {
                    const d = new Date(s.date);
                    const now = new Date();
                    return (now - d) / 86400000 <= 7;
                });
                if (!last7.length) return 0;
                const days = new Set(last7.map(s => s.date)).size;
                return Math.round(last7.reduce((a, s) => a + s.amount, 0) / days);
            });

            function renderCharts() {
                const colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'];

                new Chart(pieChart.value, {
                    type: 'doughnut',
                    data: {
                        labels: productStats.value.map(p => p.name),
                        datasets: [{ data: productStats.value.map(p => p.total), backgroundColor: colors }]
                    }
                });

                // Daily totals for last 7 days
                const dailyMap = {};
                salesData.value.forEach(s => {
                    const d = new Date(s.date);
                    if ((new Date() - d) / 86400000 <= 7) {
                        dailyMap[s.date] = (dailyMap[s.date] || 0) + s.amount;
                    }
                });
                const dates = Object.keys(dailyMap).sort();

                new Chart(lineChart.value, {
                    type: 'line',
                    data: {
                        labels: dates,
                        datasets: [{
                            label: 'Sales',
                            data: dates.map(d => dailyMap[d]),
                            borderColor: '#36A2EB',
                            tension: 0.1,
                            fill: true,
                            backgroundColor: 'rgba(54, 162, 235, 0.1)'
                        }]
                    },
                    options: { scales: { y: { beginAtZero: true } } }
                });
            }

            onMounted(async () => {
                salesData.value = generateData();
                await nextTick();
                renderCharts();
            });

            return { products, productStats, totalRevenue, avgDaily, pieChart, lineChart };
        }
    }).mount('#app');
    </script>
</body>
</html>
```

---

## 3. Chat App (InstantDB + Auth)

Multi-user real-time chat with magic code authentication.

```html
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chat Room</title>
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <style>
        .messages-container { height: calc(100vh - 200px); }
    </style>
</head>
<body class="min-h-screen bg-base-300">
    <div id="app" class="container mx-auto p-4 max-w-2xl">

        <!-- Auth: Login -->
        <div v-if="!user" class="card bg-base-100 shadow-xl mt-20">
            <div class="card-body">
                <h2 class="card-title justify-center">Join Chat</h2>

                <div v-if="!codeSent">
                    <input type="email" v-model="email" placeholder="Your email"
                           class="input input-bordered w-full mb-4" required
                           @keydown.enter="sendCode">
                    <button @click="sendCode" class="btn btn-primary w-full"
                            :disabled="sending">
                        {{ sending ? 'Sending...' : 'Send Login Code' }}
                    </button>
                </div>

                <div v-else>
                    <p class="mb-4 text-sm opacity-70">Code sent to {{ email }}</p>
                    <input type="text" v-model="code" placeholder="Enter code"
                           class="input input-bordered w-full mb-4"
                           @keydown.enter="verifyCode">
                    <button @click="verifyCode" class="btn btn-primary w-full">Verify</button>
                    <button @click="codeSent = false" class="btn btn-ghost btn-sm mt-2">Back</button>
                </div>

                <p v-if="authError" class="text-error mt-2 text-center">{{ authError }}</p>
            </div>
        </div>

        <!-- Chat -->
        <div v-else class="flex flex-col h-screen py-4">
            <div class="navbar bg-base-100 rounded-box shadow mb-4">
                <div class="flex-1">
                    <span class="text-xl font-bold">Chat Room</span>
                </div>
                <div class="flex-none gap-2">
                    <span class="badge badge-primary">{{ user.email }}</span>
                    <button @click="signOut" class="btn btn-ghost btn-sm">Logout</button>
                </div>
            </div>

            <!-- Messages -->
            <div class="messages-container overflow-y-auto bg-base-100 rounded-box p-4 mb-4" ref="messagesContainer">
                <div v-for="msg in messages" :key="msg.id"
                     :class="['chat', msg.userId === user.id ? 'chat-end' : 'chat-start']">
                    <div class="chat-header">
                        <span class="text-sm font-medium">{{ msg.senderEmail }}</span>
                        <time class="text-xs opacity-50 ml-1">{{ formatTime(msg.createdAt) }}</time>
                    </div>
                    <div class="chat-bubble" :class="msg.userId === user.id ? 'chat-bubble-primary' : ''">
                        {{ msg.content }}
                    </div>
                </div>
            </div>

            <!-- Input -->
            <form @submit.prevent="sendMessage" class="flex gap-2">
                <input type="text" v-model="newMessage" placeholder="Type a message..."
                       class="input input-bordered flex-1" required>
                <button type="submit" class="btn btn-primary">Send</button>
            </form>
        </div>
    </div>

    <script type="module">
    import { init, id } from 'https://unpkg.com/@instantdb/core@latest/dist/standalone/index.js';

    const db = init({ appId: 'YOUR_APP_ID' });
    const { createApp, ref, onMounted, onUnmounted, nextTick } = Vue;

    createApp({
        setup() {
            const user = ref(null);
            const email = ref('');
            const code = ref('');
            const codeSent = ref(false);
            const sending = ref(false);
            const authError = ref('');
            const messages = ref([]);
            const newMessage = ref('');
            const messagesContainer = ref(null);
            let unsubMessages = null;

            onMounted(() => {
                db.subscribeAuth((auth) => {
                    user.value = auth.user || null;
                    if (auth.user) subscribeMessages();
                });
            });

            onUnmounted(() => { if (unsubMessages) unsubMessages(); });

            function subscribeMessages() {
                unsubMessages = db.subscribeQuery({
                    messages: { $: { order: { serverCreatedAt: 'asc' }, limit: 100 } }
                }, (resp) => {
                    if (resp.data) {
                        messages.value = resp.data.messages;
                        nextTick(() => scrollToBottom());
                    }
                });
            }

            async function sendCode() {
                sending.value = true;
                authError.value = '';
                try {
                    await db.auth.sendMagicCode({ email: email.value });
                    codeSent.value = true;
                } catch (e) { authError.value = e.message; }
                finally { sending.value = false; }
            }

            async function verifyCode() {
                authError.value = '';
                try {
                    await db.auth.signInWithMagicCode({ email: email.value, code: code.value });
                } catch (e) { authError.value = 'Invalid code'; }
            }

            function signOut() { db.auth.signOut(); }

            function sendMessage() {
                if (!newMessage.value.trim()) return;
                db.transact(db.tx.messages[id()].update({
                    content: newMessage.value.trim(),
                    userId: user.value.id,
                    senderEmail: user.value.email,
                    createdAt: Date.now()
                }));
                newMessage.value = '';
            }

            function scrollToBottom() {
                if (messagesContainer.value) {
                    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
                }
            }

            function formatTime(ts) {
                if (!ts) return '';
                return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            }

            return {
                user, email, code, codeSent, sending, authError,
                messages, newMessage, messagesContainer,
                sendCode, verifyCode, signOut, sendMessage, formatTime
            };
        }
    }).mount('#app');
    </script>
</body>
</html>
```
