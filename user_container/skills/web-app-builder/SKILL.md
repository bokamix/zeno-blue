---
name: web-app-builder
description: "Build full-stack web applications with FastAPI (Python backend), SQLite (database), Alpine.js (frontend), Tailwind CSS + DaisyUI (styling). Use when user wants to create a web app, build an application, make a dashboard, create a tool, or develop any interactive web interface with database."
---

# Web App Builder

Build complete web applications with a simple, no-build-step stack:
- **Backend**: FastAPI (Python) - REST API + serves static files
- **Database**: SQLite - one file per project, zero configuration
- **Frontend**: Alpine.js - reactive UI directly in HTML
- **Styling**: Tailwind CSS + DaisyUI - beautiful UI from CDN

## Important: Editing Existing Apps

**When user asks to fix, improve, or change an existing app - MODIFY THE EXISTING FILES, do NOT create a new app!**

1. First, check if app already exists: `list_dir("/workspace")`
2. If app exists, read and edit existing files (`read_file`, `write_file`)
3. Only create new app if user explicitly asks for a NEW app

**Examples:**
- "Fix the button" -> Edit existing `index.html`
- "Add dark mode" -> Modify existing app files
- "The form doesn't work" -> Debug and fix existing code
- "Create a NEW todo app" -> Create new directory and files

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
/workspace/my-app/
├── app.py          # Backend: FastAPI + SQLite
├── index.html      # Frontend: Alpine.js + Tailwind
└── data.db         # Database (auto-created on first run)
```

### Minimal Example: Todo App

**app.py**
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
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

# SSE for real-time
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

@app.get("/api/todos")
async def list_todos():
    conn = get_db()
    todos = conn.execute("SELECT * FROM todos ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(t) for t in todos]

@app.post("/api/todos")
async def create_todo(request: Request):
    data = await request.json()
    conn = get_db()
    cursor = conn.execute("INSERT INTO todos (title) VALUES (?)", (data["title"],))
    conn.commit()
    todo = conn.execute("SELECT * FROM todos WHERE id = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    await broadcast("todo_created", dict(todo))
    return dict(todo)

@app.put("/api/todos/{todo_id}")
async def update_todo(todo_id: int, request: Request):
    data = await request.json()
    conn = get_db()
    conn.execute("UPDATE todos SET done = ? WHERE id = ?", (data["done"], todo_id))
    conn.commit()
    todo = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    conn.close()
    await broadcast("todo_updated", dict(todo))
    return dict(todo)

@app.delete("/api/todos/{todo_id}")
async def delete_todo(todo_id: int):
    conn = get_db()
    conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    conn.commit()
    conn.close()
    await broadcast("todo_deleted", {"id": todo_id})
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

**index.html**
```html
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Todo App</title>
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js"></script>
</head>
<body class="min-h-screen bg-base-200 p-8">
    <div x-data="todoApp()" x-init="init()" class="max-w-md mx-auto">
        <h1 class="text-3xl font-bold mb-6">Todo List</h1>

        <!-- Add form -->
        <form @submit.prevent="addTodo" class="flex gap-2 mb-6">
            <input type="text" x-model="newTitle" placeholder="What needs to be done?"
                   class="input input-bordered flex-1" required>
            <button type="submit" class="btn btn-primary">Add</button>
        </form>

        <!-- Todo list -->
        <div class="space-y-2">
            <template x-for="todo in todos" :key="todo.id">
                <div class="card bg-base-100 shadow">
                    <div class="card-body p-4 flex-row items-center gap-4">
                        <input type="checkbox" :checked="todo.done"
                               @change="toggleTodo(todo)"
                               class="checkbox checkbox-primary">
                        <span class="flex-1" :class="{'line-through opacity-50': todo.done}"
                              x-text="todo.title"></span>
                        <button @click="deleteTodo(todo.id)" class="btn btn-ghost btn-sm text-error">
                            Delete
                        </button>
                    </div>
                </div>
            </template>
        </div>

        <!-- Stats -->
        <div class="mt-6 text-sm opacity-70">
            <span x-text="todos.filter(t => !t.done).length"></span> remaining
        </div>
    </div>

    <script>
    function todoApp() {
        return {
            todos: [],
            newTitle: '',

            async init() {
                await this.loadTodos();
                this.connectSSE();
            },

            async loadTodos() {
                const res = await fetch('/api/todos');
                this.todos = await res.json();
            },

            async addTodo() {
                if (!this.newTitle.trim()) return;
                await fetch('/api/todos', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({title: this.newTitle})
                });
                this.newTitle = '';
            },

            async toggleTodo(todo) {
                await fetch(`/api/todos/${todo.id}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({done: !todo.done})
                });
            },

            async deleteTodo(id) {
                await fetch(`/api/todos/${id}`, {method: 'DELETE'});
            },

            connectSSE() {
                const es = new EventSource('/api/events');
                es.addEventListener('todo_created', (e) => {
                    this.todos.unshift(JSON.parse(e.data));
                });
                es.addEventListener('todo_updated', (e) => {
                    const todo = JSON.parse(e.data);
                    const idx = this.todos.findIndex(t => t.id === todo.id);
                    if (idx !== -1) this.todos[idx] = todo;
                });
                es.addEventListener('todo_deleted', (e) => {
                    const {id} = JSON.parse(e.data);
                    this.todos = this.todos.filter(t => t.id !== id);
                });
            }
        }
    }
    </script>
</body>
</html>
```

### Deploy

```bash
# Deploy the app
uv run app.py
```

---

## Architecture

### How It Works

1. **FastAPI** serves both the API and the frontend HTML
2. **SQLite** stores data in `data.db` in the project folder
3. **Alpine.js** makes the HTML reactive without a build step
4. **SSE** provides real-time updates without WebSockets

### Why This Stack?

- **No build step**: Just write HTML/JS and run Python
- **Single deployment**: One app serves everything
- **No CORS issues**: Frontend and API on same origin
- **Portable**: Copy the folder and it works
- **Simple debugging**: All code visible and editable

---

## Backend Reference

See `docs/backend.md` for complete backend documentation:
- Database patterns (schema, queries, relations)
- API patterns (validation, errors, pagination)
- SSE real-time patterns
- File upload handling

---

## Frontend Reference

### CDN Links

```html
<!-- Tailwind CSS + DaisyUI (styling) -->
<link href="https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css" rel="stylesheet">
<script src="https://cdn.tailwindcss.com"></script>

<!-- Alpine.js (reactivity) -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js"></script>
```

### Alpine.js Basics

See `docs/alpine.md` for full Alpine.js documentation.

**Core directives:**
- `x-data="{ count: 0 }"` - Component state
- `x-init="loadData()"` - Run on init
- `x-model="title"` - Two-way binding
- `x-text="message"` - Text content
- `@click="doSomething()"` - Event handler
- `x-for="item in items"` - Loop
- `x-if="condition"` - Conditional
- `x-show="visible"` - Show/hide

### Tailwind + DaisyUI Basics

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

## Common Patterns

### Authentication

**Backend (app.py)**
```python
@app.post("/api/register")
async def register(request: Request):
    data = await request.json()
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (data["username"], data["password"])
        )
        conn.commit()
        user = conn.execute(
            "SELECT id, username FROM users WHERE username = ?",
            (data["username"],)
        ).fetchone()
        return dict(user)
    except sqlite3.IntegrityError:
        raise HTTPException(400, "Username taken")
    finally:
        conn.close()

@app.post("/api/login")
async def login(request: Request):
    data = await request.json()
    conn = get_db()
    user = conn.execute(
        "SELECT id, username FROM users WHERE username = ? AND password = ?",
        (data["username"], data["password"])
    ).fetchone()
    conn.close()
    if not user:
        raise HTTPException(401, "Invalid credentials")
    return dict(user)
```

**Frontend (index.html)**
```javascript
// In Alpine component
user: JSON.parse(localStorage.getItem('user')) || null,

async login() {
    const res = await fetch('/api/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username: this.username, password: this.password})
    });
    if (res.ok) {
        this.user = await res.json();
        localStorage.setItem('user', JSON.stringify(this.user));
    } else {
        this.error = 'Invalid credentials';
    }
},

logout() {
    this.user = null;
    localStorage.removeItem('user');
}
```

### Login Form Template

```html
<template x-if="!user">
    <div class="max-w-sm mx-auto mt-20">
        <div class="card bg-base-100 shadow-xl">
            <div class="card-body">
                <h2 class="card-title">Login</h2>

                <div class="tabs tabs-boxed mb-4">
                    <a class="tab" :class="{'tab-active': mode === 'login'}" @click="mode = 'login'">Login</a>
                    <a class="tab" :class="{'tab-active': mode === 'register'}" @click="mode = 'register'">Register</a>
                </div>

                <form @submit.prevent="mode === 'login' ? login() : register()">
                    <div class="form-control">
                        <input type="text" x-model="username" placeholder="Username"
                               class="input input-bordered" required>
                    </div>
                    <div class="form-control mt-2">
                        <input type="password" x-model="password" placeholder="Password"
                               class="input input-bordered" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-full mt-4"
                            x-text="mode === 'login' ? 'Login' : 'Register'"></button>
                </form>

                <p x-show="error" class="text-error mt-2" x-text="error"></p>
            </div>
        </div>
    </div>
</template>
```

### Data Table

```html
<div class="overflow-x-auto">
    <table class="table">
        <thead>
            <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Status</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            <template x-for="user in users" :key="user.id">
                <tr>
                    <td x-text="user.name"></td>
                    <td x-text="user.email"></td>
                    <td>
                        <span class="badge" :class="user.active ? 'badge-success' : 'badge-ghost'"
                              x-text="user.active ? 'Active' : 'Inactive'"></span>
                    </td>
                    <td>
                        <button @click="editUser(user)" class="btn btn-ghost btn-xs">Edit</button>
                        <button @click="deleteUser(user.id)" class="btn btn-ghost btn-xs text-error">Delete</button>
                    </td>
                </tr>
            </template>
        </tbody>
    </table>
</div>
```

### Modal Dialog

```html
<!-- Trigger -->
<button @click="showModal = true" class="btn btn-primary">Open Modal</button>

<!-- Modal -->
<div x-show="showModal" class="modal modal-open">
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
```

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

## Deployment

### ⚠️ NEVER Run Apps Directly!

**DO NOT** run your app like this:
```bash
uv run app.py 8001  # WRONG - app will not be accessible!
```

Apps must be deployed through the `app-deploy` skill to get a public URL.

**Correct workflow:**
1. Write your `app.py` and `index.html`
2. Deploy using `register_app.py` (see below)
3. Get the public URL from the deployment output

### CRITICAL: Port Handling

Your `app.py` **MUST** read the port from command line argument. The deployment system assigns a dynamic port.

The boilerplate already handles this correctly:
```python
if __name__ == "__main__":
    import uvicorn
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
```

**WRONG** (will NOT work):
```python
uvicorn.run(app, host="0.0.0.0", port=8000)  # Hardcoded - BREAKS!
```

### Deploy Command

After creating `app.py` and `index.html`, deploy using:

```bash
uv run /app/user_container/skills/app-deploy/scripts/register_app.py \
  --name "my-app" \
  --cwd "/workspace/my-app" \
  --cmd "uv run app.py {port}"
```

**Parameters:**
- `--name`: App name (used in URL, lowercase, no spaces)
- `--cwd`: Directory with your `app.py` and `index.html`
- `--cmd`: Command to run. **Always use `{port}` placeholder!**

### After Deployment

The script outputs the public URL:
```
https://my-app.{username}.{domain}
```

The app runs in background and auto-restarts if it crashes.

---

## Troubleshooting

### Database Issues

**"Database is locked"**
- Make sure to close connections: `conn.close()`
- Use context managers when possible

**Schema changes**
- Delete `data.db` to recreate schema
- Or add migration logic in `init_db()`

### API Issues

**CORS errors**
- Should not happen (same origin)
- Check if you're accessing from the correct URL

**500 errors**
- Check uvicorn console output
- Add try/except with logging

### SSE Issues

**Not receiving events**
- Check EventSource is connected
- Verify broadcast is being called
- Check browser console for errors

---

## Skill API - AI w aplikacjach

Aplikacje mogą korzystać z AI (transkrypcja, analiza obrazów, LLM) przez wbudowane API.

**Dokumentacja:** Zobacz `docs/skill-api.md`

**Dynamiczne wykrywanie skilli:**
- Użyj `list_available_skills()` żeby sprawdzić co jest dostępne
- Nowe skille są automatycznie wykrywane - nie trzeba aktualizować kodu

**Kiedy używać:**
- Transkrypcja nagrań audio
- Analiza/OCR obrazów
- Generowanie tekstu przez LLM
- Podsumowania, tłumaczenia, ekstrakcja danych

**Przykład:**
```python
from skill_client import chat, transcribe, list_available_skills

# Sprawdź dostępne skille
skills = list_available_skills()
print([s['name'] for s in skills])

# Transkrypcja + podsumowanie
transcript = transcribe("/workspace/meeting.mp3")
summary = chat([{"role": "user", "content": f"Podsumuj: {transcript['result']['text']}"}])
```
