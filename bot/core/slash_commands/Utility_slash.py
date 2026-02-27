import discord
from discord import app_commands
from discord.ext import commands, tasks
import random
import io
import asyncio
import traceback
import json
import os
import time
import re
import uuid
import pytz
from services.version_service import get_current_version
from lang.lang_utils import t
import datetime
from openai import OpenAI
from typing import Union

class Utility_slash(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.is_processing = False
        gpt_token_path = client.paths['gpt_token_file']
        with open(gpt_token_path, "r") as f:
            GPT_API_KEY = f.read().strip()
        self.openai_client = OpenAI(api_key=GPT_API_KEY)
        self.rate_limit_delay = 1
        
        # Reminder setup
        self.reminders_path = client.paths['reminders_json']
        self.timezone_path = os.path.join(os.path.dirname(self.reminders_path), 'user_timezones.json')
        self.check_reminders.start()

    async def cog_load(self):
        # Register the persistent view
        self.client.add_view(ReminderView(self))

    def cog_unload(self):
        self.check_reminders.cancel()
    
    def is_bot_dm(self, message):
        return message.author == self.client.user and isinstance(message.channel, discord.DMChannel)

    @app_commands.command(name="tts", description="Make the bot speak")
    @app_commands.describe(lang="TTS language (default: server lang)", vol="TTS volume (default: 3.0)", text="Text to speak")
    async def tts(self, interaction: discord.Interaction, text: str, lang: str = None, vol: float = 3.0):
        """TTS slash command"""
        guild_id = interaction.guild.id if interaction.guild else None
        
        # Determine language if not provided
        if lang is None:
            from lang.lang_utils import GUILD_LANGS, DEFAULT_LANG
            lang = GUILD_LANGS.get(str(guild_id), DEFAULT_LANG)
        if not interaction.user.voice:
            embed = discord.Embed(title=t('audio_error_title', guild_id=guild_id), description=t('audio_not_connected', guild_id=guild_id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        await interaction.response.defer(ephemeral=False)
        voice = await self.client.audio_service.connect_to_vocal(interaction.user.voice.channel)
        if not voice: return

        embed = discord.Embed(
            title=t('sb_play_title', guild_id=guild_id), 
            description=t('tts_success_desc', vol=vol, lang=lang, text=text, guild_id=guild_id), 
            color=discord.Color.green()
        )
        embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
        embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
        await interaction.followup.send(embed=embed)
        
        await self.client.audio_service.play_tts(interaction.guild, text, lang, vol)

    @app_commands.command(name="gpt", description="Use GPT to answer a question")
    @app_commands.describe(question="Your question for GPT")
    async def gpt(self, interaction: discord.Interaction, question: str):
        """GPT slash command"""
        guild_id = interaction.guild.id if interaction.guild else None
        if self.is_processing:
            await interaction.response.send_message(t('gpt_error_running', guild_id=guild_id), ephemeral=True)
            return

        self.is_processing = True
        await interaction.response.defer(ephemeral=False)

        try:
            response = self.get_gpt_response(question, guild_id=guild_id)
            if not response:
                await interaction.followup.send(t('gpt_error_none', guild_id=guild_id), ephemeral=True)
                return
                
            response = self.clean_text(response)
            response_with_mention = f"{interaction.user.mention}\n{response}"
            
            if len(response_with_mention) > 2000:
                await self.send_long_message_slash(interaction, response_with_mention, guild_id=guild_id)
            else:
                await interaction.followup.send(response_with_mention, ephemeral=False)

            # Log request
            try:
                gpt_logs_path = self.client.paths['gpt_logs']
                with open(gpt_logs_path, "a", encoding='utf-8') as f:
                    current_time = datetime.datetime.now()
                    f.write(f"{t('log_date', guild_id=guild_id)}: {current_time.strftime('%Y-%m-%d')}\n")
                    f.write(f"{t('log_time', guild_id=guild_id)}: {current_time.strftime('%H:%M:%S')}\n")
                    f.write(f"{t('log_user', guild_id=guild_id)}: {interaction.user.mention}\n")                
                    f.write(f"{t('log_question', guild_id=guild_id)}: {question}\n")
                    f.write(f"{t('log_response', guild_id=guild_id)}: {response}\n")
                    f.write("-" * 50 + "\n")
            except Exception as e:
                print(t('gpt_log_error', error=e))

        except Exception as e:
            error_embed = discord.Embed(title=t('gpt_error_title', guild_id=guild_id), description=t('mods_unexpected_error', error=str(e), guild_id=guild_id), color=discord.Color.red())
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            print(t('log_err_slash_general', command='GPT', error=e, guild_id=guild_id))
        finally:
            self.is_processing = False

    def get_gpt_response(self, question, guild_id=None):
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": t('gpt_system_prompt', guild_id=guild_id)},
                    {"role": "user", "content": question}
                ],
                max_completion_tokens=4000,
                temperature=1
            )
            bot_response = response.choices[0].message.content.strip()
            print(t('gpt_log_header', guild_id=guild_id))
            print(t('gpt_log_question', user="User", question=question, guild_id=guild_id))
            print(t('gpt_log_response', response=bot_response[:50] + "...", guild_id=guild_id))
            return bot_response
        except Exception as e:
            print(t('log_err_slash_general', command='GPT', error=e, guild_id=guild_id))
            return t('gpt_response_error', error=str(e), guild_id=guild_id)

    def clean_text(self, text):
        text_cleaned = "\n".join(line for line in text.splitlines() if line.strip())
        return text_cleaned

    async def send_long_message_slash(self, interaction, message, guild_id=None):
        """Splits a long message into multiple messages to respect Discord limit"""
        max_length = 1900
        parts = []
        
        while len(message) > max_length:
            split_point = message.rfind('\n', 0, max_length)
            if split_point == -1:
                split_point = max_length
            
            parts.append(message[:split_point])
            message = message[split_point:].lstrip()
        
        if message:
            parts.append(message)
        
        for i, part in enumerate(parts):
            if i == 0:
                await interaction.followup.send(part, ephemeral=False)
            else:
                await interaction.followup.send(t('long_message_suite', current=i+1, total=len(parts), guild_id=guild_id) + f"\n{part}", ephemeral=False)
            await asyncio.sleep(0.5)

    @app_commands.command(name="dalle", description="Generate an image with DALL-E")
    @app_commands.describe(question="Your prompt for DALL-E")
    async def dalle(self, interaction: discord.Interaction, question: str):
        """DALL-E slash command"""
        guild_id = interaction.guild.id if interaction.guild else None
        if self.is_processing:
            await interaction.response.send_message(t('gpt_error_running', guild_id=guild_id), ephemeral=True)
            return

        self.is_processing = True
        await interaction.response.defer(ephemeral=False)

        try:
            response = self.get_dalle_response(question, guild_id=guild_id)
            if not response:
                await interaction.followup.send(t('dalle_error_none', guild_id=guild_id), ephemeral=True)
                return
                
            response_with_mention = f"{interaction.user.mention}\n{response}"
            await interaction.followup.send(response_with_mention, ephemeral=False)

            # Log request
            try:
                dalle_logs_path = self.client.paths['dalle_logs']
                with open(dalle_logs_path, "a", encoding='utf-8') as f:
                    current_time = datetime.datetime.now()
                    f.write(f"{t('log_date', guild_id=guild_id)}: {current_time.strftime('%Y-%m-%d')}\n")
                    f.write(f"{t('log_time', guild_id=guild_id)}: {current_time.strftime('%H:%M:%S')}\n")
                    f.write(f"{t('log_user', guild_id=guild_id)}: {interaction.user.mention}\n")                
                    f.write(f"{t('log_question', guild_id=guild_id)}: {question}\n")
                    f.write(f"{t('log_response', guild_id=guild_id)}: {response}\n")
                    f.write("-" * 50 + "\n")
            except Exception as e:
                print(t('dalle_log_error', error=e))

        except Exception as e:
            error_embed = discord.Embed(title=t('dalle_error_title', guild_id=guild_id), description=t('mods_unexpected_error', error=str(e), guild_id=guild_id), color=discord.Color.red())
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            print(t('log_err_slash_general', command='DALL-E', error=e, guild_id=guild_id))
        finally:
            self.is_processing = False

    def get_dalle_response(self, question, guild_id=None):
        try:
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=question,
                n=1,
                size="1024x1024",
                quality="standard"
            )
            bot_response = response.data[0].url
            print(t('dalle_log_header', guild_id=guild_id))
            print(t('dalle_log_prompt', user="User", prompt=question, guild_id=guild_id))
            print(t('dalle_log_response', user="User", guild_id=guild_id))
            return bot_response
        except Exception as e:
            print(t('log_err_slash_general', command='DALL-E', error=e, guild_id=guild_id))
            return t('dalle_response_error', error=str(e), guild_id=guild_id)

    @app_commands.command(name="8ball", description="Ask the magic 8-ball a question")
    @app_commands.describe(question="Your question")
    async def magicball(self, interaction: discord.Interaction, question: str):
        """8ball slash command"""
        guild_id = interaction.guild.id if interaction.guild else None
        responses_count = 16
        response = t(f'magicball_res_{random.randint(1, responses_count)}', guild_id=guild_id)
        embed=discord.Embed(title=t('magicball_title', guild_id=guild_id), color=discord.Color.purple())
        embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
        embed.add_field(name=t('magicball_question_field', guild_id=guild_id), value=f'{question}')
        embed.add_field(name=t('magicball_response_field', guild_id=guild_id), value=f'{response}')
        embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
        with open(self.client.paths['8ball_png'], "rb") as f:
            image_data = f.read()
        embed.set_thumbnail(url="attachment://8ball.png")
        await interaction.response.send_message(embed=embed, file=discord.File(io.BytesIO(image_data), "8ball.png"), ephemeral=False)

    @app_commands.command(name="hilaire", description="Hilaire game")
    async def hilaire(self, interaction: discord.Interaction):
        """Hilaire slash command"""
        guild_id = interaction.guild.id if interaction.guild else None
        responses_count = 11
        response = t(f'hilaire_res_{random.randint(1, responses_count)}', guild_id=guild_id)
        embed=discord.Embed(title=t('hilaire_title', guild_id=guild_id), color=discord.Color.purple())
        embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
        embed.add_field(name=t('hilaire_field', guild_id=guild_id), value=f'{response}')
        embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
        with open(self.client.paths['hilaire_png'], "rb") as f:
            image_data = f.read()
        embed.set_thumbnail(url="attachment://hilaire.png")
        await interaction.response.send_message(embed=embed, file=discord.File(io.BytesIO(image_data), "hilaire.png"), ephemeral=False)

    @app_commands.command(name="say", description="Send a message in a channel")
    @app_commands.describe(channel="The channel where to send the message", message="The message to send")
    @app_commands.default_permissions(manage_messages=True)
    async def say_channel(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        """Sends a message in a channel"""
        guild_id = interaction.guild.id if interaction.guild else None
        # Check if user has necessary permissions
        if not interaction.user.guild_permissions.manage_messages and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(t('say_perm_error', guild_id=guild_id), ephemeral=True)
            return
        
        # Check if bot can send messages in the channel
        bot_member = interaction.guild.get_member(self.client.user.id)
        if not channel.permissions_for(bot_member).send_messages:
            await interaction.response.send_message(t('say_bot_perm_error', channel=channel.mention, guild_id=guild_id), ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=False)
        
        try:
            await channel.send(message)
            embed = discord.Embed(title=t('say_success_title', guild_id=guild_id), description=t('say_success_desc', channel=channel.mention, guild_id=guild_id), color=discord.Color.green())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=embed, ephemeral=False)
        except discord.Forbidden:
            embed = discord.Embed(title=t('err_forbidden_title', guild_id=guild_id), description=t('say_bot_perm_error', channel=channel.mention, guild_id=guild_id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.HTTPException as e:
            embed = discord.Embed(title=t('err_http_title', guild_id=guild_id), description=t('err_http_desc', error=str(e), guild_id=guild_id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(title=t('error', guild_id=guild_id), description=t('mods_unexpected_error', error=str(e), guild_id=guild_id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=embed, ephemeral=True)
            
    @app_commands.command(name="deldms", description="Delete all bot DMs")
    @app_commands.default_permissions(administrator=True)
    async def delmp(self, interaction: discord.Interaction):
        """Deletes all bot DMs"""
        guild_id = interaction.guild.id if interaction.guild else None
        await interaction.response.defer(ephemeral=False)
        
        try:
            total_deleted = 0
            embed = discord.Embed(title=t('deldms_loading', guild_id=guild_id), color=discord.Color.yellow())
            embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=embed, ephemeral=False)

            tasks = []
            for member in interaction.guild.members:
                if not member.bot:
                    dm_channel = await member.create_dm()
                    messages_to_delete = [msg async for msg in dm_channel.history() if self.is_bot_dm(msg)]
                    deleted_count = len(messages_to_delete)

                    if deleted_count > 0:
                        tasks.append(dm_channel.send(t('deldms_done', guild_id=guild_id), delete_after=10))
                        tasks.append(asyncio.gather(*[msg.delete() for msg in messages_to_delete]))
                        await asyncio.sleep(self.rate_limit_delay)

                    total_deleted += deleted_count

                    if deleted_count > 0:
                        embed = discord.Embed(title=t('deldms_member_done_title', user=f"{member.name}#{member.discriminator}", guild_id=guild_id), color=discord.Color.green())
                        embed.add_field(name=t('deldms_member_done_desc', guild_id=guild_id), value=str(deleted_count))
                        embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
                        tasks.append(interaction.channel.send(embed=embed, delete_after=10))
                        await asyncio.sleep(self.rate_limit_delay)

            await asyncio.gather(*tasks)
            
            if total_deleted > 0:
                embed1 = discord.Embed(title=t('deldms_total_title', guild_id=guild_id), description=f"{total_deleted}", color=discord.Color.purple())
            else:
                embed1 = discord.Embed(title=t('deldms_total_none', guild_id=guild_id), color=discord.Color.red())
            embed1.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=embed1, ephemeral=False)
            
        except Exception as e:
            embed = discord.Embed(title=t('error', guild_id=guild_id), description=t('mods_unexpected_error', error=str(e), guild_id=guild_id), color=discord.Color.red())
            embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.followup.send(embed=embed, ephemeral=True)
            import traceback
            traceback.print_exc()
    @app_commands.command(name="leave", description="Disconnect the bot from voice channel")
    async def leave(self, interaction: discord.Interaction):
        """Unified leave command"""
        guild_id = interaction.guild.id if interaction.guild else None
        voice = discord.utils.get(self.client.voice_clients, guild=interaction.guild)
        if voice:
            # Stop any music progress tasks if it was a music session
            audio_cog = self.client.get_cog('AudioPlayer')
            if audio_cog:
                if guild_id in audio_cog.progress_tasks:
                    audio_cog.progress_tasks[guild_id].cancel()
                    del audio_cog.progress_tasks[guild_id]
                
                # Session cleanup for downloads
                asyncio.create_task(audio_cog._robust_session_cleanup())
            
            # Stop any soundboard random tasks
            sb_cog = self.client.get_cog('Soundboard_slash')
            if sb_cog and hasattr(sb_cog, 'random_task') and sb_cog.random_task and not sb_cog.random_task.done():
                sb_cog.random_task.cancel()

            await voice.disconnect()
            
            # Use a generic leave translation or fallback
            try:
                desc = t('music_btn_stopped', guild_id=guild_id) # Using an existing one or create stay consistent
            except:
                desc = "Bot disconnected."
            
            embed = discord.Embed(title=t('yt_leave_title', guild_id=guild_id), description=t('yt_leave_desc', guild_id=guild_id), color=discord.Color.green())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title=t('audio_error_title', guild_id=guild_id), description=t('audio_not_connected', guild_id=guild_id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- Reminder Logic ---

    def load_reminders(self):
        if os.path.exists(self.reminders_path):
            try:
                with open(self.reminders_path, "r", encoding='utf-8') as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            except:
                return []
        return []

    def save_reminders(self, reminders):
        with open(self.reminders_path, "w", encoding='utf-8') as f:
            json.dump(reminders, f, indent=4)

    def load_timezones(self):
        if os.path.exists(self.timezone_path):
            try:
                with open(self.timezone_path, "r", encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_timezones(self, timezones):
        with open(self.timezone_path, "w", encoding='utf-8') as f:
            json.dump(timezones, f, indent=4)

    def get_user_timezone(self, user_id):
        timezones = self.load_timezones()
        tz_name = timezones.get(str(user_id))
        if tz_name:
            try:
                return pytz.timezone(tz_name)
            except:
                pass
        return None

    def parse_time(self, time_str, user_tz=None, base_time=None):
        """Parses time strings like 10m, 1h, 1d or absolute HH:MM into a target timestamp"""
        if base_time is None:
            base_time = datetime.datetime.now(datetime.timezone.utc)
            
        units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        
        # Check for relative time (e.g. 10m)
        match_rel = re.match(r"^(\d+)([smhd])$", time_str.lower())
        if match_rel:
            amount, unit = match_rel.groups()
            return int(base_time.timestamp()) + (int(amount) * units[unit])

        # Check for absolute time (e.g. 18:30)
        match_abs = re.match(r"^(\d{1,2}):(\d{2})$", time_str)
        if match_abs:
            if not user_tz:
                return "timezone_not_set"
            hours, minutes = map(int, match_abs.groups())
            if hours > 23 or minutes > 59: return None
            
            # Use current time in user's timezone based on base_time
            now_tz = base_time.astimezone(user_tz)
            target = now_tz.replace(hour=hours, minute=minutes, second=0, microsecond=0)
            
            # If target is in the past, assume tomorrow
            if target <= now_tz:
                target += datetime.timedelta(days=1)
                
            return int(target.timestamp())
        return None

    @tasks.loop(minutes=1)
    async def check_reminders(self):
        reminders = self.load_reminders()
        now = int(time.time())
        updated = False
        
        for reminder in reminders[:]:
            try:
                target_time = reminder['target_time']
                is_initial = now >= target_time and not reminder.get('notified', False)
                spam_interval = reminder.get('spam_interval', 0) * 60
                should_resend = False
                
                if not is_initial and not reminder.get('acknowledged', False) and spam_interval > 0:
                    last_notified = reminder.get('last_notified', target_time)
                    if now >= last_notified + spam_interval:
                        should_resend = True

                if is_initial or should_resend:
                    user = self.client.get_user(reminder['user_id'])
                    if not user:
                        try: user = await self.client.fetch_user(reminder['user_id'])
                        except: pass
                    
                    if user:
                        # Resolve guild context for localization
                        guild_id = reminder.get('guild_id')
                        if not guild_id:
                            channel = self.client.get_channel(reminder['channel_id'])
                            if channel and hasattr(channel, 'guild'):
                                guild_id = channel.guild.id

                        embed = discord.Embed(title=t('reminder_embed_title', guild_id=guild_id), description=reminder['message'], color=discord.Color.gold())
                        embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
                        view = ReminderView(self, guild_id=guild_id)
                        destination_type = reminder.get('destination', 'channel')
                        msg = None
                        
                        if destination_type == 'dm':
                            try: msg = await user.send(embed=embed, view=view)
                            except:
                                channel = self.client.get_channel(reminder['channel_id'])
                                if channel: msg = await channel.send(content=user.mention, embed=embed, view=view)
                        else:
                            channel = self.client.get_channel(reminder['channel_id'])
                            if channel:
                                try: msg = await channel.send(content=user.mention, embed=embed, view=view)
                                except:
                                    try: msg = await user.send(embed=embed, view=view)
                                    except: pass
                            else:
                                try: msg = await user.send(embed=embed, view=view)
                                except: pass
                        
                        if msg: reminder['message_id'] = msg.id
                        reminder['notified'] = True
                        reminder['last_notified'] = now
                        updated = True
                
                if reminder.get('acknowledged', False) or (reminder.get('notified', False) and spam_interval <= 0):
                    reminders.remove(reminder)
                    updated = True
            except Exception as e:
                print(f"Error checking reminder: {e}")

        if updated: self.save_reminders(reminders)

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.client.wait_until_ready()

    reminder_group = app_commands.Group(name="reminder", description="Manage your reminders")
    timezone_group = app_commands.Group(name="timezone", description="Manage your local timezone", parent=reminder_group)

    @timezone_group.command(name="set", description="Set your local timezone")
    @app_commands.describe(name="Timezone name (e.g. Europe/Paris)")
    async def timezone_set(self, interaction: discord.Interaction, name: str):
        guild_id = interaction.guild.id if interaction.guild else None
        try: pytz.timezone(name)
        except: return await interaction.response.send_message(t('reminder_timezone_error_invalid', guild_id=guild_id), ephemeral=True)
            
        timezones = self.load_timezones()
        timezones[str(interaction.user.id)] = name
        self.save_timezones(timezones)
        await interaction.response.send_message(t('reminder_timezone_success', tz=name, guild_id=guild_id), ephemeral=True)

    @timezone_group.command(name="info", description="Show your current timezone")
    async def timezone_info(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id if interaction.guild else None
        tz_name = self.load_timezones().get(str(interaction.user.id))
        if not tz_name: return await interaction.response.send_message(t('reminder_timezone_not_set', guild_id=guild_id), ephemeral=True)
        await interaction.response.send_message(t('reminder_timezone_info', tz=tz_name, guild_id=guild_id), ephemeral=True)

    @reminder_group.command(name="set", description="Set a reminder")
    @app_commands.describe(time="Time format (10m, 1h, 18:30)", message="Reminder message", spam_interval="Repeat every X minutes if not ack")
    @app_commands.choices(destination=[app_commands.Choice(name="Channel", value="channel"), app_commands.Choice(name="DM", value="dm")])
    async def reminder_set(self, interaction: discord.Interaction, time: str, message: str, spam_interval: int = 0, destination: str = "channel"):
        guild_id = interaction.guild.id if interaction.guild else None
        user_tz = self.get_user_timezone(interaction.user.id)
        target_time = self.parse_time(time, user_tz, interaction.created_at)
        
        if target_time == "timezone_not_set": return await interaction.response.send_message(t('reminder_timezone_not_set', guild_id=guild_id), ephemeral=True)
        if target_time is None: return await interaction.response.send_message(t('reminder_error_time', guild_id=guild_id), ephemeral=True)
        
        reminders = self.load_reminders()
        reminders.append({
            'id': str(uuid.uuid4()), 'user_id': interaction.user.id, 'channel_id': interaction.channel_id,
            'guild_id': interaction.guild_id,
            'message': message, 'target_time': target_time, 'spam_interval': spam_interval,
            'notified': False, 'acknowledged': False, 'last_notified': 0, 'message_id': None, 'destination': destination
        })
        self.save_reminders(reminders)
        
        success_msg = t('reminder_set_success', time=f"<t:{target_time}:F>", guild_id=guild_id)
        if spam_interval > 0: success_msg += t('reminder_spam_on', interval=spam_interval, guild_id=guild_id)
        await interaction.response.send_message(success_msg, ephemeral=True)

    @reminder_group.command(name="list", description="List your reminders")
    async def reminder_list(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id if interaction.guild else None
        user_reminders = [r for r in self.load_reminders() if r['user_id'] == interaction.user.id]
        if not user_reminders: return await interaction.response.send_message(t('reminder_list_empty', guild_id=guild_id), ephemeral=True)
            
        embed = discord.Embed(title=t('reminder_list_title', guild_id=guild_id), color=discord.Color.blue())
        for idx, r in enumerate(user_reminders, 1):
            spam_text = f" (Spam: {r['spam_interval']}m)" if r['spam_interval'] > 0 else ""
            embed.add_field(name=f"#{idx} - <t:{r['target_time']}:R>", value=f"{r['message']}{spam_text}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @reminder_group.command(name="cancel", description="Cancel a reminder")
    async def reminder_cancel(self, interaction: discord.Interaction, number: int):
        guild_id = interaction.guild.id if interaction.guild else None
        reminders = self.load_reminders()
        user_reminders = [r for r in reminders if r['user_id'] == interaction.user.id]
        if number < 1 or number > len(user_reminders): return await interaction.response.send_message(t('error', guild_id=guild_id), ephemeral=True)
        
        reminder_to_remove = user_reminders[number-1]
        reminders = [r for r in reminders if r['id'] != reminder_to_remove['id']]
        self.save_reminders(reminders)
        await interaction.response.send_message(t('reminder_cancel_success', guild_id=guild_id), ephemeral=True)

class ReminderView(discord.ui.View):
    def __init__(self, cog, guild_id=None):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id
        # Localize button label
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id == "reminder_ack_btn":
                child.label = t('reminder_ack_label', guild_id=guild_id)

    @discord.ui.button(label="OK", style=discord.ButtonStyle.green, custom_id="reminder_ack_btn")
    async def acknowledge(self, interaction: discord.Interaction, button: discord.ui.Button):
        reminders = self.cog.load_reminders()
        message_id = interaction.message.id
        
        # Filter out the acknowledged reminder
        new_reminders = [r for r in reminders if r.get('message_id') != message_id]
        
        if len(new_reminders) < len(reminders):
            self.cog.save_reminders(new_reminders)
            button.disabled = True
            button.label = t('reminder_ack_success', guild_id=interaction.guild_id)
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.send_message(t('reminder_ack_error_not_found', guild_id=interaction.guild_id), ephemeral=True)


async def setup(client):
    await client.add_cog(Utility_slash(client))

