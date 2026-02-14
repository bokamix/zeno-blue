# Skill API - dostęp do AI z aplikacji

Twoja aplikacja może korzystać z AI przez Skill API.

## Setup

Env vars są automatycznie dostępne po deploy:
- `SKILL_API_TOKEN` - token autoryzacji
- `SKILL_API_URL` - URL API (http://localhost:8000/internal)
- `APP_ID` - identyfikator aplikacji

## SDK - skill_client.py

Dodaj do projektu:

```python
import os
import requests

SKILL_API_URL = os.getenv('SKILL_API_URL', 'http://localhost:8000/internal')
SKILL_API_TOKEN = os.getenv('SKILL_API_TOKEN', '')

def _headers():
    return {"Authorization": f"Bearer {SKILL_API_TOKEN}", "Content-Type": "application/json"}

def transcribe(audio_path: str, language: str = None) -> dict:
    """Transkrypcja audio na tekst."""
    args = {"audio_path": audio_path}
    if language:
        args["language"] = language
    resp = requests.post(
        f"{SKILL_API_URL}/skills/execute",
        json={"skill": "transcription", "script": "transcribe", "args": args},
        headers=_headers()
    )
    return resp.json()

def analyze_image(image_path: str, prompt: str) -> dict:
    """Analiza obrazu (OCR, opis, ekstrakcja danych)."""
    resp = requests.post(
        f"{SKILL_API_URL}/skills/execute",
        json={"skill": "image", "script": "analyze", "args": {"image_path": image_path, "prompt": prompt}},
        headers=_headers()
    )
    return resp.json()

def chat(messages: list, model: str = "cheap") -> str:
    """Wywołaj LLM. model: 'cheap' (szybki) lub 'default' (mocniejszy)."""
    resp = requests.post(
        f"{SKILL_API_URL}/llm/chat",
        json={"messages": messages, "model": model},
        headers=_headers()
    )
    data = resp.json()
    if data.get("status") == "error":
        raise Exception(data.get("error"))
    return data["content"]

def list_available_skills() -> list[dict]:
    """Zwraca listę dostępnych skilli z opisami."""
    resp = requests.get(f"{SKILL_API_URL}/skills/list", headers=_headers())
    return resp.json().get("skills", [])

def call_skill(skill: str, script: str, **args) -> dict:
    """Generyczna funkcja do wywołania dowolnego skilla."""
    resp = requests.post(
        f"{SKILL_API_URL}/skills/execute",
        json={"skill": skill, "script": script, "args": args},
        headers=_headers()
    )
    return resp.json()
```

## Przykłady

### Sprawdź dostępne skille

```python
from skill_client import list_available_skills

skills = list_available_skills()
for skill in skills:
    print(f"{skill['name']}: {skill['description'][:50]}...")
    print(f"  Skrypty: {', '.join(skill['scripts'])}")
```

### Transkrypcja audio

```python
from skill_client import transcribe

result = transcribe("/workspace/meeting.mp3")
if result["status"] == "success":
    print(result["result"]["text"])
else:
    print(f"Błąd: {result['error']}")
```

### Analiza obrazu

```python
from skill_client import analyze_image

result = analyze_image(
    "/workspace/invoice.png",
    "Wyciągnij: sprzedawca, data, kwota jako JSON"
)
if result["status"] == "success":
    print(result["result"]["response"])
```

### LLM - generowanie tekstu

```python
from skill_client import chat

# Proste zapytanie
summary = chat([
    {"role": "user", "content": "Podsumuj: " + long_text}
])
print(summary)

# Z system promptem
response = chat([
    {"role": "system", "content": "Jesteś pomocnym asystentem."},
    {"role": "user", "content": "Jak napisać REST API w Pythonie?"}
])
print(response)

# Mocniejszy model (droższy)
response = chat([
    {"role": "user", "content": "Skomplikowane zadanie..."}
], model="default")
```

### Generyczne wywołanie skilla

```python
from skill_client import call_skill

# Dla nowych skilli, które mogą pojawić się w systemie
result = call_skill("pdf", "generate", content="Hello", output_path="/workspace/out.pdf")
```

## API Reference

### GET /internal/skills/list

Zwraca listę dostępnych skilli.

**Response:**
```json
{
  "skills": [
    {
      "name": "transcription",
      "description": "Transcribe audio/video files to text using AI...",
      "scripts": ["transcribe"]
    },
    {
      "name": "image",
      "description": "Analyze images using Vision API...",
      "scripts": ["analyze", "info", "preprocess"]
    }
  ]
}
```

### POST /internal/skills/execute

Wykonuje skrypt skilla.

**Request:**
```json
{
  "skill": "transcription",
  "script": "transcribe",
  "args": {"audio_path": "/workspace/audio.mp3"}
}
```

**Response (sukces):**
```json
{
  "status": "success",
  "result": {"text": "Transkrypcja...", ...}
}
```

**Response (błąd):**
```json
{
  "status": "error",
  "error": "Insufficient balance"
}
```

### POST /internal/llm/chat

Wywołuje LLM.

**Request:**
```json
{
  "messages": [
    {"role": "system", "content": "Jesteś asystentem."},
    {"role": "user", "content": "Cześć!"}
  ],
  "model": "cheap"
}
```

**Response:**
```json
{
  "status": "success",
  "content": "Cześć! Jak mogę pomóc?",
  "usage": {"prompt_tokens": 20, "completion_tokens": 10},
  "cost_usd": 0.0001
}
```

## Koszty

Wszystkie wywołania obciążają Twój balance:

| Operacja | Przybliżony koszt |
|----------|-------------------|
| Transkrypcja | ~$0.006/min audio |
| Analiza obrazu | ~$0.003/obraz |
| LLM cheap | ~$0.0001/zapytanie |
| LLM default | ~$0.003/zapytanie |

## Błędy

Typowe błędy:

```json
{"status": "error", "error": "Insufficient balance"}
{"status": "error", "error": "Skill 'xxx' not allowed"}
{"status": "error", "error": "Script 'xxx' not found"}
{"status": "error", "error": "Skill execution timeout"}
```

## Uwagi

- Skille `app-deploy` i `web-app-builder` są zablokowane dla aplikacji (bezpieczeństwo)
- Timeout wykonania skilla: 120 sekund
- Nowe skille są automatycznie wykrywane - użyj `list_available_skills()` żeby sprawdzić aktualne
