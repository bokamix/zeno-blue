# ZENO - Mapa Projektu

Autonomiczny agent AI, natywna aplikacja desktopowa.
Architektura single-process: FastAPI + asyncio, SQLite, bez Redis/Docker.

---

## Pliki w katalogu głównym

### Punkt wejścia i uruchomienie

| Plik | Opis |
|------|------|
| `zeno.py` | Główny punkt wejścia aplikacji. Zarządza venv, instalacją zależności, budowaniem frontendu i uruchamia serwer uvicorn. Obsługuje tryb bundled (PyInstaller) i source. |
| `start.sh` | Skrypt startowy deweloperski. Tworzy `~/.zeno/venv`, instaluje zależności, buduje frontend i uruchamia `zeno.py`. |
| `install.sh` | Oficjalny instalator. Pobiera ZENO z GitHub, instaluje uv (menedżer Pythona), konfiguruje `~/.zeno`, tworzy skrypt launchera. |
| `entrypoint.sh` | Entrypoint kontenera Docker. |

### Build i pakowanie

| Plik | Opis |
|------|------|
| `build.sh` | Buduje samodzielną aplikację `ZENO.app` na macOS przez PyInstaller. |
| `zeno.spec` | Specyfikacja PyInstaller - hidden imports, pliki danych, metadane aplikacji macOS. |
| `Makefile` | Komendy deweloperskie: `make up/down` (Docker), `make local` (natywnie), `make frontend-dev/build`, `make test`. |

### Docker

| Plik | Opis |
|------|------|
| `Dockerfile` | Multi-stage build. Instaluje system deps (pandoc, LibreOffice, poppler, Node.js), Python deps przez uv, Playwright z Chromium. |
| `docker-compose.yml` | Konfiguracja Docker Compose. Port 18000:8000, volumy (workspace, data), limity zasobów (2 CPU, 4GB RAM). |
| `.dockerignore` | Pliki wykluczone z kontekstu Docker build. |

### Konfiguracja

| Plik | Opis |
|------|------|
| `requirements.txt` | Zależności Pythona (22 pakiety): anthropic, openai, fastapi, uvicorn, beautifulsoup4, pdfplumber, APScheduler, litellm, sentry-sdk itd. |
| `.env` | Konfiguracja użytkownika (gitignored). |
| `.env.example` | Szablon zmiennych środowiskowych z opisami. |
| `env.example` | Uproszczony szablon env. |
| `.gitignore` | Reguły ignorowania plików przez Git. |

### Dokumentacja

| Plik | Opis |
|------|------|
| `README.md` | Quick start, instalacja, architektura, użycie Docker. |
| `CLAUDE.md` | Instrukcje dla Claude Code - konwencje, komendy, struktura projektu. |
| `VISION.md` | Wizja produktu - misja ZENO, zasady (privacy-first, autonomia, prostota), architektura. |
| `LICENSE` | Licencja MIT. |

---

## `user_container/` - Backend Python (serce aplikacji)

### Pliki główne

| Plik | Opis |
|------|------|
| `app.py` | Główna aplikacja FastAPI. Endpointy: chat, health check, upload/download plików, zarządzanie konwersacjami, serwowanie statycznych plików frontendu, CORS, auth middleware, Sentry. |
| `config.py` | Klasa Settings (Pydantic). Ścieżki, konfiguracja LLM (OpenRouter, Groq), ustawienia agenta (max_tool_calls, max_steps, limity kontekstu), klucze API. |
| `auth.py` | Middleware autentykacji hasłowej. Sesje z tokenami JWT. |
| `security.py` | Narzędzia bezpieczeństwa (inicjalizacja pliku secrets). |
| `admin.py` | Panel administracyjny (HTTP Basic Auth). |
| `api_v1.py` | Router API v1 (dodatkowe endpointy). |
| `logger.py` | Strukturalne logowanie (agent, tools, LLM requests). |
| `pricing.py` | Kalkulacja kosztów użycia LLM. |
| `costs.json` | Dane cenowe różnych modeli. |

