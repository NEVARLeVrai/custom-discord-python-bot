import discord 
from discord import Activity, ActivityType, app_commands
from discord.ext import commands, tasks
from itertools import cycle
import os
import asyncio
import time
from cogs.Help import get_current_version
import io
import traceback
import aiohttp



# Initialiser le bot avec les intents nécessaires
intents = discord.Intents.all()
client = commands.Bot(command_prefix="=", intents=intents)

# Chemins centralisés pour les fichiers et exécutables
PATHS = {
    'token_file': "C:/Users/danie/Mon Drive/Bot Python Discord/token.txt",
    'gpt_token_file': "C:/Users/danie/Mon Drive/Bot Python Discord/tokengpt.txt",
    'ffmpeg_exe': r"C:/Users/Danie/Mon Drive/Bot Python Discord/ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe",
    'gpt_logs': "C:/Users/danie/Mon Drive/Bot Python Discord/gptlogs.txt",
    'dalle_logs': "C:/Users/danie/Mon Drive/Bot Python Discord/dallelogs.txt",
    'warns_json': "./json/warns.json",
    'levels_json': "./json/levels.json",
    'banned_words_json': "./json/banned_words.json",
    'hilaire2_png': "./img/hilaire2.png",
    'hilaire_png': "./img/hilaire.png",
    '8ball_png': "./img/8ball.png",
    'info_png': "./img/info.png",
    'version_jpg': "./img/version.jpg",
    'sounds_dir': "./Sounds",
    'cogs_dir': "./cogs",
    'cogs_slash_dir': "./cogs_slash_commands",
    'cogs_auto_commands_dir': "./cogs_auto_commands",
    'update_logs_json': "./json/update_logs.json"
}

# Configuration centralisée
CONFIG = {
    'webhook_url': "https://discord.com/api/webhooks/1447012804182933645/XTNFKEgrdDIEXGjOsylgsh4DisblEz2VKxL3JVJcza9bnyuhjsjxi1xnsP08fPNKCqKK",
    'target_user_id': 745923070736465940,
}

# Ajouter les chemins et la config au client pour y accéder depuis les cogs
client.paths = PATHS
client.config = CONFIG

activities = cycle([
    Activity(name='avec du wasabi 🌶️', type=discord.ActivityType.playing),
    Activity(name='des rolls californiens 🍙', type=discord.ActivityType.watching),
    Activity(name='l\'océan pacifique 🌊', type=ActivityType.listening),
    Activity(name='au restaurant japonais 🍱', type=discord.ActivityType.competing),
    Activity(name='=helps pour l\'aide', type=discord.ActivityType.watching),
    Activity(name='des commandes slash 🎯', type=discord.ActivityType.playing),
    Activity(name='la modération 🛡️', type=discord.ActivityType.streaming, url='https://www.youtube.com'),
    Activity(name='le leveling 📊', type=discord.ActivityType.playing),
    Activity(name='des sounds 🔊', type=ActivityType.listening),
    Activity(name='YouTube Music 🎵', type=discord.ActivityType.playing),
])

@client.event
async def on_ready():
    print(f"Bot connecté: {client.user}")
    print(f"Nombre de serveurs: {len(client.guilds)}\n")
    
    await asyncio.sleep(1)
    change_activity.start()
    
    # Synchroniser les commandes slash
    try:
        # Synchronisation par serveur (instantanée)
        for guild in client.guilds:
            try:
                await client.tree.sync(guild=guild)
            except:
                pass
        
        # Synchronisation globale
        await client.tree.sync()
        print("Commandes slash synchronisées\n")
    except Exception as e:
        print(f"Erreur lors de la synchronisation: {e}\n")


