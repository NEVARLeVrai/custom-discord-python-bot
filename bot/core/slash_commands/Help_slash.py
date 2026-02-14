import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import io
import requests
from datetime import datetime
import os
import json
import traceback
from services.version_service import get_current_version, get_version_info, get_latest_logs, get_all_history
from lang.lang_utils import t

class HelpPaginatorView(View):
    """Pagination view for the help menu"""
    def __init__(self, embeds, files=None, client=None, timeout=300):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.files = files if files else [None] * len(embeds)
        self.current_page = 0
        self.owner = None
        self.client = client
    
    async def update_message(self, interaction: discord.Interaction):
        """Updates the message with the current embed"""
        embed = self.embeds[self.current_page]
        
        if self.client:
            current_version = get_current_version(self.client)
        else:
            current_version = t('version_null')
        
        embed.set_footer(text=f"{current_version} | {t('help_paginator_footer', current=self.current_page + 1, total=len(self.embeds))}")
        
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.embeds) - 1
        
        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.NotFound:
            pass
        except Exception as e:
            print(t('log_err_msg_update', error=e))
    
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary, disabled=True)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        """Previous button"""
        if interaction.user != self.owner:
            await interaction.response.send_message(t('help_paginator_not_owner'), ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_message(interaction)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        """Next button"""
        if interaction.user != self.owner:
            await interaction.response.send_message(t('help_paginator_not_owner'), ephemeral=True)
            return
        
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            await self.update_message(interaction)
        else:
            await interaction.response.defer()

class Help_slash(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.target_user_id = client.config['target_user_id']
        self.webhook_url = client.config['webhook_url']
    
    def get_version_footer(self):
        """Helper to get version for footers"""
        return get_current_version(self.client)

    @app_commands.command(name="ping", description="Displays the bot's ping")
    async def ping(self, interaction: discord.Interaction):
        """Slash command to display ping"""
        bot_latency = round(self.client.latency * 1000)
        embed = discord.Embed(title=t('ping_pong', latency=bot_latency), color=discord.Color.random())
        embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
        embed.set_footer(text=self.get_version_footer())
        await interaction.response.send_message(embed=embed, ephemeral=False)

    def create_help_embeds(self, user: discord.User):
        """Creates all help embeds"""
        embeds = []
        files = []
        
        # Page 1: Main Helps
        embed1 = discord.Embed(title=t('help_title'), description=t('help_all_commands'), color=discord.Color.random())
        embed1.set_author(name=t('help_requested_by', user=user.name), icon_url=user.avatar)
        embed1.add_field(name="helps", value=t('help_all_commands'))
        embed1.add_field(name="ping", value=t('help_ping_desc'))
        embed1.add_field(name="version", value=t('help_version_desc'))
        embed1.add_field(name="report", value=t('help_report_desc'))
        embeds.append(embed1)
        files.append(None)

        # Page 2: Mods
        embed2 = discord.Embed(title=t('help_mods_title'), description=t('help_mods_desc'), color=discord.Color.random())
        embed2.set_author(name=t('help_requested_by', user=user.name), icon_url=user.avatar)
        embed2.add_field(name="clear", value=t('help_clear_messages_desc'))
        embed2.add_field(name="cleanraidsimple", value=t('help_cleanraidsimple_desc'))
        embed2.add_field(name="cleanraidmultiple", value=t('help_cleanraidmultiple_desc'))
        embed2.add_field(name="warn", value=t('help_warn_desc'))
        embed2.add_field(name="resetwarn", value=t('help_resetwarn_desc'))
        embed2.add_field(name="warnboard", value=t('help_warnboard_desc'))
        embed2.add_field(name="kick", value=t('help_kick_desc'))
        embed2.add_field(name="ban", value=t('help_ban_desc'))
        embed2.add_field(name="unban", value=t('help_unban_desc'))
        embed2.add_field(name="giverole", value=t('help_giverole_desc'))
        embed2.add_field(name="removerole", value=t('help_removerole_desc'))
        embed2.add_field(name="mp", value=t('help_mp_desc'))
        embed2.add_field(name="spam", value=t('help_spam_desc'))
        embed2.add_field(name="banword", value=t('help_banword_desc'))
        embed2.add_field(name="unbanword", value=t('help_unbanword_desc'))
        embed2.add_field(name="listbannedwords", value=t('help_listbannedwords_desc'))
        embed2.add_field(name=t('help_server_system_title'), value=t('help_server_system_val'), inline=False)
        embed2.add_field(name=t('help_auto_detect_title'), value=t('help_auto_detect_val'), inline=False)
        embed2.add_field(name=t('help_auto_sanctions_title'), value=t('help_auto_sanctions_val'), inline=False)
        embeds.append(embed2)
        files.append(None)

        # Page 3: Utility
        embed3 = discord.Embed(title=t('help_utility_title'), description=t('help_utility_desc'), color=discord.Color.random())
        embed3.set_author(name=t('help_requested_by', user=user.name), icon_url=user.avatar)
        embed3.add_field(name="gpt", value=t('help_gpt_desc'))
        embed3.add_field(name="dalle", value=t('help_dalle_desc'))
        embed3.add_field(name="say", value=t('help_repeat_desc'))
        embed3.add_field(name="8ball", value=t('help_8ball_desc'))
        embed3.add_field(name="hilaire", value=t('help_hilaire_desc'))
        embed3.add_field(name="deldms", value=t('help_deldms_desc'))
        embed3.add_field(name=t('help_auto_conv_title'), value=t('help_auto_conv_val'), inline=False)
        embeds.append(embed3)
        files.append(None)

        # Page 4: Vidéos & Audio (yt-dlp)
        embed4 = discord.Embed(title=t('help_video_title'), description=t('help_video_desc'), color=discord.Color.random())
        embed4.set_author(name=t('help_requested_by', user=user.name), icon_url=user.avatar)
        embed4.add_field(name="leave", value=t('help_leave_desc'))
        embed4.add_field(name="play", value=t('help_play_desc'))
        embed4.add_field(name="search", value=t('help_search_desc'))
        embed4.add_field(name="skip", value=t('help_skip_desc'))
        embed4.add_field(name="stopm", value=t('help_stopm_desc'))
        embed4.add_field(name="pause", value=t('help_pause_desc'))
        embed4.add_field(name="resume", value=t('help_resume_desc'))
        embed4.add_field(name="queue", value=t('help_queue_desc'))
        embed4.add_field(name="clearq", value=t('help_clearq_desc'))
        embed4.add_field(name="loop", value=t('help_loop_desc'))
        embed4.add_field(name=t('help_queue_info_title'), value=t('help_queue_info_val'), inline=False)
        embeds.append(embed4)
        files.append(None)

        # Page 5: Soundboard
        embed5 = discord.Embed(title=t('help_soundboard_title'), description=t('help_soundboard_desc'), color=discord.Color.random())
        embed5.set_author(name=t('help_requested_by', user=user.name), icon_url=user.avatar)
        embed5.add_field(name="slist", value=t('help_slist_desc'))
        embed5.add_field(name="splay", value=t('help_splay_desc'))
        embed5.add_field(name="sleave", value=t('help_sleave_desc'))
        embed5.add_field(name="sstop", value=t('help_sstop_desc'))
        embed5.add_field(name="srandom", value=t('help_srandom_desc'))
        embed5.add_field(name="srandomskip", value=t('help_srandomskip_desc'))
        embed5.add_field(name="srandomstop", value=t('help_srandomstop_desc'))
        embed5.add_field(name="vkick", value=t('help_vkick_desc'))
        embed5.add_field(name="tts", value=t('help_tts_desc'))
        embed5.add_field(name=t('help_formats_title'), value=t('help_formats_val'), inline=False)
        embed5.add_field(name=t('help_conflicts_title'), value=t('help_conflicts_val'), inline=False)
        embeds.append(embed5)
        files.append(None)

        # Page 6: Leveling
        embed6 = discord.Embed(title=t('help_leveling_title'), description=t('help_leveling_desc'), color=discord.Color.random())
        embed6.set_author(name=t('help_requested_by', user=user.name), icon_url=user.avatar)
        embed6.add_field(name="level, lvl", value=t('help_level_desc'))
        embed6.add_field(name="resetlevel, rsl", value=t('help_resetlevel_desc'))
        embed6.add_field(name="levelsettings, lvls", value=t('help_levelsettings_desc'))
        embed6.add_field(name="levelboard", value=t('help_levelboard_desc'))
        embed6.add_field(name=t('help_auto_system_title'), value=t('help_auto_system_val'), inline=False)
        embeds.append(embed6)
        files.append(None)

        # Page 7: MP
        embed7 = discord.Embed(title=t('help_mp_title'), description=t('help_mp_desc_field'), color=discord.Color.random())
        embed7.set_author(name=t('help_requested_by', user=user.name), icon_url=user.avatar)
        embed7.add_field(name="helps", value=t('help_all_commands'))
        embed7.add_field(name="ping", value=t('help_ping_desc'))
        embed7.add_field(name="version", value=t('help_version_desc'))
        embed7.add_field(name="report", value=t('help_report_desc'))
        embed7.add_field(name="gpt", value=t('help_gpt_desc'))
        embed7.add_field(name="dalle", value=t('help_dalle_desc'))
        
        try:
            with open(self.client.paths['info_png'], "rb") as f:
                image_data = f.read()
            file = discord.File(io.BytesIO(image_data), "info.png")
            embed7.set_thumbnail(url="attachment://info.png")
            embeds.append(embed7)
            files.append(file)
        except Exception:
            embeds.append(embed7)
            files.append(None)

        # Page 8: Owner (Visible only if user is owner)
        # We need to check if user is owner asynchronously ideally, but here we are in a synchronous method.
        # However, create_help_embeds is called from async command, so we can't easily await here without refactoring.
        # Let's check ID directly from config for simplicity as it's targeted.
        if user.id == self.target_user_id:
            embed8 = discord.Embed(title=t('help_owner_title'), description=t('help_owner_desc'), color=discord.Color.red())
            embed8.set_author(name=t('help_requested_by', user=user.name), icon_url=user.avatar)
            embed8.add_field(name="setlang", value=t('help_setlang_desc'))
            embed8.add_field(name="stop", value=t('help_stop_desc'))
            embed8.add_field(name="sync", value=t('help_sync_desc'))
            embed8.add_field(name="slashinfo", value=t('help_slashinfo_desc'))
            embed8.add_field(name="clearslash", value=t('help_clearslash_desc'))
            embeds.append(embed8)
            files.append(None)
        
        return embeds, files

    @app_commands.command(name="helps", description="Displays all available commands")
    async def helps(self, interaction: discord.Interaction):
        """Displays all available commands with pagination"""
        await interaction.response.defer(ephemeral=False)
        
        embeds, files = self.create_help_embeds(interaction.user)
        current_version = get_current_version(self.client)
        for i, embed in enumerate(embeds):
            embeds[i].set_footer(text=f"{current_version} | {t('help_paginator_footer', current=i+1, total=len(embeds))}")
        
        view = HelpPaginatorView(embeds, files, client=self.client)
        view.owner = interaction.user
        
        file = files[0]
        if file:
            await interaction.followup.send(embed=embeds[0], view=view, file=file)
        else:
            await interaction.followup.send(embed=embeds[0], view=view)

    @app_commands.command(name="version", description="Displays the bot's version")
    @app_commands.describe(history="Displays the full history if set to 'true'")
    async def version(self, interaction: discord.Interaction, history: bool = False):
        """Displays bot version"""
        try:
            current_version = get_current_version(self.client)
            latest_logs = get_latest_logs(self.client)
            
            if history:
                all_history = get_all_history(self.client)
                if not all_history:
                    embed = discord.Embed(title=t('version_history_title'), description=t('version_none'), color=discord.Color.orange())
                    embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
                    await interaction.response.send_message(embed=embed, ephemeral=False)
                    return
                
                await interaction.response.defer(ephemeral=False)
                embed = discord.Embed(title=t('version_history_title'), description=f"**{t('version_actual')}:** {current_version}\n\n", color=discord.Color.blue())
                embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
                
                for idx, entry in enumerate(all_history[:10], 1):
                    version = entry.get("version", t('version_unknown'))
                    date = entry.get("date", t('version_date_unknown'))
                    logs = entry.get("logs", t('version_no_log'))
                    if len(logs) > 200: logs = logs[:197] + "..."
                    embed.add_field(name=f"{idx}. {version} - {date}", value=f"`{logs}`", inline=False)
                
                if len(all_history) > 10:
                    embed.set_footer(text=t('version_history_limit', total=len(all_history)))
                else:
                    embed.set_footer(text=t('version_history_count', count=len(all_history)))
                
                await interaction.followup.send(embed=embed)
                return
            
            embed = discord.Embed(title=t('version_title'), color=discord.Color.random())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embed.add_field(name="", value="")
            embed.add_field(name=t('version_actual'), value=current_version)
            
            all_history = get_all_history(self.client)
            if all_history and len(all_history) > 0:
                latest_date = all_history[0].get("date", "")
                if latest_date: embed.add_field(name=t('version_last_update'), value=latest_date)
            
            embed.add_field(name=t('version_last_logs'), value=f"`{latest_logs}`", inline=False)
            embed.add_field(name="", value="")
            embed.add_field(name=t('version_history_header'), value=t('version_history_tip'), inline=False)
            embed.add_field(name=t('version_date_format'), value="`DD/MM/YYYY`")
            
            try:
                with open(self.client.paths['version_jpg'], "rb") as f:
                    image_data = f.read()
                embed.set_thumbnail(url="attachment://version.jpg")
                await interaction.response.send_message(embed=embed, file=discord.File(io.BytesIO(image_data), "version.jpg"), ephemeral=False)
            except Exception:
                await interaction.response.send_message(embed=embed, ephemeral=False)
        except Exception:
            traceback.print_exc()

    @app_commands.command(name="report", description="Report a bug or give feedback")
    @app_commands.describe(message="The report message")
    async def report(self, interaction: discord.Interaction, message: str):
        """Report a bug"""
        await interaction.response.defer(ephemeral=True)
        
        ticket_number = datetime.now().strftime("%d%m%Y")
        data = {
            "content": f"{t('report_webhook_title')}\n\n{t('report_webhook_ticket', ticket=f'{ticket_number}{interaction.user.name}')}\n{t('report_webhook_by', user=interaction.user.name)}\n{t('report_webhook_id', id=interaction.user.id)}\n{t('report_webhook_mention', mention=interaction.user.mention)}\n\n{t('report_webhook_content', message=message)}\n\n**{self.get_version_footer()}**"
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(self.client.config['webhook_url'], json=data, headers=headers)
        
        if response.status_code == 204:
            embedc2 = discord.Embed(title=t('report_title'), description=t('report_success'), color=discord.Color.green())
            embedc2.add_field(name="", value=t('report_ticket', ticket=f"{ticket_number}{interaction.user.name}"), inline=False)
            embedc2.add_field(name="", value=t('report_fix_soon'), inline=False)
            embedc2.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embedc2.set_footer(text=self.get_version_footer())
            try: await interaction.user.send(embed=embedc2)
            except: pass
            
            embedc = discord.Embed(title=t('report_title'), description=t('report_thanks'), color=discord.Color.green())
            embedc.add_field(name="", value=t('report_ticket', ticket=f"{ticket_number}{interaction.user.name}"), inline=False)
            embedc.add_field(name="", value=t('report_fix_soon'), inline=False)
            embedc.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embedc.set_footer(text=self.get_version_footer())
            await interaction.followup.send(embed=embedc, ephemeral=True)
        else:
            embedc1 = discord.Embed(title=t('report_error'), description=t('report_send_error'), color=discord.Color.red())
            embedc1.add_field(name="", value=t('report_retry_later'), inline=False)
            embedc1.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embedc1.set_footer(text=self.get_version_footer())
            await interaction.followup.send(embed=embedc1, ephemeral=True)

async def setup(client):
    await client.add_cog(Help_slash(client))