### `agent/` - Rdzeń agenta AI

| Plik | Opis |
|------|------|
| `agent.py` | Główna klasa Agent. Autonomiczne wykonywanie z dynamicznym ładowaniem skilli, wykonywaniem narzędzi, tagami `<thinking>`, zarządzaniem kontekstem, detekcją pętli, planowaniem i refleksją. |
| `llm_client.py` | Abstrakcja klienta LLM. Obsługuje Anthropic, OpenAI, OpenRouter, Groq. Streaming, liczenie tokenów, śledzenie kosztów. |
| `routing.py` | Agent routingowy - klasyfikuje złożoność zadań (depth 0/1/2) używając szybkich modeli (Groq). |
| `prompts.py` | Prompty systemowe, opisy narzędzi, szablony iniekcji skilli. |
| `skill_loader.py` | Dynamiczne odkrywanie skilli z katalogu `/skills/`. Parsuje pliki SKILL.md. |
| `skill_router.py` | Selekcja skilli oparta na TTL. Skille wygasają po N krokach bez użycia. |
| `delegate_executor.py` | Równoległe wykonywanie sub-agentów (model Haiku). |
| `explore_executor.py` | Dedykowany executor do eksploracji i badania kodu. |
| `planned_executor.py` | Logika planowania i refleksji (kiedy injektować, jak formatować). |
| `context_manager.py` | Kompresja kontekstu przy progu 70%. Zachowuje ostatnie wiadomości i podsumowania. |
| `conversation_summarizer.py` | Hierarchiczna pamięć z semantycznymi podsumowaniami. Aktualizacja co N wiadomości. |
| `context.py` | Thread-local storage kontekstu (job_id, conversation_id). |
| `loop_detector.py` | Wykrywanie powtarzających się wzorców, wymuszanie postępu. |
| `progress_estimator.py` | Estymacja postępu zadania na podstawie wywołań narzędzi. |
| `suggestion_generator.py` | Generowanie sugestii follow-up po odpowiedzi agenta. |

### `tools/` - Wbudowane narzędzia

| Plik | Opis |
|------|------|
| `shell.py` | Wykonywanie komend shell w katalogu workspace. |
| `files.py` | Operacje na plikach: read_file, write_file, edit_file, list_dir. |
| `search_tools.py` | search_in_files (grep), recall_from_chat (wyszukiwanie RAG). |
| `web_fetch.py` | Pobieranie i parsowanie stron WWW (beautifulsoup4). |
| `web_search.py` | Wyszukiwanie w internecie przez Serper API. |
| `ask_user.py` | Pytanie użytkownika o input/wyjaśnienie (blokuje job do odpowiedzi). |
| `delegate.py` | Delegowanie podzadania do równoległego sub-agenta. |
| `explore.py` | Eksploracja kodu (wyspecjalizowane do analizy plików). |
| `schedule.py` | Tworzenie/listowanie/aktualizacja zaplanowanych jobów (składnia CRON). |
| `registry.py` | Rejestr narzędzi (zarządza dostępnymi narzędziami). |

### `skills/` - Dynamiczne skille (11 katalogów)

Każdy skill to katalog z `SKILL.md` (opis + instrukcje) i `scripts/` (skrypty Python). Auto-ładowane przez SkillRouter.

| Skill | Opis |
|-------|------|
| `pdf/` | Operacje PDF: ekstrakcja, tworzenie, łączenie, dzielenie, wypełnianie formularzy. 8 skryptów. |
| `docx/` | Operacje DOCX: odczyt, zapis, edycja, manipulacja OOXML. 3 skrypty + moduł ooxml. |
| `xlsx/` | Operacje Excel: analiza, porównywanie, konwersja, przeliczanie. 4 skrypty. |
| `image/` | Analiza obrazów (Claude/GPT-4V vision), preprocessing. 3 skrypty. |
| `transcription/` | Transkrypcja audio/wideo (Whisper API). 1 skrypt. |
| `website_screenshot/` | Screenshoty stron WWW (Playwright). 1 skrypt. |
| `web-app-builder/` | Budowanie web appów (FastAPI + Alpine.js + Tailwind). 1 skrypt + docs. |
| `app-deploy/` | Deploy i zarządzanie web appami (start, stop, restart, logi, usuwanie). 8 skryptów. |
| `frontend-design/` | Asystent projektowania frontend. |
| `n8n/` | Generowanie workflow n8n. |
| `video/` | Przetwarzanie wideo (eksperymentalne). |

