# FastAPI + SQLite Backend

This document covers the backend stack for web applications: FastAPI for the API layer and SQLite for the database.

## Architecture

```
/workspace/my-app/
├── app.py          # FastAPI backend (serves API + static files)
├── index.html      # Frontend (served by FastAPI)
└── data.db         # SQLite database (auto-created)
```

- **Single process**: FastAPI serves both API endpoints and static files
- **No CORS needed**: Frontend and API on same origin
- **Real-time**: Use SSE (Server-Sent Events) for live updates
- **Persistence**: SQLite database in project directory

---

## Complete Backend Boilerplate

```python
# /// script
# dependencies = ["fastapi", "uvicorn"]
# ///

import sqlite3
import json
import asyncio
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from contextlib import asynccontextmanager

# Database path - in the same directory as the script
DB_PATH = Path(__file__).parent / "data.db"


# --- Database ---

def get_db():
    """Get a database connection with Row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database schema. Called once at startup."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            done BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()


# --- SSE (Server-Sent Events) for Real-time ---

subscribers: list[asyncio.Queue] = []


async def broadcast(event: str, data: dict):
    """Send an event to all connected SSE clients."""
    message = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    for queue in subscribers:
        await queue.put(message)


# --- App Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


# --- Authentication ---

@app.post("/api/register")
async def register(request: Request):
    """Register a new user."""
    data = await request.json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        raise HTTPException(400, "Username and password required")

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password)  # In production: hash the password!
        )
        conn.commit()
        user = conn.execute(
            "SELECT id, username FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        return dict(user)
    except sqlite3.IntegrityError:
        raise HTTPException(400, "Username already taken")
    finally:
        conn.close()


@app.post("/api/login")
async def login(request: Request):
    """Login and return user data."""
    data = await request.json()
    username = data.get("username")
    password = data.get("password")

    conn = get_db()
    user = conn.execute(
        "SELECT id, username FROM users WHERE username = ? AND password = ?",
        (username, password)
    ).fetchone()
    conn.close()

    if not user:
        raise HTTPException(401, "Invalid credentials")

    return dict(user)


# --- CRUD Operations ---

@app.get("/api/items")
async def list_items(user_id: int = None):
    """Get all items, optionally filtered by user."""
    conn = get_db()
    if user_id:
        items = conn.execute(
            "SELECT * FROM items WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
    else:
        items = conn.execute(
            "SELECT * FROM items ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return [dict(item) for item in items]


@app.post("/api/items")
async def create_item(request: Request):
    """Create a new item."""
    data = await request.json()
    user_id = data.get("user_id")
    name = data.get("name")

    if not user_id or not name:
        raise HTTPException(400, "user_id and name required")

    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO items (user_id, name) VALUES (?, ?)",
        (user_id, name)
    )
    conn.commit()

    item = conn.execute(
        "SELECT * FROM items WHERE id = ?",
        (cursor.lastrowid,)
    ).fetchone()
    conn.close()

    item_dict = dict(item)

    # Broadcast to SSE subscribers
    await broadcast("item_created", item_dict)

    return item_dict


@app.put("/api/items/{item_id}")
async def update_item(item_id: int, request: Request):
    """Update an item."""
    data = await request.json()

    conn = get_db()

    # Build SET clause dynamically
    updates = []
    values = []
    for key in ["name", "done"]:
        if key in data:
            updates.append(f"{key} = ?")
            values.append(data[key])

    if not updates:
        raise HTTPException(400, "No fields to update")

    values.append(item_id)
    conn.execute(
        f"UPDATE items SET {', '.join(updates)} WHERE id = ?",
        values
    )
    conn.commit()

    item = conn.execute(
        "SELECT * FROM items WHERE id = ?",
        (item_id,)
    ).fetchone()
    conn.close()

    if not item:
        raise HTTPException(404, "Item not found")

    item_dict = dict(item)
    await broadcast("item_updated", item_dict)

    return item_dict


@app.delete("/api/items/{item_id}")
async def delete_item(item_id: int):
    """Delete an item."""
    conn = get_db()

    item = conn.execute(
        "SELECT * FROM items WHERE id = ?",
        (item_id,)
    ).fetchone()

    if not item:
        conn.close()
        raise HTTPException(404, "Item not found")

    conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    await broadcast("item_deleted", {"id": item_id})

    return {"ok": True}


# --- SSE Endpoint ---

@app.get("/api/events")
async def events():
    """SSE endpoint for real-time updates."""
    queue = asyncio.Queue()
    subscribers.append(queue)

    async def stream():
        try:
            # Send initial connection event
            yield "event: connected\ndata: {}\n\n"

            while True:
                try:
                    # Wait for message with timeout (for keep-alive)
                    message = await asyncio.wait_for(queue.get(), timeout=30)
                    yield message
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    yield "event: ping\ndata: {}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            subscribers.remove(queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


# --- Serve Frontend ---

@app.get("/")
async def index():
    """Serve the frontend HTML."""
    html_path = Path(__file__).parent / "index.html"
    return HTMLResponse(html_path.read_text())


# --- Run ---

if __name__ == "__main__":
    import uvicorn
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
```

