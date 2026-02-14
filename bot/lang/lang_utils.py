import json
import os
import logging

logger = logging.getLogger('discord_bot')

LANG_DIR = os.path.join(os.path.dirname(__file__), '.')
DEFAULT_LANG = 'fr'

_loaded_langs = {}

def load_languages():
    """Loads all available languages into cache."""
    global _loaded_langs
    if not os.path.exists(LANG_DIR):
        logger.warning(t('lang_dir_not_found', dir=LANG_DIR))
        return

    for filename in os.listdir(LANG_DIR):
        if filename.endswith(".json"):
            lang_code = filename[:-5]
            path = os.path.join(LANG_DIR, filename)
            try:
                with open(path, encoding='utf-8') as f:
                    _loaded_langs[lang_code] = json.load(f)
                    logger.info(t('lang_loaded', lang=lang_code))
            except Exception as e:
                logger.error(t('lang_load_error', lang=lang_code, error=e))

def get_text(key, _locale=None, **kwargs):
    """
    Retrieves translated text for the given key and selected language.
    kwargs allows injecting variables into the text (e.g., {title})
    """
    if not _loaded_langs:
        load_languages()

    # Determine language: explicit _locale > Global DEFAULT_LANG
    target_lang = _locale if _locale else DEFAULT_LANG

    # Try requested language, then default language, otherwise return the key
    translations = _loaded_langs.get(target_lang) or _loaded_langs.get(DEFAULT_LANG) or {}
    text = translations.get(key, key)

    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception as e:
            # Avoid infinite recursion if t() is used in logging within this module
            print(f"Format error for key '{key}': {e}")
            return text
    return text

def t(key, _locale=None, **kwargs):
    """Shortcut for get_text."""
    return get_text(key, _locale, **kwargs)

CONFIG_FILE = os.path.join(LANG_DIR, 'config.json')

def load_config():
    """Loads language configuration."""
    global DEFAULT_LANG
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                DEFAULT_LANG = config.get('language', 'fr')
        except Exception as e:
            logger.error(t('lang_load_error', lang='config', error=e))

def save_config():
    """Saves language configuration."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({'language': DEFAULT_LANG}, f, indent=4)
    except Exception as e:
        logger.error(t('lang_save_error', error=e))

def set_language(lang_code):
    """Changes default language and saves it."""
    global DEFAULT_LANG
    if lang_code in _loaded_langs:
        DEFAULT_LANG = lang_code
        save_config()
        return True
    return False

def get_available_languages():
    """Returns list of available language codes."""
    return list(_loaded_langs.keys())

# Initial load
load_languages()
load_config()
