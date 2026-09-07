<p align="center">
  <img src="assets/keepalive_logo.png" width="140" alt="Headphone Keep Alive">
</p>

<h1 align="center">Headphone Keep Alive</h1>

<p align="center">
  A tiny tray app that plays a near silent sound so headphones that power off on their own stay awake.<br>
  Windows, macOS and Linux, same code.
</p>

<p align="center">
  <a href="https://github.com/brunoric3d/headphone-keepalive/releases/latest">Download</a> ·
  <a href="README.pt-BR.md">Português</a>
</p>

---

Many bluetooth headphones shut down after a few minutes without audio. If you work in silence and only listen now and then, they keep dying on you. This app keeps a continuous, inaudible signal on the output so the headphones always think something is playing.

## Install

Grab the file for your system from the [latest release](https://github.com/brunoric3d/headphone-keepalive/releases/latest).

| System | File | Notes |
| --- | --- | --- |
| Windows | `HeadphoneKeepAlive-windows-x64.exe` | Just run it. SmartScreen may warn about an unknown publisher: click "More info" then "Run anyway". |
| macOS Apple Silicon | `HeadphoneKeepAlive-macos-arm64.zip` | Unzip into Applications. First run: `xattr -dr com.apple.quarantine HeadphoneKeepAlive.app` |
| macOS Intel | `HeadphoneKeepAlive-macos-x64.zip` | Same as above. |
| Linux | `HeadphoneKeepAlive-linux-x64` | `chmod +x` it and run. Needs a tray host. See the Linux notes below. |

Every download is a single file. macOS is the exception: an `.app` is a folder,
so it has to travel as a zip.

The builds are not code signed, so both Windows and macOS will ask before running them. That is expected for an open source project without a paid certificate.

## Run from source

Python 3.10 or newer. Dependency versions are pinned in `requirements.txt`.

```bash
pip install -r requirements.txt
python run.py
```

On Linux you may also need PortAudio and the tray support:

```bash
# Debian, Ubuntu, Mint
sudo apt install libportaudio2 gir1.2-ayatanaappindicator3-0.1 python3-gi

# Fedora
sudo dnf install portaudio libayatana-appindicator-gtk3 python3-gobject
```

On GNOME you may need the AppIndicator Support extension for the icon to show up.

## Using it

The tray icon is violet while the sound is playing, gray when stopped and red when no audio output was found.

**Sound**

| Option | When to use |
| --- | --- |
| Pink noise | The default. Energy spread across the whole spectrum, so it survives any bluetooth codec |
| Brown noise | Deeper and duller. Use it if pink noise bothers you in a very quiet room |
| Low tone 20 Hz | Inaudible to almost everyone, but many headphones roll off that low and sleep anyway |
| High tone 19 kHz | Inaudible to most adults, but some bluetooth codecs cut above 16 kHz |
| Short pulse | A very quiet click every few seconds. Easier on the battery, but only works if your headphones wait longer than the interval |

Start with pink noise. The pure tones are only worth it if you want absolute silence and your headphones accept them.

**Volume** goes from -66 dBFS to -30 dBFS. The default is -54 dBFS, which is inaudible at normal listening levels and still far above digital silence. If your headphones keep shutting off, move up one step at a time.

**Compensate low system volume** keeps the signal at the same level at the
headphones no matter where the system volume sits. The app reads how much the
system is attenuating the output and raises the digital level by the same
amount, so a system at 10 percent no longer turns the keepalive into something
the headphones read as silence. The compensated level is capped at -30 dBFS,
which is exactly the app's own loudest preset, so compensating can never make it
louder than a level you could already pick by hand. Past that cap the menu shows
`(max)` and the signal is quieter than intended. When the system volume cannot
be read, the app does not compensate at all.

**Audio output** lets you follow the system default or pin one device. Windows exposes the same headphones once per audio API (MME, DirectSound, WASAPI, WDM-KS), so the raw device list is full of duplicates, and MME even truncates names at 31 characters. The app shows only the preferred API for each system, WASAPI on Windows, Core Audio on macOS, PulseAudio or PipeWire on Linux, and drops repeated names inside the same API. Turn on "Show all audio APIs" if you want to force a specific path.

**Follow system default output** moves the sound to whatever the system is using now. On Windows the app asks the system how many outputs exist, which costs nothing and does not touch the audio, and only reconnects when a device actually appears or disappears. On macOS and Linux there is no equally cheap signal, so it falls back to a check every 60 seconds. Either way the stream is reopened only when something really changed. Turn it off if you pinned a device.

**Start with the system** writes the startup entry in the right place for each system.

- Windows: the `Run` key under `HKEY_CURRENT_USER`
- macOS: a LaunchAgent in `~/Library/LaunchAgents`
- Linux: a `.desktop` file in `~/.config/autostart`

**Language** follows the operating system and falls back to English. You can override it in the menu. Available: English, Português, Español, Deutsch, Français, Italiano, 中文, 日本語, Русский.

## Command line

```bash
python run.py --list-devices     # audio outputs, deduplicated
python run.py --list-devices --all-apis
python run.py --list-languages
python run.py --system-volume    # show what the app reads from the system volume
python run.py --licenses         # write the third party licence texts to disk
python run.py --headless         # no tray icon, useful for testing
python run.py --version
```

## Settings

- Windows: `%APPDATA%\headphone-keepalive\config.json`
- macOS: `~/Library/Application Support/headphone-keepalive/config.json`
- Linux: `~/.config/headphone-keepalive/config.json`

## How it works

The noise is rendered at build time by `tools/make_audio.py`, which uses NumPy to shape a spectrum over an FFT, cuts everything below 30 Hz, and crossfades 50 ms of the tail over the head so the loop closes without a click. The result ships as raw 16 bit PCM in `assets/`. NumPy is a build dependency only, which is what keeps the executable at around 12 MB instead of 36 MB. Tones are cheap enough to generate at startup, at the real sample rate of the device, using a buffer of exactly one second at an integer frequency so the loop closes in phase.

At runtime the app builds one buffer with the volume applied and the channels interleaved, and the audio callback does nothing but copy bytes out of it. Nothing is computed or allocated in the realtime path. Changing the sound, the volume or the pulse interval swaps that buffer in place, so those settings take effect without touching the stream and without a single dropout.

A watchdog checks the stream every 5 seconds and reopens it if it died, because the headphones dropped or the driver killed it. Reopening no longer rebuilds the buffer, so the silence it costs went from about 400 ms to under 10 ms. Sample rate and channel count are negotiated with the driver, falling back through 44100, 32000 and 22050 if needed. The noise files are rendered at 48 kHz; playing them at another rate shifts the spectrum slightly, which for noise makes no audible difference.

## Building it yourself

The build scripts install what they need, including PyInstaller, from
`requirements-build.txt`. Run them from the project folder.

```bash
# Windows
build_windows.bat

# macOS
bash build_macos.sh

# Linux
bash build_linux.sh
```

To install the build tools by hand instead:

```bash
pip install -r requirements-build.txt
```

PyInstaller is deliberately kept out of `requirements.txt`, so that people who
only want to run the app do not have to download a build toolchain.

Output lands in `dist`. Releases are built by GitHub Actions on every `v*` tag, across four runners, and attached to a draft release.

## Troubleshooting

**Headphones still shut off.** Move the volume up one step and switch back to pink noise if you were on a pure tone. Some models only measure energy in a specific band.

**I can hear a faint hiss.** Move the volume down one step, or switch to brown noise, which is less noticeable.

**The icon is red.** No audio output was found. Open "Audio output" and click "Refresh list".

**The sound does not follow the headphones I just connected.** Make sure "Follow system default output" is checked, or pin the device directly.

## Translations

Nine languages ship with the app, in `keepalive/i18n.py`. Adding one means adding a dictionary with the same 31 keys. Corrections to the existing ones are welcome, especially for languages the author does not speak.

## License

CC0 1.0 Universal. The author waives copyright and related rights in this work
worldwide, to the extent the law allows. Do whatever you want with it, no credit
needed. See [LICENSE](LICENSE).

That waiver covers this project's own code only. The libraries it depends on keep
their own licenses, and pystray in particular is LGPL-3.0, which puts conditions
on the prebuilt executables. See [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

The notice and the full LGPL and GPL texts travel inside the executable, so they
reach anyone who downloads it. Run it with `--licenses` and it writes them into a
folder beside itself.
