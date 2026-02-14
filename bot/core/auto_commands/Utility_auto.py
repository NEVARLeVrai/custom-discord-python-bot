import discord
from discord.ext import commands
import re
import aiohttp
from urllib.parse import urlparse, urljoin
from lang.lang_utils import t

class Utility_auto(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return  # Ignore bot messages
        
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
            # Do not process /reels/audio/ links
            if '/reels/audio/' in original_link:
                return
            # Remove everything after the last /
            modified_link = original_link.rsplit('/', 1)[0] + '/'
            modified_link = modified_link.replace('instagram.com', 'eeinstagram.com')
            await self.send_modified_message(message, modified_link, t('platform_instagram'))

    async def process_twitter_message(self, message):
        twitter_link = re.search(r'(https?://(?:www\.)?twitter\.com/\S+)', message.content)
        if twitter_link:
            original_link = twitter_link.group(0)
            modified_link = original_link.replace('twitter.com', 'fxtwitter.com')
            await self.send_modified_message(message, modified_link, t('platform_twitter'))

    async def process_x_message(self, message):
        x_link = re.search(r'(https?://(?:www\.)?x\.com/\S+)', message.content)
        if x_link:
            original_link = x_link.group(0)
            modified_link = original_link.replace('x.com', 'fxtwitter.com')
            await self.send_modified_message(message, modified_link, t('platform_twitter'))

    async def get_reddit_final_url(self, url):
        """Follows Reddit redirects to get final PC link"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                # Try with HEAD first (faster)
                try:
                    async with session.head(url, allow_redirects=True) as response:
                        final_url = str(response.url)
                        return final_url
                except:
                    # If HEAD fails, try with GET
                    async with session.get(url, allow_redirects=True) as response:
                        final_url = str(response.url)
                        return final_url
        except Exception as e:
            print(t('log_err_reddit_resolve', error=e))
            return None

    async def process_reddit_message(self, message):
        # Capture reddit.com and redd.it links (short links)
        # Improved regex to better capture Reddit links
        reddit_link = re.search(r'(https?://(?:www\.)?(?:reddit\.com|redd\.it)/[^\s\)\]\>]+)', message.content)
        if reddit_link:
            original_link = reddit_link.group(0)
            # Clean link (remove trailing chars like ), ], >, etc.)
            original_link = original_link.rstrip('.,;!?)>]')
            # Remove query parameters (everything after ?)
            original_link = original_link.split('?')[0]
            
            # Follow redirect to get final PC link
            final_url = await self.get_reddit_final_url(original_link)
            if final_url:
                original_link = final_url
                # Remove query parameters from final link too
                original_link = original_link.split('?')[0]
            
            # Initialize modified_link
            modified_link = original_link
            # Replace reddit.com with vxreddit.com (keeps www. if present)
            modified_link = modified_link.replace('reddit.com', 'vxreddit.com')
            await self.send_modified_message(message, modified_link, t('platform_reddit'))

    async def send_modified_message(self, message, modified_link, platform):
        try:
            await message.delete()
        except:
            # If message cannot be deleted (embeds, permissions, etc.), continue
            pass
        
        # Send modified message without typing indicator to avoid rate limits
        await message.channel.send(f"[{message.author.display_name} - {platform}]({modified_link})")

async def setup(client):
    await client.add_cog(Utility_auto(client))