# Example Applications

Complete working examples using FastAPI + SQLite + Alpine.js.

---

## 1. Task Manager (CRUD + Auth)

A task management app with user authentication.

### app.py
```python
# /// script
# dependencies = ["fastapi", "uvicorn"]
# ///

import sqlite3
import json
import asyncio
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from contextlib import asynccontextmanager

DB_PATH = Path(__file__).parent / "data.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            done BOOLEAN DEFAULT 0,
            priority TEXT DEFAULT 'medium',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()

subscribers: list[asyncio.Queue] = []

async def broadcast(event: str, data: dict):
    message = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    for queue in subscribers:
        await queue.put(message)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

# Auth
@app.post("/api/register")
async def register(request: Request):
    data = await request.json()
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                    (data["username"], data["password"]))
        conn.commit()
        user = conn.execute("SELECT id, username FROM users WHERE username = ?",
                           (data["username"],)).fetchone()
        return dict(user)
    except sqlite3.IntegrityError:
        raise HTTPException(400, "Username taken")
    finally:
        conn.close()

@app.post("/api/login")
async def login(request: Request):
    data = await request.json()
    conn = get_db()
    user = conn.execute("SELECT id, username FROM users WHERE username = ? AND password = ?",
                       (data["username"], data["password"])).fetchone()
    conn.close()
    if not user:
        raise HTTPException(401, "Invalid credentials")
    return dict(user)

# Tasks CRUD
@app.get("/api/tasks")
async def list_tasks(user_id: int):
    conn = get_db()
    tasks = conn.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC",
                        (user_id,)).fetchall()
    conn.close()
    return [dict(t) for t in tasks]

@app.post("/api/tasks")
async def create_task(request: Request):
    data = await request.json()
    conn = get_db()
    cursor = conn.execute("INSERT INTO tasks (user_id, title, priority) VALUES (?, ?, ?)",
                         (data["user_id"], data["title"], data.get("priority", "medium")))
    conn.commit()
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    await broadcast("task_created", dict(task))
    return dict(task)

@app.put("/api/tasks/{task_id}")
async def update_task(task_id: int, request: Request):
    data = await request.json()
    conn = get_db()
    updates = []
    values = []
    for key in ["title", "done", "priority"]:
        if key in data:
            updates.append(f"{key} = ?")
            values.append(data[key])
    values.append(task_id)
    conn.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", values)
    conn.commit()
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    await broadcast("task_updated", dict(task))
    return dict(task)

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int):
    conn = get_db()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    await broadcast("task_deleted", {"id": task_id})
    return {"ok": True}

@app.get("/api/events")
async def events():
    queue = asyncio.Queue()
    subscribers.append(queue)
    async def stream():
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30)
                    yield message
                except asyncio.TimeoutError:
                    yield "event: ping\ndata: {}\n\n"
        finally:
            subscribers.remove(queue)
    return StreamingResponse(stream(), media_type="text/event-stream")

@app.get("/")
async def index():
    return HTMLResponse(Path("index.html").read_text())

if __name__ == "__main__":
    import uvicorn
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
```

