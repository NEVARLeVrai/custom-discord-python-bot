import discord 
import logging
from discord import Activity, ActivityType, app_commands
from discord.ext import commands, tasks
from itertools import cycle
import os
import asyncio
import time
import sys
import shutil
# Add parent directory to path to allow importing modules from root (services, lang, etc.)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import get_current_version
import io
import traceback
import aiohttp
from aiohttp import client_exceptions
from lang.lang_utils import t
from services.moderation_service import ModerationService
from services.leveling_service import LevelingService
from services.audio_service import AudioService

# Centralized configuration
CONFIG = {
    'webhook_url': "https://discord.com/api/webhooks/1447012804182933645/XTNFKEgrdDIEXGjOsylgsh4DisblEz2VKxL3JVJcza9bnyuhjsjxi1xnsP08fPNKCqKK",
    'target_user_id': 745923070736465940,
    'short_form_domains': ['tiktok.com', 'x.com', 'twitter.com', 'instagram.com'],
    'tiktok_args': {
        'api_hostname': 'api22-normal-c-alisg.tiktokv.com',
        'app_name': 'trill',
        'app_version': '34.1.2',
        'manifest_app_version': '2023401020',
        'aid': '1180'
    }
}

# Helper function to find files (local first, then fallback to hardcoded path)
def get_file_path(local_path, fallback_path):
    """
    Search for file in local directory first, then fallback to hardcoded path.

    Args:
        local_path: Relative path to local file (e.g., "./token/token.txt")
        fallback_path: Absolute fallback path (e.g., Google Drive path)

    Returns:
        str: Path to file (local if exists, otherwise fallback)
    """
    local_absolute = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', local_path))
    if os.path.exists(local_absolute):
        return local_absolute
    return fallback_path

# Centralized paths for files and executables
PATHS = {
    'token_file': get_file_path("token/token.txt", "C:/Users/Danie/Mon Drive/Autres/Bot Python Discord/token.txt"),
    'gpt_token_file': get_file_path("token/tokengpt.txt", "C:/Users/danie/Mon Drive/Autres/Bot Python Discord/tokengpt.txt"),
    'ffmpeg_exe': str(os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'bin', 'ffmpeg.exe' if sys.platform.startswith('win') else 'ffmpeg'))),
    'node_exe': str(os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'bin', 'node.exe' if sys.platform.startswith('win') else 'node'))),
    'gpt_logs': get_file_path("logs/gptlogs.txt", "C:/Users/danie/Mon Drive/Autres/Bot Python Discord/gptlogs.txt"),
    'dalle_logs': get_file_path("logs/dallelogs.txt", "C:/Users/danie/Mon Drive/Autres/Bot Python Discord/dallelogs.txt"),
    'warns_json': "./json/warns.json",
    'levels_json': "./json/levels.json",
    'banned_words_json': "./json/banned_words.json",
    'hilaire2_png': "./img/hilaire2.png",
    'hilaire_png': "./img/hilaire.png",
    '8ball_png': "./img/8ball.png",
    'info_png': "./img/info.png",
    'version_jpg': "./img/version.jpg",
    'sounds_dir': "./Sounds",
    'slash_commands_dir': "./core/slash_commands",
    'auto_commands_dir': "./core/auto_commands",
    'update_logs_json': "./json/update_logs.json",
    'logs_bot': "./logs",
    'downloads_dir': "./downloads"
}

os.environ['PATH'] = os.path.dirname(PATHS['ffmpeg_exe']) + os.pathsep + os.path.dirname(PATHS['node_exe']) + os.pathsep + os.environ.get('PATH', '')
os.environ['YTDLP_JS_RUNTIME'] = f"node:{PATHS['node_exe']}"
LOGS_DIR = PATHS['logs_bot']
LOG_FILE = f'{LOGS_DIR}/bot.log'
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('discord_bot')

class DiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="=", intents=intents)
        
        # Add paths and config to client to access them
        self.paths = PATHS
        self.config = CONFIG
        
        # Initialize services
        self.moderation_service = ModerationService(self)
        self.leveling_service = LevelingService(self)
        self.audio_service = AudioService(self)
        
        self.error_handler_cog = None
        
        self.activities = cycle([
            Activity(name=t('activity_playing_wasabi'), type=discord.ActivityType.playing),
            Activity(name=t('activity_watching_rolls'), type=discord.ActivityType.watching),
            Activity(name=t('activity_listening_ocean'), type=ActivityType.listening),
            Activity(name=t('activity_competing_restaurant'), type=discord.ActivityType.competing),
            Activity(name=t('activity_watching_help'), type=discord.ActivityType.watching),
            Activity(name=t('activity_playing_slash'), type=discord.ActivityType.playing),
            Activity(name=t('activity_streaming_mod'), type=discord.ActivityType.streaming, url='https://www.youtube.com'),
            Activity(name=t('activity_playing_leveling'), type=discord.ActivityType.playing),
            Activity(name=t('activity_listening_sounds'), type=ActivityType.listening),
            Activity(name=t('activity_playing_music'), type=discord.ActivityType.playing),
        ])

    async def setup_hook(self):
        """Loading extensions and initial synchronization."""
        logger.info(t('extension_loading'))
        
        # Load ErrorHandler first
        try:
            await self.load_extension("auto_commands.ErrorHandler")
            self.error_handler_cog = self.get_cog('ErrorHandler')
            logger.info(t('extension_loaded', extension="auto_commands.ErrorHandler"))
        except Exception as e:
            logger.error(t('extension_load_error', error=e))
        
        # Load slash commands (/)
        slash_commands_dir = self.paths['slash_commands_dir']
        if os.path.exists(slash_commands_dir):
            for filename in os.listdir(slash_commands_dir):
                if filename.endswith(".py") and filename != "__init__.py":
                    try:
                        await self.load_extension(f"slash_commands.{filename[:-3]}")
                        logger.info(t('extension_loaded', extension=f"slash_commands.{filename[:-3]}"))
                    except Exception as e:
                        logger.error(t('extension_load_error', error=e))
                        
        # Load automatic detectors
        auto_commands_dir = self.paths['auto_commands_dir']
        if os.path.exists(auto_commands_dir):
            for filename in os.listdir(auto_commands_dir):
                if filename.endswith(".py") and filename != "__init__.py" and filename != "ErrorHandler.py":
                    try:
                        await self.load_extension(f"auto_commands.{filename[:-3]}")
                        logger.info(t('extension_loaded', extension=f"auto_commands.{filename[:-3]}"))
                    except Exception as e:
                        logger.error(t('extension_load_error', error=e))
        
        # Slash commands synchronization
        # We sync globally only once to avoid rate limits
        # Per-guild synchronization (guild=guild) is removed as it is inefficient at scale
        try:
            synced = await self.tree.sync()
            logger.info(f"{t('slash_synced')} ({len(synced)} commands)")
        except Exception as e:
            logger.error(t('slash_sync_error', error=e))

    async def on_ready(self):
        logger.info(t('bot_connected', user=self.user))
        logger.info(t('server_count', count=len(self.guilds)))
        
        if not self.change_activity.is_running():
            self.change_activity.start()

    @tasks.loop(seconds=7)
    async def change_activity(self):
        # Check that the bot is connected
        if not self.is_ready() or self.is_closed():
            return
        
        if not hasattr(self, 'ws') or self.ws is None:
            return
        
        try:
            activity = next(self.activities)
            await self.change_presence(activity=activity)
        except (discord.errors.ConnectionClosed, client_exceptions.ClientConnectionResetError, AttributeError):
            pass
        except Exception as e:
            logger.error(t('activity_change_error', error=e))

# Global instance
client = DiscordBot()

# Global error handler for the command tree
@client.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Error handler for slash commands - delegates to ErrorHandler cog"""
    if client.error_handler_cog:
        await client.error_handler_cog.handle_app_command_error(interaction, error)  # type: ignore[attr-defined]
    else:
        # Fallback if the cog is not yet loaded or found
        # Try to retrieve the cog if it was loaded in the meantime
        cog = client.get_cog('ErrorHandler')
        if cog:
            client.error_handler_cog = cog
            await cog.handle_app_command_error(interaction, error)  # type: ignore[attr-defined]
            return

        guild_id = interaction.guild.id if interaction.guild else None
        embed = discord.Embed(
            title=t('error', guild_id=guild_id),
            description=t('error_handler_not_loaded', guild_id=guild_id),
            color=discord.Color.red()
        )
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            pass
        logger.error(t('slash_command_error', error=error, guild_id=guild_id))
        logger.error(''.join(traceback.format_exception(type(error), error, error.__traceback__)))


# Log all unhandled exceptions (except asyncio)
import sys
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical(t('unhandled_exception'), exc_info=(exc_type, exc_value, exc_traceback))
sys.excepthook = handle_exception

if __name__ == "__main__":
    try:
        if os.path.exists(client.paths['downloads_dir']):
            logger.info(t('bot_starting'))
            logger.info(t('log_cleanup_downloads', path=client.paths['downloads_dir']))
            shutil.rmtree(client.paths['downloads_dir'])
        os.makedirs(client.paths['downloads_dir'], exist_ok=True)

        logger.info(t('log_ytdlp_runtime', runtime=os.environ.get('YTDLP_JS_RUNTIME')))
        logger.info(t('log_node_path', path=client.paths['node_exe']))

        with open(client.paths['token_file'], "r") as f:
            token = f.read().strip()
        client.run(token)
    except Exception as e:
        logger.critical(t('bot_stop_critical'))
        logger.critical(''.join(traceback.format_exception(type(e), e, e.__traceback__)))
        time.sleep(10)