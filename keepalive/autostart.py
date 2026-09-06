"""Iniciar junto com o sistema, em Windows, macOS e Linux."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from . import APP_ID, APP_NAME

LAUNCH_LABEL = "com.brunoric3d.headphonekeepalive"


def _frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _command() -> list:
    """Comando que reabre o app, seja empacotado ou rodando pelo Python."""
    if _frozen():
        return [sys.executable]
    runner = Path(__file__).resolve().parent.parent / "run.py"
    if runner.exists():
        return [sys.executable, str(runner)]
    return [sys.executable, "-m", "keepalive"]


def _command_string() -> str:
    parts = _command()
    return " ".join(f'"{p}"' if " " in p else p for p in parts)


# ---------------------------------------------------------------- windows

def _win_key():
    import winreg

    return winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_ALL_ACCESS,
    )


def _win_enabled() -> bool:
    import winreg

    try:
        with _win_key() as key:
            winreg.QueryValueEx(key, APP_NAME)
        return True
    except OSError:
        return False


def _win_set(enabled: bool) -> None:
    import winreg

    with _win_key() as key:
        if enabled:
            cmd = _command_string()
            if not _frozen():
                # pythonw evita abrir janela de console no boot
                cmd = cmd.replace("python.exe", "pythonw.exe")
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except OSError:
                pass


# ---------------------------------------------------------------- macos

def _mac_plist() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LAUNCH_LABEL}.plist"


def _mac_enabled() -> bool:
    return _mac_plist().exists()


def _mac_set(enabled: bool) -> None:
    path = _mac_plist()
    if not enabled:
        if path.exists():
            subprocess.run(["launchctl", "unload", str(path)], capture_output=True)
            path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    args = "".join(f"        <string>{part}</string>\n" for part in _command())
    plist = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n'
        "<dict>\n"
        "    <key>Label</key>\n"
        f"    <string>{LAUNCH_LABEL}</string>\n"
        "    <key>ProgramArguments</key>\n"
        "    <array>\n"
        f"{args}"
        "    </array>\n"
        "    <key>RunAtLoad</key>\n"
        "    <true/>\n"
        "    <key>KeepAlive</key>\n"
        "    <false/>\n"
        "</dict>\n"
        "</plist>\n"
    )
    path.write_text(plist, encoding="utf-8")
    subprocess.run(["launchctl", "load", str(path)], capture_output=True)


# ---------------------------------------------------------------- linux

def _linux_desktop() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "autostart" / f"{APP_ID}.desktop"


def _linux_enabled() -> bool:
    return _linux_desktop().exists()


def _linux_set(enabled: bool) -> None:
    path = _linux_desktop()
    if not enabled:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        f"Exec={_command_string()}\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------- api

def is_enabled() -> bool:
    try:
        if sys.platform == "win32":
            return _win_enabled()
        if sys.platform == "darwin":
            return _mac_enabled()
        return _linux_enabled()
    except Exception:
        return False


def set_enabled(enabled: bool) -> bool:
    """Devolve o estado real depois da tentativa."""
    try:
        if sys.platform == "win32":
            _win_set(enabled)
        elif sys.platform == "darwin":
            _mac_set(enabled)
        else:
            _linux_set(enabled)
    except Exception:
        pass
    return is_enabled()