### index.html
```html
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Task Manager</title>
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js"></script>
</head>
<body class="min-h-screen bg-base-200">
    <div x-data="taskApp()" x-init="init()" class="container mx-auto p-4 max-w-2xl">

        <!-- Auth -->
        <template x-if="!user">
            <div class="card bg-base-100 shadow-xl mt-20">
                <div class="card-body">
                    <h2 class="card-title justify-center text-2xl mb-4">Task Manager</h2>
                    <div class="tabs tabs-boxed justify-center mb-4">
                        <a class="tab" :class="{'tab-active': authMode === 'login'}" @click="authMode = 'login'">Login</a>
                        <a class="tab" :class="{'tab-active': authMode === 'register'}" @click="authMode = 'register'">Register</a>
                    </div>
                    <form @submit.prevent="submitAuth">
                        <input type="text" x-model="username" placeholder="Username" class="input input-bordered w-full mb-2" required>
                        <input type="password" x-model="password" placeholder="Password" class="input input-bordered w-full mb-4" required>
                        <button type="submit" class="btn btn-primary w-full" x-text="authMode === 'login' ? 'Login' : 'Register'"></button>
                    </form>
                    <p x-show="error" class="text-error mt-2 text-center" x-text="error"></p>
                </div>
            </div>
        </template>

        <!-- Main App -->
        <template x-if="user">
            <div>
                <div class="navbar bg-base-100 rounded-box shadow mb-4">
                    <div class="flex-1">
                        <span class="text-xl font-bold">Task Manager</span>
                    </div>
                    <div class="flex-none gap-2">
                        <span class="text-sm" x-text="user.username"></span>
                        <button @click="logout" class="btn btn-ghost btn-sm">Logout</button>
                    </div>
                </div>

                <!-- Add Task -->
                <form @submit.prevent="addTask" class="flex gap-2 mb-4">
                    <input type="text" x-model="newTitle" placeholder="New task..." class="input input-bordered flex-1" required>
                    <select x-model="newPriority" class="select select-bordered">
                        <option value="low">Low</option>
                        <option value="medium" selected>Medium</option>
                        <option value="high">High</option>
                    </select>
                    <button type="submit" class="btn btn-primary">Add</button>
                </form>

                <!-- Task List -->
                <div class="space-y-2">
                    <template x-for="task in tasks" :key="task.id">
                        <div class="card bg-base-100 shadow">
                            <div class="card-body p-4 flex-row items-center gap-4">
                                <input type="checkbox" :checked="task.done" @change="toggleTask(task)" class="checkbox">
                                <span class="flex-1" :class="{'line-through opacity-50': task.done}" x-text="task.title"></span>
                                <span class="badge" :class="{
                                    'badge-error': task.priority === 'high',
                                    'badge-warning': task.priority === 'medium',
                                    'badge-info': task.priority === 'low'
                                }" x-text="task.priority"></span>
                                <button @click="deleteTask(task.id)" class="btn btn-ghost btn-sm text-error">Delete</button>
                            </div>
                        </div>
                    </template>
                </div>

                <!-- Stats -->
                <div class="stats shadow mt-4 w-full">
                    <div class="stat">
                        <div class="stat-title">Total</div>
                        <div class="stat-value" x-text="tasks.length"></div>
                    </div>
                    <div class="stat">
                        <div class="stat-title">Done</div>
                        <div class="stat-value text-success" x-text="tasks.filter(t => t.done).length"></div>
                    </div>
                    <div class="stat">
                        <div class="stat-title">Pending</div>
                        <div class="stat-value text-warning" x-text="tasks.filter(t => !t.done).length"></div>
                    </div>
                </div>
            </div>
        </template>
    </div>

    <script>
    function taskApp() {
        return {
            user: JSON.parse(localStorage.getItem('user')) || null,
            authMode: 'login',
            username: '',
            password: '',
            error: '',
            tasks: [],
            newTitle: '',
            newPriority: 'medium',

            async init() {
                if (this.user) {
                    await this.loadTasks();
                    this.connectSSE();
                }
            },

            async submitAuth() {
                this.error = '';
                const endpoint = this.authMode === 'login' ? '/api/login' : '/api/register';
                try {
                    const res = await fetch(endpoint, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({username: this.username, password: this.password})
                    });
                    if (!res.ok) throw new Error((await res.json()).detail);
                    this.user = await res.json();
                    localStorage.setItem('user', JSON.stringify(this.user));
                    await this.loadTasks();
                    this.connectSSE();
                } catch (e) {
                    this.error = e.message;
                }
            },

            logout() {
                this.user = null;
                this.tasks = [];
                localStorage.removeItem('user');
            },

            async loadTasks() {
                const res = await fetch(`/api/tasks?user_id=${this.user.id}`);
                this.tasks = await res.json();
            },

            async addTask() {
                if (!this.newTitle.trim()) return;
                await fetch('/api/tasks', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({user_id: this.user.id, title: this.newTitle, priority: this.newPriority})
                });
                this.newTitle = '';
            },

            async toggleTask(task) {
                await fetch(`/api/tasks/${task.id}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({done: !task.done})
                });
            },

            async deleteTask(id) {
                await fetch(`/api/tasks/${id}`, {method: 'DELETE'});
            },

            connectSSE() {
                const es = new EventSource('/api/events');
                es.addEventListener('task_created', (e) => {
                    const task = JSON.parse(e.data);
                    if (task.user_id === this.user.id) this.tasks.unshift(task);
                });
                es.addEventListener('task_updated', (e) => {
                    const task = JSON.parse(e.data);
                    const idx = this.tasks.findIndex(t => t.id === task.id);
                    if (idx !== -1) this.tasks[idx] = task;
                });
                es.addEventListener('task_deleted', (e) => {
                    const {id} = JSON.parse(e.data);
                    this.tasks = this.tasks.filter(t => t.id !== id);
                });
            }
        }
    }
    </script>