### `jobs/` - System kolejki zadań

In-process (zastępuje Redis):

| Plik | Opis |
|------|------|
| `queue.py` | Klasa JobQueue. In-memory `asyncio.Queue` + persystencja SQLite. Obsługa stanów jobów, enqueue/dequeue, eventy ask_user (`threading.Event` jako most sync/async). |
| `job.py` | Model Job (id, conversation_id, message, status, timestamps). |

### `db/` - Warstwa bazodanowa

| Plik | Opis |
|------|------|
| `db.py` | Wrapper SQLite z trybem WAL. Tabele: conversations, messages, jobs, job_activity, scheduled_jobs, apps, sessions. |

### `scheduler/` - Harmonogram zadań

APScheduler-based CRON scheduling:

| Plik | Opis |
|------|------|
| `scheduler.py` | Inicjalizacja schedulera, zarządzanie jobami (add, update, delete, trigger). |
| `models.py` | Modele Pydantic dla scheduled jobs. |
| `cron_utils.py` | Narzędzia CRON (parsowanie, walidacja, następne uruchomienie). |

### `runner/` - Wykonywanie skryptów

| Plik | Opis |
|------|------|
| `runner.py` | Wykonuje skrypty Python w sandboxie. Przechwytuje stdout/stderr, obsługuje timeouty. |

### `supervisor/` - Nadzorca aplikacji

Zarządza web appami deployowanymi przez użytkownika:

| Plik | Opis |
|------|------|
| `supervisor.py` | Cykl życia aplikacji (start, stop, restart, health checks, streaming logów). |
| `ports.py` | Alokacja portów (pula 3100-3199). |

### `observability/` - Monitoring

Opcjonalna obserwowalność przez Langfuse:

| Plik | Opis |
|------|------|
| `langfuse_client.py` | Inicjalizacja klienta Langfuse. |
| `trace_context.py` | Zarządzanie kontekstem trace (thread-local). |
| `decorators.py` | Dekoratory do śledzenia funkcji (@trace_function). |

### `usage/` - Śledzenie użycia

| Plik | Opis |
|------|------|
| `tracker.py` | Śledzenie użycia LLM (tokeny, koszt per request). |
| `skill_tracker.py` | Śledzenie użycia skilli (wywołania API per skill). |

### `internal_api/` - Wewnętrzne API

| Plik | Opis |
|------|------|
| `skills.py` | Endpointy zarządzania skillami (lista, przeładowanie). |
| `llm.py` | Endpoint proxy LLM (dla skilli wywołujących LLM). |

### `staged_skills/` - Skille eksperymentalne

| Katalog | Opis |
|---------|------|
| `browser_agent/` | Automatyzacja przeglądarki (Playwright, w rozwoju). |

### `templates/` - Szablony Jinja2

| Katalog | Opis |
|---------|------|
| `admin/` | Szablony HTML panelu administracyjnego. |

---

## `frontend/` - Frontend Vue 3 (Chat UI)

### Pliki konfiguracyjne

| Plik | Opis |
|------|------|
| `package.json` | Zależności NPM (39 pakietów): Vue 3, Vite, Tailwind CSS, TipTap editor, marked, highlight.js, vue-pdf-embed, xlsx, mammoth, lucide icons, Sentry. |
| `vite.config.js` | Konfiguracja Vite (PWA, proxy do backendu). |
| `tailwind.config.js` | Konfiguracja Tailwind CSS. |
| `postcss.config.js` | Konfiguracja PostCSS. |
| `index.html` | HTML entry point (montuje aplikację Vue). |

