# -*- coding: utf-8 -*-
"""
Entry point to launch the Discord bot.
Checks dependencies and launches main.py
"""
import os
import sys
import subprocess

import shutil
import platform
import urllib.request
import zipfile
import tarfile

# Set BASE_DIR to the 'bot' folder (parent of 'core') to allow imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.chdir(BASE_DIR)

from lang.lang_utils import t

# BASE_DIR is already set above

REQUIREMENTS = "core/requirements.txt"
MAIN_SCRIPT = "core/main.py"


def check_requirements():
    """Checks and installs dependencies if needed."""
    if not os.path.exists(REQUIREMENTS):
        print(t('run_req_not_found', requirements=REQUIREMENTS))
        return
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS])
    except subprocess.CalledProcessError as e:
        print(t('run_req_install_error', error=e))
        input(t('run_press_enter'))
        sys.exit(1)

def run_bot():
    """Launches the main bot."""
    try:
        subprocess.check_call([sys.executable, MAIN_SCRIPT])
    except KeyboardInterrupt:
        print(t('run_stop_user'))
    except Exception as e:
        print(t('run_critical_error', error=e))
        input(t('run_press_enter'))
        sys.exit(1)

def check_dependencies():
    """Checks if necessary dependencies (ffmpeg, node) are installed."""
    missing = []
    
    # Check FFmpeg
    if not shutil.which("ffmpeg"):
        missing.append("FFmpeg (https://ffmpeg.org/)")
        
    # Check Node.js
    if not shutil.which("node"):
        missing.append("Node.js (https://nodejs.org/)")

    # Manual path check removed as we now rely on auto-install and PATH
        
    if missing:
        print("="*60)
        print(t('run_warning_missing_deps'))
        print("="*60)
        print(t('run_missing_deps_list'))
        for dep in missing:
            print(f" - {dep}")
        print("\n" + t('run_missing_deps_hint'))
        print(t('run_manual_config_hint'))
        print("="*60)
        
        # Ask user if they want to continue
        try:
            choice = input(t('run_continue_prompt')).strip().lower()
            if choice == 'n':
                sys.exit(1)
        except EOFError:
            pass # Non-interactive mode, continue
    else:
        print(t('run_deps_check_ok'))

import platform
import urllib.request
import zipfile
import tarfile

BIN_DIR = os.path.join(BASE_DIR, 'bin')

