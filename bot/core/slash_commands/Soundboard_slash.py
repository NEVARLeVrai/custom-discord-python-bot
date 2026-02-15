import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
import random
from services.version_service import get_current_version
from lang.lang_utils import t
import mutagen
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.wave import WAVE
import random

class Soundboard_slash(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.audio_service = client.audio_service
        self.sounds_dir = client.paths['sounds_dir']
        audio_extensions = (".mp3", ".mp4", ".m4a", ".ogg", ".opus", ".wav", ".flac", ".aac")
        self.sound_files = [f for f in os.listdir(self.sounds_dir) if f.lower().endswith(audio_extensions)]

    def get_audio_duration(self, file_path):
        """Gets audio file duration in seconds."""
        try:
            audio_file = mutagen.File(file_path)
            return int(audio_file.info.length) if audio_file else None
        except Exception:
            return None

    @app_commands.command(name="slist", description="List all available sounds with duration")
    async def slist(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        
        if not self.sound_files:
            embed = discord.Embed(title=t('sb_list_title'), description=t('sb_list_empty'), color=discord.Color.red())
            return await interaction.followup.send(embed=embed)

        file_list = ""
        for i, file in enumerate(self.sound_files):
            duration = self.get_audio_duration(os.path.join(self.sounds_dir, file))
            duration_str = t('sb_duration_format', m=duration//60, s=duration%60) if duration else t('sb_duration_na')
            file_list += f"{i+1}. ({duration_str}) {os.path.splitext(file)[0]}\n"
        
        embed = discord.Embed(title=t('sb_list_title'), description=t('sb_list_desc', list=file_list), color=discord.Color.blue())
        embed.set_footer(text=get_current_version(self.client))
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="splay", description="Play a sound from the soundboard")
    @app_commands.describe(sound_num="Sound number to play (see /slist)")
    async def splay(self, interaction: discord.Interaction, sound_num: int):
        if not interaction.user.voice:
            return await interaction.response.send_message(t('sb_error_vocal'), ephemeral=True)

        await interaction.response.defer(ephemeral=False)
        
        if sound_num <= 0 or sound_num > len(self.sound_files):
            return await interaction.followup.send(t('sb_play_error_invalid_num'), ephemeral=True)

        voice = await self.audio_service.connect_to_vocal(interaction.user.voice.channel)
        if not voice: return

        sound_name = self.sound_files[sound_num-1]
        file_path = os.path.join(self.sounds_dir, sound_name)
        
        await self.audio_service.play_audio(interaction.guild, file_path, is_local=True)
        
        embed = discord.Embed(title=t('sb_play_title'), description=t('sb_play_playing', sound_name=sound_name), color=discord.Color.green())
        embed.set_footer(text=get_current_version(self.client))
        await interaction.followup.send(embed=embed)
        
        if sound_name == "Outro.mp3":
            await asyncio.sleep(58)
            if voice.channel:
                for member in voice.channel.members:
                    if not member.bot: await member.move_to(None)
            await interaction.channel.send(embed=discord.Embed(title=t('sb_play_outro_title'), description=t('sb_play_outro_desc'), color=discord.Color.yellow()))

    @app_commands.command(name="sstop", description="Stop the current sound")
    async def sstop(self, interaction: discord.Interaction):
        if self.audio_service.is_playing(interaction.guild):
            self.audio_service.stop(interaction.guild)
            await interaction.response.send_message(embed=discord.Embed(title=t('sb_stop_title'), description=t('sb_stop_desc'), color=discord.Color.red()))
        else:
            await interaction.response.send_message(t('sb_stop_error_none'), ephemeral=True)

    @app_commands.command(name="sleave", description="Make the bot leave the voice channel")
    async def sleave(self, interaction: discord.Interaction):
        voice = discord.utils.get(self.client.voice_clients, guild=interaction.guild)
        if voice:
            await voice.disconnect()
            await interaction.response.send_message(embed=discord.Embed(title=t('sb_leave_title'), description=t('sb_leave_desc'), color=discord.Color.green()))
        else:
            await interaction.response.send_message(t('sb_leave_error_none'), ephemeral=True)

    @app_commands.command(name="srandom", description="Play random sounds every 1-5 minutes")
    async def srandom(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            return await interaction.response.send_message(t('sb_error_vocal'), ephemeral=True)

        await interaction.response.defer(ephemeral=False)
        voice = await self.audio_service.connect_to_vocal(interaction.user.voice.channel)
        if not voice: return

        sb_cog = self.client.get_cog('Soundboard')
        if sb_cog:
            if sb_cog.random_task and not sb_cog.random_task.done():
                return await interaction.followup.send(t('sb_random_error_already_running'), ephemeral=True)
            sb_cog.random_task = asyncio.create_task(sb_cog.play_random_sound(interaction.channel.id))
            await interaction.followup.send(embed=discord.Embed(title=t('sb_random_title'), description=t('sb_random_started'), color=discord.Color.green()))

    @app_commands.command(name="srandomstop", description="Stop random playback")
    async def srandomstop(self, interaction: discord.Interaction):
        sb_cog = self.client.get_cog('Soundboard')
        if sb_cog and sb_cog.random_task and not sb_cog.random_task.done():
            sb_cog.random_task.cancel()
            await interaction.response.send_message(embed=discord.Embed(title=t('sb_random_stop_title'), description=t('sb_random_stop_desc'), color=discord.Color.red()))
        else:
            await interaction.response.send_message(t('sb_random_stop_error_none'), ephemeral=True)

    @app_commands.command(name="srandomskip", description="Skip the current random sound")
    async def srandomskip(self, interaction: discord.Interaction):
        if self.audio_service.is_playing(interaction.guild):
            discord.utils.get(self.client.voice_clients, guild=interaction.guild).stop()
            await interaction.response.send_message(embed=discord.Embed(title=t('sb_random_skip_title'), description=t('sb_random_skip_desc'), color=discord.Color.green()))
        else:
            await interaction.response.send_message(t('sb_random_skip_error_none'), ephemeral=True)

    @app_commands.command(name="svolume", description="Set the soundboard volume")
    @app_commands.describe(volume="Volume level (0-200, default is 100)")
    async def svolume(self, interaction: discord.Interaction, volume: int):
        if volume < 0 or volume > 200:
            embed = discord.Embed(title=t('sb_volume_error_title'), description=t('sb_volume_error_range'), color=discord.Color.red())
            embed.set_footer(text=get_current_version(self.client))
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        volume_float = volume / 100.0
        self.audio_service.set_volume(interaction.guild.id, volume_float)

        embed = discord.Embed(title=t('sb_volume_title'), description=t('sb_volume_desc', volume=volume), color=discord.Color.green())
        embed.set_footer(text=get_current_version(self.client))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="vkick", description="Kick a user from voice channel")
    @app_commands.describe(member="User to kick (optional, else all)")
    @app_commands.default_permissions(administrator=True)
    async def vkick(self, interaction: discord.Interaction, member: discord.Member = None):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(t('vocal_kick_admin_error'), ephemeral=True)
        
        if member:
            if not member.bot and member.voice:
                await member.move_to(None)
                await interaction.response.send_message(embed=discord.Embed(title=t('vocal_kick_title'), description=t('vocal_kick_desc', user=member.name), color=discord.Color.green()))
            else:
                await interaction.response.send_message(t('vocal_kick_error'), ephemeral=True)
        else:
            voice = discord.utils.get(self.client.voice_clients, guild=interaction.guild)
            if voice and voice.channel:
                for m in voice.channel.members:
                    if not m.bot: await m.move_to(None)
                await interaction.response.send_message(embed=discord.Embed(title=t('vocal_kick_title'), description=t('vocal_kick_all_desc'), color=discord.Color.green()))
            else:
                await interaction.response.send_message(t('vocal_kick_error'), ephemeral=True)

async def setup(client):
    await client.add_cog(Soundboard_slash(client))
