import discord
from discord.ext import commands
import re
import aiohttp
from collections import defaultdict
import traceback
import asyncio
from services.vxt_service import vxt_service_global

# Extracted functions from original index.py
_punct_tail = '>)].,\'" \t\r\n'

def clean_url(raw: str) -> str:
    return raw.rstrip(_punct_tail)

async def fetch_fxtwitter(status_id: str, session: aiohttp.ClientSession) -> dict | None:
    api_url = f"https://api.fxtwitter.com/status/{status_id}"
    headers = {"User-Agent": "VxT"}
    async with session.get(api_url, headers=headers) as resp:
        if resp.status == 200:
            data = await resp.json()
            return data["tweet"]
    return None

async def safe_fetch_webhook(bot, webhook_id):
    try:
        return await bot.fetch_webhook(webhook_id)
    except discord.Forbidden:
        return None

def remove_extras_after_status(processed_message):
    pattern = r'(https?://(?:twitter\.com|x\.com)/[^/]+/status/\d+)\S*'
    return re.sub(pattern, r'\1', processed_message)

def split_message(message, chunk_size=2000):
    parts = message.split('\n')
    chunks = []
    current_chunk = ""
    for part in parts:
        if len(current_chunk) + len(part) + 1 > chunk_size:
            chunks.append(current_chunk)
            current_chunk = part
        else:
            current_chunk += ('\n' + part if current_chunk else part)
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