async def load():
    global error_handler_cog
    
    # Charger ErrorHandler en premier depuis cogs_auto_commands pour gérer les erreurs dès le début
    try:
        await client.load_extension("cogs_auto_commands.ErrorHandler")
        error_handler_cog = client.get_cog('ErrorHandler')
        print(f"Chargé: cogs_auto_commands.ErrorHandler")
    except Exception as e:
        print(f"Erreur lors du chargement de cogs_auto_commands.ErrorHandler: {e}")
    
    # Charger les cogs avec commandes prefix (=)
    cogs_dir = client.paths['cogs_dir']
    for filename in os.listdir(cogs_dir):
        # Ignorer __init__.py
        if filename.endswith(".py") and filename != "__init__.py":
            try:
                await client.load_extension(f"cogs.{filename[:-3]}")
                print(f"Chargé: cogs.{filename[:-3]}")
            except Exception as e:
                print(f"Erreur lors du chargement de cogs.{filename[:-3]}: {e}")
    
    # Charger les cogs avec commandes slash (/)
    cogs_slash_dir = client.paths['cogs_slash_dir']
    if os.path.exists(cogs_slash_dir):
        for filename in os.listdir(cogs_slash_dir):
            # Ignorer __init__.py
            if filename.endswith(".py") and filename != "__init__.py":
                try:
                    await client.load_extension(f"cogs_slash_commands.{filename[:-3]}")
                    print(f"Chargé: cogs_slash_commands.{filename[:-3]}")
                except Exception as e:
                    print(f"Erreur lors du chargement de cogs_slash_commands.{filename[:-3]}: {e}")
                    
    # Charger les detecteurs automatiques (ErrorHandler déjà chargé, on l'ignore)
    cogs_auto_commands_dir = client.paths['cogs_auto_commands_dir']
    if os.path.exists(cogs_auto_commands_dir):
        for filename in os.listdir(cogs_auto_commands_dir):
            # Ignorer __init__.py et ErrorHandler.py (déjà chargé)
            if filename.endswith(".py") and filename != "__init__.py" and filename != "ErrorHandler.py":
                try:
                    await client.load_extension(f"cogs_auto_commands.{filename[:-3]}")
                    print(f"Chargé: cogs_auto_commands.{filename[:-3]}")
                except Exception as e:
                    print(f"Erreur lors du chargement de cogs_auto_commands.{filename[:-3]}: {e}")


@tasks.loop(seconds=7)
async def change_activity():
    # Vérifier que le bot est connecté et que la connexion WebSocket est stable
    if not client.is_ready() or client.is_closed():
        return
    
    # Vérifier que la connexion WebSocket existe
    if not hasattr(client, 'ws') or client.ws is None:
        return
    
    try:
        activity = next(activities)
        await client.change_presence(activity=activity)
    except (discord.errors.ConnectionClosed, aiohttp.client_exceptions.ClientConnectionResetError, AttributeError):
        # La connexion est en train de se fermer ou de se reconnecter, on ignore l'erreur
        pass
    except Exception as e:
        # Autres erreurs inattendues - on les log mais on continue
        print(f"Erreur lors du changement d'activité: {e}")
   
# Enregistrer les gestionnaires d'erreurs depuis le cog ErrorHandler
# Note: on_command_error fonctionne avec @commands.Cog.listener() dans le cog
# mais on_app_command_error doit être enregistré manuellement car il utilise @client.tree.error
error_handler_cog = None

@client.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Gestionnaire d'erreurs pour les commandes slash - délègue au cog ErrorHandler"""
    if error_handler_cog:
        await error_handler_cog.handle_app_command_error(interaction, error)
    else:
        # Fallback si le cog n'est pas encore chargé
        embed = discord.Embed(
            title="Erreur",
            description="Une erreur s'est produite. Le gestionnaire d'erreurs n'est pas encore chargé.",
            color=discord.Color.red()
        )
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            pass
        print(f"Erreur dans la commande slash (cog non chargé): {error}")
        traceback.print_exception(type(error), error, error.__traceback__)

# Les commandes owner-only (sync, slashinfo, clearslash, stop) sont maintenant dans cogs/Owner.py

# Run the bot
if __name__ == "__main__":
    try:
        print("Chargement des extensions...")
        print("")
        # Charger les extensions de manière synchrone avant le démarrage
        loop = asyncio.get_event_loop()
        loop.run_until_complete(load())
        print("")
        print("Démarrage du bot...")
        print("")
        with open(client.paths['token_file'], "r") as f:
            token = f.read().strip()
        client.run(token)
    except Exception as e:
        print("")
        print("Arrêté: impossible de lancer le bot")
        traceback.print_exc()
        time.sleep(10)