# EMLII v4.1

A self-learning chatbot that runs entirely on your own machine. It answers from what you have
taught it, guesses sensibly when it hasn't seen something before, learns from your feedback,
and can be extended with plugins. A local AI model is optional, never required.

It comes as one core file (`EMLII.py`), one desktop front-end (`emlii_gui.py`), a plugin
folder (`tools/`) and a build script that turns the app into a standalone executable.

---

## 1. What's in the folder

```
EMLII/
├── EMLII.py                 core: memory, matching, pipeline, commands, plugins, terminal + web UI
├── emlii_gui.py             desktop app (Tkinter) — imports EMLII.py
├── build_exe.py             builds the standalone app with PyInstaller
├── build_exe.bat            Windows one-click wrapper for build_exe.py
├── plugins_requirements.txt extra pip packages your plugins need (bundled into the .exe)
├── guides/                  code guides: GUIDE_1_EMLII_core.md, GUIDE_2_GUI.md, GUIDE_3_anime_plugin.md
├── tools/                   plugins (one .py file each) + README.md (plugin guide)
│   ├── convert.py  timer.py  notes.py  remember.py  weather.py  research.py  anime.py
│   └── _template.py         copy-and-edit starting point (files starting with _ are never loaded)
│
│   created at first run, next to the app:
├── data/
│   ├── emlii.db             the memory: answers, feedback votes, per-user facts (SQLite)
│   ├── config.json          small settings (see §9)
│   ├── history/chat.txt     plain-text log of everything typed and answered
│   ├── plugins/             per-plugin settings (<name>.json) and private data (<name>/)
│   ├── mem/, inputs.json    v3 storage — read once to migrate, then left untouched
│   ├── files/, downloads/   working folders created at startup (the desktop app's download folder is configurable)
└── models/                  optional: .gguf language models and Vosk speech models
```

`EMLII.py` is deliberately a single file, so the app is easy to copy, read and package.

---

## 2. Three ways to run it

| Mode | Command | Notes |
|---|---|---|
| Desktop app | `python emlii_gui.py` | Full UI. Also starts the web UI in the background (🌐 button). |
| Terminal | `python EMLII.py --terminal` | Plain text chat. Timers and reminders print as 🔔 lines. |
| Web UI | `python EMLII.py --web [port]` | Default port 5000. Needs `pip install flask`. |

Requirements: Python 3.9+ with tkinter (desktop app only). Everything else is optional:

```
pip install flask        # web UI
pip install pillow       # images and wallpapers in the desktop app
pip install pyttsx3      # spoken replies
pip install vosk sounddevice   # offline voice input
```

---

## 3. How EMLII answers (the pipeline)

Every message that doesn't start with `!` goes through these layers, in order. The first
layer that produces an answer wins.

```
 your message
      │
      ▼
 0. Context shortcuts   "another one" / "again" → fresh reply for the previous topic
 1. Exact match         a stored answer for this exact input (in the current context first)
 1b. Plugins            tools/ plugins whose TRIGGERS match the message
 2. Similarity search   TF-IDF match against everything you've taught it
 3. Pattern rules       keyword rules: greetings, thanks, "who are you", …
 4. Local AI (optional) Ollama model, shown with conversation history
 5. Teach               nothing worked → EMLII asks you what it should say
```

Why the order matters:

* A taught or corrected answer always beats a plugin and a guess — you are always the final say.
* Plugins run before similarity so "10 km in miles" is never mismatched with "5 km in miles".
* Pattern rules are not stored, so greetings stay varied.
* AI answers are stored **unverified** (see §4) and never become permanent without your 👍.

Messages starting with `!` are commands (§7) and bypass the pipeline.

### Result types

Everything in the pipeline returns a small dictionary; every front-end renders the same set:

| `type` | Meaning |
|---|---|
| `reply` | A trusted answer (taught, corrected, approved, a command or plugin result). May include `images`. |
| `predicted` | A guess, with `source` (`similarity`, `pattern`, `ai`), `confidence`, `hash`, `prompt`. UIs show 👍 / 👎 / ✎. |
| `needs_teaching` | EMLII has no answer; the UI asks you. May include `context` (the previous message). |
| `learned` | Confirmation that something was saved. |
| `kill` | The session should end. |