class LinkConverter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Make sure vxt_service has its bot set, though it might natively not strictly need it 
        # for most operations except perhaps some future logic
        vxt_service_global.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Initialize settings for all guilds
        await vxt_service_global.initialize_guilds(self.bot.guilds)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await vxt_service_global.initialize_guilds([guild])

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        master_settings = vxt_service_global.master_settings
        if not master_settings:
            return
        if not master_settings.get(payload.guild_id, {}).get("delete-bot-message", {}).get("toggle", False):
            return
            
        channel = await self.bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        
        if message.webhook_id:
            temp_webhook = await safe_fetch_webhook(self.bot, message.webhook_id)
            if temp_webhook is None:
                return     
            temp_bot = await message.guild.fetch_member(temp_webhook.user.id)
            if temp_bot.id == self.bot.user.id:
                reaction = next((react for react in message.reactions if "❌" in str(react.emoji)), None)
                if reaction is None:
                    return
                if reaction.count > master_settings[payload.guild_id]["delete-bot-message"]["number"]:
                    await message.delete()
                    return
                    
        if message.author == self.bot.user:
            reaction = next((react for react in message.reactions if "❌" in str(react.emoji)), None)
            if reaction and reaction.count > master_settings[payload.guild_id]["delete-bot-message"]["number"]:
                await message.delete()
                return

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        master_settings = vxt_service_global.master_settings
        if not master_settings or not message.guild:
            return
        if message.author == self.bot.user:
            return

        guild_id = message.guild.id
        g_settings = master_settings.get(guild_id, {})

        if not g_settings.get("message", {}).get("other_webhooks", False) and message.webhook_id:
            return

        if message.webhook_id:
            temp_webhook = await safe_fetch_webhook(self.bot, message.webhook_id)
            if temp_webhook is None:
                return     
            try:
                temp_bot = await message.guild.fetch_member(temp_webhook.user.id)
                if temp_bot.id in g_settings.get("blacklist", {}).get("users", []) or any(role.id in g_settings.get("blacklist", {}).get("roles", []) for role in temp_bot.roles):
                    return
            except discord.NotFound:
                pass

        if not message.webhook_id:
            blacklist = g_settings.get("blacklist", {})
            if message.author.id in blacklist.get("users", []) or (hasattr(message.author, "roles") and any(role.id in blacklist.get("roles", []) for role in message.author.roles)):
                return

        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', remove_extras_after_status(message.content))

        # conversion setting check
        conversion_map = g_settings.get("conversion", {})
        if len(conversion_map.keys()) > 0 and urls:
            converted_domains_message = await self.convert_domains_in_message(message, guild_id, urls)
            if converted_domains_message == message.content:
                return
                
            msg_mentions = discord.AllowedMentions.all()
            msg_send_mentions = discord.AllowedMentions.all()
            
            mention_remove = g_settings.get("mention-remove", [])
            if len(mention_remove) > 0 and (message.mention_everyone or len(message.mentions) > 0 or len(message.role_mentions) > 0):
                users_mentioned = message.mentions
                roles_mentioned = message.role_mentions
                filtered_members = [user for user in users_mentioned if user.mention not in mention_remove]
                filtered_roles = [role for role in roles_mentioned if role.mention not in mention_remove]
                everyone_allow = "everyone" not in mention_remove
                
                msg_mentions = discord.AllowedMentions(everyone=everyone_allow, users=filtered_members, roles=filtered_roles)
                msg_send_mentions = discord.AllowedMentions(everyone=everyone_allow, users=filtered_members, roles=filtered_roles)

            sent_message = None
            webhook_pref = g_settings.get("webhook", {}).get("preference", "webhooks")
            
            if webhook_pref == "webhooks":
                channel_webhooks = None
                perms = message.channel.permissions_for(message.guild.me)
                if not perms.manage_webhooks:
                    # Original raised BotMissingPermissions, log/fail silently here
                    return
                    
                parent_channel = message.channel.parent if isinstance(message.channel, discord.Thread) else message.channel
                channel_webhooks = await parent_channel.webhooks()
                
                matching_webhook = next((w for w in channel_webhooks if self.bot.user.id == w.user.id), None)
                if not matching_webhook:
                    matching_webhook = await parent_channel.create_webhook(name="VxT", reason="To send messages with converted links.")

                if len(converted_domains_message) >= 2000:
                    split_converted_message = split_message(converted_domains_message, 2000)
                    for split_chunk in split_converted_message:
                        webhook_params = {
                            'content': split_chunk,
                            'wait': True,
                            'username': message.author.display_name if g_settings.get("name-preference", "display name") == "display name" else message.author.name,
                            'avatar_url': message.author.display_avatar.url,
                            'files': [await attachment.to_file() for attachment in message.attachments],
                            'allowed_mentions': msg_mentions
                        }
                        if isinstance(message.channel, discord.Thread):
                            webhook_params['thread'] = message.channel
                        sent_message = await matching_webhook.send(**webhook_params)
                        if g_settings.get("delete-bot-message", {}).get("toggle", False):
                            await sent_message.add_reaction("❌")
                else:
                    webhook_params = {
                        'content': converted_domains_message,
                        'wait': True,
                        'username': message.author.display_name if g_settings.get("name-preference", "display name") == "display name" else message.author.name,
                        'avatar_url': message.author.display_avatar.url,
                        'files': [await attachment.to_file() for attachment in message.attachments],
                        'allowed_mentions': msg_mentions
                    }
                    if isinstance(message.channel, discord.Thread):
                        webhook_params['thread'] = message.channel
                    sent_message = await matching_webhook.send(**webhook_params)

            elif webhook_pref == "bot" and g_settings.get("webhook", {}).get("reply", False):
                if len(converted_domains_message) >= 2000:
                    for split_chunk in split_message(converted_domains_message, 2000):
                        sent_message = await message.reply(content=split_chunk, files=[await attachment.to_file() for attachment in message.attachments], allowed_mentions=msg_mentions)
                        if g_settings.get("delete-bot-message", {}).get("toggle", False):
                            await sent_message.add_reaction("❌")
                else:
                    sent_message = await message.reply(content=converted_domains_message, files=[await attachment.to_file() for attachment in message.attachments], allowed_mentions=msg_mentions)
            else:
                if len(converted_domains_message) >= 2000:
                    for split_chunk in split_message(converted_domains_message, 2000):
                        sent_message = await message.channel.send(content=split_chunk, files=[await attachment.to_file() for attachment in message.attachments], allowed_mentions=msg_send_mentions)
                        if g_settings.get("delete-bot-message", {}).get("toggle", False):
                            await sent_message.add_reaction("❌")
                else:
                    sent_message = await message.channel.send(content=converted_domains_message, files=[await attachment.to_file() for attachment in message.attachments], allowed_mentions=msg_send_mentions)

            if g_settings.get("delete-bot-message", {}).get("toggle", False) and sent_message:
                await sent_message.add_reaction("❌")

            if g_settings.get("message", {}).get("delete_original", True) == True:
                try:
                    await message.delete()
                except discord.NotFound:
                    pass

    async def convert_domains_in_message(self, message, guild_id, urls):
        processed_message = remove_extras_after_status(message.content)
        master_settings = vxt_service_global.master_settings
        g_settings = master_settings.get(guild_id, {})
        
        async with aiohttp.ClientSession() as session:
            domain_groups = defaultdict(list)
            for url in urls:
                try:
                    full_domain = re.search(r'https?://([\w.-]+)/?', url).group(1)
                    domain_parts = full_domain.split('.')
                    main_domain = '.'.join(domain_parts[-2:])
                    if url not in domain_groups[main_domain]:
                        domain_groups[main_domain].append(url)
                except AttributeError:
                    continue

            for domain, domain_urls in domain_groups.items():
                domain_urls = set(domain_urls)
                conversion_map = g_settings.get("conversion", {})
                if domain in conversion_map:
                    link_responses = {}

                    if (domain == "twitter.com" or domain == "x.com") and conversion_map[domain] == "fxtwitter.com":
                        processed_message = await self.convert_to_fxtwitter_domain(processed_message, message, guild_id, domain_urls, link_responses, session)  
                        continue

                    for url in domain_urls:
                        converted_url = url.replace(domain, conversion_map[domain])
                        processed_message = processed_message.replace(url, converted_url)

            return processed_message

    async def convert_to_fxtwitter_domain(self, processed_message, message, guild_id, domain_urls, link_responses, session):
        master_settings = vxt_service_global.master_settings
        g_settings = master_settings[guild_id]
        
        if g_settings.get("toggle") != vxt_service_global.default_settings["toggle-list"] or \
           g_settings.get("retweet") != vxt_service_global.default_settings["retweet-list"] or \
           g_settings.get("quote-tweet") != vxt_service_global.default_settings["quote-tweet-list"] or \
           g_settings.get("direct-media") != vxt_service_global.default_settings["direct-media-list"]:
            
            pattern = r"/status/(\d+)"
            temp_new_domain_urls = domain_urls.copy()
            direct_media_urls = set()
            mosaic_direct_media_urls = set()
            
            for link in domain_urls:
                link_clean = clean_url(link)
                match = re.search(pattern, link_clean)
                if match:
                    status_number = match.group(1)
                    tweet_json = await fetch_fxtwitter(status_number, session)
                    if tweet_json:
                        link_responses[link_clean] = tweet_json
                    else:
                        continue
                        
                    tweet_data = link_responses.get(link_clean)
                    if not tweet_data:
                        continue

                # Toggle checks
                t_set = g_settings.get("toggle", {})
                if t_set != vxt_service_global.default_settings["toggle-list"]:
                    if (not t_set.get("text", True) and len(tweet_data.get("text", "")) > 0) or \
                       (not t_set.get("polls", True) and (("quote" in tweet_data and "polls" in tweet_data["quote"]) or ("polls" in tweet_data))) or \
                       (not t_set.get("videos", True) and (("quote" in tweet_data and "media" in tweet_data["quote"] and "videos" in tweet_data["quote"]["media"]) or ("media" in tweet_data and "videos" in tweet_data["media"]))) or \
                       (not t_set.get("images", True) and (("quote" in tweet_data and "media" in tweet_data["quote"] and "photos" in tweet_data["quote"]["media"]) or ("media" in tweet_data and "photos" in tweet_data["media"]))):
                        temp_new_domain_urls.discard(link_clean)
                    else:
                        temp_new_domain_urls.add(link_clean)

                qt_set = g_settings.get("quote-tweet", {}).get("link_conversion", {})
                if not qt_set.get("follow tweets", True):
                    if not qt_set.get("all", True) or \
                       (not qt_set.get("polls", True) and (("quote" in tweet_data and "polls" in tweet_data["quote"]) or "polls" in tweet_data)) or \
                       (not qt_set.get("videos", True) and (("quote" in tweet_data and "media" in tweet_data["quote"] and "videos" in tweet_data["quote"]["media"]) or ("media" in tweet_data and "videos" in tweet_data["media"]))) or \
                       (not qt_set.get("images", True) and (("quote" in tweet_data and "media" in tweet_data["quote"] and "photos" in tweet_data["quote"]["media"]) or ("media" in tweet_data and "photos" in tweet_data["media"]))):
                        temp_new_domain_urls.discard(link_clean)
                    else:
                        temp_new_domain_urls.add(link_clean)

                dm_set = g_settings.get("direct-media", {})
                if dm_set.get("toggle") != vxt_service_global.default_settings["direct-media-list"]["toggle"] and \
                   ("allow" in dm_set.get("channel", []) or ["allow", message.channel.mention] in dm_set.get("channel", [])):
                    if (dm_set.get("toggle", {}).get("images", False) and "media" in tweet_data and "photos" in tweet_data["media"]) or \
                       (dm_set.get("toggle", {}).get("videos", False) and "media" in tweet_data and "videos" in tweet_data["media"]):
                        direct_media_urls.add(link_clean)

                    mi_set = dm_set.get("multiple_images", {})
                    if not mi_set.get("convert", True) and (("media" in tweet_data and "mosaic" in tweet_data["media"]) or "quote" in tweet_data and "media" in tweet_data["quote"] and "mosaic" in tweet_data["quote"]["media"]):
                        direct_media_urls.discard(link_clean)

                    if mi_set.get("convert", True) and mi_set.get("replace_with_mosaic", True) and \
                       (("media" in tweet_data and "mosaic" in tweet_data["media"]) or "quote" in tweet_data and "media" in tweet_data["quote"] and "mosaic" in tweet_data["quote"]["media"]):
                        direct_media_urls.discard(link_clean)
                        mosaic_direct_media_urls.add(link_clean)

                    qt_dm = dm_set.get("quote_tweet", {})
                    if qt_dm.get("convert", False) and \
                       ((dm_set.get("toggle", {}).get("images", False) and "quote" in tweet_data and "media" in tweet_data["quote"] and "images" in tweet_data["quote"]["media"]) or \
                        (dm_set.get("toggle", {}).get("videos", False) and "quote" in tweet_data and "media" in tweet_data["quote"] and "videos" in tweet_data["quote"]["media"])):
                        direct_media_urls.add(link_clean)

                    if qt_dm.get("convert", False) and mi_set.get("convert", True) and \
                       (dm_set.get("toggle", {}).get("images", False) and "quote" in tweet_data and "media" in tweet_data["quote"] and "mosaic" in tweet_data["quote"]["media"]) and \
                       mi_set.get("replace_with_mosaic", True):
                        mosaic_direct_media_urls.add(link_clean)

            # FXTwitter domain extractions
            fxtwitter_matches = re.findall(r"(https?://(?:\w+\.)?fxtwitter\.com/(?:\w+/)?status/(\d+)(?:\?\S*)?)", processed_message)
            for full_url, status_number in fxtwitter_matches:
                tweet_json = await fetch_fxtwitter(status_number, session)
                if tweet_json:
                   link_responses[full_url] = tweet_json

            urls_to_delete = set()
            if g_settings.get("retweet", {}).get("delete_original_tweet", False):
                original_tweet_text_to_url = {}
                for url, response in link_responses.items():
                    if "RT @" not in response.get("text", ""):
                        original_tweet_text_to_url[response["text"]] = url

                for url, response in link_responses.items():
                    tweet_text = response.get("text", "")
                    if tweet_text.startswith("RT @"):
                        try:
                            original_text = tweet_text[tweet_text.index(":") + 2:]
                            original_text = original_text.replace("...", "").replace("…", "").strip()
                            for original_tweet_text in original_tweet_text_to_url.keys():
                                if original_tweet_text.startswith(original_text):
                                    urls_to_delete.add(original_tweet_text_to_url[original_tweet_text])
                                    break
                        except ValueError:
                            pass

            if g_settings.get("quote-tweet", {}).get("remove quoted tweet", False):
                original_tweet_id_to_quote_tweet_url = {}
                for url, response in link_responses.items():
                    if "quote" in response:
                        original_tweet_id_to_quote_tweet_url[response["quote"]["id"]] = url
                for url, response in link_responses.items():
                    tweet_id = response.get("id")
                    if tweet_id in original_tweet_id_to_quote_tweet_url:
                        urls_to_delete.add(url)

            for url in urls_to_delete:
                processed_message = processed_message.replace(url, '')

            for url in mosaic_direct_media_urls:
                new_url = ""
                pref_quote = g_settings.get("direct-media", {}).get("quote_tweet", {}).get("prefer_quoted_tweet", True)
                if pref_quote and "quote" in link_responses[url]:
                    new_url = link_responses[url].get("quote", {}).get("media", {}).get('mosaic', {}).get("formats", {}).get("jpeg", "")
                else:
                    new_url = link_responses[url].get("media", {}).get('mosaic', {}).get("formats", {}).get("jpeg", "")
                if new_url:
                    processed_message = processed_message.replace(url, new_url)

            for url in direct_media_urls:
                new_url = ""
                dm_set = g_settings.get("direct-media", {})
                mi_set = dm_set.get("multiple_images", {})
                qt_dm = dm_set.get("quote_tweet", {})
                
                if mi_set.get("convert", True) and mi_set.get("replace_with_mosaic", True) and qt_dm.get("prefer_quoted_tweet", True) and \
                   "quote" in link_responses[url] and "media" in link_responses[url]["quote"] and "mosaic" in link_responses[url]["quote"]["media"]:
                    new_url = link_responses[url].get("quote", {}).get("media", {}).get('mosaic', {}).get("formats", {}).get("jpeg", "")
                elif mi_set.get("convert", True) and qt_dm.get("prefer_quoted_tweet", True) and \
                   "quote" in link_responses[url] and "media" in link_responses[url]["quote"] and "mosaic" in link_responses[url]["quote"]["media"]:
                    new_url = f"https://d.fxtwitter.com/i/status/{link_responses[url]['quote']['id']}/"
                elif qt_dm.get("prefer_quoted_tweet", True) and "quote" in link_responses[url]:
                    new_url = f"https://d.fxtwitter.com/i/status/{link_responses[url]['quote']['id']}/"
                else:
                    new_url = f"https://d.fxtwitter.com/i/status/{link_responses[url]['id']}/"
                processed_message = processed_message.replace(url, new_url)

            for url in temp_new_domain_urls:
                new_url = ""
                if url not in link_responses:
                    continue
                elif g_settings.get("translate", {}).get("toggle", False):
                    new_url = f"https://fxtwitter.com/i/status/{link_responses[url]['id']}/{g_settings['translate']['language']}"
                else:
                    new_url = f"https://fxtwitter.com/i/status/{link_responses[url]['id']}/"
                processed_message = processed_message.replace(url, new_url)

            return processed_message

        if g_settings.get("translate", {}).get("toggle", False):
            pattern = r"/status/(\d+)"
            for link in domain_urls:
                match = re.search(pattern, link)
                if match:
                    status_number = match.group(1)
                    converted_url = f"https://fxtwitter.com/i/status/{status_number}/{g_settings['translate']['language']}"
                    processed_message = processed_message.replace(link, converted_url)
            return processed_message
            
        return processed_message


async def setup(bot):
    await bot.add_cog(LinkConverter(bot))
