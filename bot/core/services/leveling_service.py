import json
import os
import threading
from lang.lang_utils import t

class LevelingService:
    def __init__(self, client):
        self.client = client
        self.levels_path = client.paths['levels_json']
        self.levels = {}
        self.is_leveling_enabled = False # Default is false as in Leveling.py
        self._lock = threading.Lock()
        self.load_levels()

    def load_levels(self):
        """Loads leveling data from JSON file."""
        if os.path.exists(self.levels_path):
            try:
                with open(self.levels_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Support for potential structure change if we want to save 'enabled' state
                    if isinstance(data, dict) and "users" in data:
                        self.levels = data.get("users", {})
                        self.is_leveling_enabled = data.get("enabled", False)
                    else:
                        self.levels = data
            except Exception as e:
                print(t('lvl_load_error', error=e))
                self.levels = {}
        else:
            self.levels = {}
            self.save_levels()

    def save_levels(self):
        """Saves leveling data to JSON file."""
        with self._lock:
            try:
                # We save both users and enabled state to make it persistent
                data = {
                    "enabled": self.is_leveling_enabled,
                    "users": self.levels
                }
                with open(self.levels_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
            except Exception as e:
                print(t('lvl_save_error', error=e))

    def get_stats(self, user_id):
        """Returns stats for a user."""
        user_id = str(user_id)
        return self.levels.get(user_id, {"level": 0, "experience": 0})

    def add_xp(self, user_id, amount=1):
        """Adds XP to a user and returns (new_level, leveled_up)."""
        if not self.is_leveling_enabled:
            return None, False

        user_id = str(user_id)
        if user_id not in self.levels:
            self.levels[user_id] = {"level": 0, "experience": 0}

        self.levels[user_id]["experience"] += amount
        
        current_xp = self.levels[user_id]["experience"]
        current_lvl = self.levels[user_id]["level"]
        
        # Level formula: XP >= (level + 1) ** 2
        leveled_up = False
        new_lvl = current_lvl
        while current_xp >= (new_lvl + 1) ** 2:
            new_lvl += 1
            leveled_up = True
        
        if leveled_up:
            self.levels[user_id]["level"] = new_lvl
        
        self.save_levels()
        return new_lvl, leveled_up

    def reset_all(self):
        """Resets all leveling data."""
        self.levels = {}
        self.save_levels()
        return True

    def toggle_system(self):
        """Toggles the leveling system status."""
        self.is_leveling_enabled = not self.is_leveling_enabled
        self.save_levels()
        return self.is_leveling_enabled
