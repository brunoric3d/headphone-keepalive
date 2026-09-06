# Third party notices

Headphone Keep Alive itself is released under CC0 1.0, see [LICENSE](LICENSE).
That waiver covers only this project's own code. The libraries it uses keep
their own licenses, listed below.

| Library | License | Project page |
| --- | --- | --- |
| pystray | LGPL-3.0 | https://github.com/moses-palmer/pystray |
| sounddevice | MIT | https://github.com/spatialaudio/python-sounddevice |
| NumPy | BSD-3-Clause and others | https://github.com/numpy/numpy |
| Pillow | MIT-CMU | https://github.com/python-pillow/Pillow |
| PortAudio (through sounddevice) | MIT | https://www.portaudio.com |

## About pystray and the LGPL

The tray icon comes from pystray, which is licensed under the GNU Lesser
General Public License version 3. The released executables bundle it, so they
are what the LGPL calls a Combined Work, and that carries obligations.

This is how the project meets them.

- This notice states that pystray is used and is covered by the LGPL-3.0.
- The full texts are in [licenses/LGPL-3.0.txt](licenses/LGPL-3.0.txt) and
  [licenses/GPL-3.0.txt](licenses/GPL-3.0.txt). They also travel inside the
  executable itself: run it with `--licenses` and it writes this notice and both
  texts into a folder beside it.
- pystray is bundled unmodified, as ordinary Python bytecode, in its own
  `pystray/` folder inside the executable. Anyone can replace it with their own
  build of the library, so the right to relink is preserved in practice.
- The source of this application is public, at
  https://github.com/brunoric3d/headphone-keepalive, and the exact build steps
  are in [.github/workflows/release.yml](.github/workflows/release.yml).

If you would rather not deal with any of that, run the app from source. Then
pystray is just an installed dependency and no combined work is distributed.

## Rebuilding pystray inside a release

1. Download the archive for your system and extract it.
2. Clone this repository and install the dependencies with your own build of
   pystray, changed however you like.
3. Run the build script for your system: `build_windows.bat`,
   `build_macos.sh` or `build_linux.sh`.

The result is the same application running against your version of the library.
