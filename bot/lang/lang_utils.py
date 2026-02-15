import json
import os
import logging

logger = logging.getLogger('discord_bot')

LANG_DIR = os.path.join(os.path.dirname(__file__), '.')
DEFAULT_LANG = 'en'
GUILD_LANGS = {} # guild_id (str) -> lang_code

_loaded_langs = {}

def load_languages():
    """Loads all available languages into cache."""
    global _loaded_langs
    if not os.path.exists(LANG_DIR):
        return

    for filename in os.listdir(LANG_DIR):
        if filename.endswith(".json") and filename not in ("config.json",):
            lang_code = filename[:-5]
            path = os.path.join(LANG_DIR, filename)
            try:
                with open(path, encoding='utf-8') as f:
                    _loaded_langs[lang_code] = json.load(f)
            except Exception as e:
                logger.error(f"Error loading language {lang_code}: {e}")

def get_text(key, _locale=None, guild_id=None, **kwargs):
    """
    Retrieves translated text for the given key and selected language.
    Priority: explicit _locale > guild_id config > Global DEFAULT_LANG
    """
    if not _loaded_langs:
        load_languages()

    # 1. Check explicit locale
    target_lang = _locale
    
    # 2. Check guild config if provided
    if not target_lang and guild_id:
        target_lang = GUILD_LANGS.get(str(guild_id))
    
    # 3. Fallback to global default
    if not target_lang:
        target_lang = DEFAULT_LANG

    # Try requested language, then default language, otherwise return the key
    translations = _loaded_langs.get(target_lang) or _loaded_langs.get(DEFAULT_LANG) or {}
    text = translations.get(key, key)

    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception as e:
            print(f"Format error for key '{key}': {e}")
            return text
    return text

def t(key, _locale=None, guild_id=None, **kwargs):
    """Shortcut for get_text."""
    return get_text(key, _locale, guild_id=guild_id, **kwargs)

CONFIG_FILE = os.path.join(LANG_DIR, 'config.json')

def load_config():
    """Loads language configuration."""
    global DEFAULT_LANG, GUILD_LANGS
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                DEFAULT_LANG = config.get('language', DEFAULT_LANG)
                GUILD_LANGS = config.get('guild_languages', {})
        except Exception as e:
            logger.error(f"Error loading config: {e}")

def save_config():
    """Saves language configuration."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'language': DEFAULT_LANG,
                'guild_languages': GUILD_LANGS
            }, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving config: {e}")

def set_language(lang_code, guild_id=None):
    """Changes language and saves it. If guild_id is provided, sets it only for that guild."""
    global DEFAULT_LANG, GUILD_LANGS
    if lang_code in _loaded_langs:
        if guild_id:
            GUILD_LANGS[str(guild_id)] = lang_code
        else:
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
