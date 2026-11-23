"""
EMLII desktop UI (Tkinter)  —  v6.1: canvas chat, wallpaper, themes, folders, voice orb, web mode, 👍/👎 feedback learning
=========================================================
Front-end for EMLII.py — keep both files in the same folder.

    python emlii_gui.py

The web UI starts automatically in the background (🌐 Web button).
The 🎤 button opens the full-screen voice orb.

Optional extras (the app works without them):
    pip install pyttsx3              # spoken replies
    pip install vosk sounddevice     # voice input (+ a Vosk model in models/)
"""
import os, sys, queue, threading, math, re, logging, json
from array import array
import io, base64, urllib.request
from time import perf_counter
import random
from pathlib import Path
from datetime import datetime

# EMLII.py uses relative paths (data/, tools/, models/) and creates them on
# import, so chdir to the app folder (the .exe's folder when packaged) first.
BASE = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
os.chdir(BASE)
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

# A windowed .exe has no console, so print() output (voice/model status, errors)
# goes to emlii.log next to the exe — send me that file if something misbehaves.
_log = None
for _name in ("stdout", "stderr"):
    if getattr(sys, _name) is None:
        if _log is None:
            try:
                _log = open(BASE / "emlii.log", "a", buffering=1, encoding="utf-8")
                print(f"\n--- EMLII GUI started {datetime.now():%Y-%m-%d %H:%M:%S} ---", file=_log)
            except OSError:
                _log = open(os.devnull, "w")
        setattr(sys, _name, _log)

# ── Settings (⚙ button) live in emlii_gui_settings.json next to the app. They are
# read first because the folder choices must be in place before EMLII loads. ────
SETTINGS_FILE = BASE / "emlii_gui_settings.json"
DIR_ENV = {"dir_data": "EMLII_DATA_DIR", "dir_downloads": "EMLII_DOWNLOADS_DIR",
           "dir_models": "EMLII_MODELS_DIR", "dir_tools": "EMLII_TOOLS_DIR"}


def _read_settings():
    try:
        d = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


SETTINGS = _read_settings()


def save_settings():
    try:
        tmp = SETTINGS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(SETTINGS, indent=2), encoding="utf-8")
        tmp.replace(SETTINGS_FILE)
    except OSError as e:
        print("[settings] could not save:", e)


def apply_dir_env(S):
    for key, env in DIR_ENV.items():
        v = str(S.get(key) or "").strip()
        if v:
            os.environ[env] = v
        else:
            os.environ.pop(env, None)


apply_dir_env(SETTINGS)

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox

import EMLII as core
Bot = core.EMLII

# ── Themes (dark = the web UI's purple palette) ──────────────────────────────
THEMES = {
    "dark": dict(bg="#0b0a10", surface="#151220", border="#2a2240", purple="#b84bff",
                 purple_hi="#d9a3ff", user_bg="#1c1430", user_border="#3a2a5c",
                 pred_bg="#2a0f24", pred_border="#ff4fd8", warn_bg="#2a2410",
                 warn_border="#f0c040", text="#d4cdea", muted="#8a82b0",
                 green="#00e676", cyan="#00c8b4", yellow="#f0c040", red="#e05555",
                 pink="#ff4fd8", btn_fg="#0b0a10"),
    "light": dict(bg="#faf8ff", surface="#efeaf9", border="#d8cdee", purple="#8a2be2",
                  purple_hi="#6b21a8", user_bg="#e9defa", user_border="#cbb6ee",
                  pred_bg="#fde7f7", pred_border="#d6339f", warn_bg="#fff6dc",
                  warn_border="#c58a00", text="#2b2540", muted="#7a7098",
                  green="#0a8f4e", cyan="#00796b", yellow="#9a6700", red="#c0392b",
                  pink="#d6339f", btn_fg="#ffffff"),
}
_D = THEMES["dark"]
THEME_PRESETS = {
    "Purple neon": _D,
    "Light": THEMES["light"],
    "Hacker green": {**_D, "bg": "#020a04", "surface": "#07140b", "border": "#12401f", "text": "#c9ffd6",
                     "muted": "#4f9a64", "purple": "#39ff14", "purple_hi": "#7dff9a", "user_bg": "#0b2414",
                     "user_border": "#17572a", "pred_bg": "#14250a", "pred_border": "#b6ff00",
                     "green": "#39ff14", "cyan": "#00ffa2", "pink": "#b6ff00"},
    "Cyberpunk": {**_D, "bg": "#0a0612", "surface": "#140b24", "border": "#3a1a66", "text": "#f0e6ff",
                  "muted": "#9a7fd0", "purple": "#ff2e97", "purple_hi": "#00f0ff", "user_bg": "#1c0f35",
                  "user_border": "#5a2aa0", "pred_bg": "#2a0a24", "pred_border": "#ff2e97",
                  "green": "#00ffa2", "cyan": "#00f0ff", "yellow": "#fcee0a", "pink": "#ff2e97"},
    "Ocean": {**_D, "bg": "#06111c", "surface": "#0c1c2d", "border": "#17405f", "text": "#d6ecff",
              "muted": "#7fa6c4", "purple": "#2f9bff", "purple_hi": "#8ccaff", "user_bg": "#0e2a45",
              "user_border": "#1f5a8a", "pred_bg": "#0b2f3a", "pred_border": "#2fe0c8",
              "green": "#2fe08a", "cyan": "#2fe0c8", "pink": "#2fe0c8"},
    "Rose": {**_D, "bg": "#140a10", "surface": "#201019", "border": "#4a1f36", "text": "#ffe4ef",
             "muted": "#c08aa4", "purple": "#ff6fa5", "purple_hi": "#ffb3d1", "user_bg": "#2e1422",
             "user_border": "#6b2a4d", "pred_bg": "#3a1428", "pred_border": "#ff6fa5", "pink": "#ff6fa5"},
    "Mono": {**_D, "bg": "#0e0e0e", "surface": "#181818", "border": "#333333", "text": "#e6e6e6",
             "muted": "#8a8a8a", "purple": "#d0d0d0", "purple_hi": "#ffffff", "user_bg": "#222222",
             "user_border": "#444444", "pred_bg": "#2a2a2a", "pred_border": "#ffffff", "pink": "#ffffff"},
}
_LEGACY_THEME = {"dark": "Purple neon", "light": "Light"}


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminance(h):
    r, g, b = hex_rgb(h)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def build_theme(S):
    """-> (preset name, colour dict): the chosen preset plus the user's own colour edits."""
    name = _LEGACY_THEME.get(S.get("theme"), S.get("theme"))
    if name not in THEME_PRESETS:
        name = "Purple neon"
    t = dict(THEME_PRESETS[name])
    own = (S.get("colors") or {}).get(name) or {}
    for k, v in own.items():
        if k in t and re.fullmatch(r"#[0-9a-fA-F]{6}", str(v)):
            t[k] = v
    if "btn_fg" not in own:                       # readable text on the accent colour
        t["btn_fg"] = "#08060e" if luminance(t["purple"]) > 0.45 else "#ffffff"
    return name, t


FONT, FONT_B = ("Consolas", 11), ("Consolas", 11, "bold")
FONT_S = ("Consolas", 8)
BUILTINS = ["help", "version", "date", "calculate", "hash", "crack", "encrypt",
            "decrypt", "dirserver", "stopserver", "memory", "tools"]


def rounded(canvas, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


def speakable(text):
    """Clean text for TTS: links become 'link', table/box characters are dropped."""
    t = re.sub(r"https?://\S+", "link", str(text))
    t = re.sub(r"[`*_#>|│●▲▼·•=─\[\]]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# ── Speech helpers ───────────────────────────────────────────────────────────
FEMALE_NAMES = ("zira", "hazel", "susan", "eva", "aria", "jenny", "heera", "catherine", "linda",
                "sabina", "helena", "hedda", "elsa", "samantha", "karen", "victoria", "moira",
                "tessa", "fiona", "allison", "ava", "female", "woman")
MALE_NAMES = ("david", "mark", "george", "james", "richard", "ravi", "guy", "daniel", "alex",
              "fred", "tom", "male", "man")


def voice_gender(v):
    g = str(getattr(v, "gender", "") or "").lower()
    n = str(getattr(v, "name", "") or "").lower()
    if "female" in g:
        return "female"
    if "male" in g:
        return "male"
    if any(h in n for h in FEMALE_NAMES):
        return "female"
    if any(h in n for h in MALE_NAMES):
        return "male"
    return "?"


def pick_voice_id(voices, wanted=None):
    """The saved voice if still installed, else the first English female voice, else any female."""
    if wanted and any(v.id == wanted for v in voices):
        return wanted
    fem = [v for v in voices if voice_gender(v) == "female"]
    if not fem:
        return None
    def english(v):
        blob = (str(v.name) + " " + str(getattr(v, "languages", "")) + " " + str(v.id)).lower()
        return "en" in blob and ("english" in blob or "en-" in blob or "en_" in blob or "en\\x" in blob)
    fem.sort(key=lambda v: not english(v))
    return fem[0].id


def make_engine(voice_id=None):
    """A pyttsx3 engine using the chosen voice — a female one by default."""
    import pyttsx3
    eng = pyttsx3.init()
    try:
        vid = pick_voice_id(eng.getProperty("voices") or [], voice_id)
        if vid:
            eng.setProperty("voice", vid)
        eng.setProperty("rate", 175)
    except Exception as e:
        print("[voice] could not select a voice:", e)
    return eng


def list_voices(current=None):
    """-> ([(id, name, gender)], id that is in use)"""
    import pyttsx3
    eng = pyttsx3.init()
    voices = eng.getProperty("voices") or []
    return [(v.id, v.name, voice_gender(v)) for v in voices], pick_voice_id(voices, current)


def input_devices():
    import sounddevice as sd
    out, seen = [], set()
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0 and d["name"] not in seen:
            seen.add(d["name"]); out.append((i, d["name"]))
    return out


def resample16k(s, src):
    """int16 array at `src` Hz -> 16 kHz (box filter for whole ratios, else linear)."""
    if src == 16000:
        return s
    if src % 16000 == 0:
        k = src // 16000
        return array("h", [sum(s[i:i + k]) // k for i in range(0, len(s) - k + 1, k)])
    ratio, n_out = src / 16000.0, int(len(s) * 16000 / src)
    out = array("h", bytes(2 * n_out))
    for i in range(n_out):
        pos = i * ratio; j = int(pos); f = pos - j
        a = s[j]; b = s[j + 1] if j + 1 < len(s) else a
        out[i] = int(a + (b - a) * f)
    return out


# ══ Voice orb ════════════════════════════════════════════════════════════════
# Port of the web UI's purple plasma orb: dot-mesh sphere, orbital rings with
# satellites, a radial level ring and a "thinking" comet sweep.
VBG  = "#07040d"
BGV  = (7, 4, 13)
C_DEEP, C_CORE, C_HI, C_HOT = (58, 10, 107), (184, 75, 255), (217, 163, 255), (255, 110, 235)
ORB_N, HALO_N, GLOW_N, BARS, SWEEP_N = 900, 18, 8, 96, 14
ORB_RINGS = [(1.62, 1.15, 0.55, 0.0, 1.6), (1.42, 0.35, -0.40, 1.7, -1.1), (1.82, -0.85, 0.28, 3.1, 0.8)]
VO_THRESH = 0.018        # mic RMS that counts as speech


def _fib(n):
    g, xs, ys, zs = math.pi * (3 - math.sqrt(5)), [], [], []
    for i in range(n):
        y = 1 - (i / (n - 1)) * 2
        r = math.sqrt(max(0.0, 1 - y * y))
        xs.append(math.cos(g * i) * r); ys.append(y); zs.append(math.sin(g * i) * r)
    return xs, ys, zs
PX, PY, PZ = _fib(ORB_N)
_ord = list(range(ORB_N)); random.Random(7).shuffle(_ord)       # first n dots are evenly spread
PX, PY, PZ = [PX[i] for i in _ord], [PY[i] for i in _ord], [PZ[i] for i in _ord]


def mixc(a, b, k):
    return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))

def rgb_over_bg(c, a):
    a = 0.0 if a < 0 else 1.0 if a > 1 else a
    return tuple(BGV[i] + (c[i] - BGV[i]) * a for i in range(3))

def hexc(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v))) for v in c)

