"""
Build EMLII into a standalone app (no Python needed on the target PC).

    python build_exe.py              # single EMLII.exe          (simplest to share)
    python build_exe.py --onedir     # folder with EMLII.exe     (starts faster, fewer antivirus flags)
    python build_exe.py --console    # keep a console window     (handy for debugging)
    python build_exe.py --dry-run    # just print the PyInstaller command

Put these side by side first:   EMLII.py   emlii_gui.py   build_exe.py   (optional: emlii.ico)

PyInstaller builds for the OS it runs on: run this on Windows for a .exe, on
macOS for a .app-style binary, on Linux for a Linux binary.

Plugins: tools/*.py are scanned for imports (standard library AND third-party) and bundled.
Extra pip packages go in plugins_requirements.txt  ("package  # import_name").

Where things live at run time (all next to the exe, so the app is portable):
    data/      memory database (emlii.db), config, chat history
    tools/     plugin .py files   (plugins can only import modules that were bundled)
    models/    local Vosk / .gguf models (too big to bundle — copy them in)
    emlii.log  output of the windowed app (voice / model status, errors)
"""
import argparse
import ast
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = "EMLII"


def have(mod):
    try:
        return importlib.util.find_spec(mod) is not None
    except (ImportError, ValueError):
        return False


# stdlib modules plugins often use that the app itself never imports — always bundled
STDLIB_EXTRAS = [
    "math", "statistics", "decimal", "fractions", "calendar", "zoneinfo", "uuid", "secrets",
    "textwrap", "csv", "html", "html.parser", "xml.etree.ElementTree", "zipfile", "base64",
    "binascii", "glob", "fnmatch", "platform", "ssl", "http.client", "urllib.parse",
    "urllib.request", "email", "email.mime.text", "smtplib", "hmac", "datetime", "heapq",
    "bisect", "pprint", "typing", "dataclasses", "enum", "contextlib", "operator", "queue",
    "sched", "ctypes", "locale", "gettext", "unicodedata", "ipaddress", "shlex", "colorsys",
]


def plugin_imports():
    """Top-level modules imported by tools/*.py (so PyInstaller can bundle them)."""
    mods = set()
    tools = HERE / "tools"
    if not tools.is_dir():
        return mods
    local = {p.stem for p in tools.glob("*.py")}
    for f in tools.glob("*.py"):
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, OSError):
            print(f"WARNING: could not parse {f.name} — skipped when scanning imports")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                mods.add(node.module)
    return {m for m in mods if m.split(".")[0] not in local}


def requirements():
    """[(pip_name, [import names])] from plugins_requirements.txt"""
    out, f = [], HERE / "plugins_requirements.txt"
    if f.is_file():
        for line in f.read_text(encoding="utf-8").splitlines():
            body, _, mods = line.partition("#")
            pkg = body.strip()
            if not pkg:
                continue
            names = [m.strip() for m in mods.split(",") if m.strip()] or \
                    [pkg.split("==")[0].split(">=")[0].replace("-", "_")]
            out.append((pkg, names))
    return out


def main():
    ap = argparse.ArgumentParser(description="Build EMLII with PyInstaller")
    ap.add_argument("--onedir", action="store_true", help="folder build instead of a single file")
    ap.add_argument("--console", action="store_true", help="show a console window")
    ap.add_argument("--name", default=NAME)
    ap.add_argument("--icon", default=None, help=".ico file (default: emlii.ico next to this script)")
    ap.add_argument("--dry-run", action="store_true", help="print the command, don't build")
    a = ap.parse_args()

    # ── sanity checks ────────────────────────────────────────────────────────
    for f in ("EMLII.py", "emlii_gui.py"):
        if not (HERE / f).is_file():
            sys.exit(f"Missing {f} — put it next to build_exe.py.")
    if not a.dry_run and not have("tkinter"):
        sys.exit("tkinter is missing. Reinstall Python with the 'tcl/tk and IDLE' option ticked "
                 "(on Linux: sudo apt install python3-tk).")
    if not have("flask"):
        print("NOTE: Flask isn't installed, so the built app will have no web mode. "
              "Run  pip install flask  and build again if you want it.")

    if not a.dry_run and not have("PyInstaller"):
        print("Installing PyInstaller …")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # ── command ──────────────────────────────────────────────────────────────
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
           "--name", a.name,
           "--onedir" if a.onedir else "--onefile",
           "--console" if a.console else "--windowed",
           "--distpath", str(HERE / "dist"),
           "--workpath", str(HERE / "build"),
           "--specpath", str(HERE / "build")]

    icon = Path(a.icon) if a.icon else HERE / "emlii.ico"
    if icon.is_file():
        cmd += ["--icon", str(icon)]

    # modules the code imports lazily / that PyInstaller can't see on its own
    hidden = ["EMLII", "sqlite3", "werkzeug.serving"] + STDLIB_EXTRAS
    reqs = requirements()
    if reqs and not a.dry_run:
        print("Installing plugin requirements …")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *[p for p, _ in reqs]])
    for _, names in reqs:
        hidden += names
    found = sorted(plugin_imports())
    missing = [m for m in found if m.split(".")[0] not in sys.stdlib_module_names and not have(m.split(".")[0])] \
        if hasattr(sys, "stdlib_module_names") else []
    for m in found:
        if m.split(".")[0] not in getattr(sys, "stdlib_module_names", ()) and have(m.split(".")[0]):
            cmd += ["--collect-submodules", m.split(".")[0]]     # third-party package used by a plugin
    hidden += found
    if found:
        print("Plugin imports found:", ", ".join(found))
    for m in missing:
        print(f"WARNING: plugins import '{m}' but it isn't installed — add it to plugins_requirements.txt")
    for m in dict.fromkeys(hidden):
        cmd += ["--hidden-import", m]
    if have("pyttsx3"):                      # spoken replies
        cmd += ["--collect-submodules", "pyttsx3"]
        if have("comtypes"):
            cmd += ["--hidden-import", "comtypes", "--hidden-import", "comtypes.client"]
    if have("vosk"):                         # offline voice input (ships native libraries)
        cmd += ["--collect-all", "vosk"]
    if have("sounddevice"):
        cmd += ["--collect-all", "sounddevice"]
    if have("PIL"):                          # wallpaper / image replies
        cmd += ["--hidden-import", "PIL.ImageTk"]
    for m in ("matplotlib", "scipy", "pandas", "IPython", "pytest", "notebook"):
        cmd += ["--exclude-module", m]       # keep the exe small

    cmd.append(str(HERE / "emlii_gui.py"))

    print("\n" + " ".join(f'"{c}"' if " " in c else c for c in cmd) + "\n")
    if a.dry_run:
        return
    subprocess.check_call(cmd, cwd=HERE)

    # ── tidy up: put plugins next to the app ─────────────────────────────────
    out = HERE / "dist" / (a.name if a.onedir else "")
    exe = out / (a.name + (".exe" if os.name == "nt" else ""))
    if (HERE / "tools").is_dir():
        shutil.copytree(HERE / "tools", out / "tools", dirs_exist_ok=True)
        print("Copied tools/ next to the app.")
    print(f"\nDone → {exe}")
    print("Copy any Vosk / .gguf model folders into a 'models' folder next to the app.")
    print("Your memory is stored in 'data' next to the app — back that folder up to keep what EMLII learned.")


if __name__ == "__main__":
    main()