### `src/` - Kod źródłowy

#### Główne pliki

| Plik | Opis |
|------|------|
| `main.js` | Inicjalizacja aplikacji Vue, setup i18n, integracja Sentry. |
| `App.vue` | Komponent root. State management, API calls, WebSocket, konwersacje, upload plików. |

#### `src/components/` - Komponenty UI

**Rdzeń interfejsu:**

| Komponent | Opis |
|-----------|------|
| `ChatView.vue` | Główny interfejs czatu. Lista wiadomości, pole input, załączniki, wyświetlanie tool calls. |
| `ChatMessage.vue` | Renderowanie pojedynczej wiadomości (markdown, bloki kodu, wyniki narzędzi). |
| `VirtualMessageList.vue` | Virtual scrolling dla dużych list wiadomości (optymalizacja). |
| `Sidebar.vue` | Eksplorator plików + lista konwersacji. Drzewo plików z rozwijaniem. |
| `HeaderBar.vue` | Górny pasek nawigacji (logo, ustawienia, przełącznik języka). |
| `TabBar.vue` | Dolny pasek zakładek (tylko mobile). |
| `EmptyState.vue` | Stan pusty z sugestiami możliwości. |

**Ładowanie i aktywność:**

| Komponent | Opis |
|-----------|------|
| `LoadingIndicator.vue` | Log aktywności podczas pracy agenta (tool calls, kroki). |
| `ActivityLog.vue` | Szczegółowy log aktywności z timestampami. |
| `ActivityStream.vue` | Stream aktywności w czasie rzeczywistym (WebSocket). |

**Sugestie i input:**

| Komponent | Opis |
|-----------|------|
| `CapabilitySuggestions.vue` | Karty z możliwościami ZENO. |
| `CapabilityModal.vue` | Pełnoekranowy modal możliwości (mobile). |
| `ScrollingCapabilities.vue` | Poziomo scrollowane tagi możliwości. |
| `InputSuggestions.vue` | Sugestie w polu input (autocomplete, mentions). |
| `PostResponseSuggestions.vue` | Sugestie follow-up po odpowiedzi agenta. |
| `RelatedQuestions.vue` | Sugestie powiązanych pytań. |

**Przeglądarki plików:**

| Komponent | Opis |
|-----------|------|
| `FileViewer.vue` | Wrapper przeglądarki plików (routing do konkretnych viewerów). |
| `FileTabContent.vue` | Zawartość zakładki pliku w sidebarze. |
| `FileTreeItem.vue` | Element drzewa plików (rekurencyjny komponent). |
| `viewers/CodeViewer.vue` | Przeglądarka kodu (highlight.js). |
| `viewers/TextViewer.vue` | Przeglądarka tekstu. |
| `viewers/MarkdownViewer.vue` | Przeglądarka Markdown (marked + highlight). |
| `viewers/ImageViewer.vue` | Przeglądarka obrazów (zoom, pan). |
| `viewers/PdfViewer.vue` | Przeglądarka PDF (vue-pdf-embed). |
| `viewers/DocxViewer.vue` | Przeglądarka DOCX (mammoth.js). |
| `viewers/ExcelViewer.vue` | Przeglądarka Excel (xlsx.js, zakładki arkuszy). |
| `viewers/HtmlViewer.vue` | Przeglądarka HTML (iframe sandbox). |
| `viewers/VideoViewer.vue` | Odtwarzacz wideo. |
| `viewers/NotionEditor.vue` | Edytor rich text oparty na TipTap (obsługa markdown). |

**Modale:**

