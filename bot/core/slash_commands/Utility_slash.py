import discord
from discord import app_commands
from discord.ext import commands
import random
import io
import asyncio
import traceback
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
            
            embed = discord.Embed(title=t('audio_error_title', guild_id=guild_id), description=t('yt_leave_desc', guild_id=guild_id), color=discord.Color.green())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title=t('audio_error_title', guild_id=guild_id), description=t('audio_not_connected', guild_id=guild_id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(client):
    await client.add_cog(Utility_slash(client))