</body>
</html>
```

---

## 2. Dashboard with Charts

A dashboard showing statistics with Chart.js.

### app.py
```python
# /// script
# dependencies = ["fastapi", "uvicorn"]
# ///

import sqlite3
import json
import random
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

DB_PATH = Path(__file__).parent / "data.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL
        );
    """)
    # Seed sample data if empty
    if conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 0:
        products = ['Laptop', 'Phone', 'Tablet', 'Watch', 'Headphones']
        for i in range(30):
            date = (datetime.now() - timedelta(days=29-i)).strftime('%Y-%m-%d')
            for product in products:
                amount = random.randint(100, 1000) * random.randint(1, 5)
                conn.execute("INSERT INTO sales (product, amount, date) VALUES (?, ?, ?)",
                           (product, amount, date))
        conn.commit()
    conn.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/api/stats")
async def get_stats():
    conn = get_db()

    # Total sales
    total = conn.execute("SELECT SUM(amount) as total FROM sales").fetchone()["total"] or 0

    # Sales by product
    by_product = conn.execute("""
        SELECT product, SUM(amount) as total
        FROM sales GROUP BY product ORDER BY total DESC
    """).fetchall()

    # Daily sales (last 7 days)
    daily = conn.execute("""
        SELECT date, SUM(amount) as total
        FROM sales
        WHERE date >= date('now', '-7 days')
        GROUP BY date ORDER BY date
    """).fetchall()

    conn.close()

    return {
        "total": total,
        "by_product": [dict(r) for r in by_product],
        "daily": [dict(r) for r in daily]
    }

@app.get("/")
async def index():
    return HTMLResponse(Path("index.html").read_text())

if __name__ == "__main__":
    import uvicorn
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
```

### index.html
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
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js"></script>
</head>
<body class="min-h-screen bg-base-200 p-8">
    <div x-data="dashboard()" x-init="init()" class="container mx-auto max-w-6xl">
        <h1 class="text-3xl font-bold mb-8">Sales Dashboard</h1>

        <!-- Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div class="stat bg-base-100 rounded-box shadow">
                <div class="stat-title">Total Revenue</div>
                <div class="stat-value text-primary" x-text="'$' + stats.total?.toLocaleString()"></div>
            </div>
            <div class="stat bg-base-100 rounded-box shadow">
                <div class="stat-title">Products</div>
                <div class="stat-value" x-text="stats.by_product?.length || 0"></div>
            </div>
            <div class="stat bg-base-100 rounded-box shadow">
                <div class="stat-title">Avg Daily</div>
                <div class="stat-value text-secondary" x-text="'$' + avgDaily.toLocaleString()"></div>
            </div>
        </div>

        <!-- Charts -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div class="card bg-base-100 shadow">
                <div class="card-body">
                    <h2 class="card-title">Sales by Product</h2>
                    <canvas id="pieChart"></canvas>
                </div>
            </div>
            <div class="card bg-base-100 shadow">
                <div class="card-body">
                    <h2 class="card-title">Daily Sales (Last 7 Days)</h2>
                    <canvas id="lineChart"></canvas>
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
                            <template x-for="item in stats.by_product" :key="item.product">
                                <tr>
                                    <td x-text="item.product"></td>
                                    <td x-text="'$' + item.total.toLocaleString()"></td>
                                    <td>
                                        <progress class="progress progress-primary w-20"
                                                  :value="item.total" :max="stats.total"></progress>
                                    </td>
                                </tr>
                            </template>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
    function dashboard() {
        return {
            stats: {},
            pieChart: null,
            lineChart: null,

            get avgDaily() {
                if (!this.stats.daily?.length) return 0;
                const sum = this.stats.daily.reduce((a, d) => a + d.total, 0);
                return Math.round(sum / this.stats.daily.length);
            },

            async init() {
                const res = await fetch('/api/stats');
                this.stats = await res.json();
                this.$nextTick(() => this.renderCharts());
            },

            renderCharts() {
                // Pie Chart
                const pieCtx = document.getElementById('pieChart');
                this.pieChart = new Chart(pieCtx, {
                    type: 'doughnut',
                    data: {
                        labels: this.stats.by_product.map(p => p.product),
                        datasets: [{
                            data: this.stats.by_product.map(p => p.total),
                            backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']
                        }]
                    }
                });

                // Line Chart
                const lineCtx = document.getElementById('lineChart');
                this.lineChart = new Chart(lineCtx, {
                    type: 'line',
                    data: {
                        labels: this.stats.daily.map(d => d.date),
                        datasets: [{
                            label: 'Sales',
                            data: this.stats.daily.map(d => d.total),
                            borderColor: '#36A2EB',
                            tension: 0.1,
                            fill: true,
                            backgroundColor: 'rgba(54, 162, 235, 0.1)'
                        }]
                    },
                    options: {
                        scales: {
                            y: { beginAtZero: true }
                        }
                    }
                });
            }
        }
    }
    </script>
</body>
</html>
```

---

## 3. Real-time Chat

A chat application with real-time message updates.

### app.py
```python
# /// script
# dependencies = ["fastapi", "uvicorn"]
# ///

import sqlite3
import json
import asyncio
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from contextlib import asynccontextmanager

DB_PATH = Path(__file__).parent / "data.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            color TEXT DEFAULT '#3B82F6'
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()

subscribers: list[asyncio.Queue] = []

async def broadcast(event: str, data: dict):
    message = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    for queue in subscribers:
        await queue.put(message)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/api/join")
async def join(request: Request):
    data = await request.json()
    username = data.get("username")
    if not username:
        raise HTTPException(400, "Username required")

    colors = ['#EF4444', '#F59E0B', '#10B981', '#3B82F6', '#8B5CF6', '#EC4899']
    import random
    color = random.choice(colors)

    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, color) VALUES (?, ?)", (username, color))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # User exists, that's ok

    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()

    await broadcast("user_joined", {"username": username})
    return dict(user)

@app.get("/api/messages")
async def list_messages(limit: int = 50):
    conn = get_db()
    messages = conn.execute("""
        SELECT m.*, u.username, u.color
        FROM messages m
        JOIN users u ON m.user_id = u.id
        ORDER BY m.created_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return list(reversed([dict(m) for m in messages]))

