#!/usr/bin/env bash
# Builds a single binary in dist/HeadphoneKeepAlive
set -e
python3 -m pip install --upgrade -r requirements-build.txt
python3 tools/make_icons.py
python3 tools/make_audio.py

EXTRA=()
PORTAUDIO=$(ldconfig -p 2>/dev/null | grep -m1 'libportaudio\.so\.2' | awk '{print $NF}' || true)
if [ -n "$PORTAUDIO" ]; then
  echo "bundling $PORTAUDIO"
  EXTRA+=(--add-binary "$PORTAUDIO:.")
else
  echo "libportaudio not found, the binary will need it installed on the target machine"
fi

python3 -m PyInstaller --noconfirm --clean \
  --name HeadphoneKeepAlive \
  --onefile \
  --add-data "assets/tray-mask.png:assets" \
  --add-data "assets/noise-pink.s16:assets" \
  --add-data "assets/noise-brown.s16:assets" \
  --add-data "THIRD-PARTY-NOTICES.md:licenses" \
  --add-data "licenses/LGPL-3.0.txt:licenses" \
  --add-data "licenses/GPL-3.0.txt:licenses" \
  --exclude-module numpy \
  --exclude-module tkinter \
  --exclude-module unittest \
  --exclude-module pydoc \
  --exclude-module doctest \
  --exclude-module ssl \
  --exclude-module _ssl \
  --exclude-module hashlib \
  --exclude-module _hashlib \
  --exclude-module dbm \
  --exclude-module _dbm \
  --exclude-module _gdbm \
  --exclude-module bz2 \
  --exclude-module PIL._avif \
  --exclude-module PIL._webp \
  --exclude-module PIL._imagingcms \
  --exclude-module PIL._imagingft \
  --exclude-module PIL._imagingtk \
  --exclude-module PIL.ImageQt \
  "${EXTRA[@]}" \
  --collect-all sounddevice \
  --collect-all pystray \
  --collect-all PIL \
  run.py
echo
echo "Done: dist/HeadphoneKeepAlive"
