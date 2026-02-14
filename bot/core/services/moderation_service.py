import json
import os
from datetime import datetime
from lang.lang_utils import t

class ModerationService:
    def __init__(self, client):
        self.client = client
        self.warns = {}
        self.banned_words = {}
        self.protected_role_id = 1236660715151167548
        self.blocked_user_id = 440168985615400984
        self.mp_conversations = {}
        self.load_data()

    def load_data(self):
        """Loads warns and banned words from JSON files"""
        # Load warns
        warns_path = self.client.paths['warns_json']
        if os.path.exists(warns_path):
            try:
                with open(warns_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.warns = data
                    else:
                        self.warns = {}
            except Exception as e:
                print(t('mods_warns_load_error', error=e))
                self.warns = {}
        else:
            self.warns = {}

        # Load banned words
        banned_words_path = self.client.paths['banned_words_json']
        if os.path.exists(banned_words_path):
            try:
                with open(banned_words_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.banned_words = data
                    else:
                        self.banned_words = {}
            except Exception as e:
                print(t('mods_banned_words_load_error', error=e))
                self.banned_words = {}
        else:
            self.banned_words = {}

    def save_warns(self):
        """Saves warns to JSON file"""
        warns_path = self.client.paths['warns_json']
        try:
            with open(warns_path, 'w', encoding='utf-8') as f:
                json.dump(self.warns, f, indent=2)
        except Exception as e:
            print(t('mods_warns_save_error', error=e))

    def save_banned_words(self):
        """Saves banned words to JSON file"""
        banned_words_path = self.client.paths['banned_words_json']
        try:
            with open(banned_words_path, 'w', encoding='utf-8') as f:
                json.dump(self.banned_words, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(t('mods_banned_words_save_error', error=e))

    def get_warn_count(self, guild_id, member_id):
        guild_id, member_id = str(guild_id), str(member_id)
        if guild_id in self.warns and member_id in self.warns[guild_id]:
            return self.warns[guild_id][member_id].get("count", 0)
        return 0

    def add_warn(self, guild_id, member_id, reason, moderator_name, count=1):
        guild_id, member_id = str(guild_id), str(member_id)
        if guild_id not in self.warns:
            self.warns[guild_id] = {}
        if member_id not in self.warns[guild_id]:
            self.warns[guild_id][member_id] = {"count": 0, "warnings": []}
        
        for _ in range(count):
            self.warns[guild_id][member_id]["count"] += 1
            self.warns[guild_id][member_id]["warnings"].append({
                "reason": reason,
                "moderator": moderator_name,
                "timestamp": datetime.now().isoformat()
            })
        self.save_warns()
        return self.warns[guild_id][member_id]["count"]

    def reset_warns(self, guild_id, member_id):
        guild_id, member_id = str(guild_id), str(member_id)
        if guild_id in self.warns and member_id in self.warns[guild_id]:
            self.warns[guild_id][member_id] = {"count": 0, "warnings": []}
            self.save_warns()
            return True
        return False

    def is_word_banned(self, guild_id, word):
        guild_id = str(guild_id)
        word = word.lower().strip()
        if guild_id in self.banned_words:
            return word in [w.lower() for w in self.banned_words[guild_id]]
        return False

    def add_banned_word(self, guild_id, word):
        guild_id = str(guild_id)
        word = word.lower().strip()
        if guild_id not in self.banned_words:
            self.banned_words[guild_id] = []
        if word not in self.banned_words[guild_id]:
            self.banned_words[guild_id].append(word)
            self.save_banned_words()
            return True
        return False

    def remove_banned_word(self, guild_id, word):
        guild_id = str(guild_id)
        word = word.lower().strip()
        if guild_id in self.banned_words and word in self.banned_words[guild_id]:
            self.banned_words[guild_id].remove(word)
            self.save_banned_words()
            return True
        return False

    def set_mp_conversation(self, member_id, channel_id):
        self.mp_conversations[str(member_id)] = channel_id

    def get_mp_conversation(self, member_id):
        return self.mp_conversations.get(str(member_id))

    def remove_mp_conversation(self, member_id):
        if str(member_id) in self.mp_conversations:
            del self.mp_conversations[str(member_id)]