---

## Database Patterns

### Schema Definition

Define tables in `init_db()`:

```python
def init_db():
    conn = get_db()
    conn.executescript("""
        -- Users table
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- Posts table with foreign key
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- Tags (many-to-many example)
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS post_tags (
            post_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (post_id, tag_id),
            FOREIGN KEY (post_id) REFERENCES posts(id),
            FOREIGN KEY (tag_id) REFERENCES tags(id)
        );
    """)
    conn.commit()
    conn.close()
```

### Common SQLite Types

| Python | SQLite | Notes |
|--------|--------|-------|
| `str` | `TEXT` | Default string type |
| `int` | `INTEGER` | Whole numbers |
| `float` | `REAL` | Floating point |
| `bool` | `INTEGER` | 0 or 1 |
| `datetime` | `TEXT` | ISO format string |
| `dict/list` | `TEXT` | JSON string |

### Querying Examples

```python
# Get single record
user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
if user:
    return dict(user)

# Get multiple records
posts = conn.execute(
    "SELECT * FROM posts WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
    (user_id, 10)
).fetchall()
return [dict(p) for p in posts]

# Count records
count = conn.execute("SELECT COUNT(*) FROM posts WHERE user_id = ?", (user_id,)).fetchone()[0]

# Join tables
results = conn.execute("""
    SELECT p.*, u.username
    FROM posts p
    JOIN users u ON p.user_id = u.id
    WHERE p.id = ?
""", (post_id,)).fetchone()
```

---

## API Patterns

### Request Validation

```python
@app.post("/api/posts")
async def create_post(request: Request):
    data = await request.json()

    # Validate required fields
    title = data.get("title")
    user_id = data.get("user_id")

    if not title:
        raise HTTPException(400, "Title is required")
    if not user_id:
        raise HTTPException(400, "user_id is required")

    # Validate length
    if len(title) > 200:
        raise HTTPException(400, "Title too long (max 200 characters)")

    # Continue with creation...
```

### Error Handling

```python
from fastapi import HTTPException

# 400 Bad Request - invalid input
raise HTTPException(400, "Invalid email format")

# 401 Unauthorized - not logged in
raise HTTPException(401, "Please log in")

# 403 Forbidden - no permission
raise HTTPException(403, "You don't have access to this resource")

# 404 Not Found
raise HTTPException(404, "Post not found")

# 409 Conflict - duplicate
raise HTTPException(409, "Username already taken")
```

### Pagination

```python
@app.get("/api/posts")
async def list_posts(page: int = 1, limit: int = 20):
    offset = (page - 1) * limit

    conn = get_db()

    # Get total count
    total = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]

    # Get page of results
    posts = conn.execute(
        "SELECT * FROM posts ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    conn.close()

    return {
        "items": [dict(p) for p in posts],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }
```

---

## Real-time with SSE

### Backend Pattern

```python
# Global subscribers list
subscribers: list[asyncio.Queue] = []

async def broadcast(event: str, data: dict):
    """Send event to all connected clients."""
    message = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    for queue in subscribers:
        await queue.put(message)

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
```

### Frontend Pattern

```javascript
connectSSE() {
    this.eventSource = new EventSource('/api/events');

    this.eventSource.addEventListener('connected', () => {
        console.log('SSE connected');
    });

    this.eventSource.addEventListener('item_created', (e) => {
        const item = JSON.parse(e.data);
        this.items.push(item);
    });

    this.eventSource.addEventListener('item_updated', (e) => {
        const item = JSON.parse(e.data);
        const idx = this.items.findIndex(i => i.id === item.id);
        if (idx !== -1) this.items[idx] = item;
    });

    this.eventSource.addEventListener('item_deleted', (e) => {
        const { id } = JSON.parse(e.data);
        this.items = this.items.filter(i => i.id !== id);
    });

    this.eventSource.onerror = () => {
        console.log('SSE disconnected, reconnecting...');
        setTimeout(() => this.connectSSE(), 3000);
    };
}
```

---

## File Uploads

### Backend

```python
from fastapi import UploadFile, File
import shutil
from pathlib import Path

UPLOADS_DIR = Path(__file__).parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    # Generate unique filename
    ext = Path(file.filename).suffix
    filename = f"{uuid.uuid4()}{ext}"
    file_path = UPLOADS_DIR / filename

    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "filename": filename,
        "url": f"/uploads/{filename}",
        "size": file_path.stat().st_size
    }

# Serve uploaded files
from fastapi.staticfiles import StaticFiles
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
```

### Frontend

```html
<input type="file" @change="uploadFile" accept="image/*">
```

```javascript
async uploadFile(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData
    });

    const data = await res.json();
    this.imageUrl = data.url;
}
```

---

## Deployment

The app is deployed using the `app-deploy` skill:

```bash
# Deploy the app
uv run app.py
```

The app will be available at `https://app-name.{username}.{domain}`.
