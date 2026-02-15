import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
from services.version_service import get_current_version
from lang.lang_utils import t
import asyncio

class Mods_auto(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.moderation_service = client.moderation_service
        self.protected_role_id = self.moderation_service.protected_role_id
    
    @commands.Cog.listener()
    async def on_ready(self):
        # Start task to check ended timeouts after a delay
        await asyncio.sleep(5)
        if not self.check_timeout_end.is_running():
            self.check_timeout_end.start()
    
    @tasks.loop(minutes=1)
    async def check_timeout_end(self):
        """Periodically checks if timeouts are finished and restores roles"""
        warns = self.moderation_service.warns
        
        for guild_id_str, guild_data in warns.items():
            try:
                guild = self.client.get_guild(int(guild_id_str))
                if not guild:
                    continue
                
                role = guild.get_role(self.protected_role_id)
                if not role:
                    continue
                
                for member in guild.members:
                    member_id_str = str(member.id)
                    if member_id_str in guild_data:
                        member_data = guild_data[member_id_str]
                        
                        if member.timed_out_until is None or member.timed_out_until < datetime.now(timezone.utc):
                            if member_data.get("role_removed", False):
                                    try:
                                        await member.add_roles(role, reason=t('mods_auto_role_restored_reason', guild_id=guild.id))
                                        member_data["role_removed"] = False
                                        self.moderation_service.save_warns()
                                    except Exception as e:
                                        print(t('log_err_role_restore', error=e, guild_id=guild.id))
            except Exception as e:
                print(t('log_err_timeout_check', error=e)) # Global log, guild_id not strictly needed or known here
    
    @check_timeout_end.before_loop
    async def before_check_timeout_end(self):
        await self.client.wait_until_ready()
    
    async def remove_protected_role(self, member, guild):
        """Removes the protected role"""
        try:
            role = guild.get_role(self.protected_role_id)
            if role and role in member.roles:
                await member.remove_roles(role, reason=t('mods_auto_role_temporary_removal_reason', guild_id=guild.id))
                return True
        except Exception:
            pass
        return False
    
    async def auto_warn_for_banned_word(self, member: discord.Member, guild: discord.Guild, channel: discord.TextChannel, banned_word: str):
        """Automatically warns a member for using a banned word"""
        if member.bot:
            return
        
        reason = t('mods_reason_banned_word', word=banned_word, guild_id=guild.id)
        
        # Use service
        total_warn_count = self.moderation_service.add_warn(
            guild_id=guild.id,
            member_id=member.id,
            reason=reason,
            moderator_name=t('mods_moderator_auto', guild_id=guild.id),
            count=1
        )
        
        # DM
        try:
            warn_dm = discord.Embed(title=t('mods_dm_warn_title', guild_id=guild.id), description=t('mods_dm_warn_desc', server=guild.name, guild_id=guild.id), color=discord.Color.orange())
            warn_dm.add_field(name=t('mods_moderator_field', guild_id=guild.id), value=t('mods_moderator_auto', guild_id=guild.id), inline=False)
            warn_dm.add_field(name=t('mods_reason_field', guild_id=guild.id), value=reason, inline=False)
            warn_dm.add_field(name=t('mods_warn_total_field', guild_id=guild.id), value=f"{total_warn_count}", inline=False)
            warn_dm.set_footer(text=get_current_version(self.client, guild_id=guild.id))
            await member.send(embed=warn_dm)
        except:
            pass
        
        # Automatic actions
        if total_warn_count >= 20: 
            await self.remove_protected_role(member, guild)
            try:
                await guild.ban(member, reason=t('mods_auto_ban_reason', guild_id=guild.id))
                action_embed = discord.Embed(title=t('mods_auto_action_title', guild_id=guild.id), description=t('mods_auto_ban_desc', member=member.mention, guild_id=guild.id), color=discord.Color.red())
                action_embed.set_footer(text=get_current_version(self.client, guild_id=guild.id))
                await channel.send(embed=action_embed)
            except: pass
        elif total_warn_count >= 15:
            await self.remove_protected_role(member, guild)
            try:
                await guild.kick(member, reason=t('mods_auto_kick_reason', guild_id=guild.id))
                action_embed = discord.Embed(title=t('mods_auto_action_title', guild_id=guild.id), description=t('mods_auto_kick_desc', member=member.mention, guild_id=guild.id), color=discord.Color.red())
                action_embed.set_footer(text=get_current_version(self.client, guild_id=guild.id))
                await channel.send(embed=action_embed)
            except: pass
        elif total_warn_count >= 10 or total_warn_count >= 5:
            duration = 10
            role_was_removed = await self.remove_protected_role(member, guild)
            timeout_until = datetime.now(timezone.utc) + timedelta(minutes=duration)
            try:
                await member.edit(timed_out_until=timeout_until, reason=t('mods_auto_timeout_reason', count=total_warn_count, guild_id=guild.id))
                if role_was_removed:
                    guild_id, member_id = str(guild.id), str(member.id)
                    self.moderation_service.warns[guild_id][member_id]["role_removed"] = True
                    self.moderation_service.save_warns()
                
                action_desc = t('mods_auto_timeout_desc', member=member.mention, duration=duration, count=total_warn_count, guild_id=guild.id)
                action_embed = discord.Embed(title=t('mods_auto_action_title', guild_id=guild.id), description=action_desc, color=discord.Color.yellow())
                action_embed.set_footer(text=get_current_version(self.client, guild_id=guild.id))
                await channel.send(embed=action_embed)
            except: pass

    @commands.Cog.listener()
    async def on_message(self, message):
        """Detects banned words"""
        if message.author.bot or not isinstance(message.channel, discord.TextChannel) or not message.content:
            return
        
        if message.content.startswith("="):
            return
        
        guild_id = message.guild.id
        banned_words_list = self.moderation_service.banned_words.get(str(guild_id), [])
        
        msg_lower = message.content.lower()
        for word in banned_words_list:
            if word.lower() in msg_lower:
                try:
                    await message.delete()
                    await self.auto_warn_for_banned_word(message.author, message.guild, message.channel, word)
                    break
                except:
                    pass

async def setup(client):
    await client.add_cog(Mods_auto(client))
