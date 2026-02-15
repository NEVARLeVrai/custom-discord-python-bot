import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import pytz
import asyncio
import json
import os
from services.version_service import get_current_version
from lang.lang_utils import t

class Mods_slash(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.moderation_service = client.moderation_service
        self.protected_role_id = self.moderation_service.protected_role_id
        self.blocked_user_id = self.moderation_service.blocked_user_id
    
    async def cog_load(self):
        # Data is already loaded by the service
        pass

    @app_commands.command(name="clear", description="Delete messages")
    @app_commands.describe(amount="Number of messages to delete (max 70)")
    @app_commands.default_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int):
        """Delete messages"""
        guild_id = interaction.guild.id if interaction.guild else None
        # Check permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(t('help_no_permission', guild_id=guild_id), ephemeral=True)
            return
        
        # Defer immediately to avoid double response issues
        await interaction.response.defer(ephemeral=False)
        
        max_amount = 70
        if amount > max_amount:
            await interaction.followup.send(t('mods_spam_max_error', max=max_amount, guild_id=guild_id), ephemeral=False)
            amount = max_amount
        
        if amount < 1:
            await interaction.followup.send(t('mods_spam_min_error', guild_id=guild_id), ephemeral=True)
            return
        
        try:
            # purge() deletes messages, but not the interaction message
            # We must delete amount messages (not amount+1 because there is no command message)
            deleted = await interaction.channel.purge(limit=amount, check=lambda m: not m.pinned)
            
            # Try to send confirmation message quickly
            # Webhook expires after 15 minutes, but we try anyway
            try:
                # Use wait=True to ensure webhook is available
                await interaction.followup.send(t('mods_clear_success', count=len(deleted), guild_id=guild_id), ephemeral=False, wait=False)
            except (discord.NotFound, discord.HTTPException) as e:
                # Webhook expired or HTTP error - send normal message to channel
                try:
                    if interaction.channel:
                        embed = discord.Embed(
                            title=t('mods_clear_title', guild_id=guild_id),
                            description=t('mods_clear_success', count=len(deleted), guild_id=guild_id),
                            color=discord.Color.green()
                        )
                        embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
                        await interaction.channel.send(embed=embed, delete_after=5)
                except Exception as channel_error:
                    # If we can't send message, just log
                    print(t('log_err_msg_send', error=channel_error, guild_id=guild_id))
            except Exception as e:
                # Other error - log but continue
                print(t('log_err_msg_send', error=e, guild_id=guild_id))
                
        except discord.Forbidden:
            error_embed = discord.Embed(
                title=t('mods_error_title', guild_id=guild_id),
                description=t('mods_clear_perm_error', guild_id=guild_id),
                color=discord.Color.red()
            )
            error_embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            try:
                await interaction.followup.send(embed=error_embed, ephemeral=True, wait=False)
            except (discord.NotFound, discord.HTTPException):
                # Webhook expired - send normal message
                try:
                    if interaction.channel:
                        await interaction.channel.send(embed=error_embed, delete_after=10)
                except:
                    pass
        except Exception as e:
            error_embed = discord.Embed(
                title=t('mods_error_title', guild_id=guild_id),
                description=t('mods_clear_error', error=str(e), guild_id=guild_id),
                color=discord.Color.red()
            )
            error_embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            try:
                await interaction.followup.send(embed=error_embed, ephemeral=True, wait=False)
            except (discord.NotFound, discord.HTTPException):
                # Webhook expired - send normal message
                try:
                    if interaction.channel:
                        await interaction.channel.send(embed=error_embed, delete_after=10)
                except:
                    pass
            except Exception as send_error:
                print(t('log_err_msg_send', error=send_error, guild_id=guild_id))

    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.describe(member="The member to kick", reason="The reason for the kick")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        """Kick a member"""
        guild_id = interaction.guild.id if interaction.guild else None
        if reason is None:
            reason = t('mods_kick_reason_default', guild_id=guild_id)
        # Check permissions
        if not interaction.user.guild_permissions.kick_members:
            await interaction.response.send_message(t('help_no_permission', guild_id=guild_id), ephemeral=True)
            return
        
        # Check that one cannot kick oneself
        if member.id == interaction.user.id:
            await interaction.response.send_message(t('mods_no_self_kick', guild_id=guild_id), ephemeral=True)
            return
        
        # Check role hierarchy
        if interaction.user.top_role <= member.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(t('mods_kick_hierarchy_error', guild_id=guild_id), ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=False)
        
        try:
            # Send DM to user
            try:
                kick_dm = discord.Embed(title=t('mods_dm_kick_title', guild_id=guild_id), description=t('mods_dm_kick_desc', server=interaction.guild.name, guild_id=guild_id), color=discord.Color.yellow())
                kick_dm.add_field(name=t('mods_moderator_field', guild_id=guild_id), value=f"{interaction.user.name} ({interaction.user.mention})", inline=False)
                kick_dm.add_field(name=t('mods_reason_field', guild_id=guild_id), value=reason, inline=False)
                kick_dm.set_footer(text=get_current_version(self.client, guild_id=guild_id))
                await member.send(embed=kick_dm)
            except discord.Forbidden:
                pass
            
            # Kick member
            await interaction.guild.kick(member, reason=reason)
            
            # Confirmation
            conf_embed = discord.Embed(title=t('mods_success_title', guild_id=guild_id), description="", color=discord.Color.yellow())
            conf_embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            conf_embed.add_field(name=t('mods_kicked_field', guild_id=guild_id), value=t('mods_kicked_desc', member=member.mention, moderator=interaction.user.mention, guild_id=guild_id), inline=False)
            conf_embed.add_field(name=t('mods_reason_field', guild_id=guild_id), value=reason, inline=False)
            conf_embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=conf_embed, ephemeral=False)
        except discord.Forbidden:
            error_embed = discord.Embed(title=t('mods_error_title', guild_id=guild_id), description=t('mods_kick_perm_error', guild_id=guild_id), color=discord.Color.red())
            await interaction.followup.send(embed=error_embed, ephemeral=True)
        except Exception as e:
            error_embed = discord.Embed(title=t('mods_error_title', guild_id=guild_id), description=t('mods_error_occurred', error=str(e), guild_id=guild_id), color=discord.Color.red())
            await interaction.followup.send(embed=error_embed, ephemeral=True)

    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.describe(member="The member to warn", reason="The reason for the warning", count="Number of warns to add (default: 1)")
    @app_commands.default_permissions(manage_messages=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str, count: int = 1):
        """Warns a member"""
        guild_id = interaction.guild.id if interaction.guild else None
        # Check if we are in a server (not in DM)
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(t('mods_no_mp_error', guild_id=guild_id), ephemeral=True)
            return

        # Checks
        if interaction.user.id == member.id:
            await interaction.response.send_message(t('mods_no_self_warn', guild_id=guild_id), ephemeral=True)
            return
        
        if member.bot:
            await interaction.response.send_message(t('mods_no_bot_warn', guild_id=guild_id), ephemeral=True)
            return
        
        if interaction.user.id == self.blocked_user_id:
            await interaction.response.send_message(t('mods_no_permission', guild_id=guild_id), ephemeral=True)
            return
        
        if count < 1:
            count = 1
        if count > 10:
            await interaction.response.send_message(t('mods_warn_max_count_error', guild_id=guild_id), ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=False)
        
        # Use service
        total_warn_count = self.moderation_service.add_warn(
            guild_id=interaction.guild.id,
            member_id=member.id,
            reason=reason,
            moderator_name=interaction.user.name,
            count=count
        )
        
        # Confirmation embed
        conf_embed = discord.Embed(title=t('mods_success_title', guild_id=guild_id), description="", color=discord.Color.orange())
        conf_embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
        
        if count > 1:
            conf_embed.add_field(name=t('mods_dm_warn_title', guild_id=guild_id), value=t('mods_warn_added', member=member.mention, count=count, moderator=interaction.user.mention, guild_id=guild_id), inline=False)
        else:
            conf_embed.add_field(name=t('mods_dm_warn_title', guild_id=guild_id), value=t('mods_warn_added_single', member=member.mention, moderator=interaction.user.mention, guild_id=guild_id), inline=False)
        
        conf_embed.add_field(name=t('mods_reason_field', guild_id=guild_id), value=reason, inline=False)
        conf_embed.add_field(name=t('mods_warn_total_field', guild_id=guild_id), value=f"{total_warn_count}", inline=False)
        conf_embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
        await interaction.followup.send(embed=conf_embed)
        
        # Send DM
        if not member.bot:
            try:
                warn_dm = discord.Embed(title=t('mods_dm_warn_title', guild_id=guild_id), description=t('mods_dm_warn_desc', server=interaction.guild.name, guild_id=guild_id), color=discord.Color.orange())
                if count > 1:
                    warn_dm.add_field(name=t('mods_dm_warn_title', guild_id=guild_id), value=t('mods_warn_added', member=member.mention, count=count, moderator=interaction.user.mention, guild_id=guild_id), inline=False)
                else:
                    warn_dm.add_field(name=t('mods_moderator_field', guild_id=guild_id), value=f"{interaction.user.name} ({interaction.user.mention})", inline=False)
                warn_dm.add_field(name=t('mods_reason_field', guild_id=guild_id), value=reason, inline=False)
                warn_dm.add_field(name=t('mods_warn_total_field', guild_id=guild_id), value=f"{total_warn_count}", inline=False)
                warn_dm.set_footer(text=get_current_version(self.client, guild_id=guild_id))
                await member.send(embed=warn_dm)
            except discord.Forbidden:
                pass

    @app_commands.command(name="resetwarn", description="Reset a member's warns")
    @app_commands.describe(member="The member whose warns to reset")
    @app_commands.default_permissions(manage_messages=True)
    async def resetwarn(self, interaction: discord.Interaction, member: discord.Member):
        """Reset a member's warns (per server)"""
        guild_id = interaction.guild.id if interaction.guild else None
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(t('mods_no_mp_error', guild_id=guild_id), ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=False)
        
        if self.moderation_service.reset_warns(interaction.guild.id, member.id):
            conf_embed = discord.Embed(title=t('mods_success_title', guild_id=guild_id), description=t('mods_reset_warn_desc', member=member.mention, guild_id=guild_id), color=discord.Color.green())
            conf_embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            conf_embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=conf_embed)
        else:
            await interaction.followup.send(t('mods_reset_warn_no_warns', member=member.mention, guild_id=guild_id), ephemeral=True)

    @app_commands.command(name="warnboard", description="Displays the warns leaderboard")
    async def warnboard(self, interaction: discord.Interaction):
        """Displays the warns leaderboard (per server)"""
        guild_id = interaction.guild.id if interaction.guild else None
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(t('mods_no_mp_error', guild_id=guild_id), ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=False)
        
        guild_id = str(interaction.guild.id)
        warns = self.moderation_service.warns
        
        if str(guild_id) not in warns or not warns[str(guild_id)]:
            embed = discord.Embed(title=t('mods_lb_title', guild_id=guild_id), description=t('mods_lb_empty', guild_id=guild_id), color=discord.Color.orange())
            await interaction.followup.send(embed=embed)
            return
        
        warn_list = []
        for m_id, data in warns[guild_id].items():
            count = data.get("count", 0)
            if count > 0:
                member = interaction.guild.get_member(int(m_id))
                warn_list.append((member, count, m_id))
        
        warn_list.sort(key=lambda x: x[1], reverse=True)
        top_warns = warn_list[:10]
        
        embed = discord.Embed(title=t('mods_lb_title', guild_id=guild_id), description=t('mods_lb_desc', server=interaction.guild.name, guild_id=guild_id), color=discord.Color.orange())
        embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
        embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
        
        leaderboard_text = ""
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        for idx, (member, count, m_id) in enumerate(top_warns):
            medal = medals[idx] if idx < len(medals) else f"{idx+1}."
            if member:
                leaderboard_text += f"{medal} **{member.display_name}** ({member.mention}) - **{count}** {t('mods_warn_suffix', guild_id=guild_id)}\n"
            else:
                leaderboard_text += f"{medal} **<@{m_id}>** ({t('mods_lb_left_server', guild_id=guild_id)}) - **{count}** {t('mods_warn_suffix', guild_id=guild_id)}\n"
        
        embed.add_field(name="", value=leaderboard_text or t('mods_lb_empty', guild_id=guild_id), inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.describe(user="The member or ID to ban", reason="The reason for the ban")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, user: str, reason: str):
        """Ban a member"""
        guild_id = interaction.guild.id if interaction.guild else None
        await interaction.response.defer(ephemeral=False)
        
        try:
            # Try to convert to int (ID) or get member
            try:
                target_id = int(''.join(filter(str.isdigit, user)))
            except ValueError:
                await interaction.followup.send(t('mods_ban_format_error', guild_id=guild_id), ephemeral=True)
                return
            
            # Ban
            try:
                await interaction.guild.ban(discord.Object(id=target_id), reason=reason)
                embed = discord.Embed(title=t('mods_success_title', guild_id=guild_id), description=t('mods_ban_id_desc', id=target_id, moderator=interaction.user.mention, guild_id=guild_id), color=discord.Color.red())
                embed.add_field(name=t('mods_reason_field', guild_id=guild_id), value=reason, inline=False)
                embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
                await interaction.followup.send(embed=embed)
            except discord.Forbidden:
                await interaction.followup.send(t('mods_ban_perm_error', guild_id=guild_id), ephemeral=True)
            except discord.NotFound:
                await interaction.followup.send(t('mods_mp_user_not_found', guild_id=guild_id), ephemeral=True)
        except Exception as e:
            await interaction.followup.send(t('mods_error_occurred', error=str(e), guild_id=guild_id), ephemeral=True)

    @app_commands.command(name="unban", description="Unban a member")
    @app_commands.describe(user_id="The ID of the user to unban")
    @app_commands.default_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str):
        """Unban a member"""
        guild_id = interaction.guild.id if interaction.guild else None
        await interaction.response.defer(ephemeral=False)
        
        try:
            user = discord.Object(id=int(user_id))
            await interaction.guild.unban(user)
            
            conf_embed = discord.Embed(title=t('mods_success_title', guild_id=guild_id), description="", color=discord.Color.green())
            conf_embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            conf_embed.add_field(name=t('mods_unban_title', guild_id=guild_id), value=t('mods_unban_desc', id=user_id, moderator=interaction.user.mention, guild_id=guild_id), inline=False)
            conf_embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=conf_embed, ephemeral=False)
        except Exception as e:
            await interaction.followup.send(t('mods_unban_error', error=str(e), guild_id=guild_id), ephemeral=True)

    @app_commands.command(name="banword", description="Add a word to the banned words list")
    @app_commands.describe(word="The word to ban")
    @app_commands.default_permissions(manage_messages=True)
    async def banword(self, interaction: discord.Interaction, word: str):
        """Adds a word to the banned words list"""
        guild_id = interaction.guild.id if interaction.guild else None
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(t('mods_no_mp_error', guild_id=guild_id), ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=False)
        
        if self.moderation_service.add_banned_word(interaction.guild.id, word):
            embed = discord.Embed(title=t('mods_success_title', guild_id=guild_id), description=t('mods_bw_added', word=word, guild_id=guild_id), color=discord.Color.green())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(t('mods_bw_already_banned', word=word, guild_id=guild_id), ephemeral=True)

    @app_commands.command(name="unbanword", description="Remove a word from the banned words list")
    @app_commands.describe(word="The word to remove")
    @app_commands.default_permissions(manage_messages=True)
    async def unbanword(self, interaction: discord.Interaction, word: str):
        """Removes a word from the banned words list"""
        guild_id = interaction.guild.id if interaction.guild else None
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(t('mods_no_mp_error', guild_id=guild_id), ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=False)
        
        if self.moderation_service.remove_banned_word(interaction.guild.id, word):
            embed = discord.Embed(title=t('mods_success_title', guild_id=guild_id), description=t('mods_bw_removed', word=word, guild_id=guild_id), color=discord.Color.green())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(t('mods_bw_not_found', word=word, guild_id=guild_id), ephemeral=True)

    @app_commands.command(name="listbannedwords", description="Displays the list of banned words")
    @app_commands.default_permissions(manage_messages=True)
    async def listbannedwords(self, interaction: discord.Interaction):
        """Displays the list of banned words"""
        guild_id = interaction.guild.id if interaction.guild else None
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(t('mods_no_mp_error', guild_id=guild_id), ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=False)
        
        guild_id = str(interaction.guild.id)
        banned_words = self.moderation_service.banned_words
        
        if str(guild_id) not in banned_words or not banned_words[str(guild_id)]:
            embed = discord.Embed(title=t('mods_bw_list_title', guild_id=guild_id), description=t('mods_bw_list_empty', guild_id=guild_id), color=discord.Color.orange())
            await interaction.followup.send(embed=embed)
            return
        
        words_list = banned_words[guild_id]
        display_list = words_list[:20]
        words_text = ", ".join(display_list)
        
        if len(words_list) > 20:
            words_text += t('mods_bw_list_more', count=len(words_list)-20, guild_id=guild_id)
            
        embed = discord.Embed(title=t('mods_bw_list_title', guild_id=guild_id), description=words_text, color=discord.Color.blue())
        embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
        embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="spam", description="Spam messages")
    @app_commands.describe(amount="Number of messages", channel="The channel where to send messages", message="The message to spam")
    @app_commands.default_permissions(administrator=True)
    async def spam(self, interaction: discord.Interaction, amount: int, channel: discord.TextChannel, message: str):
        """Spam messages"""
        guild_id = interaction.guild.id if interaction.guild else None
        await interaction.response.defer(ephemeral=False)
        
        max_amount = 200
        if amount > max_amount:
            await interaction.followup.send(t('mods_spam_max_error', max=max_amount, guild_id=guild_id), ephemeral=False)
            amount = max_amount

        embed = discord.Embed(title=t('mods_spam_sent_title', guild_id=guild_id), description=t('mods_spam_sent_desc_channel', amount=amount, channel=channel.mention, guild_id=guild_id), color=discord.Color.green())
        embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
        embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
        await interaction.followup.send(embed=embed, ephemeral=False)

        sent_messages = 0
        while sent_messages < amount:
            if sent_messages >= max_amount:
                break
            await channel.send(message)
            sent_messages += 1
            await asyncio.sleep(0.5)

    @app_commands.command(name="cleanraidsimple", description="Delete a channel by name")
    @app_commands.describe(name="The name of the channel to delete")
    @app_commands.default_permissions(manage_messages=True)
    async def cleanraidsimple(self, interaction: discord.Interaction, name: str):
        """Delete a channel by name"""
        guild_id = interaction.guild.id if interaction.guild else None
        await interaction.response.defer(ephemeral=False)
        
        found = False
        channeldel = None 
        
        for channel in self.client.get_all_channels():
            if channel.name == name:
                found = True
                channeldel = channel
                        
        if found:
            embed4 = discord.Embed(title=t('mods_raid_clean_title', guild_id=guild_id), description=t('mods_raid_clean_deleting', channel=channeldel.name, guild_id=guild_id), color=discord.Color.yellow())
            embed4.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed4.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=embed4, ephemeral=False)           
            await channeldel.delete()
            embed3 = discord.Embed(title=t('mods_raid_clean_title', guild_id=guild_id), description=t('mods_raid_clean_success', channel=channeldel.name, guild_id=guild_id), color=discord.Color.green())
            embed3.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed3.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=embed3, ephemeral=False)
            
        else:
            embed5 = discord.Embed(title=t('mods_raid_clean_title', guild_id=guild_id), description=t('mods_raid_clean_not_found', name=name, guild_id=guild_id), color=discord.Color.red())
            embed5.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed5.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=embed5, ephemeral=False)

    @app_commands.command(name="cleanraidmultiple", description="Delete channels by date")
    @app_commands.describe(raid_date="Date of raid (format: YYYY-MM-DD)", raid_time="Time of raid (format: HH:MM or HHhMM)")
    @app_commands.default_permissions(manage_messages=True)
    async def cleanraidmultiple(self, interaction: discord.Interaction, raid_date: str, raid_time: str):
        """Delete channels by date"""
        guild_id = interaction.guild.id if interaction.guild else None
        await interaction.response.defer(ephemeral=False)
        
        try:
            raid_datetime_str = raid_date + " " + raid_time.replace("h", ":")
            raid_datetime = datetime.strptime(raid_datetime_str, "%Y-%m-%d %H:%M")
            time_difference = datetime.now(pytz.utc).hour - datetime.now().hour
            raid_datetime = raid_datetime.replace(hour=time_difference+raid_datetime.hour, tzinfo=pytz.UTC)
            
            deleted_count = 0
            for channel in self.client.get_all_channels():
                if channel.created_at > raid_datetime:
                    try:
                        await channel.delete()
                        deleted_count += 1
                    except:
                        pass
            
            embed6 = discord.Embed(title=t('mods_raid_clean_time_title', guild_id=guild_id), description=t('mods_raid_clean_time_success', time=raid_datetime, guild_id=guild_id), color=discord.Color.green())
            embed6.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed6.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=embed6, ephemeral=False)
        except Exception as e:
            embed = discord.Embed(title=t('mods_error_title', guild_id=guild_id), description=t('mods_raid_clean_time_error', error=str(e), guild_id=guild_id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=embed, ephemeral=True)

    async def is_owner_check(self, interaction: discord.Interaction) -> bool:
        """Checks if the user is the bot owner"""
        try:
            app_info = await self.client.application_info()
            return interaction.user.id == app_info.owner.id
        except:
            return False

    @app_commands.command(name="giverole", description="Give a role to a user")
    @app_commands.describe(member="The user", role="The role to give")
    async def giverole(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        """Give a role"""
        guild_id = interaction.guild.id if interaction.guild else None
        # Check if user is owner
        if not await self.is_owner_check(interaction):
            await interaction.response.send_message(t('err_not_owner_desc', guild_id=guild_id), ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=False)
        
        try:
            await member.add_roles(role, reason=t('mods_giverole_reason', user=interaction.user, guild_id=guild_id))
            conf_embed = discord.Embed(title=t('mods_success_title', guild_id=guild_id), description="", color=discord.Color.random())
            conf_embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            conf_embed.add_field(name=f"@{role.name}", value=t('mods_giverole_desc', user=member.mention, guild_id=guild_id), inline=False)
            conf_embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=conf_embed, ephemeral=False)
            
        except discord.Forbidden:
            conf_embed1 = discord.Embed(title=t('mods_error_title', guild_id=guild_id), description="", color=discord.Color.red())
            conf_embed1.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            conf_embed1.add_field(name=t('mods_role_perm_error', guild_id=guild_id), value=" ", inline=False)
            conf_embed1.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=conf_embed1, ephemeral=False)
            
        except discord.HTTPException as e:
            error_embed = discord.Embed(title=t('mods_error_title', guild_id=guild_id), description=t('mods_error_occurred', error=str(e), guild_id=guild_id), color=discord.Color.red())
            error_embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=error_embed, ephemeral=True)
        except Exception as e:
            error_embed = discord.Embed(title=t('mods_error_title', guild_id=guild_id), description=t('mods_unexpected_error', error=str(e), guild_id=guild_id), color=discord.Color.red())
            error_embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=error_embed, ephemeral=True)

    @app_commands.command(name="removerole", description="Remove a role from a user")
    @app_commands.describe(member="The user", role="The role to remove")
    async def removerole(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        """Remove a role"""
        guild_id = interaction.guild.id if interaction.guild else None
        # Check if user is owner
        if not await self.is_owner_check(interaction):
            await interaction.response.send_message(t('err_not_owner_desc', guild_id=guild_id), ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=False)
        
        try:
            await member.remove_roles(role, reason=t('mods_removerole_reason', user=interaction.user, guild_id=guild_id))
            conf_embed = discord.Embed(title=t('mods_success_title', guild_id=guild_id), description="", color=discord.Color.random())
            conf_embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            conf_embed.add_field(name=f"@{role.name}", value=t('mods_removerole_desc', user=member.mention, guild_id=guild_id), inline=False)
            conf_embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=conf_embed, ephemeral=False)

        except discord.Forbidden:
            conf_embed1 = discord.Embed(title=t('mods_error_title', guild_id=guild_id), description="", color=discord.Color.red())
            conf_embed1.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            conf_embed1.add_field(name=t('mods_role_perm_error', guild_id=guild_id), value=" ", inline=False)
            conf_embed1.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=conf_embed1, ephemeral=False)

        except discord.HTTPException as e:
            error_embed = discord.Embed(title=t('mods_error_title', guild_id=guild_id), description=t('mods_error_occurred', error=str(e), guild_id=guild_id), color=discord.Color.red())
            error_embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=error_embed, ephemeral=True)
        except Exception as e:
            error_embed = discord.Embed(title=t('mods_error_title', guild_id=guild_id), description=t('mods_unexpected_error', error=str(e), guild_id=guild_id), color=discord.Color.red())
            error_embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=error_embed, ephemeral=True)

    @app_commands.command(name="mp", description="Send a private message to a user")
    @app_commands.describe(user="The user", message="The message to send")
    async def mp(self, interaction: discord.Interaction, user: discord.User, message: str):
        """Send a private message"""
        guild_id = interaction.guild.id if interaction.guild else None
        await interaction.response.defer(ephemeral=False)
        
        try:
            # Send message in DM
            await user.send(f"{t('mods_mp_user_dm_title', user=interaction.user.name, mention=interaction.user.mention, guild_id=guild_id)}\n\n{message}")
            
            # Save conversation so replies are forwarded
            self.moderation_service.set_mp_conversation(user.id, interaction.user.id)
            
            # Confirmation
            embed = discord.Embed(title=t('mods_mp_sent_title', guild_id=guild_id), description=t('mods_mp_sent_desc', user=user.mention, guild_id=guild_id), color=discord.Color.green())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed.add_field(name=t('mods_mp_field_message', guild_id=guild_id), value=message[:500] + ("..." if len(message) > 500 else ""), inline=False)
            embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=embed, ephemeral=False)
            
        except discord.Forbidden:
            embed = discord.Embed(title=t('mods_error_title', guild_id=guild_id), description=t('mods_mp_error_forbidden', user=user.mention, guild_id=guild_id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(title=t('mods_error_title', guild_id=guild_id), description=t('mods_unexpected_error', error=str(e), guild_id=guild_id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(client):
    await client.add_cog(Mods_slash(client))

