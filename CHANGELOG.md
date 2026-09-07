# Changelog

## Unreleased

- The signal now compensates for the system volume. A low system volume used to
  drag the keepalive down with it until the headphones read it as silence. The
  compensated level is capped at the app's own loudest preset

- Noise is rendered at build time and shipped as raw PCM, so NumPy is no longer
  a runtime dependency. The Linux executable went from 36.3 MB to 12.6 MB
- Reopening the audio stream no longer rebuilds the buffer, which removed a
  gap of about 400 ms that happened every 30 seconds
- Sound, volume and pulse interval now change with the stream running, with no
  interruption at all
- On Windows the app detects new or removed outputs by asking the system,
  instead of tearing the stream down on a timer

## 1.0.0

First public release.

- Tray app that plays a near silent signal so auto-off headphones stay awake
- Five signal types: pink noise, brown noise, 20 Hz tone, 19 kHz tone, short pulse
- Six volume steps from -66 dBFS to -30 dBFS, default -54 dBFS
- Output picker that hides the duplicates Windows creates for every audio API
- Follows the system default output, so the sound moves when headphones reconnect
- Watchdog that reopens the stream when the device drops
- Start with the system on Windows, macOS and Linux
- Interface in 9 languages, detected from the operating system
- Settings saved to disk