Every chat result also carries a `topic` dict (`id`, `label`, `fit`, `members`, `switched`).

---

## 4. Memory and trust

All learned answers live in `data/emlii.db` (SQLite). Each row is keyed by the md5 of the exact
input text and stores the input, the response, where it came from (`source`), 👍/👎 counts and
usage statistics.

**Sources and trust**

| Source | Trusted from the start? |
|---|---|
| `taught`, `corrected`, `migrated` (imported from v3) | Yes |
| `similarity`, `pattern`, `ai` (guesses) | No — shown as "predicted" until you approve |

* A guess becomes trusted once you give it a 👍. Only trusted answers are used as a source for
  later similarity matches, so one bad guess can never snowball.
* A 👎 on a guess blocks it immediately: it is no longer returned, and EMLII won't hand the same
  answer back for that input. Trusted answers need several 👎 votes to be blocked.
* Quality is `(👍 + prior) / (votes + prior)`; blocking happens below 0.30. Taught and corrected
  answers start with a high prior, AI guesses with a low one.
* Teaching or correcting always replaces the old answer and resets its votes.

**Per-user facts** (`facts` table) — a small key/value memory per username ("name = Sam").
Taught replies may use them: `Hi {name}!`, or `Hi {name|friend}!` with a fallback.

**Migration** — the first launch of v4 imports v3's `data/mem/` files and `inputs.json`
automatically. The old files are left in place.

---

## 5. Similarity search

Pure Python, no dependencies, fully offline.

1. Text is lowercased, split into words, and lightly stemmed ("passwords" ≈ "password").
2. Each stored input becomes a vector of words and word pairs, weighted by TF-IDF (rare words
   count more; filler words like "the" and "is" count less).
3. Unknown words in your message are corrected against words EMLII has seen (typo tolerance).
   A never-seen content word counts extra, because it usually means a different topic.
4. The score blends cosine similarity with how much of **your message** is covered, so
   "reset password" still finds "how do I reset my password".
5. Among candidates over the threshold, better-rated answers rank higher.

The threshold is `0.50` (`similarity_threshold` in `config.json`). Raise it for fewer, safer
guesses; lower it for more guesses. For one- and two-word inputs there is also a spelling-only
fallback. The index is rebuilt lazily whenever memory changes.

---

## 6. Conversation context and topics

EMLII doesn't just remember "the last message" — it tracks **topics**, so "why?" about colours is never
confused with "why?" about food, even if you talked about something else in between.

* **Every conversation topic gets its own record:** a numeric id, an *anchor* (the memory row that
  started it — stable across sessions and across different wordings), a keyword *profile* (word weights
  that fade as the topic drifts) and its *members* (your messages and EMLII's replies, each with a
  **fit score** showing how well it matches the topic).
