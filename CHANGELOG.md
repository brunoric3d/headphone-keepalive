# Changelog

## 1.1.0

A low system volume used to drag the keepalive down with it until the
headphones read it as silence. That is fixed, and the audio no longer has a gap
every time the stream reopens.

**Compensation for the system volume**

- The signal now holds its level at the headphones no matter where the system
  volume sits. Capped at -24 dBFS, which keeps it exact down to a system volume
  of about 12 percent
- Some Windows endpoints report a fake dB range, answering with a number near
  zero no matter where the slider sits. The attenuation is now derived from the
  volume scalar whenever the reported dB disagrees with it
- The system volume is read every second on Windows, which shortens the window
  where the signal is louder than intended after the volume goes back up
- New menu entry to turn the compensation off, and `--system-volume` on the
  command line to see exactly what the app reads

**Audio and size**

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
