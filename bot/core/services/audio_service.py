import discord
import asyncio
from typing import Dict, List, Optional, Any
import os
from lang.lang_utils import t

class AudioService:
    def __init__(self, client):
        self.client = client
        self.queues: Dict[int, List[Dict[str, Any]]] = {}  # guild_id -> list of videos
        self.loop_states: Dict[int, bool] = {}
        self.pause_states: Dict[int, bool] = {}
        self.ffmpeg_path = client.paths['ffmpeg_exe']
        self.ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn',
            'executable': self.ffmpeg_path
        }

    def get_queue(self, guild_id: int) -> List[Dict[str, Any]]:
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]

    def clear_queue(self, guild_id: int):
        if guild_id in self.queues:
            self.queues[guild_id].clear()

    async def connect_to_vocal(self, channel: discord.VoiceChannel) -> Optional[discord.VoiceProtocol]:
        """Connects or moves to a voice channel."""
        guild_id = channel.guild.id
        voice = discord.utils.get(self.client.voice_clients, guild=channel.guild)

        if voice and voice.is_connected():
            if voice.channel != channel:
                await voice.move_to(channel)
            return voice
        else:
            return await channel.connect()

    async def play_audio(self, guild: discord.Guild, source_url: str, is_local: bool = False, after_cb=None):
        """Plays audio from a URL or local path."""
        voice = discord.utils.get(self.client.voice_clients, guild=guild)
        if not voice:
            return

        if voice.is_playing():
            voice.stop()
            await asyncio.sleep(0.5)

        options = self.ffmpeg_options if not is_local else {'executable': self.ffmpeg_path}
        
        voice.play(discord.FFmpegPCMAudio(source_url, **options), after=after_cb)
        self.pause_states[guild.id] = False

    def stop(self, guild: discord.Guild):
        voice = discord.utils.get(self.client.voice_clients, guild=guild)
        if voice and voice.is_playing():
            voice.stop()
            self.clear_queue(guild.id)

    def pause(self, guild: discord.Guild):
        voice = discord.utils.get(self.client.voice_clients, guild=guild)
        if voice and voice.is_playing():
            voice.pause()
            self.pause_states[guild.id] = True
            return True
        return False

    def resume(self, guild: discord.Guild):
        voice = discord.utils.get(self.client.voice_clients, guild=guild)
        if voice and voice.is_paused():
            voice.resume()
            self.pause_states[guild.id] = False
            return True
        return False

    def is_playing(self, guild: discord.Guild) -> bool:
        voice = discord.utils.get(self.client.voice_clients, guild=guild)
        return voice.is_playing() if voice else False

    def is_paused(self, guild: discord.Guild) -> bool:
        voice = discord.utils.get(self.client.voice_clients, guild=guild)
        return voice.is_paused() if voice else False

    async def play_tts(self, guild: discord.Guild, text: str, lang: str = 'fr', volume: str = '1.0'):
        """Plays TTS audio via Google Translate."""
        voice = discord.utils.get(self.client.voice_clients, guild=guild)
        if not voice:
            return

        max_length = 200
        text_parts = [text[i:i+max_length] for i in range(0, len(text), max_length)]

        for part in text_parts:
            if voice.is_playing():
                voice.stop()
                await asyncio.sleep(0.5)
            
            options = {
                'executable': self.ffmpeg_path,
                'options': f"-af volume={volume}"
            }
            url = f"http://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl={lang}&q={part}"
            
            voice.play(discord.FFmpegPCMAudio(url, **options))
            self.pause_states[guild.id] = False
            
            while voice.is_playing():
                await asyncio.sleep(1)

    async def dc_if_empty(self, voice_client: discord.VoiceClient):
        """Auto-disconnect logic."""
        await asyncio.sleep(120)
        if voice_client.is_connected() and len(voice_client.channel.members) == 1:
            await voice_client.disconnect()
            return True
        return False
