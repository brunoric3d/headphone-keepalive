#!/usr/bin/env bash
# Builds dist/HeadphoneKeepAlive.app
set -e
python3 -m pip install --upgrade -r requirements-build.txt
python3 tools/make_icons.py
python3 tools/make_audio.py
python3 -m PyInstaller --noconfirm --clean \
  --name HeadphoneKeepAlive \
  --windowed \
  --icon assets/icon.icns \
  --osx-bundle-identifier com.brunoric3d.headphonekeepalive \
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
  --collect-all sounddevice \
  --collect-all pystray \
  --collect-all PIL \
  run.py
echo
echo "Done: dist/HeadphoneKeepAlive.app"
echo "If macOS blocks it: xattr -dr com.apple.quarantine dist/HeadphoneKeepAlive.app"