@app.post("/api/messages")
async def create_message(request: Request):
    data = await request.json()
    conn = get_db()
    cursor = conn.execute("INSERT INTO messages (user_id, content) VALUES (?, ?)",
                         (data["user_id"], data["content"]))
    conn.commit()
    message = conn.execute("""
        SELECT m.*, u.username, u.color
        FROM messages m
        JOIN users u ON m.user_id = u.id
        WHERE m.id = ?
    """, (cursor.lastrowid,)).fetchone()
    conn.close()

    await broadcast("new_message", dict(message))
    return dict(message)

@app.get("/api/events")
async def events():
    queue = asyncio.Queue()
    subscribers.append(queue)
    async def stream():
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30)
                    yield message
                except asyncio.TimeoutError:
                    yield "event: ping\ndata: {}\n\n"
        finally:
            subscribers.remove(queue)
    return StreamingResponse(stream(), media_type="text/event-stream")

@app.get("/")
async def index():
    return HTMLResponse(Path("index.html").read_text())

if __name__ == "__main__":
    import uvicorn
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
```

### index.html
```html
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chat Room</title>
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js"></script>
    <style>
        .messages-container { height: calc(100vh - 200px); }
    </style>
</head>
<body class="min-h-screen bg-base-300">
    <div x-data="chatApp()" x-init="init()" class="container mx-auto p-4 max-w-2xl">

        <!-- Join -->
        <template x-if="!user">
            <div class="card bg-base-100 shadow-xl mt-20">
                <div class="card-body">
                    <h2 class="card-title justify-center">Join Chat</h2>
                    <form @submit.prevent="join">
                        <input type="text" x-model="username" placeholder="Your name"
                               class="input input-bordered w-full mb-4" required>
                        <button type="submit" class="btn btn-primary w-full">Join</button>
                    </form>
                </div>
            </div>
        </template>

        <!-- Chat -->
        <template x-if="user">
            <div class="flex flex-col h-screen py-4">
                <div class="navbar bg-base-100 rounded-box shadow mb-4">
                    <div class="flex-1">
                        <span class="text-xl font-bold">Chat Room</span>
                    </div>
                    <div class="flex-none">
                        <span class="badge" :style="'background-color: ' + user.color" x-text="user.username"></span>
                    </div>
                </div>

                <!-- Messages -->
                <div class="messages-container overflow-y-auto bg-base-100 rounded-box p-4 mb-4" x-ref="messagesContainer">
                    <template x-for="msg in messages" :key="msg.id">
                        <div class="chat" :class="msg.user_id === user.id ? 'chat-end' : 'chat-start'">
                            <div class="chat-header">
                                <span :style="'color: ' + msg.color" x-text="msg.username"></span>
                                <time class="text-xs opacity-50 ml-1" x-text="formatTime(msg.created_at)"></time>
                            </div>
                            <div class="chat-bubble" :style="msg.user_id === user.id ? 'background-color: ' + msg.color : ''"
                                 x-text="msg.content"></div>
                        </div>
                    </template>
                </div>

                <!-- Input -->
                <form @submit.prevent="sendMessage" class="flex gap-2">
                    <input type="text" x-model="newMessage" placeholder="Type a message..."
                           class="input input-bordered flex-1" required>
                    <button type="submit" class="btn btn-primary">Send</button>
                </form>
            </div>
        </template>
    </div>

    <script>
    function chatApp() {
        return {
            user: null,
            username: '',
            messages: [],
            newMessage: '',

            async init() {
                const saved = localStorage.getItem('chatUser');
                if (saved) {
                    this.user = JSON.parse(saved);
                    await this.loadMessages();
                    this.connectSSE();
                }
            },

            async join() {
                const res = await fetch('/api/join', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: this.username})
                });
                this.user = await res.json();
                localStorage.setItem('chatUser', JSON.stringify(this.user));
                await this.loadMessages();
                this.connectSSE();
            },

            async loadMessages() {
                const res = await fetch('/api/messages');
                this.messages = await res.json();
                this.$nextTick(() => this.scrollToBottom());
            },

            async sendMessage() {
                if (!this.newMessage.trim()) return;
                await fetch('/api/messages', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({user_id: this.user.id, content: this.newMessage})
                });
                this.newMessage = '';
            },

            connectSSE() {
                const es = new EventSource('/api/events');
                es.addEventListener('new_message', (e) => {
                    this.messages.push(JSON.parse(e.data));
                    this.$nextTick(() => this.scrollToBottom());
                });
            },

            scrollToBottom() {
                const container = this.$refs.messagesContainer;
                if (container) container.scrollTop = container.scrollHeight;
            },

            formatTime(ts) {
                return new Date(ts).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
            }
        }
    }
    </script>
