"""Icone e menu da bandeja."""

from __future__ import annotations

from typing import List

import pystray
from pystray import Menu, MenuItem

from . import APP_NAME, VERSION, autostart, config as cfg, i18n, icon as icon_art
from .audio import AudioEngine, list_output_devices


class TrayApp:
    def __init__(self) -> None:
        self.config = cfg.Config()
        self.t = i18n.Translator(self.config.get("language"))
        self.engine = AudioEngine(self.config, on_state_change=self._refresh)
        self._devices: List = []
        self.icon = pystray.Icon(
            "headphone-keepalive",
            icon_art.make_icon("off"),
            APP_NAME,
            menu=self._build_menu(),
        )

    # ---------------------------------------------------------------- textos

    def _sound_label(self) -> str:
        current = self.config.get("sound")
        for key, text_key in cfg.SOUND_LABELS:
            if key == current:
                return self.t(text_key)
        return str(current)

    def _level_label(self) -> str:
        current = float(self.config.get("level_db"))
        for text_key, value in cfg.LEVEL_PRESETS:
            if abs(value - current) < 0.01:
                return f"{self.t(text_key)} ({value:.0f} dB)"
        return f"{current:.0f} dB"

    def _status_line(self) -> str:
        state, detail = self.engine.status
        if state == "playing" and self.engine.running:
            return self.t("status_playing", device=self.engine.active_device or self.t("default_output"))
        if state == "error":
            return self.t("status_error", error=detail)
        return self.t("status_stopped")

    # ---------------------------------------------------------------- estado

    def _refresh(self) -> None:
        try:
            if self.engine.running:
                state = "on"
            elif self.config.get("enabled"):
                state = "error"
            else:
                state = "off"
            self.icon.icon = icon_art.make_icon(state)
            self.icon.title = f"{APP_NAME} - {self._status_line()}"
            self.icon.update_menu()
        except Exception:
            pass

    def _rebuild(self) -> None:
        try:
            self.icon.menu = self._build_menu()
        except Exception:
            pass
        self._refresh()

    def _notify(self, message: str) -> None:
        try:
            self.icon.notify(message, APP_NAME)
        except Exception:
            pass

    # ---------------------------------------------------------------- acoes

    def _toggle(self, _icon=None, _item=None) -> None:
        enabled = not bool(self.config.get("enabled"))
        self.config.set("enabled", enabled)
        if enabled:
            self.engine.start()
        else:
            self.engine.stop()
        self._refresh()

    def _set_sound(self, key: str):
        def action(_icon=None, _item=None) -> None:
            self.config.set("sound", key)
            self.engine.apply_settings()
            self._refresh()

        return action

    def _set_level(self, value: float):
        def action(_icon=None, _item=None) -> None:
            self.engine.set_level_db(value)
            self._refresh()

        return action

    def _set_pulse(self, seconds: float):
        def action(_icon=None, _item=None) -> None:
            self.config.set("pulse_interval", seconds)
            self.engine.apply_settings()
            self._refresh()

        return action

    def _set_device(self, name, hostapi=None):
        def action(_icon=None, _item=None) -> None:
            self.config.set("device", name)
            self.config.set("device_hostapi", hostapi)
            self.engine.restart()
            self._rebuild()

        return action

    def _set_language(self, choice: str):
        def action(_icon=None, _item=None) -> None:
            self.config.set("language", choice)
            self.t.set(choice)
            self._rebuild()

        return action

    def _rescan(self, _icon=None, _item=None) -> None:
        self.engine.rescan()
        self._rebuild()

    def _toggle_all_apis(self, _icon=None, _item=None) -> None:
        self.config.set("show_all_apis", not bool(self.config.get("show_all_apis")))
        self._rebuild()

    def _toggle_follow(self, _icon=None, _item=None) -> None:
        self.config.set("follow_default", not bool(self.config.get("follow_default")))
        self._refresh()

    def _toggle_autostart(self, _icon=None, _item=None) -> None:
        wanted = not bool(autostart.is_enabled())
        real = autostart.set_enabled(wanted)
        self.config.set("autostart", real)
        if real != wanted:
            self._notify(self.t("notify_autostart_failed"))
        self._refresh()

    def _quit(self, _icon=None, _item=None) -> None:
        self.engine.shutdown()
        self.icon.stop()

    # ---------------------------------------------------------------- menu

    def _device_menu(self) -> Menu:
        show_all = bool(self.config.get("show_all_apis"))
        self._devices = list_output_devices(all_apis=show_all)
        items = [
            MenuItem(
                self.t("menu_default_device"),
                self._set_device(None),
                checked=lambda item: not self.config.get("device"),
                radio=True,
            ),
            Menu.SEPARATOR,
        ]
        for dev in self._devices:
            name = dev["name"]
            label = name if len(name) <= 42 else name[:39] + "..."
            if show_all:
                label = f"{label}  [{dev['hostapi']}]"
            items.append(
                MenuItem(
                    label,
                    self._set_device(name, dev["hostapi"]),
                    checked=(
                        lambda n, a: lambda item: (
                            self.config.get("device") == n
                            and (not show_all or self.config.get("device_hostapi") == a)
                        )
                    )(name, dev["hostapi"]),
                    radio=True,
                )
            )
        items.append(Menu.SEPARATOR)
        items.append(
            MenuItem(
                self.t("menu_show_all_apis"),
                self._toggle_all_apis,
                checked=lambda item: bool(self.config.get("show_all_apis")),
            )
        )
        items.append(MenuItem(self.t("menu_refresh"), self._rescan))
        return Menu(*items)

    def _language_menu(self) -> Menu:
        items = [
            MenuItem(
                self.t("lang_auto", name=i18n.LANGUAGE_NAMES.get(self.t.detected, self.t.detected)),
                self._set_language("auto"),
                checked=lambda item: self.config.get("language") in (None, "auto"),
                radio=True,
            ),
            Menu.SEPARATOR,
        ]
        for code, name in i18n.available():
            items.append(
                MenuItem(
                    name,
                    self._set_language(code),
                    checked=(lambda c: lambda item: self.config.get("language") == c)(code),
                    radio=True,
                )
            )
        return Menu(*items)

    def _build_menu(self) -> Menu:
        sound_items = [
            MenuItem(
                self.t(text_key),
                self._set_sound(key),
                checked=(lambda k: lambda item: self.config.get("sound") == k)(key),
                radio=True,
            )
            for key, text_key in cfg.SOUND_LABELS
        ]

        level_items = [
            MenuItem(
                f"{self.t(text_key)} ({value:.0f} dB)",
                self._set_level(value),
                checked=(lambda v: lambda item: abs(float(self.config.get("level_db")) - v) < 0.01)(value),
                radio=True,
            )
            for text_key, value in cfg.LEVEL_PRESETS
        ]

        pulse_items = [
            MenuItem(
                self.t("menu_seconds", n=int(seconds)),
                self._set_pulse(seconds),
                checked=(lambda s: lambda item: abs(float(self.config.get("pulse_interval")) - s) < 0.01)(seconds),
                radio=True,
            )
            for seconds in cfg.PULSE_INTERVALS
        ]

        return Menu(
            MenuItem(lambda item: self._status_line(), None, enabled=False),
            Menu.SEPARATOR,
            MenuItem(
                self.t("menu_active"),
                self._toggle,
                checked=lambda item: bool(self.config.get("enabled")),
                default=True,
            ),
            Menu.SEPARATOR,
            MenuItem(lambda item: self.t("menu_sound", name=self._sound_label()), Menu(*sound_items)),
            MenuItem(lambda item: self.t("menu_volume", name=self._level_label()), Menu(*level_items)),
            MenuItem(self.t("menu_pulse"), Menu(*pulse_items)),
            MenuItem(self.t("menu_output"), self._device_menu()),
            Menu.SEPARATOR,
            MenuItem(
                self.t("menu_follow_default"),
                self._toggle_follow,
                checked=lambda item: bool(self.config.get("follow_default")),
            ),
            MenuItem(
                self.t("menu_autostart"),
                self._toggle_autostart,
                checked=lambda item: autostart.is_enabled(),
            ),
            MenuItem(self.t("menu_language"), self._language_menu()),
            Menu.SEPARATOR,
            MenuItem(self.t("menu_version", version=VERSION), None, enabled=False),
            MenuItem(self.t("menu_quit"), self._quit),
        )

    # ---------------------------------------------------------------- run

    def run(self) -> None:
        def setup(icon) -> None:
            icon.visible = True
            if self.config.get("enabled"):
                self.engine.start()
            self._refresh()

        self.icon.run(setup=setup)
