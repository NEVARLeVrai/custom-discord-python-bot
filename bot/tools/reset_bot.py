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

# Paths to directories to ensure existence
REQUIRED_DIRS = [
    os.path.join(bot_root, "bin"),
    os.path.join(bot_root, "logs"),
    os.path.join(bot_root, "json"),
    os.path.join(bot_root, "lang"),
    os.path.join(bot_root, "downloads"),
    os.path.join(bot_root, "img"),
    os.path.join(bot_root, "Sounds")
]

# Path to downloads directory for specialized cleanup
DOWNLOADS_DIR = os.path.join(bot_root, "downloads")

# Paths to data files
DATA_FILES = [
    os.path.join(bot_root, "json", "warns.json"),
    os.path.join(bot_root, "json", "levels.json"),
    os.path.join(bot_root, "json", "banned_words.json"),
    os.path.join(bot_root, "lang", "config.json")
]

# Path to log files
LOG_FILES = [
    os.path.join(bot_root, "logs", "bot.log"),
    os.path.join(bot_root, "logs", "gptlogs.txt"),
    os.path.join(bot_root, "logs", "dallelogs.txt")
]

def safe_remove(path):
    """Safely remove a file or directory, retrying if locked."""
    if not os.path.exists(path):
        return True
    
    print(f"Removing {path}...")
    for i in range(3):
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
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
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({}, f, indent=4)
        print(f"✓ Reset logic: {os.path.basename(path)}")
    except Exception as e:
        print(f"⚠ Failed to reset {path}: {e}")

def reset_log_file(path):
    """Recreates an empty log file."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write("")
        print(f"✓ Reset log: {os.path.basename(path)}")
    except Exception as e:
        print(f"⚠ Failed to reset log file {path}: {e}")

def delete_pycache(root_dir):
    """Recursively deletes __pycache__ directories."""
    print("Cleaning __pycache__ folders...")
    count = 0
    for root, dirs, files in os.walk(root_dir):
        if "__pycache__" in dirs:
            pycache_path = os.path.join(root, "__pycache__")
            if safe_remove(pycache_path):
                count += 1
    
    if count == 0:
        print("· No __pycache__ folders found.")
    else:
        print(f"✓ Cleaned {count} pycache directories.")

def ensure_structure():
    """Ensures essential directories exist."""
    print("\n--- Verifying Project Structure ---")
    for directory in REQUIRED_DIRS:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"✓ Created missing directory: {os.path.relpath(directory, bot_root)}")
            except Exception as e:
                print(f"⚠ Could not create {directory}: {e}")
        else:
            print(f"· Directory exists: {os.path.relpath(directory, bot_root)}")

def main():
    print("====================================================")
    print("⚠️  BOT RESET TOOL - FULL CLEANUP ⚠️")
    print("====================================================")
    print("This will delete:")
    print("- Warns, levels, and server configurations")
    print("- Banned words and all logs")
    print("- Temporary downloads and cached files")
    print("- Binaries (FFmpeg/Node) to force re-installation")
    print("====================================================")
    
    # 1. Structure Check
    ensure_structure()

    # 2. Reset Data Files
    print("\n--- Resetting Data Files ---")
    for file_path in DATA_FILES:
        if os.path.exists(file_path):
            safe_remove(file_path)
        reset_json_file(file_path)

    # 3. Reset Logs
    print("\n--- Resetting Logs ---")
    for log_path in LOG_FILES:
        if os.path.exists(log_path):
            safe_remove(log_path)
        reset_log_file(log_path)

    # 4. Clean Downloads
    print("\n--- Cleaning Downloads ---")
    if os.path.exists(DOWNLOADS_DIR):
        if safe_remove(DOWNLOADS_DIR):
            os.makedirs(DOWNLOADS_DIR, exist_ok=True)
            print("✓ Downloads directory cleared and recreated.")

    # 5. Clean PyCache
    print("\n--- Cleaning Python Cache ---")
    delete_pycache(bot_root)

    # 6. Delete Binaries
    print("\n--- Deleting Binaries (Force Re-install) ---")
    if os.path.exists(BIN_DIR):
        if safe_remove(BIN_DIR):
            os.makedirs(BIN_DIR, exist_ok=True)
            print("✓ bin/ directory cleared and ready for run.py")
    else:
        print("· No bin directory found.")

    print("\n" + "="*50)
    print("✅ RESET COMPLETE.")
    print("Run 'run.bat' or './run.sh' to re-initialize dependencies.")
    print("="*50)

if __name__ == "__main__":
    main()