</body>
</html>
```

---

## 4. E-commerce Product Page

A product listing page with shopping cart.

### app.py
```python
# /// script
# dependencies = ["fastapi", "uvicorn"]
# ///

import sqlite3
import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

DB_PATH = Path(__file__).parent / "data.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            image TEXT,
            category TEXT
        );
    """)
    # Seed sample data
    if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        products = [
            ("Wireless Headphones", "Premium noise-canceling headphones", 199.99, "https://picsum.photos/seed/headphones/300/200", "Electronics"),
            ("Smart Watch", "Fitness tracking with heart rate monitor", 299.99, "https://picsum.photos/seed/watch/300/200", "Electronics"),
            ("Laptop Stand", "Ergonomic aluminum laptop stand", 49.99, "https://picsum.photos/seed/stand/300/200", "Accessories"),
            ("Mechanical Keyboard", "RGB backlit mechanical keyboard", 129.99, "https://picsum.photos/seed/keyboard/300/200", "Electronics"),
            ("USB-C Hub", "7-in-1 USB-C hub with HDMI", 59.99, "https://picsum.photos/seed/hub/300/200", "Accessories"),
            ("Webcam HD", "1080p webcam with microphone", 79.99, "https://picsum.photos/seed/webcam/300/200", "Electronics"),
        ]
        for p in products:
            conn.execute("INSERT INTO products (name, description, price, image, category) VALUES (?, ?, ?, ?, ?)", p)
        conn.commit()
    conn.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/api/products")
async def list_products(category: str = None):
    conn = get_db()
    if category:
        products = conn.execute("SELECT * FROM products WHERE category = ?", (category,)).fetchall()
    else:
        products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return [dict(p) for p in products]

@app.get("/api/categories")
async def list_categories():
    conn = get_db()
    categories = conn.execute("SELECT DISTINCT category FROM products").fetchall()
    conn.close()
    return [c["category"] for c in categories]

@app.get("/")
async def index():
    return HTMLResponse(Path("index.html").read_text())

if __name__ == "__main__":
    import uvicorn
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
```

### index.html
```html
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tech Store</title>
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js"></script>
</head>
<body class="min-h-screen bg-base-200">
    <div x-data="storeApp()" x-init="init()">

        <!-- Navbar -->
        <div class="navbar bg-base-100 shadow-lg sticky top-0 z-50">
            <div class="flex-1">
                <a class="btn btn-ghost text-xl">Tech Store</a>
            </div>
            <div class="flex-none">
                <div class="dropdown dropdown-end">
                    <div tabindex="0" role="button" class="btn btn-ghost btn-circle">
                        <div class="indicator">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                            </svg>
                            <span class="badge badge-sm indicator-item badge-primary" x-text="cartCount"></span>
                        </div>
                    </div>
                    <div tabindex="0" class="mt-3 z-[1] card card-compact dropdown-content w-72 bg-base-100 shadow">
                        <div class="card-body">
                            <span class="font-bold text-lg" x-text="cartCount + ' Items'"></span>
                            <template x-for="item in cart" :key="item.id">
                                <div class="flex justify-between items-center py-2 border-b">
                                    <span x-text="item.name"></span>
                                    <div class="flex items-center gap-2">
                                        <span class="text-sm" x-text="'x' + item.qty"></span>
                                        <button @click="removeFromCart(item.id)" class="btn btn-ghost btn-xs">X</button>
                                    </div>
                                </div>
                            </template>
                            <span class="text-info font-bold" x-text="'Total: $' + cartTotal.toFixed(2)"></span>
                            <div class="card-actions">
                                <button class="btn btn-primary btn-block" :disabled="cart.length === 0">Checkout</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Content -->
        <div class="container mx-auto p-4">
            <!-- Categories -->
            <div class="flex gap-2 mb-6 flex-wrap">
                <button @click="selectedCategory = null" class="btn btn-sm"
                        :class="{'btn-primary': !selectedCategory}">All</button>
                <template x-for="cat in categories" :key="cat">
                    <button @click="selectedCategory = cat" class="btn btn-sm"
                            :class="{'btn-primary': selectedCategory === cat}" x-text="cat"></button>
                </template>
            </div>

            <!-- Products Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <template x-for="product in filteredProducts" :key="product.id">
                    <div class="card bg-base-100 shadow-xl">
                        <figure><img :src="product.image" :alt="product.name" class="h-48 w-full object-cover"></figure>
                        <div class="card-body">
                            <h2 class="card-title" x-text="product.name"></h2>
                            <p class="text-sm opacity-70" x-text="product.description"></p>
                            <div class="flex justify-between items-center mt-4">
                                <span class="text-2xl font-bold text-primary" x-text="'$' + product.price"></span>
                                <button @click="addToCart(product)" class="btn btn-primary">Add to Cart</button>
                            </div>
                        </div>
                    </div>
                </template>
            </div>
        </div>

        <!-- Toast -->
        <div x-show="toast" x-transition class="toast toast-end">
            <div class="alert alert-success">
                <span x-text="toast"></span>
            </div>
        </div>
    </div>

    <script>
    function storeApp() {
        return {
            products: [],
            categories: [],
            selectedCategory: null,
            cart: JSON.parse(localStorage.getItem('cart')) || [],
            toast: '',

            get filteredProducts() {
                if (!this.selectedCategory) return this.products;
                return this.products.filter(p => p.category === this.selectedCategory);
            },

            get cartCount() {
                return this.cart.reduce((sum, item) => sum + item.qty, 0);
            },

            get cartTotal() {
                return this.cart.reduce((sum, item) => sum + item.price * item.qty, 0);
            },

            async init() {
                const [productsRes, categoriesRes] = await Promise.all([
                    fetch('/api/products'),
                    fetch('/api/categories')
                ]);
                this.products = await productsRes.json();
                this.categories = await categoriesRes.json();
            },

            addToCart(product) {
                const existing = this.cart.find(i => i.id === product.id);
                if (existing) {
                    existing.qty++;
                } else {
                    this.cart.push({...product, qty: 1});
                }
                this.saveCart();
                this.showToast(`${product.name} added to cart!`);
            },

            removeFromCart(id) {
                this.cart = this.cart.filter(i => i.id !== id);
                this.saveCart();
            },

            saveCart() {
                localStorage.setItem('cart', JSON.stringify(this.cart));
            },

            showToast(message) {
                this.toast = message;
                setTimeout(() => this.toast = '', 2000);
            }
        }
    }
    </script>
</body>
</html>
```
