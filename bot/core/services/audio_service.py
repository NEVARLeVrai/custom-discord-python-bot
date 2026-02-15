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
        self.volumes: Dict[int, float] = {}  # guild_id -> volume (0.0 to 2.0)
        self.history: Dict[int, List[Dict[str, Any]]] = {}  # guild_id -> previous songs
        self.current_track: Dict[int, Dict[str, Any]] = {}  # guild_id -> current playing track
        self.ffmpeg_path = client.paths['ffmpeg_exe']
        self.ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn',
            'executable': self.ffmpeg_path
        }
        self._last_play_time: Dict[int, float] = {}
        self._last_seek_offset: Dict[int, int] = {}

    def get_queue(self, guild_id: int) -> List[Dict[str, Any]]:
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]

    def clear_queue(self, guild_id: int):
        if guild_id in self.queues:
            self.queues[guild_id].clear()

    def set_volume(self, guild_id: int, volume: float):
        """Set volume for guild (0.0 to 2.0)."""
        new_vol = max(0.0, min(2.0, volume))
        self.volumes[guild_id] = new_vol
        
        # Apply to active voice client if possible
        voice = discord.utils.get(self.client.voice_clients, guild__id=guild_id)
        if voice and voice.source:
            if isinstance(voice.source, discord.PCMVolumeTransformer):
                voice.source.volume = new_vol

    def get_volume(self, guild_id: int) -> float:
        """Get current volume for guild (default 0.3)."""
        return self.volumes.get(guild_id, 0.3)

    def add_to_history(self, guild_id: int, track: Dict[str, Any]):
        """Add track to history."""
        if guild_id not in self.history:
            self.history[guild_id] = []
        self.history[guild_id].append(track)
        if len(self.history[guild_id]) > 50:
            self.history[guild_id].pop(0)

    def get_previous(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get previous track from history."""
        if guild_id in self.history and len(self.history[guild_id]) > 0:
            return self.history[guild_id].pop()
        return None

    async def connect_to_vocal(self, channel: discord.VoiceChannel) -> Optional[discord.VoiceProtocol]:
        """Connects or moves to a voice channel."""
        voice = discord.utils.get(self.client.voice_clients, guild=channel.guild)

        if voice and voice.is_connected():
            if voice.channel != channel:
                await voice.move_to(channel)
            return voice
        else:
            return await channel.connect()

    async def play_audio(self, guild: discord.Guild, source_url: str, is_local: bool = False, after_cb=None, title: str = None, start_time: int = 0, duration: int = None):
        """Plays audio from a URL or local path."""
        voice = discord.utils.get(self.client.voice_clients, guild=guild)
        if not voice:
            return

        if guild.id in self.current_track and self.current_track[guild.id] and start_time == 0:
            self.add_to_history(guild.id, self.current_track[guild.id])

        if voice.is_playing() or voice.is_paused():
            voice.stop()
            await asyncio.sleep(0.5)

        volume = self.get_volume(guild.id)

        if is_local:
            options = {'executable': self.ffmpeg_path}
            if start_time > 0:
                options['options'] = f'-vn -ss {start_time}'
            else:
                options['options'] = '-vn'
        else:
            before_opts = self.ffmpeg_options['before_options']
            if start_time > 0:
                before_opts = f'-ss {start_time} {before_opts}'

            options = {
                'before_options': before_opts,
                'options': '-vn',
                'executable': self.ffmpeg_path
            }

        ffmpeg_source = discord.FFmpegPCMAudio(source_url, **options)
        volume_source = discord.PCMVolumeTransformer(ffmpeg_source, volume=volume)
        
        voice.play(volume_source, after=after_cb)
        self.pause_states[guild.id] = False

        # Position tracking
        import time
        self._last_play_time[guild.id] = time.time()
        self._last_seek_offset[guild.id] = start_time

        # Update current track info
        if start_time == 0 or guild.id not in self.current_track:
            self.current_track[guild.id] = {
                'title': title or source_url, 
                'url': source_url, 
                'duration': duration
            }
        elif duration is not None:
            self.current_track[guild.id]['duration'] = duration

    def stop(self, guild: discord.Guild):
        voice = discord.utils.get(self.client.voice_clients, guild=guild)
        if voice:
            voice.stop()
            self.clear_queue(guild.id)
            if guild.id in self.current_track:
                self.current_track[guild.id] = None

    def pause(self, guild: discord.Guild):
        voice = discord.utils.get(self.client.voice_clients, guild=guild)
        if voice and voice.is_playing():
            voice.pause()
            self.pause_states[guild.id] = True
            # Update position tracking on pause
            import time
            elapsed = time.time() - self._last_play_time.get(guild.id, time.time())
            self._last_seek_offset[guild.id] = self._last_seek_offset.get(guild.id, 0) + int(elapsed)
            self._last_play_time[guild.id] = time.time() 
            return True
        return False

    def resume(self, guild: discord.Guild):
        voice = discord.utils.get(self.client.voice_clients, guild=guild)
        if voice and voice.is_paused():
            voice.resume()
            self.pause_states[guild.id] = False
            # Update play time on resume
            import time
            self._last_play_time[guild.id] = time.time()
            return True
        return False

    def is_playing(self, guild: discord.Guild) -> bool:
        voice = discord.utils.get(self.client.voice_clients, guild=guild)
        return voice.is_playing() if voice else False

    def is_paused(self, guild: discord.Guild) -> bool:
        voice = discord.utils.get(self.client.voice_clients, guild=guild)
        return voice.is_paused() if voice else False

    async def play_tts(self, guild: discord.Guild, text: str, lang: str = 'fr', volume: float = 1.0):
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
                'options': "-vn"
            }
            url = f"http://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl={lang}&q={part}"
            
            ffmpeg_source = discord.FFmpegPCMAudio(url, **options)
            volume_source = discord.PCMVolumeTransformer(ffmpeg_source, volume=volume)
            voice.play(volume_source)
            self.pause_states[guild.id] = False
            
            while voice.is_playing() or voice.is_paused():
                await asyncio.sleep(1)

    async def seek(self, guild: discord.Guild, seconds: int, after_cb=None) -> bool:
        """Seek in current track to specific second."""
        if guild.id not in self.current_track or not self.current_track[guild.id]:
            return False

        track = self.current_track[guild.id]
        await self.play_audio(guild, track['url'], is_local=False, after_cb=after_cb,
                             title=track['title'], start_time=max(0, seconds), duration=track.get('duration'))
        return True

    async def dc_if_empty(self, voice_client: discord.VoiceClient):
        """Auto-disconnect if alone in channel."""
        await asyncio.sleep(120)
        if voice_client and voice_client.is_connected() and len(voice_client.channel.members) == 1:
            await voice_client.disconnect()
            return True
        return False

    def format_time(self, seconds: int) -> str:
        """Format seconds into HH:MM:SS or MM:SS."""
        if seconds is None:
            return "??:??"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def create_progress_bar(self, guild_id: int, length: int = 15) -> str:
        """Generate a progress bar string for the current guild."""
        track = self.current_track.get(guild_id)
        if not track or not track.get('duration'):
            return f"`[{ '▬' * length }]` 00:00 / 00:00"

        pos = self.get_current_position(guild_id)
        duration = track['duration']
        
        percent = min(1.0, pos / duration)
        filled = int(percent * length)
        
        # Build bar: [▬▬🔘▬▬▬▬▬▬]
        bar = list('▬' * length)
        if filled < length:
            bar[filled] = '🔘'
        else:
            bar[-1] = '🔘'
            
        bar_str = "".join(bar)
        
        cur_fmt = self.format_time(pos)
        dur_fmt = self.format_time(duration)
        
        return f"`[{bar_str}]` {cur_fmt} / {dur_fmt}"

    def get_current_position(self, guild_id: int) -> int:
        """Estimate current playback position in seconds."""
        import time
        now = time.time()
        start_offset = self._last_seek_offset.get(guild_id, 0)
        
        voice = discord.utils.get(self.client.voice_clients, guild__id=guild_id)
        if not voice or not (voice.is_playing() or voice.is_paused()):
            return 0
            
        if voice.is_paused():
            return start_offset
            
        elapsed = now - self._last_play_time.get(guild_id, now)
        return start_offset + int(elapsed)

    async def seek_relative(self, guild, delta_seconds: int, after_cb=None):
        """Seek relative to current position."""
        guild_id = guild.id if hasattr(guild, 'id') else guild
        pos = self.get_current_position(guild_id)
        new_seek = max(0, pos + delta_seconds)
        current_track = self.current_track.get(guild_id)
        if current_track:
            await self.seek(guild, new_seek, after_cb=after_cb)
            return new_seek
        return None