def blend(c, a):
    return hexc(rgb_over_bg(c, a))


class VoiceMode:
    """Full-screen hands-free voice conversation with the animated orb."""

    def __init__(self, app):
        self.app = app
        self.open = False
        self.state = "idle"
        self.muted = False
        self.speak = True
        self.can_listen = False
        self.teach = None
        self.cap = None
        self.stream = None
        self.engine = None
        self.token = 0
        self.mic_level = 0.0
        self.job = None
        self.ov = None
        self._tts_failed = False
        self.src_rate, self.src_ch, self.mic_name = 16000, 1, ""
        self.noise, self.thresh, self._quiet, self._hinted = 0.004, VO_THRESH, 0, False
        self.level = self.target = self.pulse = self.heat = self.sweep = self.ang = self.t = 0.0
        self.spin = 1.0
        self._barcol = self._ringcol = None
        self.nd, self.cost, self.adapt, self._last, self._geom = ORB_N, 0.0, 0, None, None
        self.halo_col, self.glow_col = [None] * HALO_N, [None] * GLOW_N

    # ── open / close ─────────────────────────────────────────────────────────
    def toggle(self):
        self.close() if self.open else self.show()

    def lift(self):
        if self.open and self.ov is not None:
            self.ov.lift()

    def show(self):
        a, root = self.app, self.app.root
        self.open, self.muted, self.teach, self.cap = True, False, None, None
        self.state = "idle"
        self.level = self.target = self.pulse = self.heat = self.sweep = self.ang = self.t = 0.0
        self.spin = 1.0
        self._barcol = self._ringcol = None
        self.nd, self.cost, self.adapt, self._last, self._geom = ORB_N, 0.0, 0, None, None
        self.halo_col, self.glow_col = [None] * HALO_N, [None] * GLOW_N
        self.token += 1

        ov = self.ov = tk.Frame(root, bg=VBG)
        ov.place(x=0, y=0, relwidth=1, relheight=1)
        top = tk.Frame(ov, bg=VBG); top.pack(fill="x", padx=18, pady=(14, 0))
        tk.Label(top, text="[EMLII] VOICE", bg=VBG, fg="#d9a3ff",
                 font=("Consolas", 12, "bold")).pack(side="left")
        self.mode_lbl = tk.Label(top, text="", bg=VBG, fg="#8a82b0", font=("Consolas", 9))
        self.mode_lbl.pack(side="left", padx=10)
        self._btn(top, "✕ close", self.close).pack(side="right")

        self.cv = tk.Canvas(ov, bg=VBG, highlightthickness=0, bd=0, cursor="hand2")
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Button-1>", lambda e: self.tap())
        self.status_lbl = tk.Label(ov, text="idle", bg=VBG, fg="#d9a3ff", font=("Consolas", 10, "bold"))
        self.status_lbl.pack(pady=(0, 6))
        tf = tk.Frame(ov, bg=VBG, height=66)
        tf.pack(fill="x", padx=16); tf.pack_propagate(False)
        self.text_lbl = tk.Label(tf, text="", bg=VBG, fg="#d4cdea", font=("Consolas", 12),
                                 wraplength=560, justify="center", anchor="n")
        self.text_lbl.pack(fill="both", expand=True)
        ctl = tk.Frame(ov, bg=VBG); ctl.pack(pady=(8, 22))
        self.mute_btn = self._btn(ctl, "mute mic", self.toggle_mute); self.mute_btn.pack(side="left", padx=5)
        self.spk_btn = self._btn(ctl, "voice replies: on", self.toggle_speech); self.spk_btn.pack(side="left", padx=5)
        vb = self._btn(ctl, "voice ▾", lambda: self.app.voice_menu(vb)); vb.pack(side="left", padx=5)
        mb = self._btn(ctl, "mic ▾", lambda: self.app.mic_menu(mb)); mb.pack(side="left", padx=5)

        self._build_items()
        root.bind("<Escape>", lambda e: self.close())

        ok, why = self._open_mic()
        if ok:
            self._mode_text()
            self.frame()
            self.say(f"Hi {a.username}, I'm listening.")
        else:
            self.frame()
            self._show_text(why)
            self._set("idle", "speech input unavailable — tap the orb to retry")

    def close(self):
        if not self.open:
            return
        self.open = False
        self.token += 1
        self.cap = None
        self._stop_engine()
        if self.job:
            try: self.app.root.after_cancel(self.job)
            except Exception: pass
            self.job = None
        if self.stream is not None:
            try: self.stream.stop(); self.stream.close()
            except Exception: pass
            self.stream = None
        self.app.root.unbind("<Escape>")
        if self.ov is not None:
            self.ov.destroy(); self.ov = None
        try: self.app.entry.focus_set()
        except Exception: pass

    def _mode_text(self):
        self.mode_lbl.configure(text=f"offline · {core.STT_NAME} · mic: {self.mic_name[:26]}")

    def reopen_mic(self):
        """Called after the user picks another microphone."""
        if self.stream is not None:
            try: self.stream.stop(); self.stream.close()
            except Exception: pass
            self.stream = None
        self.cap = None
        self._quiet, self._hinted = 0, False
        ok, why = self._open_mic()
        if ok:
            self._mode_text(); self.listen()
        else:
            self._show_text(why); self._set("idle", "speech input unavailable — tap the orb to retry")

    def _show_text(self, text):
        text = str(text)
        self.text_lbl.configure(text=text if len(text) <= 180 else text[:177] + "…")

    def _btn(self, parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd, bg=VBG, fg="#8a82b0", bd=0,
                         highlightthickness=1, highlightbackground="#2a2240",
                         activebackground="#1c1430", activeforeground="#d9a3ff",
                         font=("Consolas", 9), padx=12, pady=3, cursor="hand2")

    # ── microphone ───────────────────────────────────────────────────────────
    def _open_mic(self):
        if self.stream is not None:
            return True, ""
        if not self.app.voice_ready:
            self.can_listen = False
            return False, "Voice is still loading — tap the orb in a moment."
        if core.STT_MODEL is None:
            self.can_listen = False
            return False, (f"No offline speech model ({core.STT_STATUS}).\n"
                           "Needs: pip install vosk sounddevice  +  a Vosk model in models/")
        try:
            import sounddevice as sd
        except Exception as e:
            self.can_listen = False
            return False, f"Microphone access needs 'sounddevice' ({e}).  pip install sounddevice"
        dev = self.app.mic_index()
        try:
            info = sd.query_devices(dev, "input")
        except Exception as e:
            self.can_listen = False
            return False, f"No microphone found: {e}"
        default_rate = int(info.get("default_samplerate") or 48000)
        last = "unknown error"
        for rate in dict.fromkeys((16000, default_rate)):
            for ch in (1, 2):
                if ch > int(info["max_input_channels"]):
                    continue
                try:
                    st = sd.RawInputStream(samplerate=rate, channels=ch, dtype="int16",
                                           blocksize=rate // 10, device=dev, callback=self._audio_cb)
                    self.src_rate, self.src_ch = rate, ch      # set before the first callback
                    st.start()
                except Exception as e:
                    last = str(e)
                    print(f"[voice] mic open failed ({rate} Hz, {ch} ch): {e}")
                    continue
                self.stream, self.mic_name = st, str(info["name"])
                self.can_listen = True
                print(f"[voice] microphone: {self.mic_name} @ {rate} Hz x{ch}")
                return True, ""
        self.can_listen = False
        return False, f"Could not open the microphone ({info['name']}): {last}"

    def _newcap(self):
        return {"pre": [], "chunks": [], "talking": False, "silent": 0.0, "ms": 0.0}

    def _audio_cb(self, indata, frames, ti, status):
        """Audio thread: level meter + energy-based start/stop of one utterance."""
        s = array("h"); s.frombytes(bytes(indata))
        if self.src_ch == 2:
            s = s[0::2]
        s = resample16k(s, self.src_rate)
        b = s.tobytes()
        n = len(s) or 1
        rms = math.sqrt(sum(v * v for v in s) / n) / 32768.0
        lv = min(1.0, rms * 5)
        self.mic_level = lv if lv > self.mic_level else self.mic_level * 0.8 + lv * 0.2
        # digital silence for ~3 s = muted mic or Windows privacy block
        self._quiet = self._quiet + 1 if rms < 0.0004 else 0
        if self._quiet >= 30 and not self._hinted:
            self._hinted = True
            self.app.q.put(("v_text", "No sound from the microphone. Try mic ▾ to pick another one, "
                                      "and check Windows Settings → Privacy → Microphone."))
        c = self.cap
        if c is None or not c["talking"]:                  # track room noise → adaptive threshold
            if rms < self.thresh * 1.5:
                self.noise = self.noise * 0.97 + rms * 0.03
                self.thresh = max(0.006, min(0.05, self.noise * 3 + 0.004))
        if c is None or self.state != "listening":
            return
        ms = n / 16.0
        if not c["talking"]:
            c["pre"].append(b)
            if len(c["pre"]) > 5:
                c["pre"].pop(0)
            if rms > self.thresh:
                c["talking"], c["chunks"], c["pre"] = True, c["pre"], []
                self.app.q.put(("v_text", "…"))
            return
        c["chunks"].append(b); c["ms"] += ms
        c["silent"] = 0.0 if rms > self.thresh else c["silent"] + ms
        if c["silent"] > 900 or c["ms"] > 15000:
            self._finish(c)

    def _finish(self, c):
        self.cap = None
        if c["ms"] - c["silent"] < 250:                # a click or cough, not speech
            self.cap = self._newcap()
            return
        self._set("thinking", "transcribing")
        threading.Thread(target=self._transcribe, args=(b"".join(c["chunks"]),), daemon=True).start()

    def _transcribe(self, data):
        try: text = core.transcribe_pcm(data)
        except Exception: text = ""
        self.app.q.put(("v_heard", text))

    # ── state machine ────────────────────────────────────────────────────────
    def _set(self, state, label=None):
        self.state = state
        self.app.q.put(("v_status", label or state))

    def listen(self):
        if not self.open:
            return
        if self.muted:
            self._set("idle", "mic muted"); return
        if not self.can_listen:
            self._set("idle", "speech input unavailable — tap the orb to retry"); return
        self.cap = self._newcap()
        self._set("listening", "listening — tell me the response" if self.teach else "listening · offline")

    def on_event(self, kind, p):
        if kind == "v_tts_fail":
            self.speak = False
            if self.open: self.spk_btn.configure(text="voice replies: off")
            self.app.sysmsg(f"Voice replies unavailable ({p}). Install: pip install pyttsx3")
            return
        if not self.open:
            return
        if kind == "v_status":   self.status_lbl.configure(text=str(p).upper())
        elif kind == "v_text":   self._show_text(p)
        elif kind == "v_heard":
            if p:
                self.handle(p)
            else:
                self._show_text("Didn't catch that — try again."); self.listen()
        elif kind == "v_result": self.respond(p)
        elif kind == "v_spoke" and p == self.token:
            self.listen()

    def handle(self, text):
        a = self.app
        self._set("thinking")
        self._show_text(text)
        a.user(text); a.log_line(text)
        if re.fullmatch(r"(stop|goodbye|close|exit voice|end voice)\.?", text.strip(), re.I):
            self.close(); return
        if self.teach:
            t, self.teach = self.teach, None
            try:
                Bot.learn(t["hash"], text, t["prompt"])
                a.sysmsg("✓ Response saved"); a.bot(text)
                self.say("Got it. I will remember that.")
            except Exception:
                self.say("Sorry, I could not save that.")
            return
        threading.Thread(target=self._process, args=(text,), daemon=True).start()

    def _process(self, text):
        try: r = Bot.process(text, self.app.username)
        except Exception: r = {"type": "reply", "text": "Something went wrong."}
        self.app.q.put(("v_result", r))

    def respond(self, r):
        a = self.app
        if not r or not r.get("type"):
            self.say("I did not get a response."); return
        t = r["type"]
        if t == "needs_teaching":
            self.teach = {"hash": r["hash"], "prompt": r["prompt"]}
            a.bot(f"I don't know how to respond to \"{r['prompt']}\".", style="warn")
            a.sysmsg(f"Voice teach: waiting for a response to \"{r['prompt']}\"")
            self.say("I do not know how to respond to that yet. What should I say?")
        elif t == "kill":
            a.render(r)
        elif t in ("reply", "learned", "predicted"):
            a.render(r)
            txt = r["text"]
            if t == "reply" and (txt.count("\n") >= 4 or "http" in txt):   # a tool's table / links
                self.say("Done. The result is in the chat.")
            else:
                self.say(txt)
        elif t == "crack_start":
            a.sysmsg("Cracking… (dictionary + brute force)")
            threading.Thread(target=lambda: a.q.put(("result", {
                "type": "crack_done", "hash": r["hash"],
                "data": core.crack_hash(r["hash"], verbose=False)})), daemon=True).start()
            self.say("Cracking that hash. I will put the result in the chat.")
        elif t in ("help", "hash_result", "crypt_result", "dirserver"):
            a.render(r); self.say("Done. The result is in the chat.")
        else:
            a.render(r); self.say(r.get("text") or "Done.")

    # ── speaking ─────────────────────────────────────────────────────────────
    def say(self, text):
        if not self.open:
            return
        self._show_text(text)
        if not self.speak:
            self.listen(); return
        self.token += 1
        self._set("speaking")
        threading.Thread(target=self._tts, args=(speakable(text), self.token), daemon=True).start()

    def _tts(self, text, tok):
        with self.app._tts_lock:
            try:
                import pyttsx3
                eng = make_engine(self.app.voice_id); self.engine = eng
                try: eng.connect("started-word", lambda name, location, length: setattr(self, "pulse", 1.0))
                except Exception: pass
                eng.say(text[:600]); eng.runAndWait(); eng.stop()
            except Exception as e:
                if not self._tts_failed:
                    self._tts_failed = True
                    self.app.q.put(("v_tts_fail", str(e)[:80]))
            finally:
                self.engine = None
        self.app.q.put(("v_spoke", tok))

    def _stop_engine(self):
        try:
            if self.engine is not None: self.engine.stop()
        except Exception:
            pass

    # ── controls ─────────────────────────────────────────────────────────────
    def tap(self):
        if self.state == "speaking":
            self.token += 1; self._stop_engine(); self.listen()
        elif self.muted:
            self.toggle_mute()
        elif self.state == "idle":
            if not self.can_listen:
                ok, why = self._open_mic()
                if not ok:
                    self._show_text(why); return
                self._mode_text()
            self.listen()

    def toggle_mute(self):
        self.muted = not self.muted
        self.mute_btn.configure(text="unmute mic" if self.muted else "mute mic",
                                fg="#e05555" if self.muted else "#8a82b0",
                                highlightbackground="#e05555" if self.muted else "#2a2240")
        if self.muted:
            self.cap = None; self._set("idle", "mic muted")
        else:
            self.listen()

    def toggle_speech(self):
        self.speak = not self.speak
        if not self.speak and self.state == "speaking":
            self.token += 1; self._stop_engine(); self.listen()
        self.spk_btn.configure(text="voice replies: " + ("on" if self.speak else "off"))

    # ── orb: canvas items are created once, then moved/recoloured every frame ─
    def _build_items(self):
        cv = self.cv
        self.halo = [cv.create_oval(0, 0, 1, 1, fill=VBG, outline="") for _ in range(HALO_N)]
        self.glow = [cv.create_oval(0, 0, 1, 1, fill=VBG, outline="") for _ in range(GLOW_N)]
        self.bars = [cv.create_line(0, 0, 1, 1, width=2, capstyle="round", fill=VBG) for _ in range(BARS)]
        self.arcs = [cv.create_arc(0, 0, 1, 1, start=0, extent=4, style="arc", width=2.5,
                                   outline=VBG, state="hidden") for _ in range(SWEEP_N)]
        self.rings = [cv.create_line(*([0, 0] * 97), width=1, fill=VBG) for _ in ORB_RINGS]
        self.dots = [cv.create_rectangle(0, 0, 1, 1, outline="", fill=VBG) for _ in range(ORB_N)]
        self.dot_col = [None] * ORB_N
        self.sats = [(cv.create_oval(0, 0, 1, 1, fill=VBG, outline=""),
                      cv.create_oval(0, 0, 1, 1, fill=VBG, outline="")) for _ in ORB_RINGS]

    def frame(self):
        if not self.open:
            return
        now = perf_counter()
        dt = 0.033 if self._last is None else max(0.008, min(0.08, now - self._last))
        self._last = now
        try:
            self._draw(dt)
        except tk.TclError:
            return
        cost = perf_counter() - now
        self.cost = self.cost * 0.9 + cost * 0.1
        self.adapt += 1
        if self.adapt >= 20:                       # slow machine → fewer dots, fast → more
            self.adapt = 0
            if self.cost > 0.026 and self.nd > 300:
                self._set_dots(self.nd - 150)
            elif self.cost < 0.009 and self.nd < ORB_N:
                self._set_dots(self.nd + 150)
        delay = max(1, 33 - int(cost * 1000))
        self.job = self.app.root.after(delay, self.frame)

    def _set_dots(self, n):
        n = max(300, min(ORB_N, n))
        for i in range(ORB_N):
            self.cv.itemconfigure(self.dots[i], state="normal" if i < n else "hidden")
        self.nd = n

    def _draw(self, dt=0.033):
        cv = self.cv
        w, h = cv.winfo_width(), cv.winfo_height()
        if w < 60 or h < 60:
            return
        sin, cos = math.sin, math.cos
        st = self.state
        f = dt / 0.0333
        sm = lambda k: 1 - (1 - k) ** f            # frame-rate independent smoothing
        self.t += dt; t = self.t
        self.pulse *= 0.81 ** f
        if st == "listening":  tg = max(0.06, self.mic_level)
        elif st == "speaking": tg = 0.22 + 0.18 * sin(t * 7) * sin(t * 2.3) + 0.45 * self.pulse
        elif st == "thinking": tg = 0.14 + 0.08 * sin(t * 4)
        else:                  tg = 0.04
        self.level += (tg - self.level) * sm(0.26)
        L = self.level
        heat_t = 1 if st == "speaking" else 0.55 if st == "thinking" else (0.2 + L * 0.6) if st == "listening" else 0
        self.heat  += (heat_t - self.heat) * sm(0.12)
        self.spin  += ((3.2 if st == "thinking" else 1) - self.spin) * sm(0.10)
        self.sweep += ((1 if st == "thinking" else 0) - self.sweep) * sm(0.15)
        self.ang   += dt * self.spin
        heat, ang = self.heat, self.ang

        R, cx, cy = min(w, h) * 0.25, w / 2, h / 2
        tint = mixc(C_CORE, C_HOT, heat * 0.45)
        coords, conf = cv.coords, cv.itemconfigure

        # halo (concentric bands stand in for the radial gradient) + core glow
        a0, a1 = 0.20 + 0.30 * L, 0.16 + 0.10 * L
        def halo_rgb(s):
            if s < 0.4:
                k = s / 0.4
                return rgb_over_bg(mixc(tint, C_DEEP, k), a0 + (a1 - a0) * k)
            return rgb_over_bg(C_DEEP, a1 * (1 - (s - 0.4) / 0.6))
        regeom = self._geom != (w, h)
        self._geom = (w, h)
        for i, item in enumerate(self.halo):
            u = (HALO_N - i) / HALO_N
            if regeom:
                rad = R * (0.2 + 2.5 * u)
                coords(item, cx - rad, cy - rad, cx + rad, cy + rad)
            col = hexc(halo_rgb(u))
            if col != self.halo_col[i]:
                conf(item, fill=col); self.halo_col[i] = col
        ga = 0.10 + 0.32 * L + 0.08 * heat
        for i, item in enumerate(self.glow):
            u = (GLOW_N - i) / GLOW_N
            rad = R * 1.05 * u
            base = halo_rgb(min(1, (rad - 0.2 * R) / (2.5 * R)) if rad > 0.2 * R else 0)
            add = ga * (1 - u)
            col = tuple(base[k] + C_HI[k] * add for k in range(3))
            if regeom:
                coords(item, cx - rad, cy - rad, cx + rad, cy + rad)
            col = hexc(col)
            if col != self.glow_col[i]:
                conf(item, fill=col); self.glow_col[i] = col

        # radial level ring
        rr = R * 1.34
        barcol = blend(tint, 0.55 + 0.3 * heat)
        for i, item in enumerate(self.bars):
            a = (i / BARS) * 6.2832 + ang * 0.08
            wob = 0.5 + 0.5 * sin(i * 0.9 + t * 3.1) * sin(i * 0.37 - t * 2.1)
            ln = 2 + (L * 1.5 + self.pulse * 0.35) * wob * R * 0.42
            c, s = cos(a), sin(a)
            coords(item, cx + c * rr, cy + s * rr, cx + c * (rr + ln), cy + s * (rr + ln))
            if barcol != self._barcol:
                conf(item, fill=barcol)
        self._barcol = barcol

        # thinking sweep (comet arc)
        if self.sweep > 0.02:
            base, r2 = ang * 2.2, R * 1.22
            for k, item in enumerate(self.arcs):
                if regeom:
                    coords(item, cx - r2, cy - r2, cx + r2, cy + r2)
                conf(item, start=-math.degrees(base - k * 0.07), extent=math.degrees(0.07) + 0.6,
                     outline=blend(C_HI, self.sweep * (1 - k / SWEEP_N) * 0.9), state="normal")
        else:
            for item in self.arcs:
                conf(item, state="hidden")

        # orbital rings + satellites
        ringcol = blend(C_CORE, 0.22 + 0.18 * heat)
        for idx, (rg_r, tilt, ys, y0, sat) in enumerate(ORB_RINGS):
            yaw = y0 + ang * ys
            ct, st2, cy2, sy2 = cos(tilt), sin(tilt), cos(yaw), sin(yaw)
            def pt(th):
                x, y = cos(th) * rg_r, sin(th) * rg_r
                y1, z1 = y * ct, y * st2
                x2, z2 = x * cy2 + z1 * sy2, -x * sy2 + z1 * cy2
                p = 1 / (1 - z2 * 0.13)
                return cx + x2 * R * p, cy + y1 * R * p, z2, p
            flat = []
            for i in range(97):
                q = pt(i / 96 * 6.2832); flat += (q[0], q[1])
            coords(self.rings[idx], *flat)
            if ringcol != self._ringcol:
                conf(self.rings[idx], fill=ringcol)
            q = pt(t * sat * 1.3 + y0)
            depth = max(0.35, min(1, 0.7 + q[2] * 0.25))
            g_item, c_item = self.sats[idx]
            coords(g_item, q[0] - 7 * q[3], q[1] - 7 * q[3], q[0] + 7 * q[3], q[1] + 7 * q[3])
            coords(c_item, q[0] - 2.4 * q[3], q[1] - 2.4 * q[3], q[0] + 2.4 * q[3], q[1] + 2.4 * q[3])
            conf(g_item, fill=blend(C_CORE, 0.25 * depth))
            conf(c_item, fill=blend(C_HI, 0.9 * depth))
        self._ringcol = ringcol

        # dot-mesh sphere
        ay, ax = ang * 0.35, 0.45 + sin(t * 0.2) * 0.15
        cyw, syw, cxw, sxw = cos(ay), sin(ay), cos(ax), sin(ax)
        tbl = []
        for b in range(24):                            # 12 depth steps x 2 heat steps
            tt, hh = (b // 2 + 0.5) / 12, 0.25 + 0.5 * (b % 2)
            c = mixc(C_DEEP, C_CORE, min(1, tt * 1.15))
            c = mixc(c, C_HI, hh * 0.75)
            c = mixc(c, C_HOT, heat * 0.35 * hh)
            tbl.append(blend(c, 0.10 + 0.80 * tt))
        last, items = self.dot_col, self.dots
        breathe = 0.015 * sin(t * 1.5)
        for i in range(self.nd):
            x, y, z = PX[i], PY[i], PZ[i]
            d = L * (0.55 * sin(x * 3.1 + t * 1.9) * cos(y * 2.7 - t * 1.4)
                     + 0.40 * sin(z * 4.2 + t * 2.4) + 0.30 * sin((x + y) * 5 - t * 3))
            r = 1 + d + breathe
            px, py, pz = x * r, y * r, z * r
            x1, z1 = px * cyw + pz * syw, -px * syw + pz * cyw
            y1, z2 = py * cxw - z1 * sxw, py * sxw + z1 * cxw
            persp = 1 / (1 - z2 * 0.22)
            tz = (z2 + 1.2) / 2.4
            tz = 0 if tz < 0 else 0.999 if tz > 0.999 else tz
            hz = abs(d) * 3 + heat * 0.7
            hz = 0.999 if hz > 0.999 else hz
            col = tbl[int(tz * 12) * 2 + (1 if hz > 0.45 else 0)]
            sz = (1.3 + 1.3 * tz) * persp
            X, Y = cx + x1 * R * persp, cy + y1 * R * persp
            coords(items[i], X, Y, X + sz, Y + sz)
            if last[i] != col:
                conf(items[i], fill=col); last[i] = col


class ChatFeed:
    """The message list, drawn straight onto a canvas instead of one widget per message.
    Nothing is created or destroyed per message, so redraws can't blank the chat, and a
    wallpaper can show through behind the bubbles."""
    PAD, GAP = 16, 9

    def __init__(self, app, cv):
        self.app, self.cv = app, cv
        self.refs = []                                  # PhotoImage references
        self.y_end, self.W, self.H, self.wrap, self.hh, self.valid = 12, 0, 0, 420, 14, False
        self._wall_key, self._wall_ref, self._src, self._job = None, None, {}, None

    @property
    def t(self):
        return self.app.t

    def font(self, kind):
        fs = self.app.fs
        return {"body": ("Consolas", fs), "small": ("Consolas", max(7, fs - 2)),
                "smallb": ("Consolas", max(7, fs - 3), "bold"), "tiny": ("Consolas", max(6, fs - 4))}[kind]

    # ── primitives ───────────────────────────────────────────────────────────
    def measure(self, text, kind, width=0):
        it = self.cv.create_text(-9000, -9000, text=text, font=self.font(kind), anchor="nw", width=width)
        bb = self.cv.bbox(it)
        self.cv.delete(it)
        return bb[2] - bb[0], bb[3] - bb[1]

    def T(self, x, y, text, kind, fill, tags, width=0, justify="left"):
        return self.cv.create_text(x, y, text=text, font=self.font(kind), fill=fill, anchor="nw",
                                   width=width, justify=justify, tags=tags)

    @staticmethod
    def _tags(tag):
        return (tag, tag + "c", "content")

    # ── whole-feed layout ────────────────────────────────────────────────────
    def relayout(self, bottom=None):
        cv = self.cv
        try:
            at_bottom = bottom if bottom is not None else cv.yview()[1] >= 0.97
        except Exception:
            at_bottom = True
        W, H = max(cv.winfo_width(), 320), max(cv.winfo_height(), 200)
        self.W, self.H, self.wrap = W, H, max(220, min(620, int(W * 0.8) - 60))
        cv.delete("content")
        cv.configure(cursor="")
        self.refs = []
        self._backdrop(W, H)
        self.hh = self.measure("Ag", "smallb")[1] + 5
        y = 12
        for i, m in enumerate(self.app.msgs):
            y = self._safe(m, i, y)
        self.y_end, self.valid = y, True
        self._region(self._typing(y) if self.app.busy else y)
        if at_bottom:
            self.to_bottom()

    def schedule(self):
        """Debounced relayout for window resizes."""
        if self._job:
            self.cv.after_cancel(self._job)
        self._job = self.cv.after(90, self._go)

    def _go(self):
        self._job = None
        if (self.cv.winfo_width(), self.cv.winfo_height()) != (self.W, self.H):
            self.relayout()

    def append(self, m):
        if not self.valid or max(self.cv.winfo_width(), 320) != self.W:
            return self.relayout(bottom=True)
        self.cv.delete("typing")
        y = self._safe(m, len(self.app.msgs) - 1, self.y_end)
        self.y_end = y
        self._region(self._typing(y) if self.app.busy else y)
        self.to_bottom()

    def show_typing(self):
        if not self.valid:
            return
        self.cv.delete("typing")
        self._region(self._typing(self.y_end))
        self.to_bottom()

    def hide_typing(self):
        if self.valid:
            self.cv.delete("typing")
            self._region(self.y_end)

    def _typing(self, y):
        t = self.t
        return self._bubble("typing", y, "bot", t["surface"], t["border"],
                            self._text_builder("EMLII is thinking…", t["muted"], "small"), padx=12, pady=6)

    def _region(self, y):
        self.cv.configure(scrollregion=(0, 0, self.W, max(y + 14, self.cv.winfo_height())))

    def to_bottom(self):
        self.cv.yview_moveto(1.0)
        self.cv.after_idle(lambda: self.cv.yview_moveto(1.0))

    # ── one message ──────────────────────────────────────────────────────────
    def _safe(self, m, i, y):
        try:
            return self._draw_msg(m, i, y)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.cv.create_text(self.PAD, y, text=f"[could not draw a message: {e}]", anchor="nw",
                                fill=self.t["red"], font=self.font("small"), tags=("content",))
            return y + 24

    def _draw_msg(self, m, i, y):
        t, k, tag, ts = self.t, m["k"], f"m{i}", m.get("ts", "")
        if k == "sys":
            bottom = self._bubble(tag, y, "sys", t["bg"], t["border"],
                                  self._text_builder(m["text"], t["muted"], "small", "center"),
                                  dashed=True, padx=12, pady=5)
        elif k == "user":
            bottom = self._bubble(tag, y, "user", t["user_bg"], t["user_border"],
                                  self._text_builder(m["text"], t["text"], "body"),
                                  header=(self.app.username, t["muted"], ts, None))
        elif k == "bot":
            fill, line = {"normal": (t["surface"], t["border"]),
                          "predicted": (t["pred_bg"], t["pred_border"]),
                          "warn": (t["warn_bg"], t["warn_border"])}[m.get("style", "normal")]
            bottom = self._bubble(tag, y, "bot", fill, line, self._bot_builder(m, fill, line),
                                  header=("EMLII", t["purple_hi"], ts, m.get("badge")))
        elif k == "kv":
            bottom = self._bubble(tag, y, "bot", t["surface"], t["border"], self._kv_builder(m),
                                  header=("EMLII", t["purple_hi"], ts, None))
        else:
            return y
        self._copy_binding(tag, m)
        return bottom + self.GAP

    def _text_builder(self, text, color, kind, justify="left"):
        def build(x, y, tag):
            self.T(x, y, text, kind, color, self._tags(tag), width=self.wrap, justify=justify)
        return build

    def _bot_builder(self, m, fill, line):
        def build(x, y, tag):
            cv, tags = self.cv, self._tags(tag)
            it = self.T(x, y, m["text"], "body", self.t["purple_hi"], tags, width=self.wrap)
            cy = cv.bbox(it)[3]
            for data in m.get("img_data", []):
                ph = self.app._photo(data, min(360, self.wrap))
                if ph is None:
                    continue
                self.refs.append(ph)
                cy += 8
                cv.create_image(x, cy, image=ph, anchor="nw", tags=tags)
                cy += ph.height()
            if m.get("pending"):
                self._actions(m, x, cy, tag, fill, line)
        return build

    def _kv_builder(self, m):
        def build(x, y, tag):
            t, cv, tags = self.t, self.cv, self._tags(tag)
            ti = self.T(x, y, m["title"].upper(), "tiny", t["muted"], tags, width=self.wrap)
            yy = cv.bbox(ti)[3] + 6
            rows = m["rows"]
            lw = max([self.measure(str(a), "body")[0] for a, _ in rows] or [0])
            rcw = max(140, self.wrap - lw - 16)
            for a, c in rows:
                li = self.T(x, yy, str(a), "body", t[m["lc"]], tags)
                ri = self.T(x + lw + 16, yy, str(c), "body", t[m.get("rc_for", {}).get(a, m["rc"])],
                            tags, width=rcw)
                yy = max(cv.bbox(li)[3], cv.bbox(ri)[3]) + 3
        return build

    def _actions(self, m, x, y, tag, fill, line):
        """The 'Right?  ✓ good  ✗ bad  ✎ edit' row under a predicted reply."""
        cv, t, tags = self.cv, self.t, self._tags(tag)
        bb = cv.bbox(tag + "c")
        cw = max(bb[2] - bb[0], 275)
        y += 10
        cv.create_line(x, y, x + cw, y, fill=line, tags=tags)
        y += 8
        self.T(x, y + 4, "Right?", "tiny", t["muted"], tags)
        xr = self._btn(x + cw, y, "✎ edit", t["muted"], fill, tag + "e", tags, lambda: self.app.edit_pred(m))
        xr = self._btn(xr - 8, y, "✗ bad", t["red"], fill, tag + "b", tags, lambda: self.app.reject_pred(m))
        self._btn(xr - 8, y, "✓ good", t["green"], fill, tag + "o", tags, lambda: self.app.accept_pred(m))

    def _btn(self, xr, y, label, color, fill, btag, tags, cb):
        cv = self.cv
        w, h = self.measure(label, "small")
        x1 = xr - w - 18
        tg = tags + (btag,)
        cv.create_rectangle(x1, y, xr, y + h + 8, outline=color, fill=fill, tags=tg)
        cv.create_text(x1 + 9, y + 4, text=label, font=self.font("small"), fill=color, anchor="nw", tags=tg)
        cv.tag_bind(btag, "<Button-1>", lambda e: cb())
        cv.tag_bind(btag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
        cv.tag_bind(btag, "<Leave>", lambda e: cv.configure(cursor=""))
        return x1

    def _bubble(self, tag, y, align, fill, line, build, header=None, dashed=False, padx=13, pady=9, r=10):
        """Build the content at the origin, measure it, put a rounded box behind it, then slide it into place."""
        cv = self.cv
        top = y + (self.hh if header else 0)
        build(padx, top + pady, tag)
        bb = cv.bbox(tag + "c")
        if bb is None:
            return top
        width, height = bb[2] + padx, (bb[3] - top) + pady
        kw = dict(fill=fill, outline=line, width=1, tags=(tag, "content"))
        if dashed:
            kw["dash"] = (3, 3)
        poly = rounded(cv, 1, top, width - 1, top + height, r, **kw)
        cv.tag_lower(poly, tag + "c")
        x0 = {"user": self.W - self.PAD - width, "bot": self.PAD, "sys": (self.W - width) / 2}[align]
        cv.move(tag, x0, 0)
        if header:
            self._header(tag, y, align, header, x0, width)
        return top + height

    def _header(self, tag, y, align, header, bx, bw):
        name, color, ts, badge = header
        cv, t, htag = self.cv, self.t, tag + "h"
        tags = (htag, "content")
        it = cv.create_text(0, y, text=name.upper(), font=self.font("smallb"), fill=color, anchor="nw", tags=tags)
        x = cv.bbox(it)[2] + 8
        if badge:
            label, ck = badge
            bi = cv.create_text(x + 5, y + 1, text=label, font=self.font("tiny"), fill=t[ck], anchor="nw", tags=tags)
            b2 = cv.bbox(bi)
            cv.create_rectangle(x, b2[1] - 1, b2[2] + 5, b2[3] + 1, outline=t[ck], tags=tags)
            x = b2[2] + 13
        cv.create_text(x, y + 1, text=ts, font=self.font("tiny"), fill=t["muted"], anchor="nw", tags=tags)
        hb = cv.bbox(htag)
        dx = bx if align != "user" else bx + bw - (hb[2] - hb[0])
        cv.move(htag, dx - hb[0], 0)

    def _copy_binding(self, tag, m):
        text = m["text"] if "text" in m else "\n".join(f"{a}  {c}" for a, c in m.get("rows", []))

        def popup(e):
            menu = tk.Menu(self.app.root, tearoff=0)
            menu.add_command(label="Copy", command=lambda: (self.app.root.clipboard_clear(),
                                                            self.app.root.clipboard_append(text)))
            menu.tk_popup(e.x_root, e.y_root)
        self.cv.tag_bind(tag, "<Button-3>", popup)

    # ── background: solid / gradient / wallpaper ─────────────────────────────
    def _backdrop(self, W, H):
        cv, S, t = self.cv, self.app.settings, self.t
        mode = S.get("bg_mode", "solid")
        key = (W, H, mode, t["bg"], S.get("bg_color2"), S.get("bg_image"), S.get("bg_dim"))
        cv.configure(bg=t["bg"])
        if key == self._wall_key and cv.find_withtag("wall"):
            return
        cv.delete("wall")
        self._wall_key, self._wall_ref = key, None
        ph = None
        try:
            if mode == "gradient":
                ph = self._gradient(W, H, t["bg"], S.get("bg_color2") or t["surface"])
            elif mode == "image" and S.get("bg_image"):
                ph = self._wallpaper(W, H, S["bg_image"], int(S.get("bg_dim", 55)), t["bg"])
        except Exception as e:
            print("[background]", e)
        if ph is not None:
            self._wall_ref = ph
            cv.create_image(0, cv.canvasy(0), image=ph, anchor="nw", tags="wall")
            cv.tag_lower("wall")

    def _gradient(self, W, H, c1, c2):
        a, b = hex_rgb(c1), hex_rgb(c2)
        cols = [mixc(a, b, y / max(1, H - 1)) for y in range(H)]
        try:
            from PIL import Image, ImageTk
            im = Image.new("RGB", (1, H))
            im.putdata([tuple(int(v) for v in c) for c in cols])
            return ImageTk.PhotoImage(im.resize((W, H)))
        except ImportError:
            ph = tk.PhotoImage(width=1, height=H)
            ph.put(" ".join(hexc(c) for c in cols), to=(0, 0))
            return ph.zoom(W, 1)

    def _wallpaper(self, W, H, path, dim, bg):
        try:
            from PIL import Image, ImageTk, ImageOps
        except ImportError:
            raise RuntimeError("wallpaper images need Pillow (pip install pillow)")
        if path not in self._src:
            self._src = {path: Image.open(path).convert("RGB")}
        im = ImageOps.fit(self._src[path], (W, H), Image.LANCZOS)
        im = Image.blend(im, Image.new("RGB", (W, H), hex_rgb(bg)), max(0, min(90, dim)) / 100)
        return ImageTk.PhotoImage(im)


class SettingsDialog:
    """⚙ Settings: theme colours, background, and folders."""
    COLOR_FIELDS = [("bg", "Background"), ("surface", "Panels and bars"), ("border", "Borders"),
                    ("text", "Text"), ("muted", "Muted text"), ("purple", "Accent (buttons)"),
                    ("purple_hi", "Accent light / EMLII text"), ("user_bg", "Your bubble"),
                    ("user_border", "Your bubble border"), ("pred_bg", "Prediction bubble"),
                    ("pred_border", "Prediction border"), ("green", "Success / OK")]
    DIR_FIELDS = [("dir_data", "Data folder", "memory, chat history, saves, config", "data"),
                  ("dir_downloads", "Downloads folder", "!download and !waifu save here", "downloads"),
                  ("dir_models", "Models folder", "voice (Vosk) and AI models", "models"),
                  ("dir_tools", "Tools folder", "plugins (.py files)", "tools")]
    RESTART = ("dir_data", "dir_models", "dir_tools")

    def __init__(self, app):
        from tkinter import filedialog, colorchooser
        self.fd, self.cc, self.app = filedialog, colorchooser, app
        S = app.settings
        self.preset = app.preset
        self.colors = {k: dict(v) for k, v in (S.get("colors") or {}).items()}
        self.grad = S.get("bg_color2") or "#1a0f3a"
        win = self.win = tk.Toplevel(app.root)
        win.title("EMLII settings")
        win.geometry("620x700")
        win.transient(app.root)
        nb = ttk.Notebook(win)
        nb.pack(fill="both", expand=True, padx=10, pady=(10, 4))
        self.sw = {}
        self._tab_theme(nb)
        self._tab_background(nb)
        self._tab_folders(nb)
        bar = ttk.Frame(win)
        bar.pack(fill="x", padx=10, pady=10)
        ttk.Button(bar, text="Apply", command=self.apply).pack(side="left")
        ttk.Button(bar, text="Save & close", command=lambda: self.apply(True)).pack(side="right")
        ttk.Button(bar, text="Cancel", command=win.destroy).pack(side="right", padx=6)

    # ── theme ────────────────────────────────────────────────────────────────
    def _tab_theme(self, nb):
        f = ttk.Frame(nb, padding=14)
        nb.add(f, text="  Theme  ")
        row = ttk.Frame(f); row.pack(fill="x")
        ttk.Label(row, text="Preset").pack(side="left")
        self.preset_var = tk.StringVar(value=self.preset)
        cb = ttk.Combobox(row, textvariable=self.preset_var, values=list(THEME_PRESETS),
                          state="readonly", width=18)
        cb.pack(side="left", padx=8)
        cb.bind("<<ComboboxSelected>>", self._preset_changed)
        ttk.Button(row, text="Reset my colours", command=self._reset_colors).pack(side="left")
        grid = ttk.Frame(f); grid.pack(fill="x", pady=(14, 6))
        for i, (key, label) in enumerate(self.COLOR_FIELDS):
            ttk.Label(grid, text=label).grid(row=i, column=0, sticky="w", pady=3)
            b = tk.Button(grid, width=12, relief="flat", bd=1, cursor="hand2",
                          command=lambda k=key: self._pick(k))
            b.grid(row=i, column=1, padx=14, pady=3)
            self.sw[key] = b
        fr = ttk.Frame(f); fr.pack(fill="x", pady=(10, 0))
        ttk.Label(fr, text="Chat text size").pack(side="left")
        self.fs_var = tk.IntVar(value=int(self.app.fs))
        ttk.Spinbox(fr, from_=8, to=20, width=5, textvariable=self.fs_var).pack(side="left", padx=8)
        ttk.Label(f, text="Pick a preset, change any colour, then press Apply to preview.",
                  foreground="#777").pack(anchor="w", pady=(12, 0))
        self._refresh_swatches()

    def _color(self, key):
        return self.colors.get(self.preset, {}).get(key) or THEME_PRESETS[self.preset][key]

    def _refresh_swatches(self):
        for key, b in self.sw.items():
            c = self._color(key)
            b.configure(bg=c, activebackground=c, text=c, fg="#000000" if luminance(c) > 0.5 else "#ffffff")

    def _preset_changed(self, _e=None):
        self.preset = self.preset_var.get()
        self._refresh_swatches()

    def _reset_colors(self):
        self.colors.pop(self.preset, None)
        self._refresh_swatches()

    def _pick(self, key):
        _, hx = self.cc.askcolor(self._color(key), parent=self.win, title="Choose a colour")
        if hx:
            self.colors.setdefault(self.preset, {})[key] = hx
            self._refresh_swatches()

    # ── background ───────────────────────────────────────────────────────────
    def _tab_background(self, nb):
        S = self.app.settings
        f = ttk.Frame(nb, padding=14)
        nb.add(f, text="  Background  ")
        self.bg_mode = tk.StringVar(value=S.get("bg_mode", "solid"))
        for val, label in (("solid", "Solid colour   (the Background colour on the Theme tab)"),
                           ("gradient", "Gradient   (Background colour → bottom colour)"),
                           ("image", "Wallpaper image")):
            ttk.Radiobutton(f, text=label, variable=self.bg_mode, value=val).pack(anchor="w", pady=2)
        g = ttk.Frame(f); g.pack(fill="x", pady=(12, 4))
        ttk.Label(g, text="Gradient bottom colour").pack(side="left")
        self.grad_btn = tk.Button(g, width=12, relief="flat", cursor="hand2", command=self._pick_grad)
        self.grad_btn.pack(side="left", padx=10)
        self._paint_grad()
        im = ttk.Frame(f); im.pack(fill="x", pady=(12, 4))
        ttk.Label(im, text="Image").pack(side="left")
        self.bg_image = tk.StringVar(value=S.get("bg_image", ""))
        ttk.Entry(im, textvariable=self.bg_image).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(im, text="Browse…", command=self._browse_image).pack(side="left")
        d = ttk.Frame(f); d.pack(fill="x", pady=(10, 0))
        ttk.Label(d, text="Dim image").pack(side="left")
        self.bg_dim = tk.IntVar(value=int(S.get("bg_dim", 55)))
        ttk.Scale(d, from_=0, to=90, variable=self.bg_dim, orient="horizontal").pack(
            side="left", fill="x", expand=True, padx=10)
        ttk.Label(d, textvariable=self.bg_dim, width=3).pack(side="left")
        ttk.Label(d, text="%").pack(side="left")
        try:
            import PIL  # noqa: F401
            note = "Tip: dim the image so message text stays readable."
        except ImportError:
            note = "Wallpaper images need Pillow:   pip install pillow   (solid and gradient work without it)"
        ttk.Label(f, text=note, foreground="#777", wraplength=520).pack(anchor="w", pady=(12, 0))

    def _paint_grad(self):
        self.grad_btn.configure(bg=self.grad, activebackground=self.grad, text=self.grad,
                                fg="#000000" if luminance(self.grad) > 0.5 else "#ffffff")

    def _pick_grad(self):
        _, hx = self.cc.askcolor(self.grad, parent=self.win, title="Gradient bottom colour")
        if hx:
            self.grad = hx
            self._paint_grad()

    def _browse_image(self):
        p = self.fd.askopenfilename(parent=self.win, title="Choose a wallpaper",
                                    filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                                               ("All files", "*.*")])
        if p:
            self.bg_image.set(p)
            self.bg_mode.set("image")

    # ── folders ──────────────────────────────────────────────────────────────
    def _tab_folders(self, nb):
        S = self.app.settings
        f = ttk.Frame(nb, padding=14)
        nb.add(f, text="  Folders  ")
        self.dir_vars = {}
        for key, label, note, default in self.DIR_FIELDS:
            box = ttk.LabelFrame(f, text=label, padding=8)
            box.pack(fill="x", pady=5)
            var = tk.StringVar(value=S.get(key, ""))
            self.dir_vars[key] = var
            row = ttk.Frame(box); row.pack(fill="x")
            ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)
            ttk.Button(row, text="Browse…", command=lambda k=key: self._browse_dir(k)).pack(side="left", padx=4)
            ttk.Button(row, text="Open", command=lambda v=var, d=default: self._open_dir(v, d)).pack(side="left")
            ttk.Button(row, text="Reset", command=lambda v=var: v.set("")).pack(side="left", padx=4)
            when = "needs a restart" if key in self.RESTART else "applies immediately"
            ttk.Label(box, text=f"{note}  ·  empty = ./{default} next to the app  ·  {when}",
                      foreground="#777", wraplength=520).pack(anchor="w", pady=(4, 0))
        ttk.Label(f, text="Changing the data, models or tools folder doesn't move what's already in the "
                          "old one — copy its contents across.", foreground="#777",
                  wraplength=540).pack(anchor="w", pady=(10, 0))

    def _browse_dir(self, key):
        p = self.fd.askdirectory(parent=self.win, title="Choose a folder")
        if p:
            self.dir_vars[key].set(p)

    def _open_dir(self, var, default):
        p = Path(var.get().strip() or BASE / default)
        try:
            p.mkdir(parents=True, exist_ok=True)
            os.startfile(str(p))
        except AttributeError:
            import subprocess
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(p)])
        except OSError as e:
            messagebox.showerror("Open folder", str(e), parent=self.win)

    # ── apply ────────────────────────────────────────────────────────────────
    def apply(self, close=False):
        app, S = self.app, self.app.settings
        dirs = {k: v.get().strip() for k, v in self.dir_vars.items()}
        for k, v in dirs.items():
            if v:
                try:
                    Path(v).mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    messagebox.showerror("Folders", f"Can't use '{v}':\n{e}", parent=self.win)
                    return
        if self.bg_mode.get() == "image" and not Path(self.bg_image.get().strip()).is_file():
            messagebox.showerror("Background", "Pick an image file first (or choose another background).",
                                 parent=self.win)
            return
        try: fs = max(8, min(20, int(self.fs_var.get())))
        except (tk.TclError, ValueError): fs = 11
        S.update(theme=self.preset, colors=self.colors, font_size=fs, bg_mode=self.bg_mode.get(),
                 bg_color2=self.grad, bg_image=self.bg_image.get().strip(),
                 bg_dim=int(float(self.bg_dim.get())), **dirs)
        save_settings()
        apply_dir_env(S)                                  # downloads folder takes effect right away
        app.apply_appearance()
        if any(S.get(k, "") != app.startup_dirs.get(k, "") for k in self.RESTART):
            if messagebox.askyesno("Restart needed", "Folder changes for data, models or tools need EMLII "
                                   "to restart.\n\nRestart now?", parent=self.win):
                app.restart()
                return
        if close:
            self.win.destroy()


