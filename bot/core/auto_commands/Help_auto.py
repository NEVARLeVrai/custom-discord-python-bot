import discord
from discord.ext import commands
from lang.lang_utils import t

class Help_auto(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.client.user:
            return  # Ignore messages sent by the bot itself
        
        if isinstance(message.channel, discord.DMChannel):
            user = message.author
            content = message.content
            
            # Check if message is a command or mention
            if content.startswith("=") or message.mention_everyone or self.client.user in message.mentions:
                return  # Ignore command messages or mentions
            
            # Check if it's a reply to a DM initiated by =mp command
            mods_cog = self.client.get_cog('Mods')
            if mods_cog and hasattr(mods_cog, 'mp_conversations'):
                if user.id in mods_cog.mp_conversations:
                    # It's a reply to a DM initiated by =mp
                    original_sender_id = mods_cog.mp_conversations[user.id]
                    original_sender = self.client.get_user(original_sender_id)
                    
                    if original_sender:
                        await original_sender.send(f"{t('help_auto_dm_reply_title', user=user, mention=user.mention)}\n\n{content}")
                    return
            
            # Otherwise, forward to target_user_id as before
            target_user = self.client.get_user(self.client.config['target_user_id'])
            
            if target_user:
                await target_user.send(f"{t('help_auto_dm_forward_title', user=user)}\n\n{content}")

async def setup(client):
    await client.add_cog(Help_auto(client))

