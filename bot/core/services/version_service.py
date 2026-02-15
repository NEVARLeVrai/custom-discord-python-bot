import os
import json
import traceback
from lang.lang_utils import t

def get_version_info(client, guild_id=None):
    """Reads version info from update_logs.json file"""
    try:
        update_logs_path = client.paths['update_logs_json']
        if os.path.exists(update_logs_path):
            with open(update_logs_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        else:
            return {
                "current_version": t('version_null', guild_id=guild_id),
                "history": []
            }
    except Exception:
        traceback.print_exc()
        return {
            "current_version": t('version_null', guild_id=guild_id),
            "history": []
        }

def get_current_version(client, guild_id=None):
    """Returns current version"""
    data = get_version_info(client, guild_id=guild_id)
    return data.get("current_version", t('version_null', guild_id=guild_id))

def get_latest_logs(client, guild_id=None):
    """Returns logs of the latest version"""
    data = get_version_info(client, guild_id=guild_id)
    history = data.get("history", [])
    if history:
        return history[0].get("logs", t('version_no_logs', guild_id=guild_id))
    return t('version_no_update_logs', guild_id=guild_id)

def get_all_history(client):
    """Returns whole version history"""
    data = get_version_info(client)
    return data.get("history", [])
