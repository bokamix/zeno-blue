# Permissions — Conception

## Cel

Zbudowanie systemu, który daje użytkownikowi kontrolę nad tym, co agent może robić — bez konieczności ręcznego zatwierdzania każdej banalnej operacji.

Agent w zeno.blue może wykonywać realne akcje: pisać pliki, uruchamiać komendy shell, instalować pakiety, robić requesty sieciowe. Bez kontroli uprawnień użytkownik nie wie, co agent robi "za jego plecami". Z drugiej strony, pytanie o pozwolenie przy każdym `ls` czy `cat` byłoby nie do zniesienia.

**Rozwiązanie:** inteligentna klasyfikacja operacji + granularne reguły co wymaga pytania, a co nie.

---

## Filozofia

> Domyślnie: odczyt w workspace jest zawsze OK. Zapis wymaga zgody raz w sesji. Operacje destrukcyjne i poza workspace — zawsze pytaj.

Agent powinien działać swobodnie w granicach "bezpiecznych" operacji. Użytkownik wchodzi do akcji tylko gdy ryzyko rzeczywiście istnieje.

---

## Klasyfikacja zakresów (scopes)

Każda operacja agenta jest klasyfikowana do jednego ze zakresów:

| Scope | Opis | Domyślna reguła |
|---|---|---|
| `workspace` | Odczyt plików w workspace | zawsze OK |
| `shell_read_workspace` | Komendy read-only (ls, cat, grep...) | zawsze OK |
| `shell_write_workspace` | Zapis/modyfikacja w workspace (mkdir, cp...) | pytaj raz w sesji |
| `shell_install` | Instalacja pakietów (pip, npm, brew...) | pytaj raz w sesji |
| `shell_network` | Ruch sieciowy (curl, wget, ssh...) | pytaj raz w sesji |
| `web` | web_search, web_fetch | pytaj raz w sesji |
| `scheduling` | Tworzenie zaplanowanych zadań | pytaj raz w sesji |
| `shell_destructive` | Operacje niszczące (rm -rf, chmod, sudo, kill...) | pytaj zawsze |
| `outside_workspace` | Cokolwiek poza katalogiem workspace | pytaj zawsze |

---

## Poziomy reguł

- **`allow`** — bez pytania
- **`ask_once`** — pytaj raz w sesji, potem zapamiętaj zgodę
- **`ask_always`** — pytaj przy każdym wywołaniu
- **`deny`** — zawsze blokuj

---

## Zapamiętywanie decyzji

Użytkownik przy każdym prompt ma trzy opcje:
1. **Jednorazowo** — tylko ta konkretna operacja
2. **Na sesję** — wszystkie takie operacje do końca sesji (jak `ask_once`)
3. **Zawsze** — zapisuje regułę permanentnie do bazy

Reguły permanentne nadpisują domyślne i są ładowane przy starcie każdej sesji.

---

## Tryb headless

Gdy agent działa bez UI (np. scheduled job), system automatycznie:
- zezwala na operacje read-only w workspace
- blokuje wszystko inne (brak możliwości zapytania użytkownika)

---

## Przepływ w UI

1. Agent próbuje wykonać operację wymagającą zgody
2. Job zmienia status na `waiting_for_permission`
3. Frontend wykrywa status przez polling i wyświetla `PermissionPrompt`
4. Użytkownik klika Allow / Deny i wybiera sposób zapamiętania
5. Frontend wysyła odpowiedź do backendu, job jest wznawiany

Wizualnie: PermissionPrompt pojawia się w tym samym miejscu co QuestionPrompt i OAuthPrompt — w stopce chatu, poniżej wiadomości.

---

## Co NIE jest celem

- Nie budujemy sandboxa OS-owego (bez seccomp, bez kontenerów per-operacja)
- Nie logujemy każdej operacji do auditu
- Nie obsługujemy wieloużytkownikowych polityk

System jest przeznaczony dla jednego użytkownika zarządzającego własnym agentem.
