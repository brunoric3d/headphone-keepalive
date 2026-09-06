@echo off
REM Builds dist\HeadphoneKeepAlive.exe with no console window.
python -m pip install --upgrade -r requirements-build.txt || exit /b 1
python tools\make_icons.py || exit /b 1
python tools\make_audio.py || exit /b 1
python -m PyInstaller --noconfirm --clean ^
  --name HeadphoneKeepAlive ^
  --onefile ^
  --windowed ^
  --icon assets\icon.ico ^
  --add-data "assets/tray-mask.png:assets" ^
  --add-data "assets/noise-pink.s16:assets" ^
  --add-data "assets/noise-brown.s16:assets" ^
  --add-data "THIRD-PARTY-NOTICES.md:licenses" ^
  --add-data "licenses/LGPL-3.0.txt:licenses" ^
  --add-data "licenses/GPL-3.0.txt:licenses" ^
  --exclude-module numpy ^
  --exclude-module tkinter ^
  --exclude-module unittest ^
  --exclude-module pydoc ^
  --exclude-module doctest ^
  --exclude-module ssl ^
  --exclude-module _ssl ^
  --exclude-module hashlib ^
  --exclude-module _hashlib ^
  --exclude-module dbm ^
  --exclude-module _dbm ^
  --exclude-module _gdbm ^
  --exclude-module bz2 ^
  --exclude-module PIL._avif ^
  --exclude-module PIL._webp ^
  --exclude-module PIL._imagingcms ^
  --exclude-module PIL._imagingft ^
  --exclude-module PIL._imagingtk ^
  --exclude-module PIL.ImageQt ^
  --collect-all sounddevice ^
  --collect-all pystray ^
  --collect-all PIL ^
  run.py
echo.
echo Done: dist\HeadphoneKeepAlive.exe
