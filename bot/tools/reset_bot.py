import os
import json
import shutil
import time

# Base directory for the project (assuming this script is in tools/ and run from project root or tools/)
# We want to target the 'bot_discord' folder which is in the project root.
# If this script is in <root>/tools/reset_bot.py, then project root is one level up.

current_dir = os.path.dirname(os.path.abspath(__file__))
# current_dir is .../bot/tools
# bot_root is .../bot
bot_root = os.path.dirname(current_dir)
# Path to bin directory (FFmpeg, Node.js)
BIN_DIR = os.path.join(bot_root, "bin")

# Paths to data files
DATA_FILES = [
    os.path.join(bot_root, "json", "warns.json"),
    os.path.join(bot_root, "json", "levels.json"),
    os.path.join(bot_root, "json", "banned_words.json")
]

# Path to log files
LOG_FILES = [
    os.path.join(bot_root, "logs", "bot.log"),
    os.path.join(bot_root, "logs", "gptlogs.txt"),
    os.path.join(bot_root, "logs", "dallelogs.txt")
]

def safe_remove(path):
    """Safely remove a file, retrying if locked."""
    if not os.path.exists(path):
        return True
    
    print(f"Removing {path}...")
    for i in range(3):
        try:
            os.remove(path)
            return True
        except Exception as e:
            if i == 2:
                print(f"⚠ Could not delete {path}: {e}")
                return False
            time.sleep(1)
    return False

def reset_json_file(path):
    """Recreates a JSON file with an empty object {}."""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({}, f, indent=4)
        print(f"✓ Reset to empty JSON: {path}")
    except Exception as e:
        print(f"⚠ Failed to reset {path}: {e}")

def reset_log_file(path):
    """Recreates an empty log file."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write("")
        print(f"✓ Reset log file: {path}")
    except Exception as e:
        print(f"⚠ Failed to reset log file {path}: {e}")

def delete_pycache(root_dir):
    """Recursively deletes __pycache__ directories."""
    print("Finding and deleting __pycache__ folders...")
    count = 0
    for root, dirs, files in os.walk(root_dir):
        if "__pycache__" in dirs:
            pycache_path = os.path.join(root, "__pycache__")
            try:
                shutil.rmtree(pycache_path)
                print(f"✓ Deleted: {pycache_path}")
                count += 1
            except Exception as e:
                print(f"⚠ Could not delete {pycache_path}: {e}")
    
    if count == 0:
        print("· No __pycache__ folders found.")

def main():
    print("⚠️  WARNING: This will delete all warns, levels, banned words, logs, and binaries (bin/). ⚠️")
    print("Configuration files (update_logs.json) will be preserved.")
    
    # Auto-confirmation since user asked for it, but good to have a check if run manually
    # For now we proceed as this is a tool script.
    
    print("\n--- Resetting Data Files ---")
    for file_path in DATA_FILES:
        if os.path.exists(file_path):
            if safe_remove(file_path):
                reset_json_file(file_path)
        else:
            print(f"· File not found (creating empty): {file_path}")
            reset_json_file(file_path)

    print("\n--- Resetting Logs ---")
    for log_path in LOG_FILES:
        if os.path.exists(log_path):
            if safe_remove(log_path):
                reset_log_file(log_path)
        else:
            # For logs, we only care about existing ones or creating the main bot.log
            if log_path.endswith("bot.log"):
                reset_log_file(log_path)

    print("\n--- Cleaning Cache ---")
    delete_pycache(bot_root)
    # Also clean cache in the tools folder itself just in case
    delete_pycache(current_dir)

    print("\n--- Deleting Binaries (bin/) ---")
    if os.path.exists(BIN_DIR):
        try:
            shutil.rmtree(BIN_DIR)
            print(f"✓ Deleted bin directory: {BIN_DIR}")
        except Exception as e:
            print(f"⚠ Could not delete {BIN_DIR}: {e}")
    else:
        print("· No bin directory found.")

    print("\n✅ Bot reset complete.")

if __name__ == "__main__":
    main()