| Komponent | Opis |
|-----------|------|
| `modals/SettingsModal.vue` | Modal ustawień (motyw, język, klucze API, wybór modelu). |
| `modals/ScheduledJobsModal.vue` | Podgląd/edycja zaplanowanych zadań. |
| `modals/SchedulerDetailModal.vue` | Edycja pojedynczego zaplanowanego zadania. |
| `modals/CustomSkillsModal.vue` | Zarządzanie custom skillami. |
| `modals/IntegrationsModal.vue` | Integracje zewnętrzne. |
| `modals/AppsModal.vue` | Zarządzanie deployowanymi appami. |
| `modals/CreateItemModal.vue` | Tworzenie nowego pliku/folderu. |
| `modals/MobileNavSheet.vue` | Nawigacja mobile (bottom drawer). |
| `modals/CancelConfirmModal.vue` | Dialog potwierdzenia anulowania. |
| `modals/RestartConfirmModal.vue` | Dialog potwierdzenia restartu. |

**Inne komponenty:**

| Komponent | Opis |
|-----------|------|
| `ConversationItem.vue` | Element listy konwersacji (tytuł, timestamp, podgląd). |
| `ConversationList.vue` | Lista konwersacji z grupowaniem (Dziś, Wczoraj itd.). |
| `LoginScreen.vue` | Ekran logowania (autentykacja hasłem). |
| `SetupScreen.vue` | Ekran początkowej konfiguracji (wprowadzenie klucza API). |
| `OAuthPrompt.vue` | Prompt autoryzacji OAuth (Google, GitHub). |
| `QuestionPrompt.vue` | Prompt pytania (narzędzie ask_user). |
| `PullToRefresh.vue` | Gest pull-to-refresh (mobile). |
| `Toast.vue` | Komponent powiadomień toast. |
| `UpdateBanner.vue` | Baner dostępnej aktualizacji. |
| `InstallPrompt.vue` | Prompt instalacji PWA. |
| `ZenoIcon.vue` | Komponent ikony/logo ZENO. |

#### `src/composables/` - Composables Vue

| Plik | Opis |
|------|------|
| `useApi.js` | Wrapper klienta API (obsługa auth, błędów, WebSocket). |
| `state/useChatState.js` | Stan czatu (wiadomości, konwersacje, aktywna konwersacja). |
| `state/useJobState.js` | Stan jobów (oczekujące, aktywny, logi aktywności). |
| `state/useWorkspaceState.js` | Stan workspace (drzewo plików, bieżący plik). |
| `state/useUIState.js` | Stan UI (sidebar, modale, motyw, język). |
| `state/useSettingsState.js` | Stan ustawień (klucze API, wybór modelu, preferencje). |
| `useMarkdownRenderer.js` | Renderowanie Markdown (marked + sanityzacja + highlight). |
| `useFileDetection.js` | Detekcja typu pliku (rozszerzenie → odpowiedni viewer). |
| `useConversationGrouping.js` | Grupowanie konwersacji po dacie (Dziś, Wczoraj, Ten Tydzień itd.). |
| `useMentions.js` | Obsługa @mentions w inpucie (autocomplete plików/folderów). |
| `useSwipeGesture.js` | Detekcja gestów swipe (nawigacja mobile). |
| `useToast.js` | Helpery powiadomień toast. |
| `useUpdateStatus.js` | Sprawdzanie aktualizacji ZENO. |

#### `src/locales/` - Tłumaczenia i18n

| Plik | Opis |
|------|------|
| `en.json` | Tłumaczenia angielskie (400+ stringów). |
| `pl.json` | Tłumaczenia polskie (400+ stringów). |
| `index.js` | Setup i18n (vue-i18n). |

#### `src/styles/`

| Plik | Opis |
|------|------|
| `main.css` | Globalne style CSS (importy Tailwind, zmienne motywu, animacje). |

### `dist/` - Zbudowany frontend

Produkcyjny output builda (serwowany przez FastAPI jako pliki statyczne):

| Zawartość | Opis |
|-----------|------|
| `index.html` | Zbudowany HTML entry point. |
| `assets/` | JavaScript, CSS, fonty (hashowane nazwy dla cache busting). |
| `icons/` | Ikony PWA (192x192, 512x512, apple-touch-icon). |
| `sounds/` | Dźwięki powiadomień. |
| `manifest.json` | Manifest PWA. |
| `sw.js` | Service worker (offline support). |
| `what-you-can-do-*.json` | Sugestie możliwości (EN, PL). |

