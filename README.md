# Python Discord Bot _(Bot and all comments are in French)_

A complete **Discord bot** with numerous features, developed in **Python** using **discord.py**.  
⚠️ _All bot commands, responses, and comments in the code are written in French._

---

## 📋 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Configuration](#️-configuration)
- [Project Structure](#-project-structure)
- [Slash Commands](#-slash-commands)
- [Error Handling](#️-error-handling)
- [Notes](#-notes)
- [Warnings](#️-warnings)
- [Bug Reporting](#-bug-reporting)

---

## 🚀 Features

### 🧩 General Commands

- **`=helps`** – Displays all available commands
- **`=ping`** – Shows the bot's latency in ms
- **`=version`** or **`=v`** – Displays the bot's version
- **`=report [message]`** – Report a bug or send feedback
- **`=stop`** – Stops the bot _(owner only)_
- **`=sync`**, **`=syncslash`**, or **`=reloadslash`** – Re-sync slash commands _(owner only)_
- **`=clearslash`**, **`=clearslashcommands`**, or **`=deleteslash`** – Remove all slash commands _(owner only)_
- **`=slashinfo`**, **`=slashdebug`**, or **`=cmdinfo`** – Display slash command diagnostics _(owner only)_

---

### 🛡️ Moderation

- **`=clear [amount]`** – Delete messages (max 70)
- **`=warn [@user] [reason] [count]`** – Warn a user
- **`=resetwarn [@user]`** – Reset user warnings
- **`=warnboard`** – Show warnings leaderboard
- **`=kick [@user] [reason]`** – Kick a user
- **`=ban [@user or ID] [reason]`** – Ban a user
- **`=unban [ID]`** – Unban a user
- **`=cleanraidsimple [name]`** – Delete a channel by name
- **`=cleanraidmultiple [date] [time]`** – Delete channels by date
- **`=giverole [@user] [@role]`** – Give a role _(owner only)_
- **`=removerole [@user] [@role]`** – Remove a role _(owner only)_
- **`=mp [@user or ID] [message]`** – Send a private message
- **`=spam [count] [#channel or mention] [message]`** – Spam messages _(admin only)_
- **`=banword [word]`** – Add a banned word
- **`=unbanword [word]`** – Remove a banned word
- **`=listbannedwords`** – Display all banned words

**Per-Server System:**

- **Warns and banned words are server-specific** – Each server has its own independent list of banned words and warns
- **No cross-server data** – Warns and banned words from one server do not affect other servers

**Automatic Features:**

- **Banned word detection** – Automatically detects and deletes messages containing banned words (per server)
- **Automatic warn** – Users receive a warn via DM when using a banned word (reason: "mot banni utilisé : [word]")
- **Automatic sanctions** – 5 warns → 10 min timeout · 10 warns → 10 min timeout · 15 warns → kick · 20 warns → ban
- **Role protection** – Protected roles are temporarily removed during sanctions and restored after timeout
- **Sanctions are server-specific** – Warns are tracked separately for each server

---

### 🧰 Utility

- **`=gpt [question]`** – Ask GPT a question
- **`=dalle [prompt]`** – Generate an image using DALL·E
- **`=repeat [#channel or @user] [message]`** – Repeat a message
- **`=8ball [question]`** – Ask the magic 8-ball
- **`=hilaire`** – Hilaire game
- **`=deldms`** – Delete all bot DMs _(admin only)_
- **`=tts [language] [volume] [text]`** – Make the bot speak (e.g. `=tts fr 3.0 Hello`)

> The bot automatically joins the user's voice channel and stays connected for other audio features.

---

### 🔗 Automatic Link Conversion

Automatically converts social-media links for cleaner Discord embeds:

- **Instagram** → `eeinstagram.com`
- **Twitter/X** → `fxtwitter.com`
- **Reddit** → `vxreddit.com` (expands short links like `redd.it`)

Original messages are deleted and replaced with the optimized link.

---

### 🎵 Soundboard

- **`=slist`** – List available sounds
- **`=splay [number]`** – Play a sound (auto joins VC)
- **`=sleave`** – Leave VC
- **`=sstop`** – Stop sound
- **`=srandom`** – Play random sounds every 1–5 min
- **`=srandomskip`** – Skip current random sound
- **`=srandomstop`** – Stop random playback
- **`=vkick [@user]`** – Kick a user from VC _(admin only)_

Supported formats : MP3 / MP4 / M4A / OGG / OPUS / WAV / FLAC / AAC

---

### 📺 YouTube Player

- **`=play [URL]`** – Play a YouTube video
- **`=search [query]`** – Search and play
- **`=skip`**, **`=stopm`**, **`=pause`**, **`=resume`**, **`=queue`**, **`=clearq`**, **`=loop`**, **`=leave`** – Manage playback

---

### 🧬 Leveling System

- **`=level [@user]`** – View level
- **`=resetlevel`** – Reset all levels _(admin only)_
- **`=levelsettings`** – Toggle leveling
- **`=levelboard`** – Show leaderboard

**Automatic Features:**

- **Automatic XP** – Each message = +1 XP (when leveling is enabled)
- **Level up formula** – Level up when XP ≥ (level + 1)²
- **Level up notification** – Automatic congratulation message when a user levels up

---

## 📦 Installation

### Requirements

- Python 3.8 or higher
- FFmpeg
- Discord Bot Token
- OpenAI API Token
- `aiohttp` library

### Steps

```bash
git clone <repository-url>
cd bot_discord
pip install -r requirements.txt
python main.py
```

### Configuration

Edit `main.py`:

```python
PATHS = {
    "token_file": "./token.txt",
    "gpt_token_file": "./tokengpt.txt",
    "ffmpeg_exe": "./ffmpeg.exe"
}
```

---

## ⚙️ Configuration

Invite the bot with :

- `bot`
- `applications.commands`

Required permissions :

- Read / Send Messages
- Manage Messages
- Kick / Ban Members
- Connect & Speak in Voice Channels

---

## 📁 Project Structure

```
bot_discord/
├── main.py                    # Point d'entrée principal, configuration centralisée
├── requirements.txt
├── cogs/                      # Commandes prefix (=)
│   ├── Help.py
│   ├── Mods.py
│   ├── Utility.py
│   ├── Soundboard.py
│   ├── Youtube.py
│   ├── Leveling.py
│   └── Owner.py               # Commandes owner-only
├── cogs_slash_commands/       # Commandes slash (/)
│   ├── Help_slash.py
│   ├── Mods_slash.py
│   ├── Utility_slash.py
│   ├── Soundboard_slash.py
│   ├── Youtube_slash.py
│   ├── Leveling_slash.py
│   └── Owner_slash.py
├── cogs_auto_commands/        # Détections automatiques et gestion d'erreurs
│   ├── ErrorHandler.py        # Gestion centralisée des erreurs
│   ├── Mods_auto.py           # Détection mots bannis + warns automatiques
│   ├── Leveling_auto.py       # Système de leveling automatique
│   ├── Utility_auto.py        # Conversion automatique des liens sociaux
│   └── Help_auto.py           # Forwarding automatique des MPs
├── json/
│   ├── warns.json             # Warns organisés par serveur: {guild_id: {user_id: {...}}}
│   ├── levels.json
│   ├── banned_words.json      # Mots bannis organisés par serveur: {guild_id: [words]}
│   └── update_logs.json
├── img/
│   ├── 8ball.png
│   ├── hilaire.png
│   ├── hilaire2.png
│   ├── version.jpg
│   └── info.png
├── Sounds/                    # Fichiers audio pour le soundboard
└── Others/
    └── Run Bot.bat
```

---

## 🧩 Slash Commands

All commands are available as **slash commands** and sync automatically on startup.  
Use :

- **`=sync`** → Force sync
- **`=clearslash`** → Remove all slash commands
- **`=slashinfo`** → Diagnostics

Global sync may take up to 1 hour to propagate.

---

## 🛡️ Error Handling

Comprehensive French-language error system with centralized error handling (`cogs_auto_commands/ErrorHandler.py`) :

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

Example :

```
┌─────────────────────────────────────┐
│  Permissions insuffisantes          │
│                                     │
│  Vous n'avez pas les permissions    │
│  nécessaires pour utiliser cette    │
│  commande.                          │
│                                     │
│  Permissions requises :             │
│  Manage Messages, Kick Members      │
└─────────────────────────────────────┘
```

---

## 📝 Notes

- Some commands work in DMs
- The bot deletes command messages after execution
- Leveling can be enabled/disabled by admins
- Automatic link conversion for Instagram, X (Twitter), and Reddit
- Soundboard, YouTube, and TTS share a single voice connection
- All paths and configurations are centralized in `main.py` (`client.paths` and `client.config`)
- Automatic features are separated into `cogs_auto_commands/` for better organization
- Error handling is centralized in `ErrorHandler.py`
- Banned words trigger automatic warnings via DM
- Protected roles are automatically managed during sanctions
- **Warns and banned words are server-specific** – Each server has independent moderation data

---

## ⚠️ Warnings

- Keep all tokens private
- Ensure required permissions are granted
- Some commands are restricted to admins or owners

---

## 🐛 Bug Reporting

Use :

```
=report [message]
```

to send feedback or report a bug.  
A ticket is automatically sent to the developer.

---

**Developed with ❤️ in Python by [NEVAR](https://github.com/NEVARLeVrai)**