* **Each message is matched to a topic.** A message that resembles a topic's profile (similarity ≥ 0.35)
  joins it — even an older one, which is how EMLII "switches back" (you'll see `↩ back to topic 2 · food`).
  Otherwise it starts a new topic. Up to 8 topics per user are kept, each resumable for 30 minutes.
* **Vague follow-ups** ("why?", "and then?", "what about it?") belong to the live topic. If a follow-up names
  a subject ("and the food one?") and another topic fits those words better, it goes there instead.
* **Follow-ups you teach are stored per topic answer**, so the same "why?" can have a different
  answer in every topic. Paraphrases of the earlier question land in the same topic because they reach the same answer.
* **The optional AI fallback** only receives the current topic's messages, not unrelated chat.
* **Commands:** `!topic` lists topics and members with fit scores · `!topic new` starts a new topic ·
  `!topic <n>` jumps back to topic n · `!reset` forgets everything.
* **Repeats** ("another one", "again", "one more") regenerate a reply for the topic's last subject.
* Plugins can read the live topic through `ctx["topic"]`.

Topics live in memory (per user); the answers you teach live in the database. The maths is in
`guides/GUIDE_4_maths.md` (§3).

---

## 7. Commands

| Command | What it does |
|---|---|
| `!help`, `!version`, `!date` | Info |
| `!calculate <expr>` | Evaluate a math expression |
| `!hash <text>` | MD5 / SHA1 / SHA256 / SHA512 |
| `!crack <hash>` | Dictionary + brute-force crack |
| `!encrypt <text>` / `!decrypt <text>` | ROT-13 Caesar cipher |
| `!dirserver [path]` / `!stopserver` | Start / stop a LAN file server (port 8080) |
| `!memory` | Learning statistics |
| `!good` / `!bad [better reply]` | Rate the last reply; `!bad <text>` also teaches the right one |
| `!forget <text>` | Delete what EMLII learned for that exact input |
| `!ai on\|off` | Turn the optional AI fallback on or off (saved) |
| `!topic` (or `!context`) / `!reset` | Show conversation topics (`!topic new`, `!topic <n>`) / forget them all |
| `!tools …` | Manage plugins (§8) |
| `exit`, `quit`, `leave`, `q` | End the session |

Plugin commands (`!convert`, `!timer`, …) appear in `!help` too.

---

## 8. Plugins

A plugin is one `.py` file in `tools/`. Type `!tools reload` to load it — no restart.

```python
COMMAND  = "hello"                       # required: the !command word and plugin name
HELP     = "Says hello"
VERSION  = "1.0"
SETTINGS = {"greeting": "Hello"}         # defaults, stored in data/plugins/hello.json
TRIGGERS = [r"^say hello to (?P<who>\w+)$"]   # regexes that make it answer normal chat

def run(arg, ctx): ...                   # !hello <arg>
def on_chat(text, match, ctx): ...       # chat message matched a trigger (None = decline)
def on_load(ctx): ...                    # after load/reload
def on_unload(): ...                     # before reload/disable
```

`ctx` provides: `username`, `history`, `facts`, `memory`, `settings`, `data_dir`, `notify`, `log`, `ask_ai`
(plus `PATHS` and `fs` from v4.0). Plugin replies can include `"images": [urls]` (desktop app).

`!tools` lists, reloads, enables/disables and configures plugins. Plugin replies are live data
and are never stored as learned answers; `!good`/`!bad` after one rate the plugin instead.
Each plugin loads under its own module name, and a broken plugin is reported and skipped.

Starter plugins: `convert` (units), `timer` (timers/reminders that survive restarts), `notes`,
`remember` (facts about you), `weather` (Open-Meteo, no key), plus two larger ones:

* **`research`** — `deep research on <topic>` queries Wikipedia, arXiv, OpenAlex, Crossref, PubMed,
  news (GDELT), Hacker News and Open Library in parallel, merges duplicate papers, and writes a
  cited report (overview, key points, recurring themes, top papers, news, books, numbered sources).
  Reports are saved and cached. Key points are extracted sentences, not model-written; set
  `use_ai` to add an optional local-model synthesis.
* **`anime`** — anime, manga, manhwa and manhua: info/search, top lists, season, today's airing
  schedule, latest chapters, follow-list with `!anime updates` (optional background alerts),
  character lookup, merged news from several outlets, and SFW waifu/husbando/neko images and
  reaction GIFs with `!anime download` to save them. Every feature has several providers and
  fails over automatically; `!anime check` tests them from your computer. SFW only.

Both plugins send your queries to third-party public APIs and depend on those services staying
available; they need an internet connection.

> Plugins run in-process with your user's permissions — no sandbox, no timeout. Only install
> plugins you trust. See `tools/README.md` for the full contract and limitations.

---

## 9. Configuration, folders and environment

`data/config.json` (created on demand):

| Key | Meaning |
|---|---|
| `similarity_threshold` | Match strictness, default `0.5` |
| `ai_enabled` | Optional AI fallback on/off (also `!ai on/off`) |
| `tools_disabled` | Plugins switched off with `!tools disable` |

Environment variables (the desktop app sets these from its Settings → folders):
`EMLII_DATA_DIR`, `EMLII_TOOLS_DIR`, `EMLII_MODELS_DIR`, `EMLII_DOWNLOADS_DIR`.

### Optional AI and voice models

* **AI:** drop a `.gguf` file in `models/` and EMLII registers the newest one with a running
  Ollama (`ollama serve`, `ollama` on PATH). With no file it falls back to a model you pulled
  yourself. If Ollama isn't reachable the layer is silently skipped.
* **Speech input:** put a Vosk model (a folder containing `am/` and `conf/`, or the downloaded `.zip`) in `models/` (needs `vosk`).
* **Speech output:** `pyttsx3`.

---

## 10. The desktop app

`emlii_gui.py` is a front-end over the same core — all the learning logic lives in `EMLII.py`.
It has a canvas-based chat with themes, wallpaper (solid, gradient or image), configurable
folders, a command/plugin sidebar, spoken replies, a full-screen voice orb, inline images, and
the web UI one click away.

Predicted replies show **✓ good / ✗ bad / ✎ edit**: *good* approves the answer, *bad* flags it
and offers to teach the right one, *edit* replaces it directly. Timer and reminder alerts
arrive as 🔔 messages.

---

## 11. Web UI and API

`python EMLII.py --web` serves a single-page chat UI at `http://127.0.0.1:5000` (also on your
LAN address). It has no login: anyone who can reach the port can chat, run commands and
trigger plugins. Don't expose it on untrusted networks.

| Endpoint | Purpose |
|---|---|
| `POST /api/chat` | `{message, username}` → a result dict |
| `POST /api/teach` | `{hash, response, original_text}` |
| `POST /api/correct` | `{hash, response, original_text}` |
| `POST /api/feedback` | `{hash, vote: 1\|-1, text?, prompt?, source?}` |
| `GET /api/notifications?username=` | Pending timer/plugin alerts (polled by the UI) |
| `GET /api/plugins` | Loaded plugins and the active AI model |
| `POST /api/crack` | Hash cracking |
| `GET /api/voice_caps`, `POST /api/stt`, `POST /api/tts` | Voice features |

---

## 12. Building a standalone app

PyInstaller builds for the operating system it runs on (Windows → `.exe`).

```
python build_exe.py              # single EMLII.exe
python build_exe.py --onedir     # folder build — starts faster, fewer antivirus flags
python build_exe.py --console    # keep a console window for debugging
python build_exe.py --dry-run    # print the PyInstaller command only
```

On Windows you can double-click `build_exe.bat`. The script scans `tools/*.py` for imports and
bundles them, and installs anything listed in `plugins_requirements.txt`. Optional extras
(Pillow, pyttsx3, Vosk, sounddevice) are bundled only if installed when you build.

At run time the app keeps `data/`, `tools/`, `models/` and `emlii.log` next to the executable,
so it is portable — back up `data/` to keep what EMLII has learned. Plugins are read from disk,
so you can edit them after building; a plugin needing a *new third-party package* needs a rebuild.

---

## 13. Architecture at a glance

```
            ┌────────────── front-ends ──────────────┐
            │  Terminal   Desktop (Tkinter)   Web UI │
            └───────┬──────────────┬─────────────┬───┘
                    └──────────────┼─────────────┘
                                   ▼
                       EMLII.process(text, user)
                                   │
        ┌───────────┬──────────────┼───────────────┬────────────┐
        ▼           ▼              ▼               ▼            ▼
    context      Store          Index           plugins       AI (opt.)
  (last turns)  (SQLite:      (TF-IDF,        (tools/*.py,   (Ollama)
                answers,       typo-fix,       TRIGGERS,
                votes,         feedback-       ctx services)
                facts)         weighted)
```

| Piece | Role |
|---|---|
| `Store` | SQLite wrapper: answers, votes, facts, metadata. Thread-safe. |
| `Index` | Lazily rebuilt TF-IDF search over trusted, non-blocked inputs. |
| `EMLII` class | `process()`, `learn()`, `correct()`, `feedback()`, `commands()`. |
| Plugin registry | Loads `tools/`, dispatches commands and chat triggers, builds `ctx`. |
| Notifications | In-memory queue per user, polled by all three front-ends. |

---

## 14. Limitations

* Matching is statistical word similarity, not understanding. Treat guesses as guesses — that is
  what 👍/👎 is for.
* Topics are kept in memory only (8 per user, resumable for 30 minutes); answers you teach are saved.
* Notifications are in memory: lost on restart (timers themselves are saved), and only delivered
  to an open UI using the same username.
* The web UI has no authentication; plugins have no sandbox or timeout.
* Images show in the desktop app only; JPEGs need Pillow.
* The optional AI depends on a separately running Ollama and can be wrong.

---
