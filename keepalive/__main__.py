"""Entry point. Runs in the system tray, or headless with --headless."""

from __future__ import annotations

import argparse
import sys
import time

from . import APP_NAME, VERSION


LICENCE_FILES = ["THIRD-PARTY-NOTICES.md", "LGPL-3.0.txt", "GPL-3.0.txt"]


def _write_licenses() -> int:
    """Extrai os textos de licenca que viajam dentro do executavel.

    A pystray e LGPL-3.0, e a licenca exige que uma copia dela acompanhe o
    programa distribuido. Como o download e um arquivo so, os textos vao
    embutidos e saem por aqui.
    """
    from pathlib import Path

    from .resources import bundled_path

    target = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path.cwd()
    target = target / "HeadphoneKeepAlive-licenses"

    written = []
    for name in LICENCE_FILES:
        source = bundled_path("licenses", name)
        if source is None:
            continue
        target.mkdir(parents=True, exist_ok=True)
        destination = target / name
        destination.write_bytes(source.read_bytes())
        written.append(destination)

    if not written:
        print("licence texts are not bundled in this build")
        print("they are in the repository: https://github.com/brunoric3d/headphone-keepalive")
        return 1

    print(f"wrote {len(written)} files to {target}")
    for path in written:
        print(f"  {path.name}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="keepalive", description=APP_NAME)
    parser.add_argument("--headless", action="store_true", help="run without the tray icon")
    parser.add_argument("--list-devices", action="store_true", help="list audio outputs and exit")
    parser.add_argument("--all-apis", action="store_true", help="with --list-devices, show every audio API")
    parser.add_argument("--list-languages", action="store_true", help="list available interface languages and exit")
    parser.add_argument("--system-volume", action="store_true", help="show what the app reads from the system volume and exit")
    parser.add_argument("--licenses", action="store_true", help="write the third party licence texts next to this program and exit")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {VERSION}")
    args = parser.parse_args(argv)

    if args.system_volume:
        from . import syslevel

        result = syslevel.query()
        if result is None:
            print("could not read the system volume on this platform")
            print("the app will not compensate, which is the safe default")
            return 1
        attenuation, scalar, muted = result
        print(f"attenuation : {attenuation:+.1f} dB   (0 dB means the slider is at maximum)")
        print(f"slider      : {scalar * 100:.0f} %" if scalar is not None else "slider      : unknown")
        print(f"muted       : {muted}")
        print()
        print("with the default -54 dBFS preset the app would play at "
              f"{min(-54.0 - attenuation, -30.0):.0f} dBFS")
        return 0

    if args.licenses:
        return _write_licenses()

    if args.list_languages:
        from . import i18n

        detected = i18n.detect()
        for code, name in i18n.available():
            mark = "  (detected)" if code == detected else ""
            print(f"{code}  {name}{mark}")
        return 0

    if args.list_devices:
        from .audio import default_output_name, list_output_devices

        default = (default_output_name() or "").lower()
        devices = list_output_devices(all_apis=args.all_apis)
        for dev in devices:
            mark = "  (default)" if dev["name"].lower() == default else ""
            print(f"[{dev['index']:3d}] {dev['name']}  [{dev['hostapi']}]{mark}")
        if not args.all_apis:
            hidden = len(list_output_devices(all_apis=True)) - len(devices)
            if hidden > 0:
                print(f"\n{hidden} more outputs from other audio APIs. Use --all-apis to see them.")
        return 0

    if args.headless:
        from .audio import AudioEngine
        from .config import Config

        config = Config()
        engine = AudioEngine(config)
        engine.start()
        print(f"{APP_NAME}: {engine.status_text}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        engine.shutdown()
        return 0

    from .tray import TrayApp

    TrayApp().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
