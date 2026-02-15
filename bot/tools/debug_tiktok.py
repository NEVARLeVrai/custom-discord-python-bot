import sys
import os
import subprocess
import json

# TO DO TIKTOK LINK AND DOWNLOAD FIX

# Add bot directory to path to import requirements if needed, but we'll specific imports
# Setup paths exactly like main.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN_DIR = os.path.join(BASE_DIR, 'bin')
FFMPEG_EXE = os.path.join(BIN_DIR, 'ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg')
NODE_EXE = os.path.join(BIN_DIR, 'node.exe' if sys.platform == 'win32' else 'node')

print(f"FFmpeg path: {FFMPEG_EXE}")
print(f"Node path: {NODE_EXE}")

# Set environment variables
os.environ['PATH'] = BIN_DIR + os.pathsep + os.environ.get('PATH', '')
os.environ['YTDLP_JS_RUNTIME'] = f"node:{NODE_EXE}"

try:
    from yt_dlp import YoutubeDL
except ImportError:
    print("Installing requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", os.path.join(BASE_DIR, "core", "requirements.txt")])
    from yt_dlp import YoutubeDL

URL = "https://vm.tiktok.com/ZNRfubePC/"

def test_extraction():
    print(f"\nTesting extraction for: {URL}")
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': False,
        'outtmpl': 'tiktok_test.%(ext)s',
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            # Try downloading
            info = ydl.extract_info(URL, download=True)
            filename = ydl.prepare_filename(info)
        
        print("\nDownload Successful!")
        print(f"Title: {info.get('title')}")
        print(f"File: {filename}")
        return info, filename
    except Exception as e:
        print(f"\nExtraction/Download Failed: {e}")
        return None, None

def test_ffmpeg(audio_url, headers=None):
    print(f"\nTesting FFmpeg on URL...")
    
    # Simulate exactly what we did in AudioService
    # We constructed a string for before_options and let discord.py (or us) handle it.
    # discord.py splits the string using shlex usually? actually it depends.
    # In AudioService:
    # options['before_options'] = start_opts + f' -headers "{headers_str}"'
    # Then discord.py does: command = [exe] + before_opts.split() + ... 
    # Wait, discord.py does NOT use shlex.split() by default on string arguments? 
    # It usually expects a sequence or a string. If string, it passes it as arguments.
    # Let's check how we launch it here.
    
    cmd = [FFMPEG_EXE]
    
    before_opts = ['-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '5']
    
    if headers:
        headers_list = []
        for k, v in headers.items():
            headers_list.append(f"{k}: {v}")
        if headers_list:
            headers_str = "\r\n".join(headers_list) + "\r\n"
            # Attempting to match the behavior of passing it as a single argument vs separate
            # The issue is likely how newlines are passed in the argument list.
            before_opts.extend(['-headers', headers_str])
            
    cmd.extend(before_opts)
            
    cmd.extend([
        '-i', audio_url,
        '-vn',
        '-f', 'null', # Discard output
        '-'
    ])
    
    print(f"Command: {' '.join(cmd)}")
    
    try:
        # Run for 5 seconds then kill to see if it started
        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        try:
            stdout, stderr = process.communicate(timeout=5)
            print(f"FFmpeg finished naturally (unexpected for stream). RC: {process.returncode}")
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            print("FFmpeg started successfully (killed after 5s).")
            
        print("FFmpeg Output:")
        print(stderr.decode('utf-8', errors='replace'))
        
    except Exception as e:
        print(f"FFmpeg execution failed: {e}")

if __name__ == "__main__":
    info = test_extraction()
    if info:
        # Test 1: Raw URL without headers
        print("\n--- TEST 1: Raw URL without headers ---")
        test_ffmpeg(info['url'])
        
        # Test 2: URL with headers (if available)
        if info.get('http_headers'):
            print("\n--- TEST 2: URL with headers ---")
            test_ffmpeg(info['url'], info['http_headers'])
