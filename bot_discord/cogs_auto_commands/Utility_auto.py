import discord
from discord.ext import commands
import re
import aiohttp
from urllib.parse import urlparse, urljoin

class Utility_auto(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return  # Ignorer les messages des bots
        
        elif 'instagram.com' in message.content:
            await self.process_instagram_message(message)
        elif 'twitter.com' in message.content:
            await self.process_twitter_message(message)
        elif 'x.com' in message.content:
            await self.process_x_message(message)
        elif 'reddit.com' in message.content or 'redd.it' in message.content:
            await self.process_reddit_message(message)


    async def process_instagram_message(self, message):
        instagram_link = re.search(r'(https?://(?:www\.)?instagram\.com/\S+)', message.content)
        if instagram_link:
            original_link = instagram_link.group(0)
            # Ne pas traiter les liens /reels/audio/
            if '/reels/audio/' in original_link:
                return
            # Supprimer tout ce qui vient après le dernier /
            modified_link = original_link.rsplit('/', 1)[0] + '/'
            modified_link = modified_link.replace('instagram.com', 'eeinstagram.com')
            await self.send_modified_message(message, modified_link, "Instagram")

    async def process_twitter_message(self, message):
        twitter_link = re.search(r'(https?://(?:www\.)?twitter\.com/\S+)', message.content)
        if twitter_link:
            original_link = twitter_link.group(0)
            modified_link = original_link.replace('twitter.com', 'fxtwitter.com')
            await self.send_modified_message(message, modified_link, "X (Twitter)")

    async def process_x_message(self, message):
        x_link = re.search(r'(https?://(?:www\.)?x\.com/\S+)', message.content)
        if x_link:
            original_link = x_link.group(0)
            modified_link = original_link.replace('x.com', 'fxtwitter.com')
            await self.send_modified_message(message, modified_link, "X (Twitter)")

    async def get_reddit_final_url(self, url):
        """Suit les redirections Reddit pour récupérer le lien PC final"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                # Essayer d'abord avec HEAD (plus rapide)
                try:
                    async with session.head(url, allow_redirects=True) as response:
                        final_url = str(response.url)
                        return final_url
                except:
                    # Si HEAD échoue, essayer avec GET
                    async with session.get(url, allow_redirects=True) as response:
                        final_url = str(response.url)
                        return final_url
        except Exception as e:
            print(f"Erreur lors de la résolution de l'URL Reddit: {e}")
            return None

    async def process_reddit_message(self, message):
        # Capturer les liens reddit.com et redd.it (liens courts)
        # Regex améliorée pour mieux capturer les liens Reddit
        reddit_link = re.search(r'(https?://(?:www\.)?(?:reddit\.com|redd\.it)/[^\s\)\]\>]+)', message.content)
        if reddit_link:
            original_link = reddit_link.group(0)
            # Nettoyer le lien (enlever les caractères de fin comme ), ], >, etc.)
            original_link = original_link.rstrip('.,;!?)>]')
            # Supprimer les paramètres de requête (tout ce qui vient après ?)
            original_link = original_link.split('?')[0]
            
            # Suivre la redirection pour récupérer le lien PC final
            final_url = await self.get_reddit_final_url(original_link)
            if final_url:
                original_link = final_url
                # Supprimer les paramètres de requête du lien final aussi
                original_link = original_link.split('?')[0]
            
            # Initialiser modified_link
            modified_link = original_link
            # Remplacer reddit.com par vxreddit.com (garde www. si présent)
            modified_link = modified_link.replace('reddit.com', 'vxreddit.com')
            await self.send_modified_message(message, modified_link, "Reddit")

    async def send_modified_message(self, message, modified_link, platform):
        try:
            await message.delete()
        except:
            # Si on ne peut pas supprimer le message (embeds, permissions, etc.), on continue
            pass
        
        # Envoyer le message modifié sans indicateur de frappe pour éviter les rate limits
        await message.channel.send(f"[{message.author.display_name} - {platform}]({modified_link})")

async def setup(client):
    await client.add_cog(Utility_auto(client))