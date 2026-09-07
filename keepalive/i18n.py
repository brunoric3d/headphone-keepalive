"""Textos da interface em varios idiomas, com deteccao do idioma do sistema.

Nao usamos gettext de proposito: sao poucas strings e assim o app continua
sendo um pacote Python puro, sem arquivos .mo para empacotar.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

FALLBACK = "en"

LANGUAGE_NAMES = {
    "en": "English",
    "pt": "Português",
    "es": "Español",
    "de": "Deutsch",
    "fr": "Français",
    "it": "Italiano",
    "zh": "中文",
    "ja": "日本語",
    "ru": "Русский",
}

STRINGS: Dict[str, Dict[str, str]] = {
    "en": {
        "status_stopped": "Stopped",
        "status_playing": "Playing on {device}",
        "status_error": "Error: no audio output ({error})",
        "default_output": "default output",
        "menu_active": "Active",
        "menu_sound": "Sound: {name}",
        "menu_volume": "Volume: {name}",
        "menu_pulse": "Pulse interval",
        "menu_seconds": "{n} seconds",
        "menu_output": "Audio output",
        "menu_default_device": "System default",
        "menu_show_all_apis": "Show all audio APIs",
        "menu_refresh": "Refresh list",
        "menu_follow_default": "Follow system default output",
        "menu_compensate": "Compensate low system volume",
        "menu_autostart": "Start with the system",
        "menu_language": "Language",
        "lang_auto": "Automatic ({name})",
        "menu_version": "Version {version}",
        "menu_quit": "Quit",
        "notify_autostart_failed": "Could not change the startup setting.",
        "sound_pink": "Pink noise (recommended)",
        "sound_brown": "Brown noise (deeper)",
        "sound_tone_low": "Low tone 20 Hz",
        "sound_tone_high": "High tone 19 kHz",
        "sound_pulse": "Short pulse",
        "level_min": "Minimum",
        "level_very_low": "Very low",
        "level_low": "Low",
        "level_medium": "Medium",
        "level_high": "High",
        "level_very_high": "Very high",
    },
    "pt": {
        "status_stopped": "Parado",
        "status_playing": "Tocando em {device}",
        "status_error": "Erro: sem saída de áudio ({error})",
        "default_output": "saída padrão",
        "menu_active": "Ativo",
        "menu_sound": "Som: {name}",
        "menu_volume": "Volume: {name}",
        "menu_pulse": "Intervalo do pulso",
        "menu_seconds": "{n} segundos",
        "menu_output": "Saída de áudio",
        "menu_default_device": "Padrão do sistema",
        "menu_show_all_apis": "Mostrar todas as APIs de áudio",
        "menu_refresh": "Atualizar lista",
        "menu_follow_default": "Seguir a saída padrão do sistema",
        "menu_compensate": "Compensar volume baixo do sistema",
        "menu_autostart": "Iniciar com o sistema",
        "menu_language": "Idioma",
        "lang_auto": "Automático ({name})",
        "menu_version": "Versão {version}",
        "menu_quit": "Sair",
        "notify_autostart_failed": "Não consegui mudar o início automático.",
        "sound_pink": "Ruído rosa (recomendado)",
        "sound_brown": "Ruído marrom (mais grave)",
        "sound_tone_low": "Tom grave 20 Hz",
        "sound_tone_high": "Tom agudo 19 kHz",
        "sound_pulse": "Pulso curto",
        "level_min": "Mínimo",
        "level_very_low": "Muito baixo",
        "level_low": "Baixo",
        "level_medium": "Médio",
        "level_high": "Alto",
        "level_very_high": "Muito alto",
    },
    "es": {
        "status_stopped": "Detenido",
        "status_playing": "Reproduciendo en {device}",
        "status_error": "Error: sin salida de audio ({error})",
        "default_output": "salida predeterminada",
        "menu_active": "Activo",
        "menu_sound": "Sonido: {name}",
        "menu_volume": "Volumen: {name}",
        "menu_pulse": "Intervalo del pulso",
        "menu_seconds": "{n} segundos",
        "menu_output": "Salida de audio",
        "menu_default_device": "Predeterminado del sistema",
        "menu_show_all_apis": "Mostrar todas las API de audio",
        "menu_refresh": "Actualizar lista",
        "menu_follow_default": "Seguir la salida predeterminada del sistema",
        "menu_compensate": "Compensar volumen bajo del sistema",
        "menu_autostart": "Iniciar con el sistema",
        "menu_language": "Idioma",
        "lang_auto": "Automático ({name})",
        "menu_version": "Versión {version}",
        "menu_quit": "Salir",
        "notify_autostart_failed": "No se pudo cambiar el inicio automático.",
        "sound_pink": "Ruido rosa (recomendado)",
        "sound_brown": "Ruido marrón (más grave)",
        "sound_tone_low": "Tono grave 20 Hz",
        "sound_tone_high": "Tono agudo 19 kHz",
        "sound_pulse": "Pulso corto",
        "level_min": "Mínimo",
        "level_very_low": "Muy bajo",
        "level_low": "Bajo",
        "level_medium": "Medio",
        "level_high": "Alto",
        "level_very_high": "Muy alto",
    },
    "de": {
        "status_stopped": "Gestoppt",
        "status_playing": "Wiedergabe auf {device}",
        "status_error": "Fehler: keine Audioausgabe ({error})",
        "default_output": "Standardausgabe",
        "menu_active": "Aktiv",
        "menu_sound": "Klang: {name}",
        "menu_volume": "Lautstärke: {name}",
        "menu_pulse": "Pulsintervall",
        "menu_seconds": "{n} Sekunden",
        "menu_output": "Audioausgabe",
        "menu_default_device": "Systemstandard",
        "menu_show_all_apis": "Alle Audio-APIs anzeigen",
        "menu_refresh": "Liste aktualisieren",
        "menu_follow_default": "Standardausgabe des Systems folgen",
        "menu_compensate": "Niedrige Systemlautstärke ausgleichen",
        "menu_autostart": "Mit dem System starten",
        "menu_language": "Sprache",
        "lang_auto": "Automatisch ({name})",
        "menu_version": "Version {version}",
        "menu_quit": "Beenden",
        "notify_autostart_failed": "Autostart konnte nicht geändert werden.",
        "sound_pink": "Rosa Rauschen (empfohlen)",
        "sound_brown": "Braunes Rauschen (tiefer)",
        "sound_tone_low": "Tiefer Ton 20 Hz",
        "sound_tone_high": "Hoher Ton 19 kHz",
        "sound_pulse": "Kurzer Impuls",
        "level_min": "Minimum",
        "level_very_low": "Sehr leise",
        "level_low": "Leise",
        "level_medium": "Mittel",
        "level_high": "Laut",
        "level_very_high": "Sehr laut",
    },
    "fr": {
        "status_stopped": "Arrêté",
        "status_playing": "Lecture sur {device}",
        "status_error": "Erreur : aucune sortie audio ({error})",
        "default_output": "sortie par défaut",
        "menu_active": "Actif",
        "menu_sound": "Son : {name}",
        "menu_volume": "Volume : {name}",
        "menu_pulse": "Intervalle d'impulsion",
        "menu_seconds": "{n} secondes",
        "menu_output": "Sortie audio",
        "menu_default_device": "Par défaut du système",
        "menu_show_all_apis": "Afficher toutes les API audio",
        "menu_refresh": "Actualiser la liste",
        "menu_follow_default": "Suivre la sortie par défaut du système",
        "menu_compensate": "Compenser un volume système faible",
        "menu_autostart": "Démarrer avec le système",
        "menu_language": "Langue",
        "lang_auto": "Automatique ({name})",
        "menu_version": "Version {version}",
        "menu_quit": "Quitter",
        "notify_autostart_failed": "Impossible de modifier le démarrage automatique.",
        "sound_pink": "Bruit rose (recommandé)",
        "sound_brown": "Bruit brun (plus grave)",
        "sound_tone_low": "Son grave 20 Hz",
        "sound_tone_high": "Son aigu 19 kHz",
        "sound_pulse": "Impulsion courte",
        "level_min": "Minimum",
        "level_very_low": "Très faible",
        "level_low": "Faible",
        "level_medium": "Moyen",
        "level_high": "Fort",
        "level_very_high": "Très fort",
    },
    "it": {
        "status_stopped": "Fermo",
        "status_playing": "In riproduzione su {device}",
        "status_error": "Errore: nessuna uscita audio ({error})",
        "default_output": "uscita predefinita",
        "menu_active": "Attivo",
        "menu_sound": "Suono: {name}",
        "menu_volume": "Volume: {name}",
        "menu_pulse": "Intervallo dell'impulso",
        "menu_seconds": "{n} secondi",
        "menu_output": "Uscita audio",
        "menu_default_device": "Predefinita di sistema",
        "menu_show_all_apis": "Mostra tutte le API audio",
        "menu_refresh": "Aggiorna elenco",
        "menu_follow_default": "Segui l'uscita predefinita del sistema",
        "menu_compensate": "Compensare il volume di sistema basso",
        "menu_autostart": "Avvia con il sistema",
        "menu_language": "Lingua",
        "lang_auto": "Automatico ({name})",
        "menu_version": "Versione {version}",
        "menu_quit": "Esci",
        "notify_autostart_failed": "Non è stato possibile cambiare l'avvio automatico.",
        "sound_pink": "Rumore rosa (consigliato)",
        "sound_brown": "Rumore marrone (più grave)",
        "sound_tone_low": "Tono grave 20 Hz",
        "sound_tone_high": "Tono acuto 19 kHz",
        "sound_pulse": "Impulso breve",
        "level_min": "Minimo",
        "level_very_low": "Molto basso",
        "level_low": "Basso",
        "level_medium": "Medio",
        "level_high": "Alto",
        "level_very_high": "Molto alto",
    },
    "zh": {
        "status_stopped": "已停止",
        "status_playing": "正在播放：{device}",
        "status_error": "错误：没有音频输出（{error}）",
        "default_output": "默认输出",
        "menu_active": "启用",
        "menu_sound": "声音：{name}",
        "menu_volume": "音量：{name}",
        "menu_pulse": "脉冲间隔",
        "menu_seconds": "{n} 秒",
        "menu_output": "音频输出",
        "menu_default_device": "系统默认",
        "menu_show_all_apis": "显示所有音频 API",
        "menu_refresh": "刷新列表",
        "menu_follow_default": "跟随系统默认输出",
        "menu_compensate": "补偿系统音量过低",
        "menu_autostart": "开机启动",
        "menu_language": "语言",
        "lang_auto": "自动（{name}）",
        "menu_version": "版本 {version}",
        "menu_quit": "退出",
        "notify_autostart_failed": "无法更改开机启动设置。",
        "sound_pink": "粉红噪声（推荐）",
        "sound_brown": "棕色噪声（更低沉）",
        "sound_tone_low": "低频音 20 Hz",
        "sound_tone_high": "高频音 19 kHz",
        "sound_pulse": "短脉冲",
        "level_min": "最低",
        "level_very_low": "很低",
        "level_low": "低",
        "level_medium": "中",
        "level_high": "高",
        "level_very_high": "很高",
    },
    "ja": {
        "status_stopped": "停止中",
        "status_playing": "{device} で再生中",
        "status_error": "エラー: 音声出力がありません ({error})",
        "default_output": "既定の出力",
        "menu_active": "有効",
        "menu_sound": "音: {name}",
        "menu_volume": "音量: {name}",
        "menu_pulse": "パルス間隔",
        "menu_seconds": "{n} 秒",
        "menu_output": "音声出力",
        "menu_default_device": "システムの既定",
        "menu_show_all_apis": "すべてのオーディオ API を表示",
        "menu_refresh": "一覧を更新",
        "menu_follow_default": "システムの既定の出力に追従",
        "menu_compensate": "システム音量が低いときに補正",
        "menu_autostart": "システム起動時に開始",
        "menu_language": "言語",
        "lang_auto": "自動 ({name})",
        "menu_version": "バージョン {version}",
        "menu_quit": "終了",
        "notify_autostart_failed": "自動起動の設定を変更できませんでした。",
        "sound_pink": "ピンクノイズ (推奨)",
        "sound_brown": "ブラウンノイズ (より低め)",
        "sound_tone_low": "低音 20 Hz",
        "sound_tone_high": "高音 19 kHz",
        "sound_pulse": "短いパルス",
        "level_min": "最小",
        "level_very_low": "とても小さい",
        "level_low": "小さい",
        "level_medium": "中",
        "level_high": "大きい",
        "level_very_high": "とても大きい",
    },
    "ru": {
        "status_stopped": "Остановлено",
        "status_playing": "Воспроизведение на {device}",
        "status_error": "Ошибка: нет аудиовыхода ({error})",
        "default_output": "выход по умолчанию",
        "menu_active": "Включено",
        "menu_sound": "Звук: {name}",
        "menu_volume": "Громкость: {name}",
        "menu_pulse": "Интервал импульса",
        "menu_seconds": "{n} с",
        "menu_output": "Аудиовыход",
        "menu_default_device": "По умолчанию в системе",
        "menu_show_all_apis": "Показать все аудио API",
        "menu_refresh": "Обновить список",
        "menu_follow_default": "Следовать за выходом по умолчанию",
        "menu_compensate": "Компенсировать низкую громкость системы",
        "menu_autostart": "Запускать вместе с системой",
        "menu_language": "Язык",
        "lang_auto": "Автоматически ({name})",
        "menu_version": "Версия {version}",
        "menu_quit": "Выход",
        "notify_autostart_failed": "Не удалось изменить автозапуск.",
        "sound_pink": "Розовый шум (рекомендуется)",
        "sound_brown": "Коричневый шум (ниже)",
        "sound_tone_low": "Низкий тон 20 Гц",
        "sound_tone_high": "Высокий тон 19 кГц",
        "sound_pulse": "Короткий импульс",
        "level_min": "Минимум",
        "level_very_low": "Очень тихо",
        "level_low": "Тихо",
        "level_medium": "Средне",
        "level_high": "Громко",
        "level_very_high": "Очень громко",
    },
}


def available() -> List[Tuple[str, str]]:
    """Codigos e nomes dos idiomas, na ordem em que aparecem no menu."""
    return [(code, LANGUAGE_NAMES.get(code, code)) for code in STRINGS]


def _normalize(raw: Optional[str]) -> Optional[str]:
    """Transforma pt_BR.UTF-8, pt-br, zh_Hans_CN e afins em pt, zh, etc."""
    if not raw:
        return None
    code = str(raw).replace("-", "_").split(".")[0].split("_")[0].strip().lower()
    return code if code in STRINGS else None


def _from_environment() -> Optional[str]:
    for name in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(name)
        if value and value.lower() not in ("c", "posix"):
            # LANGUAGE pode vir com varios idiomas separados por dois pontos
            for part in value.split(":"):
                code = _normalize(part)
                if code:
                    return code
    return None


def _from_windows() -> Optional[str]:
    try:
        import ctypes
        import locale as locale_module

        lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        return _normalize(locale_module.windows_locale.get(lcid))
    except Exception:
        return None


def _from_macos() -> Optional[str]:
    try:
        out = subprocess.run(
            ["defaults", "read", "-g", "AppleLanguages"],
            capture_output=True,
            text=True,
            timeout=3,
        ).stdout
        for line in out.splitlines():
            code = _normalize(line.strip().strip('",'))
            if code:
                return code
    except Exception:
        pass
    return None


def _from_locale_module() -> Optional[str]:
    try:
        import locale as locale_module

        for getter in ("getlocale", "getdefaultlocale"):
            func = getattr(locale_module, getter, None)
            if not func:
                continue
            try:
                value = func()
            except Exception:
                continue
            if value and value[0]:
                code = _normalize(value[0])
                if code:
                    return code
    except Exception:
        pass
    return None


def detect() -> str:
    """Idioma do sistema, com queda para ingles quando nao reconhecemos."""
    if sys.platform == "win32":
        return _from_windows() or _from_environment() or _from_locale_module() or FALLBACK
    if sys.platform == "darwin":
        return _from_environment() or _from_macos() or _from_locale_module() or FALLBACK
    return _from_environment() or _from_locale_module() or FALLBACK


class Translator:
    """Guarda o idioma atual e traduz por chave."""

    def __init__(self, choice: str = "auto") -> None:
        self.detected = detect()
        self.set(choice)

    def set(self, choice: Optional[str]) -> None:
        self.choice = choice or "auto"
        self.code = self.detected if self.choice == "auto" else _normalize(self.choice) or FALLBACK

    @property
    def language_name(self) -> str:
        return LANGUAGE_NAMES.get(self.code, self.code)

    def __call__(self, key: str, **kwargs) -> str:
        table = STRINGS.get(self.code, STRINGS[FALLBACK])
        text = table.get(key) or STRINGS[FALLBACK].get(key) or key
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                return text
        return text