class WebServer:
    """Runs EMLII's Flask web UI on a background thread inside this process."""

    def __init__(self):
        self.srv, self.port, self.error = None, None, None

    @property
    def running(self):
        return self.srv is not None

    def start(self, first_port=5000):
        if self.running:
            return True
        if not getattr(core, "FLASK_AVAILABLE", False):
            self.error = "Flask is not installed (pip install flask)"
            return False
        try:
            from werkzeug.serving import make_server
        except ImportError as e:
            self.error = str(e); return False
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        for port in range(first_port, first_port + 10):
            try:
                self.srv = make_server("0.0.0.0", port, core.app, threaded=True)
                self.port, self.error = port, None
                threading.Thread(target=self.srv.serve_forever, daemon=True).start()
                return True
            except OSError:
                continue
        self.error = f"ports {first_port}-{first_port + 9} are all in use"
        return False

    def stop(self):
        if self.srv:
            try: self.srv.shutdown(); self.srv.server_close()
            except Exception: pass
        self.srv, self.port = None, None

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}" if self.port else None

    @property
    def lan_url(self):
        try: return f"http://{core.get_lan_ip()}:{self.port}" if self.port else None
        except Exception: return None



class App:
    def __init__(self, root):
        self.root = root
        self.settings = SETTINGS
        self.startup_dirs = {k: SETTINGS.get(k, "") for k in DIR_ENV}
        self.q = queue.Queue()            # worker threads -> UI thread
        self.history, self.hist_i = [], 0
        self.msgs = []                    # message dicts; the ChatFeed draws them
        self.busy = False
        self.voice = VoiceMode(self)
        self.web = WebServer()
        self.speak_on = False
        self._tts_lock = threading.Lock()
        self._tts_warned = False
        self.voice_ready = False
        self.show_sidebar = True
        self._settings_win = None

        cfg = {}
        try: cfg = core.load_config()
        except Exception: pass
        S = self.settings
        self.voice_id = S.get("voice_id") or cfg.get("gui_voice") or None   # None = automatic (female)
        self.mic_pref = S.get("mic_pref") or cfg.get("gui_mic") or ""       # device name, "" = system default
        try: self.fs = max(8, min(20, int(S.get("font_size", 11))))
        except (TypeError, ValueError): self.fs = 11
        self.preset, self.t = build_theme({**S, "theme": S.get("theme") or cfg.get("gui_theme")})

        root.title(f"EMLII v{Bot.VERSION}")
        root.geometry("980x680")
        root.minsize(640, 460)
        icon = BASE / "emlii.ico"
        if icon.exists():
            try: root.iconbitmap(str(icon))
            except Exception: pass

        self.username = simpledialog.askstring(
            "EMLII", "Enter your username:", parent=root) or "User"

        self.ui = None
        self.build_ui()
        self.bot(f"Hello, {self.username}. I am EMLII v{Bot.VERSION}.\n"
                 "I learn and predict — the more we chat, the smarter I get.\n"
                 "Type !help, or click a command in the sidebar.")

        root.after(50, self._poll)
        root.after(1000, self._poll_notes)
        core.load_tools()
        self.web.start()
        self._refresh_status()
        self.fill_sidebar()
        threading.Thread(target=self._load_models, daemon=True).start()
        threading.Thread(target=self._load_voice, daemon=True).start()

    # ══ UI construction (rebuilt wholesale when the theme changes) ═══════════
    def build_ui(self):
        t = self.t
        pending = self.entry.get() if getattr(self, "entry", None) else ""
        if self.ui is not None:
            self.ui.destroy()
        self.root.configure(bg=t["bg"])
        self.ui = tk.Frame(self.root, bg=t["bg"])
        self.ui.pack(fill="both", expand=True)

        def btn(parent, text, cmd):
            return tk.Button(parent, text=text, command=cmd, bg=t["surface"], fg=t["muted"],
                             bd=0, highlightthickness=1, highlightbackground=t["border"],
                             activebackground=t["bg"], activeforeground=t["purple_hi"],
                             padx=9, pady=2, cursor="hand2", font=("Consolas", 9))

        # top bar
        bar = tk.Frame(self.ui, bg=t["surface"]); bar.pack(fill="x")
        tk.Label(bar, text="EMLII", bg=t["surface"], fg=t["purple_hi"],
                 font=("Consolas", 14, "bold")).pack(side="left", padx=(14, 4), pady=9)
        tk.Label(bar, text=f"v{Bot.VERSION}", bg=t["surface"], fg=t["muted"],
                 font=FONT_S).pack(side="left", pady=(6, 0))
        btn(bar, "☰", self.toggle_sidebar).pack(side="left", padx=10)
        self.web_btn = btn(bar, "🌐 Web", self.web_menu)
        self.web_btn.pack(side="left")
        tk.Frame(bar, bg=t["border"], width=0).pack(side="right", padx=4)
        btn(bar, "⚙ Settings", self.open_settings).pack(side="right", padx=3)
        btn(bar, "◐", self.quick_toggle).pack(side="right", padx=3)
        ab = btn(bar, "🎙 Audio", lambda: self.audio_menu(ab)); ab.pack(side="right", padx=3)
        btn(bar, "Clear", self.clear).pack(side="right", padx=3)
        self.speak_btn = btn(bar, "🔊 on" if self.speak_on else "🔊 off", self.toggle_speak)
        self.speak_btn.pack(side="right", padx=3)
        tk.Label(bar, text=f"session: {self.username}", bg=t["surface"], fg=t["muted"],
                 font=FONT_S).pack(side="right", padx=8)
        tk.Frame(self.ui, bg=t["border"], height=1).pack(fill="x")

        # status bar, then input row (packed to the bottom before the expanding middle)
        self.status = tk.Label(self.ui, text="", bg=t["bg"], fg=t["muted"], anchor="w",
                               font=("Consolas", 9), padx=12)
        self.status.pack(side="bottom", fill="x")

        box = tk.Frame(self.ui, bg=t["surface"], highlightthickness=1,
                       highlightbackground=t["border"])
        box.pack(side="bottom", fill="x")
        tk.Label(box, text=f"{self.username} ▶", bg=t["surface"], fg=t["purple_hi"],
                 font=FONT_B).pack(side="left", padx=(14, 8), pady=11)
        self.entry = tk.Entry(box, bg=t["surface"], fg=t["text"], insertbackground=t["purple_hi"],
                              font=FONT, relief="flat", bd=0,
                              disabledbackground=t["surface"], disabledforeground=t["muted"])
        self.entry.pack(side="left", fill="x", expand=True, ipady=5, pady=11)
        self.entry.insert(0, pending)
        self.entry.bind("<Return>", lambda e: self.on_send())
        self.entry.bind("<Up>", lambda e: self._recall(-1))
        self.entry.bind("<Down>", lambda e: self._recall(1))
        self.mic_btn = tk.Button(box, text="🎤", command=self.voice.toggle, bd=0, padx=10,
                                 cursor="hand2", highlightthickness=1,
                                 highlightbackground=t["border"], bg=t["surface"], fg=t["muted"],
                                 activebackground=t["bg"])
        self.mic_btn.pack(side="left", padx=(8, 0))
        tk.Button(box, text="Send", command=self.on_send, bg=t["purple"], fg=t["btn_fg"],
                  bd=0, font=FONT_B, padx=16, pady=3, cursor="hand2",
                  activebackground=t["purple_hi"]).pack(side="left", padx=12, pady=9)

        # middle: sidebar + scrolling bubble feed
        mid = tk.Frame(self.ui, bg=t["bg"]); mid.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(mid, bg=t["surface"], width=210)
        self.sidebar.pack_propagate(False)
        if self.show_sidebar:
            self.sidebar.pack(side="left", fill="y")
        self.sb = ttk.Scrollbar(mid)
        self.sb.pack(side="right", fill="y")
        self.cv = tk.Canvas(mid, bg=t["bg"], highlightthickness=0, bd=0, yscrollcommand=self._yscroll)
        self.sb.configure(command=self.cv.yview)
        self.cv.pack(side="left", fill="both", expand=True)
        self.feedview = ChatFeed(self, self.cv)
        self.cv.bind("<Configure>", lambda e: self.feedview.schedule())
        self.cv.bind_all("<MouseWheel>", self._wheel)

        self.fill_sidebar()
        self._refresh_status()
        self.root.update_idletasks()
        self.feedview.relayout(bottom=True)
        self.voice.lift()
        if self.busy:
            self.entry.configure(state="disabled")
        else:
            self.entry.focus_set()

    # ── sidebar ──────────────────────────────────────────────────────────────
    def fill_sidebar(self):
        t, sb = self.t, self.sidebar
        for w in sb.winfo_children():
            w.destroy()

        def heading(text):
            tk.Label(sb, text=text, bg=t["surface"], fg=t["muted"], anchor="w",
                     font=("Consolas", 9, "bold")).pack(fill="x", padx=14, pady=(14, 3))

        def item(cmd, desc=""):
            row = tk.Label(sb, text=f"!{cmd}", bg=t["surface"], fg=t["purple_hi"], anchor="w",
                           font=FONT, cursor="hand2")
            row.pack(fill="x", padx=14)
            row.bind("<Button-1>", lambda e, c=cmd: self.insert_command(c))
            row.bind("<Enter>", lambda e, r=row: r.configure(fg=t["pink"]))
            row.bind("<Leave>", lambda e, r=row: r.configure(fg=t["purple_hi"]))
            if desc:
                tk.Label(sb, text=desc, bg=t["surface"], fg=t["muted"], anchor="w",
                         font=FONT_S, wraplength=180, justify="left").pack(fill="x", padx=14)

        heading("COMMANDS")
        for c in BUILTINS:
            item(c)
        heading("PLUGINS")
        if core.TOOLS:
            for c, mod in core.TOOLS.items():
                item(c, getattr(mod, "HELP", ""))
        else:
            tk.Label(sb, text="none in tools/", bg=t["surface"], fg=t["muted"],
                     anchor="w", font=("Consolas", 9)).pack(fill="x", padx=14)

    def insert_command(self, cmd):
        self.entry.delete(0, "end")
        self.entry.insert(0, f"!{cmd} ")
        self.entry.focus_set()

    def toggle_sidebar(self):
        self.show_sidebar = not self.show_sidebar
        if self.show_sidebar:
            self.sidebar.pack(side="left", fill="y", before=self.cv)
        else:
            self.sidebar.pack_forget()

    def quick_toggle(self):
        """◐ — flip between Light and your last dark preset."""
        S = self.settings
        if self.preset == "Light":
            S["theme"] = S.get("last_dark") or "Purple neon"
        else:
            S["last_dark"], S["theme"] = self.preset, "Light"
        save_settings()
        self.apply_appearance()

    def apply_appearance(self):
        S = self.settings
        try: self.fs = max(8, min(20, int(S.get("font_size", 11))))
        except (TypeError, ValueError): self.fs = 11
        self.preset, self.t = build_theme(S)
        self.build_ui()

    def open_settings(self):
        w = self._settings_win
        if w is not None and w.win.winfo_exists():
            w.win.lift()
            return
        self._settings_win = SettingsDialog(self)

    def restart(self):
        import subprocess
        try: self.web.stop()
        except Exception: pass
        cmd = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, str(Path(__file__).resolve())]
        try:
            subprocess.Popen(cmd, cwd=str(BASE))
        except Exception as e:
            messagebox.showerror("Restart", f"Couldn't restart ({e}).\nPlease reopen EMLII yourself.")
            return
        self.root.destroy()

    # ══ Chat feed ════════════════════════════════════════════════════════════
    def _yscroll(self, a, b):
        self.sb.set(a, b)
        try: self.cv.coords("wall", 0, self.cv.canvasy(0))    # the wallpaper stays put while you scroll
        except tk.TclError: pass

    def _wheel(self, e):
        if self.cv.yview() != (0.0, 1.0):
            self.cv.yview_scroll(int(-e.delta / 120), "units")

    def scroll_bottom(self):
        self.feedview.to_bottom()

    def clear(self):
        self.msgs.clear()
        self.feedview.relayout(bottom=True)

    def draw_all(self):
        self.feedview.relayout(bottom=True)

    def add(self, m):
        m.setdefault("ts", datetime.now().strftime("%H:%M"))
        self.msgs.append(m)
        self.feedview.append(m)

    # public message helpers
    def user(self, text):   self.add({"k": "user", "text": text})
    def sysmsg(self, text): self.add({"k": "sys", "text": text})
    def kv(self, title, rows, lc="purple_hi", rc="muted"):
        self.add({"k": "kv", "title": title, "rows": rows, "lc": lc, "rc": rc})

    def bot(self, text, badge=None, style="normal", result=None, images=None):
        m = {"k": "bot", "text": text, "badge": badge, "style": style,
             "result": result, "pending": style == "predicted",
             "images": list(images or [])[:4], "img_data": []}
        self.add(m)
        if m["images"]:
            threading.Thread(target=self._fetch_images, args=(m,), daemon=True).start()
        if not self.voice.open:
            self.speak(speakable(text) if images else text)

    def _fetch_images(self, m):
        for url in m["images"]:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "EMLII/1.0"})
                with urllib.request.urlopen(req, timeout=15) as r:
                    data = r.read(8_000_000)
                self.q.put(("img", (m, data)))
            except Exception as e:
                print("[image] could not load", url, e)

    def _photo(self, data, maxw=360):
        """PhotoImage from raw bytes: Pillow if installed (any format), else Tk's own PNG/GIF."""
        try:
            from PIL import Image, ImageTk
            im = Image.open(io.BytesIO(data))
            im.thumbnail((max(160, maxw), 360))
            return ImageTk.PhotoImage(im.convert("RGBA"))
        except ImportError:
            pass
        except Exception:
            return None
        try:
            ph = tk.PhotoImage(data=base64.b64encode(data))
            if ph.width() > maxw:
                ph = ph.subsample(-(-ph.width() // maxw))
            return ph
        except Exception:
            return None                                 # e.g. a JPEG without Pillow

    def _image_arrived(self, m, data):
        m["img_data"].append(data)
        self.feedview.relayout()

    # ── prediction actions ───────────────────────────────────────────────────
    def _vote(self, m, vote):
        """Send 👍/👎 to EMLII's memory. Returns the feedback result dict (or None on error)."""
        r = m.get("result") or {}
        try:
            return Bot.feedback(r["hash"], vote, text=m["text"], prompt=r.get("prompt"), source=r.get("source"))
        except Exception as e:
            self.sysmsg(f"Could not save feedback: {e}")
            return None

    def accept_pred(self, m):
        """👍 — the answer becomes trusted and can be used for future matches."""
        self._vote(m, 1)
        m.update(pending=False, style="normal", badge=None)
        self.feedview.relayout()

    def reject_pred(self, m):
        """👎 — flag the answer (it may be blocked), then offer to teach the right one."""
        res = self._vote(m, -1)
        r = m.get("result") or {}
        new = simpledialog.askstring(
            "What should I have said?",
            f"You marked this reply as wrong:\n{m['text']}\n\nType the right reply (Cancel to just flag it):",
            parent=self.root)
        if new and new.strip():
            try:
                Bot.correct(r["hash"], new.strip(), r.get("prompt"))
            except Exception as e:
                self.sysmsg(f"Could not save the correction: {e}")
                return
            m.update(text=new.strip(), pending=False, style="normal", badge=None)
            self.sysmsg("Correction saved.")
        else:
            blocked = bool(res and res.get("blocked"))
            m.update(pending=False, style="warn",
                     badge=("✗ flagged · won't reuse" if blocked else "✗ flagged", "red"))
        self.feedview.relayout()

    def edit_pred(self, m):
        r = m.get("result") or {}
        new = simpledialog.askstring(
            "Correct EMLII", f"Current reply:\n{m['text']}\n\nType the correct reply:",
            parent=self.root)
        if not (new and new.strip()):
            return
        try:
            Bot.correct(r["hash"], new.strip(), r.get("prompt"))
        except Exception as e:
            self.sysmsg(f"Could not save the correction: {e}")
            return
        m.update(text=new.strip(), pending=False, style="normal", badge=None)
        self.feedview.relayout()
        self.sysmsg("Correction saved.")

    # ── status ───────────────────────────────────────────────────────────────
    def _refresh_status(self):
        parts = [f"model: {core.ACTIVE_MODEL or core.OLLAMA_MODEL}"]
        if core.STT_MODEL:
            parts.append(f"voice: {core.STT_NAME}")
        if self.web.running:
            parts.append(f"web: {self.web.url}")
        elif self.web.error:
            parts.append(f"web off: {self.web.error}")
        self.status.configure(text="   ·   ".join(parts))

    def _load_models(self):
        self.q.put(("status", "registering local model with Ollama…"))
        try: core.load_models()
        except Exception as e: print("[models]", e)
        self.q.put(("refresh", None))

    def _load_voice(self):
        try: core.load_voice()
        except Exception as e: print("[voice]", e)
        self.voice_ready = True
        self.q.put(("refresh", None))

    # ══ Sending ══════════════════════════════════════════════════════════════
    def _recall(self, step):
        if self.history:
            self.hist_i = max(0, min(len(self.history), self.hist_i + step))
            self.entry.delete(0, "end")
            if self.hist_i < len(self.history):
                self.entry.insert(0, self.history[self.hist_i])
        return "break"

    def on_send(self):
        text = self.entry.get().strip()
        if not text or self.busy:
            return
        self.entry.delete(0, "end")
        self.history.append(text)
        self.hist_i = len(self.history)
        self.submit(text)

    def submit(self, text):
        if self.busy:
            return
        self.user(text)
        self.log_line(text)
        self.set_busy(True)
        threading.Thread(target=self._work, args=(text,), daemon=True).start()

    def log_line(self, text):
        try:
            with open(core.PATHS["history"] + "chat.txt", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().ctime()}] {self.username}: {text}\n")
        except OSError:
            pass

    def set_busy(self, busy):
        self.busy = busy
        self.entry.configure(state="disabled" if busy else "normal")
        if busy:
            self.feedview.show_typing()
        else:
            self.feedview.hide_typing()
            self.entry.focus_set()

    def _work(self, text):
        try:
            result = Bot.process(text, self.username)
            if result and result.get("type") == "crack_start":
                self.q.put(("note", "Cracking… (dictionary + brute force)"))
                result = {"type": "crack_done", "hash": result["hash"],
                          "data": core.crack_hash(result["hash"], verbose=False)}
            self.q.put(("result", result))
        except Exception as e:
            self.q.put(("error", str(e)))

    def _poll(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "result":
                    self.set_busy(False); self.render(payload)
                elif kind == "error":
                    self.set_busy(False); self.bot(f"Error: {payload}", style="warn")
                elif kind == "note":
                    self.sysmsg(payload)
                elif kind == "status":
                    self.status.configure(text=payload)
                elif kind == "refresh":
                    self._refresh_status(); self.fill_sidebar()
                elif kind == "img":
                    self._image_arrived(*payload)
                elif kind.startswith("v_"):
                    self.voice.on_event(kind, payload)
        except queue.Empty:
            pass
        self.root.after(50, self._poll)

    def _poll_notes(self):
        """Timers, reminders and other plugin alerts."""
        try:
            for n in core.pop_notifications(self.username):
                self.bot(f"🔔 {n['text']}")
        except Exception as e:
            print("[notify]", e)
        self.root.after(1000, self._poll_notes)

    # ── Result dicts → bubbles (mirrors render_terminal) ─────────────────────
    def render(self, r):
        tp = r.get("topic") if isinstance(r, dict) else None
        if tp and tp.get("switched"):
            self.sysmsg(f"↩ back to topic {tp['id']} · {tp['label']}")
        if not r:
            return
        t = r.get("type")

        if t in ("reply", "learned"):
            self.bot(r["text"], images=r.get("images"))

        elif t == "predicted":
            names = {"similarity": ("~similar input", "purple_hi"), "pattern": ("~pattern", "purple_hi"),
                     "ai": ("~ai model", "yellow")}
            label, ck = names.get(r.get("source"), ("~predicted", "pink"))
            conf = int(r.get("confidence", 0) * 100)
            self.bot(r["text"], badge=(f"{label} · {conf}%", ck), style="predicted", result=r)

        elif t == "needs_teaching":
            after = f"  (after \"{r['context']}\")" if r.get("context") else ""
            self.bot(f"I don't know how to respond to \"{r['prompt']}\"{after}.", style="warn")
            answer = simpledialog.askstring(
                "Teach EMLII", f"How should I respond to:\n\n{r['prompt']}{after}", parent=self.root)
            if answer and answer.strip():
                Bot.learn(r["hash"], answer.strip(), r["prompt"])
                self.bot(answer.strip())
            else:
                self.sysmsg("Skipped.")

        elif t == "help":
            self.kv("Commands", [(c, d) for c, d in r["commands"]], lc="purple_hi", rc="muted")

        elif t == "hash_result":
            self.kv(f"Hashes of \"{r['input']}\"",
                    [(a.upper(), h) for a, h in r["results"].items()], lc="pink", rc="cyan")

        elif t == "crack_done":
            d = r["data"]
            if d["found"]:
                self.kv("Cracked!", [(d["algo"].upper(), d["text"])], lc="pink", rc="yellow")
            else:
                self.bot("Could not crack that hash.", style="warn")

        elif t == "crypt_result":
            self.kv(f"{r['mode']} · {r['method']}",
                    [("Input", r["original"]), ("Output", r["output"])], lc="muted", rc="text")
            self.msgs[-1]["rc_for"] = {"Output": "yellow"}
            self.draw_all()

        elif t == "dirserver":
            self.kv("File server started",
                    [("Directory", r["directory"]), ("LAN URL", r["url"])], lc="muted", rc="cyan")

        elif t == "kill":
            self.root.after(300, self.root.destroy)

        else:
            self.bot(str(r.get("text", r)))

    # ══ Voice output ═════════════════════════════════════════════════════════
    def toggle_speak(self):
        if not self.speak_on:
            try:
                import pyttsx3  # noqa: F401
            except ImportError:
                messagebox.showinfo("Speech", "Spoken replies need pyttsx3:\n\n"
                                    f"{sys.executable} -m pip install pyttsx3")
                return
        self.speak_on = not self.speak_on
        self.speak_btn.configure(text="🔊 on" if self.speak_on else "🔊 off")

    def speak(self, text):
        if self.speak_on:
            threading.Thread(target=self._speak_worker, args=(text,), daemon=True).start()

    def _speak_worker(self, text):
        with self._tts_lock:
            try:
                eng = make_engine(self.voice_id)
                eng.say(speakable(text)[:600])
                eng.runAndWait()
                eng.stop()
            except Exception as e:
                if not self._tts_warned:
                    self._tts_warned = True
                    self.q.put(("note", f"Speech output failed: {e}"))

    # ══ Audio settings: voice + microphone ═══════════════════════════════════
    def _popup(self, m, anchor):
        m.tk_popup(anchor.winfo_rootx(), anchor.winfo_rooty() + anchor.winfo_height())

    def _fill_voice_menu(self, m):
        try:
            voices, current = list_voices(self.voice_id)
        except Exception as e:
            m.add_command(label=f"pyttsx3 unavailable: {str(e)[:50]}", state="disabled"); return
        if not voices:
            m.add_command(label="No voices installed", state="disabled"); return
        for vid, name, g in voices:
            short = name.replace("Microsoft ", "").split(" - ")[0]
            tag = {"female": "♀", "male": "♂"}.get(g, " ")
            m.add_command(label=f"{'✓' if vid == current else '  '} {tag} {short}",
                          command=lambda v=vid: self.set_voice(v))
        if not any(g == "female" for _, _, g in voices):
            m.add_separator()
            m.add_command(label="No female voice installed — add one in Windows", state="disabled")
            m.add_command(label="Settings → Time & language → Speech", state="disabled")

    def _fill_mic_menu(self, m):
        try:
            devs = input_devices()
        except Exception as e:
            m.add_command(label=f"sounddevice unavailable: {str(e)[:50]}", state="disabled"); return
        m.add_command(label=f"{'✓' if not self.mic_pref else '  '} System default",
                      command=lambda: self.set_mic(""))
        for _, name in devs:
            m.add_command(label=f"{'✓' if name == self.mic_pref else '  '} {name}",
                          command=lambda n=name: self.set_mic(n))

    def voice_menu(self, anchor):
        m = tk.Menu(self.root, tearoff=0); self._fill_voice_menu(m); self._popup(m, anchor)

    def mic_menu(self, anchor):
        m = tk.Menu(self.root, tearoff=0); self._fill_mic_menu(m); self._popup(m, anchor)

    def audio_menu(self, anchor):
        m = tk.Menu(self.root, tearoff=0)
        v = tk.Menu(m, tearoff=0); self._fill_voice_menu(v); m.add_cascade(label="Voice", menu=v)
        d = tk.Menu(m, tearoff=0); self._fill_mic_menu(d); m.add_cascade(label="Microphone", menu=d)
        m.add_separator()
        m.add_command(label=f"Speak chat replies: {'on' if self.speak_on else 'off'}",
                      command=self.toggle_speak)
        self._popup(m, anchor)

    def set_voice(self, vid):
        self.voice_id = vid
        self.settings["voice_id"] = vid
        save_settings()
        def sample():
            with self._tts_lock:
                try:
                    eng = make_engine(vid); eng.say("Hello, this is my voice."); eng.runAndWait(); eng.stop()
                except Exception as e:
                    self.q.put(("note", f"Could not play a sample: {e}"))
        threading.Thread(target=sample, daemon=True).start()

    def mic_index(self):
        """Index of the preferred microphone, or None for the system default."""
        if not self.mic_pref:
            return None
        try:
            for i, name in input_devices():
                if name == self.mic_pref:
                    return i
        except Exception:
            pass
        return None

    def set_mic(self, name):
        self.mic_pref = name
        self.settings["mic_pref"] = name
        save_settings()
        if self.voice.open:
            self.voice.reopen_mic()
        else:
            self.sysmsg(f"Microphone set to: {name or 'system default'}")

    # ══ Web mode (runs inside this app) ══════════════════════════════════════
    def web_menu(self):
        m = tk.Menu(self.root, tearoff=0)
        if self.web.running:
            m.add_command(label=f"Open  {self.web.url}", command=self.open_web)
            if self.web.lan_url:
                m.add_command(label=f"Copy network link  {self.web.lan_url}", command=self.copy_lan)
            m.add_separator()
            m.add_command(label="Stop web server", command=self.stop_web)
        else:
            m.add_command(label="Start web server", command=self.start_web)
            if self.web.error:
                m.add_separator(); m.add_command(label=self.web.error, state="disabled")
        x, y = self.web_btn.winfo_rootx(), self.web_btn.winfo_rooty() + self.web_btn.winfo_height()
        m.tk_popup(x, y)

    def open_web(self):
        import webbrowser
        webbrowser.open(self.web.url)

    def copy_lan(self):
        self.root.clipboard_clear(); self.root.clipboard_append(self.web.lan_url)
        self.sysmsg("Network link copied.")

    def start_web(self):
        if self.web.start():
            self.sysmsg(f"Web mode running at {self.web.url}")
        else:
            messagebox.showinfo("Web mode", f"Could not start the web server:\n\n{self.web.error}")
        self._refresh_status()

    def stop_web(self):
        self.web.stop()
        self.sysmsg("Web server stopped.")
        self._refresh_status()


def main():
    root = tk.Tk()
    try:
        App(root)
    except Exception as e:
        messagebox.showerror("EMLII", f"Failed to start:\n{e}")
        raise
    root.mainloop()


if __name__ == "__main__":
    main()
