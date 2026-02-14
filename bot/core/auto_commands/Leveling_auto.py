import discord
from discord.ext import commands
import json
from services.version_service import get_current_version
from lang.lang_utils import t

class Leveling_auto(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.leveling_service = client.leveling_service
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not isinstance(message.channel, discord.TextChannel):
            return

        # XP attribution via service
        new_lvl, leveled_up = self.leveling_service.add_xp(message.author.id)
        
        if leveled_up:
            embed = discord.Embed(
                title=t('lvl_new_level_title'), 
                description=t('lvl_new_level_desc', user=message.author.mention, level=new_lvl), 
                color=discord.Color.green()
            )
            embed.set_author(name=f"{message.author.name}", icon_url=message.author.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await message.channel.send(embed=embed)

async def setup(client):
    await client.add_cog(Leveling_auto(client))