def install_dependencies():
    # Ajout : variable d'environnement pour yt-dlp (runtime JS)
    # Pour Windows, Linux, Mac : injecte le chemin du Node portable
    node_exe_name = "node.exe" if platform.system().lower() == 'windows' else "node"
    node_path = os.path.join(BIN_DIR, node_exe_name)
    if os.path.exists(node_path):
        os.environ['YTDLP_JS_RUNTIME'] = f'node:{node_path}'
        # Optionnel : ajoute bot/bin au PATH pour garantir la détection
        os.environ['PATH'] = BIN_DIR + os.pathsep + os.environ['PATH']
    """Automatically downloads and installs missing dependencies (FFmpeg, Node.js)."""
    if not os.path.exists(BIN_DIR):
        os.makedirs(BIN_DIR, exist_ok=True)
    # Prepend BIN_DIR to PATH so we prioritize our portable tools
    # This change propagates to the subprocess (main.py)
    os.environ["PATH"] = BIN_DIR + os.pathsep + os.environ["PATH"]
    system = platform.system().lower()
    
    # --- FFmpeg Installation ---
    ffmpeg_exe = "ffmpeg.exe" if system == 'windows' else "ffmpeg"
    ffmpeg_path = os.path.join(BIN_DIR, ffmpeg_exe)
    is_mac = system == 'darwin'

    import re
    def get_latest_ffmpeg_url():
        # Récupère dynamiquement le lien du dernier build git master essentials
        try:
            # FFmpeg release stable (ZIP pour Windows, tar.xz pour Linux, ZIP pour Mac)
            if system == 'windows':
                return "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            elif system == 'linux':
                return "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
            elif is_mac:
                return "https://evermeet.cx/ffmpeg/ffmpeg.zip"
        except Exception as e:
            print(f"FFmpeg URL fetch error: {e}")
        # Fallback
        return "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

    if not os.path.exists(ffmpeg_path):
        print(t('run_ffmpeg_not_found_dl', system=system))
        try:
            url = get_latest_ffmpeg_url()
            if system == 'windows':
                filename = "ffmpeg.zip"
                download_path = os.path.join(BIN_DIR, filename)
                print(t('run_dl_start', url=url))
                opener = urllib.request.build_opener()
                opener.addheaders = [('User-agent', 'Mozilla/5.0')]
                urllib.request.install_opener(opener)
                urllib.request.urlretrieve(url, download_path)
                print("Download complete.")
                print(t('run_extract_ffmpeg'))
                with zipfile.ZipFile(download_path, 'r') as zip_ref:
                    for file in zip_ref.namelist():
                        if file.endswith("bin/ffmpeg.exe"):
                            zip_ref.extract(file, BIN_DIR)
                            src = os.path.join(BIN_DIR, file)
                            dst = os.path.join(BIN_DIR, "ffmpeg.exe")
                            shutil.move(src, dst)
                            break
                os.remove(download_path)
            elif system == 'linux':
                filename = "ffmpeg.tar.xz"
                download_path = os.path.join(BIN_DIR, filename)
                print(t('run_dl_start', url=url))
                opener = urllib.request.build_opener()
                opener.addheaders = [('User-agent', 'Mozilla/5.0')]
                urllib.request.install_opener(opener)
                urllib.request.urlretrieve(url, download_path)
                print(t('run_extract_ffmpeg'))
                with tarfile.open(download_path, "r:xz") as tar:
                    for member in tar.getmembers():
                        if member.name.endswith("ffmpeg"):
                            member.name = "ffmpeg"
                            tar.extract(member, BIN_DIR)
                            break
                os.chmod(os.path.join(BIN_DIR, "ffmpeg"), 0o755)
                os.remove(download_path)
            elif is_mac:
                filename = "ffmpeg.zip"
                download_path = os.path.join(BIN_DIR, filename)
                print(t('run_dl_start', url=url))
                urllib.request.urlretrieve(url, download_path)
                print(t('run_extract_ffmpeg'))
                with zipfile.ZipFile(download_path, 'r') as zip_ref:
                    for file in zip_ref.namelist():
                        if file.endswith("ffmpeg"):
                            zip_ref.extract(file, BIN_DIR)
                            src = os.path.join(BIN_DIR, file)
                            dst = os.path.join(BIN_DIR, "ffmpeg")
                            shutil.move(src, dst)
                            break
                os.remove(download_path)
                os.chmod(os.path.join(BIN_DIR, "ffmpeg"), 0o755)
            print(t('run_ffmpeg_installed'))
        except Exception as e:
            print(t('run_ffmpeg_install_error', error=e))

    # --- Node.js Installation ---
    node_exe_name = "node.exe" if system == 'windows' else "node"
    node_bin_path = os.path.join(BIN_DIR, node_exe_name)

    import re
    def get_latest_node_url():
        # Récupère dynamiquement le lien du dernier Node.js LTS pour Windows
        try:
            page_url = "https://nodejs.org/en/download/"
            opener = urllib.request.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            urllib.request.install_opener(opener)
            with urllib.request.urlopen(page_url) as resp:
                html = resp.read().decode('utf-8')
            if system == 'windows':
                match = re.search(r'https://nodejs.org/dist/v([\d\.]+)/node.exe', html)
                if match:
                    return f"https://nodejs.org/dist/v{match.group(1)}/node.exe"
            elif system == 'linux':
                match = re.search(r'https://nodejs.org/dist/v([\d\.]+)/node-v([\d\.]+)-linux-x64.tar.gz', html)
                if match:
                    return f"https://nodejs.org/dist/v{match.group(1)}/node-v{match.group(2)}-linux-x64.tar.gz"
            elif is_mac:
                match = re.search(r'https://nodejs.org/dist/v([\d\.]+)/node-v([\d\.]+)-darwin-x64.tar.gz', html)
                if match:
                    return f"https://nodejs.org/dist/v{match.group(1)}/node-v{match.group(2)}-darwin-x64.tar.gz"
        except Exception as e:
            print(f"Node.js URL fetch error: {e}")
        # Fallback
        return "https://nodejs.org/dist/latest/win-x64/node.exe"

    if not os.path.exists(node_bin_path):
        print(t('run_node_not_found_dl', system=system))
        try:
            url = get_latest_node_url()
            if system == 'windows':
                print(t('run_dl_start', url=url))
                urllib.request.urlretrieve(url, node_bin_path)
            elif system == 'linux':
                filename = "node.tar.gz"
                download_path = os.path.join(BIN_DIR, filename)
                print(t('run_dl_start', url=url))
                urllib.request.urlretrieve(url, download_path)
                print(t('run_extract_node'))
                with tarfile.open(download_path, "r:gz") as tar:
                    for member in tar.getmembers():
                        if member.name.endswith("bin/node"):
                            member.name = "node"
                            tar.extract(member, BIN_DIR)
                            break
                os.chmod(os.path.join(BIN_DIR, "node"), 0o755)
                os.remove(download_path)
            elif is_mac:
                filename = "node.tar.gz"
                download_path = os.path.join(BIN_DIR, filename)
                print(t('run_dl_start', url=url))
                urllib.request.urlretrieve(url, download_path)
                print(t('run_extract_node'))
                with tarfile.open(download_path, "r:gz") as tar:
                    for member in tar.getmembers():
                        if member.name.endswith("bin/node"):
                            member.name = "node"
                            tar.extract(member, BIN_DIR)
                            break
                os.chmod(os.path.join(BIN_DIR, "node"), 0o755)
                os.remove(download_path)
            print(t('run_node_installed'))
        except Exception as e:
            print(t('run_node_install_error', error=e))
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    check_requirements()   # Install pip reqs FIRST
    install_dependencies() # Auto-install missing binaries
    check_dependencies()   # Verify installations (including manual paths)
    run_bot()