### `public/` - Zasoby statyczne

Pliki kopiowane do `dist/` podczas builda (favikona, ikony PWA, dźwięki, manifest).

---

## `workspace/` - Przestrzeń robocza użytkownika

Katalog roboczy użytkownika - agent ma pełny dostęp do odczytu/zapisu.

| Katalog | Opis |
|---------|------|
| `artifacts/` | Wygenerowane artefakty (strony HTML, obrazy, raporty). |
| `tools/` | Custom narzędzia użytkownika (np. `yt_top_finder/` z tool.py i manifest.json). |
| Różne projekty | Projekty użytkownika: `dental-clinic/`, `booking-system/`, `clipboard-viewer/` itd. |
| `logs/` | Logi użytkownika. |
| `.research/` | Notatki badawcze i dane. |

---

## `data/` - Dane aplikacji

| Zawartość | Opis |
|-----------|------|
| `runtime.db` | Główna baza SQLite (konwersacje, wiadomości, joby, scheduled jobs, appy). |
| `chroma/` | ChromaDB vector store (dla RAG/recall_from_chat). |
| `uv-cache/` | Cache pakietów uv (cache zależności Python). |
| `*.db` (stare) | Legacy bazy danych (agent.db, app.db, zeno.db - nieużywane). |

---

## `build/` i `dist/` - Artefakty builda

| Katalog | Opis |
|---------|------|
| `build/zeno/` | Pliki pośrednie PyInstaller. |
| `dist/ZENO.app/` | Bundle aplikacji macOS (samodzielna appka). |
| `dist/zeno` | Wykonywalny plik Unix (standalone). |

---

## `scripts/` - Skrypty pomocnicze

| Plik | Opis |
|------|------|
| `serve.sh` | Skrypt serwera deweloperskiego (alternatywa dla Makefile). |

---

## Kluczowe mechanizmy architektury

### Single-Process
- Brak Redis - in-memory `asyncio.Queue` + persystencja SQLite
- Brak wymagania Docker - działa natywnie przez `zeno.py` lub jako bundle `.app`
- Brak procesów workerów - joby przez `asyncio.to_thread(agent.run)` w procesie FastAPI
- SQLite z trybem WAL - obsługuje równoczesne odczyty/zapisy

### Przepływ wykonywania zadań
1. Użytkownik wysyła wiadomość → endpoint FastAPI tworzy Job
2. Job w kolejce → `JobQueue.enqueue(job_id)`
3. Background worker dequeue → `agent.run()` w wątku
4. Agent wykonuje z narzędziami → wyniki zapisane do DB
5. Frontend odpytuje lub otrzymuje update przez WebSocket

### Przepływ ask_user (most sync/async)
1. Agent wywołuje `ask_user()` (w wątku)
2. Tworzy `threading.Event`, zapisuje pytanie do DB
3. Blokuje wątek czekając na event
4. Użytkownik odpowiada przez frontend → API ustawia event
5. Wątek budzi się, kontynuuje wykonywanie

### System skilli
- **Auto-discovery** - skanuje `/skills/` w poszukiwaniu plików SKILL.md
- **TTL-based** - skille aktywowane na N kroków, potem wygasają
- **SkillRouter** - wybiera relevantne skille per turn na podstawie zadania
- **Custom skills** - użytkownik dodaje skrypty Python do katalogu skills/

### Zarządzanie kontekstem
- Kompresja przy progu 70% (140k tokenów z limitu 200k)
- Ostatnie 5 wymian zawsze pełne
- Hierarchiczne podsumowania aktualizowane co N wiadomości
- Zachowuje pary tool_results + tool_calls (bez osieroconych)

### Optymalizacja kosztów
- Groq (Llama 3.1) do natychmiastowej, darmowej klasyfikacji zadań
- Haiku do sub-agentów, podsumowań, kompresji
- Per-request śledzenie tokenów, kalkulacja kosztów, integracja Langfuse
