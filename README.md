# Python Discord Bot

A complete **Discord bot** with numerous features, developed in **Python** using **discord.py**.

---

## 📋 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [How to Launch](#-how-to-launch)
- [Configuration](#-configuration)
- [Project Structure](#-project-structure)
- [Slash Commands](#-slash-commands)
- [Error Handling](#-error-handling)
- [Notes](#-notes)
- [Warnings](#-warnings)
- [Bug Reporting](#-bug-reporting)

---

## 🚀 Features

### 🌍 Internationalization (Full Support)

- **`/setlang [language]`** – Change the bot's language (English `en` or French `fr`) for the current server.
- **Complete Coverage** – All commands, system logs, and error responses are fully localized.
- **Server-Specific Support** – Each server can have its own independent language setting.
- **Persisted Preference** – Settings are saved in `bot/lang/config.json` and persist across restarts.

### 🧩 General Commands

- **`/helps`** – Displays all available commands
- **`/ping`** – Shows the bot's latency in ms
- **`/version`** – Displays the bot's version
- **`/report [message]`** – Report a bug or send feedback
- **`/stop`** – Stops the bot _(owner only)_
- **`/sync`** Re-sync slash commands _(owner only)_
- **`/clearslash`** – Remove all slash commands _(owner only)_
- **`/slashinfo`** – Display slash command diagnostics _(owner only)_

---

### 🛡️ Moderation

- **`/clear [amount]`** – Delete messages (max 70)
- **`/warn [@user] [reason] [count]`** – Warn a user
- **`/resetwarn [@user]`** – Reset user warnings
- **`/warnboard`** – Show warnings leaderboard
- **`/kick [@user] [reason]`** – Kick a user
- **`/ban [@user or ID] [reason]`** – Ban a user
- **`/unban [ID]`** – Unban a user
- **`/cleanraidsimple [name]`** – Delete a channel by name
- **`/cleanraidmultiple [date] [time]`** – Delete channels by date
- **`/giverole [@user] [@role]`** – Give a role _(owner only)_
- **`/removerole [@user] [@role]`** – Remove a role _(owner only)_
- **`/mp [@user or ID] [message]`** – Send a private message
- **`/spam [count] [#channel or mention] [message]`** – Spam messages _(admin only)_
- **`/banword [word]`** – Add a banned word
- **`/unbanword [word]`** – Remove a banned word
- **`/listbannedwords`** – Display all banned words

**Per-Server System:**

- **Warns, banned words, and language are server-specific** – Each server has its own independent list of banned words, warns, and language preference.
- **No cross-server data** – Settings from one server do not affect others.

**Automatic Features:**

- **Banned word detection** – Automatically detects and deletes messages containing banned words (per server)
- **Automatic warn** – Users receive a warn via DM when using a banned word (reason: "banned word used: [word]")
- **Automatic sanctions** – 5 warns → 10 min timeout · 10 warns → 10 min timeout · 15 warns → kick · 20 warns → ban
- **Role protection** – Protected roles are temporarily removed during sanctions and restored after timeout
- **Sanctions are server-specific** – Warns are tracked separately for each server

---

### 🧰 Utility

- **`/gpt [question]`** – Ask GPT a question
- **`/dalle [prompt]`** – Generate an image using DALL·E
- **`/say [#channel] [message]`** – Send a message in a channel
- **`/8ball [question]`** – Ask the magic 8-ball
- **`/hilaire`** – Hilaire game
- **`/deldms`** – Delete all bot DMs _(admin only)_
- **`/tts [language] [volume] [text]`** – Make the bot speak (e.g. `/tts en 3.0 Hello`)

### 🕒 Reminders & Timezone

Personal reminder system with timezone awareness.

- **Commands**: `/reminder set`, `/reminder list`, `/reminder cancel`, `/reminder timezone set`.
- **Time Formats**:
  - Relative: `10m`, `1h`, `2d`
  - Absolute (Time): `18:30`, `18:30:45`
  - Absolute (Date): `27/02 18:30`, `27/02/26 18:30`, `27/02/2026 18:30`
- **Confirmation**: Uses Discord dynamic timestamps (auto-adjusts to your device).
- **Spam Mode**: Optional recurring alerts until acknowledged via a button.

---

### 🧹 Maintenance & Reset

- **Cleanup Tool**: `bot/tools/reset_bot.py` is now fully localized (FR/EN) and ensures data integrity.
- **Launcher UX**: `run.py` displays real-time download speed and progress for dependencies.

> The bot automatically joins the user's voice channel and stays connected for other audio features.

---

### 🎵 Soundboard

- **`/slist`** – List available sounds
- **`/splay [number]`** – Play a sound (auto joins VC)
- **`/leave`** – Leave VC
- **`/sstop`** – Stop sound
- **`/svolume [0-200]`** – Set soundboard volume
- **`/srandom`** – Play random sounds every 1–5 min
- **`/srandomskip`** – Skip current random sound
- **`/srandomstop`** – Stop random playback
- **`/vkick [@user]`** – Kick a user from VC _(admin only)_

Supported formats : MP3 / MP4 / M4A / OGG / OPUS / WAV / FLAC / AAC

---

### 🎵 AudioPlayer (yt-dlp) - **MAJOR UPDATE!**

**New Interactive UI with Buttons:**

- ⏮️ Previous | ⏯️ Play/Pause | ⏭️ Skip | 🔁 Loop
- ⏪ -15s | ⏩ +15s | 📋 Queue | ⏹️ Stop

**Playback Commands:**

- **`/mplay [URL]`** – Play a video or audio from any supported site (YouTube, TikTok, X, etc.)
- **`/msearch [query]`** – Search and play with interactive menu
- **`/mskip`** – Skip the current track
- **`/mstop`** – Stop playback and clear queue
- **`/mpause`** – Pause the current track
- **`/mresume`** – Resume playback
- **`/leave`** – Disconnect from voice channel

**Queue Management:**

- **`/mqueue`** – Display the queue
- **`/mclearqueue`** – Clear the queue
- **`/maddqueue [URL]`** – Add song to queue without playing
- **`/mremovequeue [position]`** – Remove song from queue

**Advanced Controls:**

- **`/mloop`** – Toggle loop mode
- **`/mprevious`** – Play the previous track
- **`/mseek [minutes] [seconds]`** – Seek to specific time
- **`/mvolume [0-200]`** – Set music volume (real-time, no restart)
- **Dynamic Progress Bar** – "Now Playing" embed includes a visual progress bar

- **Universal Local Playback (⏮️)** – The bot now automatically downloads **all** audio sources locally before playing. This ensures 100% stability, no buffering, and perfect seek/skip utility for every supported platform (YouTube, TikTok, SoundCloud, etc.).
- **Persistent UI** – The player message is only replaced when a new track starts. It stays visible even if the song ends or the queue is empty.
- **Universal Seek Support** – Skip buttons (+15s / -15s) now work perfectly for all platforms.
- **Session-Based Cleanup** – Temporary audio files are preserved during your session for stability and cleared only when you leave or stop.
- **Universal Exit Listener** – One-click cleanup even if the bot is kicked or timed out.

Supported platforms: [see full list](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) (YouTube, TikTok, X, Facebook, SoundCloud, Twitch, Vimeo, etc.)

Powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp).

---

### 🔗 Link Conversion (VxT-Python Port)

Full-fidelity port of **VxT-Python** (conversion of social media links for better embeds).

- **Zero configuration needed** – Automatically converts links from X (Twitter), Instagram, TikTok, and more.
- **Unbundled Commands** – All 14 configuration modules are available as top-level `vxt-` commands.
- **`/vxt-toggle [type]`** – Toggle conversion for all, text, images, videos, or polls.
- **`/vxt-direct-media toggle [type]`** – Toggle subdomain addition for Twitter images/videos.
- **`/vxt-direct-media channel [action] [channel]`** – Manage allowed/prohibited channels.
- **`/vxt-direct-media multiple-images [option]`** – Configure mosaic or conversion for multi-images.
- **`/vxt-direct-media quote-tweet [option]`** – Configure quote tweet behavior in direct media.
- **`/vxt-translate toggle`** – Enable/disable tweet translation.
- **`/vxt-translate language [language]`** – Set target language with autocomplete.
- **`/vxt-blacklist [action] [user/role]`** – Manage blacklisted users and roles.
- **`/vxt-mention remove [action] [mention]`** – Manage mentions to ignore.
- **`/vxt-mention remove-all [groups]`** – Toggle removal for all, roles, or users mentions.
- **`/vxt-conversion-list add/update/remove/list`** – Manage custom domain conversions.
- **`/vxt-quote-tweet link-conversion [type]`** – Toggle specific quote tweet link conversion details.
- **`/vxt-quote-tweet remove-quoted-tweet`** – Toggle removal of original quoted tweets.
- **`/vxt-message [delete_original] [other_webhooks]`** – Configure webhook and deletion behavior.
- **`/vxt-retweet [delete_original]`** – Toggle original deletion for retweets.
- **`/vxt-webhooks [preference] [reply]`** – Set preference between webhooks and replies.
- **`/vxt-delete-bot-message [toggle] [count]`** – Configure bot message deletion via reactions.
- **`/vxt-name-preference [preference]`** – Choose between display name and username for webhooks.
- **`/vxt-reset-settings`** – Reset all VxT settings to default for the server.
- **`/vxt-error-list`** – List recent conversion errors.
 
 _Uses webhooks to seamlessly replace messages while maintaining user identity._
 
 ---
 
 ### 🧬 Leveling System

- **`/level [@user]`** – View level
- **`/resetlevel`** – Reset all levels _(admin only)_
- **`/levelsettings`** – Toggle leveling
- **`/levelboard`** – Show leaderboard

**Automatic Features:**

- **Automatic XP** – Each message = +1 XP (when leveling is enabled)
- **Level up formula** – Level up when XP ≥ (level + 1)²
- **Level up notification** – Automatic congratulation message when a user levels up

---

## 📦 Installation

### Requirements

**Zero configuration required!** The bot is **portable**.

1.  **Prerequisites**: Have [Python 3.8+](https://www.python.org/downloads/) installed.
2.  **Launch the bot**:
- Double-click on `run.bat` (Windows).
- Or run `./run.sh` (Linux/Mac).

✨ **Magic**: On first launch, the bot will **automatically**:

- Install all Python dependencies (`discord.py`, `yt-dlp`, `openai`, etc.)
- Download **FFmpeg** (for audio/soundboard) with real-time speed & progress tracking
- Download **Node.js** (for AudioPlayer) with real-time speed & progress tracking

All tools are installed in `bot/bin/` and **will not affect your system**.

### Python Dependencies

The bot automatically installs these packages from `bot/core/requirements.txt`

### Token Configuration

**Required:** You need a Discord bot token to run the bot.

#### 📋 How to get a Discord token:

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application or select an existing one
3. Go to the **Bot** section
4. Click **Reset Token** and copy your token
5. Enable these **Privileged Gateway Intents**:
   - ✅ Presence Intent
   - ✅ Server Members Intent
   - ✅ Message Content Intent

#### 📝 Configure the token:

**Current configuration:** The bot reads the token from a file path specified in `bot/core/main.py` (line 31).

**Default path:**

```python
'token_file': "C:/Users/Danie/Mon Drive/Autres/Bot Python Discord/token.txt"
```

**To configure:**

1. Edit `bot/core/main.py` line 31 with your desired path, OR
2. Create a `token.txt` file at the path specified in `main.py`
3. Put your Discord token inside (just the token, nothing else)

**Example `token.txt`:**

```
MTIzNDU2Nzg5MDEyMzQ1Njc4.GhIjKl.MnOpQrStUvWxYz1234567890AbCdEfGhIjKlMnOp
```

**⚠️ Important:** Never share your token or commit it to Git (already in `.gitignore`)

#### 🔧 Alternative: Use a local `.env` file (Optional)

For better portability, you can use a `.env` file in the project root:

**`.env` file:**

```env
DISCORD_TOKEN=your_token_here
GPT_TOKEN=your_gpt_token_here
```

> Note: To use `.env`, you need to modify `bot/core/main.py` to load from environment variables instead of files.

---

## 🚀 How to Launch

The project includes convenient scripts in the root directory that automatically check for dependencies (Python, Node.js, FFmpeg).

### 🪟 Windows

Double-click on `run.bat` in the root folder, or run in terminal:

```cmd
run.bat
```

### 🐧 Linux / Mac

Make the script executable and run it:

```bash
chmod +x run.sh
./run.sh
```

---

## 🛠️ Administration Tools

### Reset Bot

A comprehensive tool is available to **reset** the bot's data (warns, levels, logs, banned words) and clear cache to zero if needed.

Run:

```bash
python bot/tools/reset_bot.py
```

_Note: This will perform a total cleanup of dynamic data and logs, but will preserve core configurations like `update_logs.json`._

---

## ⚙️ Project Structure

```
Python-Discord-Bot/
├── run.bat                    # Launcher (Windows)
├── run.sh                     # Launcher (Linux/Mac)
└── bot/
    ├── bin/                   # Portable tools (FFmpeg, Node.js) - Created automatically
    ├── core/                  # Source Code
    │   ├── main.py            # Entry point
    │   ├── run.py             # Launcher logic & auto-installation
    │   ├── requirements.txt
    │   ├── services/          # Business logic (Audio, Leveling, Mod...)
    │   ├── slash_commands/    # Slash commands (/)
    │   └── auto_commands/     # Auto commands & Error handling
    ├── json/                  # Data (config, warns, levels...)
    ├── lang/                  # Localization (fr.json, en.json)
    ├── img/                   # Images / Assets
    ├── Sounds/                # Audio files for Soundboard
    ├── logs/                  # Log files
    └── tools/                 # Admin scripts (reset_bot.py, clean_lang.py)
```

---

## 🧩 Slash Commands

All commands are available as **slash commands** and sync automatically on startup.
Use :

- **`/sync`** → Force sync
- **`/clearslash`** → Remove all slash commands
- **`/slashinfo`** → Diagnostics

Global sync may take up to 1 hour to propagate.

---

## 🛡️ Error Handling

Comprehensive error system with centralized error handling:

- Unknown command
- Missing permissions
- Invalid arguments
- Cooldown active
- Owner-only command
- Not usable in DM
- HTTP errors
- Resource not found
- Attribute errors

All errors are also logged to the console with full tracebacks.

---

## ⚠️ Warnings

- Keep all tokens private
- Ensure required permissions are granted (including Intent `Message Content`)
- Some commands are restricted to admins or owners

---

## 🐛 Bug Reporting

Use :

```
/report [message]
```

to send feedback or report a bug.
A ticket is automatically sent to the developer via webhook.

---

**Developed with ❤️ in Python by [NEVAR](https://github.com/NEVARLeVrai)**

---

### 📜 Credits & Acknowledgements

- **VxT-Python**: Special thanks to **[Aris-In-Vain](https://github.com/Aris-In-Vain/VxT-Python)** for the original Link Conversion logic and configuration structure.
- **Link Services**: Powered by [FixTweet](https://github.com/dangeredwolf/FixTweet) (dangeredwolf), [InstaFix](https://github.com/Wikidepia/InstaFix) (Wikidepia), and others.
- **Tools**: Powered by [discord.py](https://github.com/Rapptz/discord.py) and [yt-dlp](https://github.com/yt-dlp/yt-dlp).
