import json
import os
import re

"""
Utility script to clean up and sort language files (fr.json, en.json).
It parses the Python source code to find used translation keys and removes unused ones.
Note: To reset all bot data (logs, warns, levels, cache), use tools/reset_bot.py instead.
"""

# Always relative to this script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Fix path to avoid 'bot/bot/lang' duplication
if os.path.basename(BASE_DIR) == 'bot':
    PROJECT_ROOT = os.path.dirname(BASE_DIR)
    BOT_DIR = BASE_DIR
else:
    PROJECT_ROOT = BASE_DIR
    BOT_DIR = os.path.join(BASE_DIR, 'bot')
LANG_DIR = os.path.join(BOT_DIR, 'lang')

def get_used_keys():
    used_keys = set()
    for root, dirs, files in os.walk(BOT_DIR):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Standard t('key') and t("key")
                matches = re.findall(r"t\(['\"]([^'\"]+)['\"]", content)
                used_keys.update(matches)
                
                # Special cases for dynamic keys
                if 'magicball_res_' in content:
                    for i in range(1, 21): # Accommodate potential expansion
                        used_keys.add(f'magicball_res_{i}')
                if 'hilaire_res_' in content:
                    for i in range(1, 15): # Accommodate potential expansion
                        used_keys.add(f'hilaire_res_{i}')
    return used_keys

def clean_and_sort():
    used_keys = get_used_keys()
    
    for lang_file in ['fr.json', 'en.json']:
        file_path = os.path.join(LANG_DIR, lang_file)
        if not os.path.exists(file_path):
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Remove unused keys but keep some permanent ones if necessary
        # (none identified as permanent yet, they should all be in code)
        clean_data = {k: v for k, v in data.items() if k in used_keys}
        
        # Sort alphabetically
        sorted_data = dict(sorted(clean_data.items()))
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(sorted_data, f, ensure_ascii=False, indent=2)
            
        print(f"{lang_file}: {len(data)} -> {len(sorted_data)} keys (cleaned and sorted)")

if __name__ == "__main__":
    clean_and_sort()
