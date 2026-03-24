import json
import os
import copy

class VxTService:
    def __init__(self, bot=None):
        self.bot = bot
        
        self.default_settings = {
            "conversion-list": {"twitter.com": "fxtwitter.com", "x.com": "fxtwitter.com",
                                "instagram.com": "ddinstagram.com", "tiktok.com": "tiktxk.com"}, 
            "name-preference-list": "display name", 
            "mention-remove-list": [], 
            "toggle-list": {"all": True, "text": True, "images": True, "videos": True, "polls": True}, 
            "quote-tweet-list": {"link_conversion": {"follow tweets": True, "all": True, "text": True, "images": True, "videos": True, "polls": True}, "remove quoted tweet": False}, 
            "message-list": {"delete_original": True, "other_webhooks": False}, 
            "retweet-list": {"delete_original_tweet": False}, 
            "direct-media-list": {"toggle": {"images": False, "videos": False}, "channel": ["allow"], "multiple_images": {"convert": True, "replace_with_mosaic": True}, "quote_tweet": {"convert": False, "prefer_quoted_tweet": True}}, 
            "translate-list": {"toggle": False, "language": "en"}, 
            "delete-bot-message-list": {"toggle": False, "number": 1}, 
            "webhook-list": {"preference": "webhooks", "reply": False}, 
            "blacklist-list": {"users": [], "roles": []}
        }
        
        self.master_settings = {}
        # Make the lists dir local to bot/json
        # __file__ is in bot/core/services -> dirname is services -> dirname is core -> dirname is bot
        self.base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "json", "vxt_lists")
        os.makedirs(self.base_dir, exist_ok=True)

    def get_file_path(self, file_name):
        return os.path.join(self.base_dir, f"{file_name}.json" if not file_name.endswith('.json') else file_name)

    def convert_str_to_int(self, data):
        if isinstance(data, dict):
            # Guild IDs are always strings in JSON, convert to int for internal use
            return {int(k) if isinstance(k, str) and k.isdigit() else k: self.convert_str_to_int(v) for k, v in data.items()}
        elif isinstance(data, list):
            # Only convert to set if it's meant to be a set (mentions or blacklist)
            # This is a bit hacky but keeps the original logic which relies on .add() and .remove()
            return [self.convert_str_to_int(item) for item in data]
        elif isinstance(data, str) and data.isdigit():
            return int(data)
        else:
            return data

    def convert_set_to_list(self, data):
        if isinstance(data, dict):
            return {str(k): self.convert_set_to_list(v) for k, v in data.items()}
        elif isinstance(data, set):
            return list(data)
        elif isinstance(data, list):
            return [self.convert_set_to_list(item) for item in data]
        else:
            return data

    def read_file_content(self, file_name, empty_value=None):
        if empty_value is None:
            empty_value = {}
            
        file_path = self.get_file_path(file_name)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                try:
                    content = json.load(file)
                    return self.convert_str_to_int(content)
                except json.JSONDecodeError:
                    return copy.deepcopy(empty_value)
        else:
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(empty_value, file)
            return copy.deepcopy(empty_value)

    async def write_file_content(self, file_name, modified_content):
        file_path = self.get_file_path(file_name)
        modified_content = self.convert_set_to_list(modified_content)

        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(modified_content, file, indent=4)
        
        # update master_settings in memory
        await self.load_settings()
        return True

    async def load_settings(self):
        for filename, default_val in self.default_settings.items():
            temp_file = self.read_file_content(filename, {})
            for guild_id, settings in temp_file.items():
                if guild_id not in self.master_settings:
                    self.master_settings[guild_id] = {}
                key = filename[:-5] if filename.endswith('-list') else filename
                self.master_settings[guild_id][key] = settings

    async def initialize_guilds(self, guilds):
        for filename in self.default_settings.keys():
            temp_list = self.read_file_content(filename, {})
            changed = False
            for guild in guilds:
                if guild.id not in temp_list:
                    temp_list[guild.id] = self.default_settings[filename]
                    changed = True
            
            if changed:
                file_path = self.get_file_path(filename)
                mod_content = self.convert_set_to_list(temp_list)
                with open(file_path, 'w', encoding='utf-8') as file:
                    json.dump(mod_content, file, indent=4)
                    
        await self.load_settings()

vxt_service_global = VxTService()
