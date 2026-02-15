import discord
import os
from discord import app_commands
from discord.ext import commands
from yt_dlp import YoutubeDL
import asyncio
from lang.lang_utils import t
from services.version_service import get_current_version

class MusicControlView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id
        
        # Dynamic labels
        self.rewind_button.label = t('music_btn_rewind_label', guild_id=guild_id)
        self.forward_button.label = t('music_btn_forward_label', guild_id=guild_id)
        self.volume_down_button.label = t('music_btn_vol_down_label', guild_id=guild_id)
        self.volume_up_button.label = t('music_btn_vol_up_label', guild_id=guild_id)
        self.queue_button.label = t('music_btn_queue_label', guild_id=guild_id)
        self.stop_button.label = t('music_btn_stop_label', guild_id=guild_id)
        
        # Loop button state
        is_loop = self.cog.audio_service.loop_states.get(self.guild_id, False)
        self.loop_button.style = discord.ButtonStyle.success if is_loop else discord.ButtonStyle.secondary

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary, custom_id="music_previous")
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        previous = self.cog.audio_service.get_previous(self.guild_id)
        if previous:
            await self.cog.audio_service.play_audio(
                interaction.guild, previous['url'], after_cb=lambda e: self.cog.check_queue(interaction),
                title=previous['title']
            )
            await interaction.followup.send(t('music_btn_previous_playing', title=previous['title'], guild_id=self.guild_id), ephemeral=True)
        else:
            await interaction.followup.send(t('music_btn_previous_none', guild_id=self.guild_id), ephemeral=True)

    @discord.ui.button(emoji="⏪", style=discord.ButtonStyle.secondary, custom_id="music_rewind")
    async def rewind_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_seek = await self.cog.audio_service.seek_relative(interaction.guild, -15)
        if new_seek is not None:
            await interaction.response.send_message(t('music_btn_seek_rewind', time=15, guild_id=self.guild_id), ephemeral=True)
        else:
            await interaction.response.send_message(t('music_seek_error', guild_id=self.guild_id), ephemeral=True)

    @discord.ui.button(emoji="⏯️", style=discord.ButtonStyle.primary, custom_id="music_pause")
    async def pause_resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.cog.audio_service.is_paused(interaction.guild):
            if self.cog.audio_service.resume(interaction.guild):
                await interaction.response.send_message(t('music_btn_resumed', guild_id=self.guild_id), ephemeral=True)
            else:
                await interaction.response.send_message(t('music_btn_resume_none', guild_id=self.guild_id), ephemeral=True)
        elif self.cog.audio_service.is_playing(interaction.guild):
            if self.cog.audio_service.pause(interaction.guild):
                await interaction.response.send_message(t('music_btn_paused', guild_id=self.guild_id), ephemeral=True)
            else:
                await interaction.response.send_message(t('music_btn_pause_none', guild_id=self.guild_id), ephemeral=True)
        else:
            await interaction.response.send_message(t('music_btn_nothing_playing', guild_id=self.guild_id), ephemeral=True)

    @discord.ui.button(emoji="⏩", style=discord.ButtonStyle.secondary, custom_id="music_forward")
    async def forward_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_seek = await self.cog.audio_service.seek_relative(interaction.guild, 15)
        if new_seek is not None:
            await interaction.response.send_message(t('music_btn_seek_forward', time=15, guild_id=self.guild_id), ephemeral=True)
        else:
            await interaction.response.send_message(t('music_seek_error', guild_id=self.guild_id), ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="music_skip")
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.cog.audio_service.is_playing(interaction.guild) or self.cog.audio_service.is_paused(interaction.guild):
            queue = self.cog.audio_service.get_queue(self.guild_id)
            next_track = queue[0] if queue else None
            voice = discord.utils.get(self.cog.client.voice_clients, guild=interaction.guild)
            if voice:
                voice.stop()
            desc = t('music_btn_skipped_next', title=next_track['title'], guild_id=self.guild_id) if next_track else t('music_btn_skipped_empty', guild_id=self.guild_id)
            await interaction.response.send_message(desc, ephemeral=True)
        else:
            await interaction.response.send_message(t('music_btn_nothing_playing', guild_id=self.guild_id), ephemeral=True)

    @discord.ui.button(emoji="🔉", style=discord.ButtonStyle.secondary, custom_id="music_vol_down")
    async def volume_down_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        current_volume = int(self.cog.audio_service.get_volume(self.guild_id) * 100)
        new_volume = max(0, current_volume - 10)
        self.cog.audio_service.set_volume(self.guild_id, new_volume / 100.0)
        await interaction.response.send_message(t('music_btn_vol_set', emoji="🔉", vol=new_volume, guild_id=self.guild_id), ephemeral=True)

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, custom_id="music_vol_up")
    async def volume_up_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        current_volume = int(self.cog.audio_service.get_volume(self.guild_id) * 100)
        new_volume = min(200, current_volume + 10)
        self.cog.audio_service.set_volume(self.guild_id, new_volume / 100.0)
        await interaction.response.send_message(t('music_btn_vol_set', emoji="🔊", vol=new_volume, guild_id=self.guild_id), ephemeral=True)

    @discord.ui.button(emoji="📋", style=discord.ButtonStyle.secondary, custom_id="music_queue")
    async def queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        queue = self.cog.audio_service.get_queue(self.guild_id)
        if not queue:
            await interaction.response.send_message(t('music_btn_queue_empty', guild_id=self.guild_id), ephemeral=True)
        else:
            queue_list = "\n".join([f"**{i+1}.** {v['title']}" for i, v in enumerate(queue[:10])])
            if len(queue) > 10:
                queue_list += f"\n\n{t('music_btn_queue_more', count=len(queue) - 10, guild_id=self.guild_id)}"
            await interaction.response.send_message(t('music_btn_queue_title', list=queue_list, guild_id=self.guild_id), ephemeral=True)

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary, custom_id="music_loop")
    async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_loop = not self.cog.audio_service.loop_states.get(self.guild_id, False)
        self.cog.audio_service.loop_states[self.guild_id] = is_loop
        button.style = discord.ButtonStyle.success if is_loop else discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(t('music_btn_loop_enabled', guild_id=self.guild_id) if is_loop else t('music_btn_loop_disabled', guild_id=self.guild_id), ephemeral=True)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="music_stop")
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild.id
        if guild_id in self.cog.progress_tasks:
            self.cog.progress_tasks[guild_id].cancel()
            del self.cog.progress_tasks[guild_id]
        
        self.cog.audio_service.stop(interaction.guild)
        await interaction.response.send_message(t('music_btn_stopped', guild_id=guild_id), ephemeral=True)
        
        # Delete the embed message
        try:
            await interaction.message.delete()
        except:
            pass
        
        if guild_id in self.cog.active_messages:
            del self.cog.active_messages[guild_id]

class YoutubeSearchSelectView(discord.ui.View):
    def __init__(self, videos, cog):
        super().__init__(timeout=60)
        self.videos = videos
        self.cog = cog
        options = [
            discord.SelectOption(label=t('yt_search_video_label', num=i+1, guild_id=cog.client.get_guild(videos[0]['guild_id']).id if 'guild_id' in videos[0] else None), description=video['title'][:100], value=str(i))
            for i, video in enumerate(videos)
        ]
        self.add_item(YoutubeSearchSelect(options, videos, cog))

class YoutubeSearchSelect(discord.ui.Select):
    def __init__(self, options, videos, cog):
        guild_id = cog.client.get_guild(videos[0]['guild_id']).id if videos and 'guild_id' in videos[0] else None
        super().__init__(placeholder=t('yt_search_select_placeholder', guild_id=guild_id), min_values=1, max_values=1, options=options)
        self.videos = videos
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id if interaction.guild else None
        await interaction.response.defer()
        await interaction.response.defer()

        index = int(self.values[0])
        selected = self.videos[index]
        play_options = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'skip_unavailable_fragments': True,
            'noplaylist': True,
            'js_runtimes': {'node': {'path': self.cog.client.paths['node_exe']}}
        }
        try:
            video_url = selected.get('webpage_url', f"https://www.youtube.com/watch?v={selected['id']}")
            with YoutubeDL(play_options) as ydl:
                v_info = ydl.extract_info(video_url, download=False)
            audio_url = v_info['url']
            title = v_info.get('title', selected.get('title', video_url))
            queue = self.cog.audio_service.get_queue(interaction.guild.id)
            if self.cog.audio_service.is_playing(interaction.guild) or self.cog.audio_service.is_paused(interaction.guild):
                queue.append({'title': title, 'url': audio_url})
                embed = discord.Embed(title=t('yt_queue_add_title', guild_id=guild_id), description=t('yt_queue_add_desc', title=title, guild_id=guild_id), color=discord.Color.blue())
                await interaction.followup.send(embed=embed)
            else:
                duration = v_info.get('duration')
                await self.cog.audio_service.play_audio(interaction.guild, audio_url, after_cb=lambda e: self.cog.check_queue(interaction), title=title, duration=duration)
                
                embed = discord.Embed(title=t('yt_play_title', guild_id=guild_id), description=t('yt_playing_desc_quoted', title=title, guild_id=guild_id), color=discord.Color.green())
                embed.add_field(name=t('yt_progress', guild_id=guild_id), value=self.cog.audio_service.create_progress_bar(interaction.guild.id), inline=False)
                embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
                embed.set_footer(text=get_current_version(self.cog.client, guild_id=guild_id))
                
                view = MusicControlView(self.cog, interaction.guild.id)
                message = await interaction.followup.send(embed=embed, view=view)
                self.cog.active_messages[interaction.guild.id] = message
                
                # Start progress update loop
                if interaction.guild.id in self.cog.progress_tasks:
                    self.cog.progress_tasks[interaction.guild.id].cancel()
                self.cog.progress_tasks[interaction.guild.id] = asyncio.create_task(
                    self.cog._update_progress_loop(interaction.guild.id, message, embed)
                )
            self.view.stop()
        except Exception as e:
            embed = discord.Embed(title=t('yt_error_title', guild_id=guild_id), description=t('yt_search_error_general', error=str(e), guild_id=guild_id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.cog.client, guild_id=guild_id))
            await interaction.followup.send(embed=embed, ephemeral=True)
            print(t('log_err_search', error=e, guild_id=guild_id))

class Video_slash(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.audio_service = client.audio_service
        self.progress_tasks = {}  # guild_id -> asyncio.Task
        self.active_messages = {}  # guild_id -> discord.Message
    
    def check_queue(self, interaction: discord.Interaction):
        async def inner_check_queue():
            guild_id = interaction.guild.id
            queue = self.audio_service.get_queue(guild_id)
            if queue:
                # Cancel previous progress task
                if guild_id in self.progress_tasks:
                    self.progress_tasks[guild_id].cancel()
                    del self.progress_tasks[guild_id]

                next_video = queue.pop(0)
                await self.audio_service.play_audio(interaction.guild, next_video['url'], after_cb=lambda e: self.check_queue(interaction), title=next_video['title'], duration=next_video.get('duration'))
                
                # Auto disconnect check
                asyncio.create_task(self.audio_service.dc_if_empty(discord.utils.get(self.client.voice_clients, guild=interaction.guild)))
                
                embed = discord.Embed(title=t('yt_play_title', guild_id=guild_id), description=t('yt_playing_desc', title=next_video["title"], guild_id=guild_id), color=discord.Color.green())
                embed.add_field(name=t('yt_progress', guild_id=guild_id), value=self.audio_service.create_progress_bar(guild_id), inline=False)
                embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
                embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
                
                view = MusicControlView(self, guild_id)
                message = await interaction.channel.send(embed=embed, view=view)
                self.active_messages[guild_id] = message
                
                # Start progress update loop
                self.progress_tasks[guild_id] = asyncio.create_task(self._update_progress_loop(guild_id, message, embed))

        self.client.loop.create_task(inner_check_queue())

    async def _update_progress_loop(self, guild_id, message, embed):
        """Background task to update the progress bar in the embed."""
        guild = self.client.get_guild(guild_id)
        if not guild: return

        try:
            while guild_id in self.progress_tasks:
                await asyncio.sleep(10)
                
                if not self.audio_service.is_playing(guild) and not self.audio_service.is_paused(guild):
                    break
                
                # Update progress bar
                new_progress = self.audio_service.create_progress_bar(guild_id)
                # We assume progress is the ONLY field or the first one
                embed.set_field_at(0, name=t('yt_progress', guild_id=guild_id), value=new_progress, inline=False)
                
                try:
                    await message.edit(embed=embed)
                except (discord.NotFound, discord.HTTPException):
                    break
        except asyncio.CancelledError:
            pass
        finally:
            if guild_id in self.progress_tasks:
                # Only remove if it's THIS task (not a newer one)
                if asyncio.current_task() == self.progress_tasks[guild_id]:
                    del self.progress_tasks[guild_id]

    @app_commands.command(name="mplay", description="Play a video or audio from a link (YouTube, TikTok, X, etc.)")
    @app_commands.describe(url="Video or audio link (YouTube, TikTok, X, etc.)")
    async def mplay(self, interaction: discord.Interaction, url: str):

        if not interaction.user.voice:
            guild_id = interaction.guild.id if interaction.guild else None
            embed = discord.Embed(title=t('yt_error_title', guild_id=guild_id), description=t('yt_error_not_in_voice', guild_id=guild_id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        await interaction.response.defer(ephemeral=False)

        voice = await self.audio_service.connect_to_vocal(interaction.user.voice.channel)
        if not voice: return

        ydl_options = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'js_runtimes': {'node': {'path': self.client.paths['node_exe']}}
        }
        try:
            with YoutubeDL(ydl_options) as ydl:
                info = ydl.extract_info(url, download=False)
            audio_url = info['url']
            title = info.get('title', url)

            queue = self.audio_service.get_queue(interaction.guild.id)

            if not (self.audio_service.is_playing(interaction.guild) or self.audio_service.is_paused(interaction.guild)):
                duration = info.get('duration')
                
                # Check for short-form content to use download strategy (TikTok, X, Instagram, etc.)
                # This avoids 403/Forbidden errors with ffmpeg streaming
                is_short_form = any(domain in url for domain in ['tiktok.com', 'x.com', 'twitter.com', 'instagram.com'])
                extractor_short_form = any(domain in info.get('extractor', '').lower() for domain in ['tiktok', 'twitter', 'instagram'])

                if is_short_form or extractor_short_form:
                    # Download for Short Form Content
                    if not os.path.exists("downloads"):
                        os.makedirs("downloads")
                    
                    with YoutubeDL({'outtmpl': f'downloads/%(id)s.%(ext)s', 'quiet': True, 'no_warnings': True, 'format': 'bestaudio/best'}) as ydl_down:
                        info = ydl_down.extract_info(url, download=True)
                        audio_url = ydl_down.prepare_filename(info)
                    
                    # Play local file
                    def cleanup(error):
                        self.check_queue(interaction)
                        try:
                            if os.path.exists(audio_url):
                                os.remove(audio_url)
                        except Exception as e:
                            print(f"Error removing file {audio_url}: {e}")

                    await self.audio_service.play_audio(interaction.guild, audio_url, is_local=True, after_cb=cleanup, title=title, duration=duration)
                else:
                    # Stream for others
                    await self.audio_service.play_audio(interaction.guild, audio_url, after_cb=lambda e: self.check_queue(interaction), title=title, duration=duration)

                embed = discord.Embed(title=t('yt_play_title', guild_id=interaction.guild.id), description=t('yt_playing_desc', title=title, guild_id=interaction.guild.id), color=discord.Color.green())
                embed.add_field(name=t('yt_progress', guild_id=interaction.guild.id), value=self.audio_service.create_progress_bar(interaction.guild.id), inline=False)
                
                embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
                embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))

                view = MusicControlView(self, interaction.guild.id)
                message = await interaction.followup.send(embed=embed, view=view)
                self.active_messages[interaction.guild.id] = message
                
                # Start progress update loop
                if interaction.guild.id in self.progress_tasks:
                    self.progress_tasks[interaction.guild.id].cancel()
                self.progress_tasks[interaction.guild.id] = asyncio.create_task(self._update_progress_loop(interaction.guild.id, message, embed))
            else:
                queue.append({'title': title, 'url': audio_url, 'duration': info.get('duration')})
                embed = discord.Embed(title=t('yt_queue_add_title', guild_id=interaction.guild.id), description=t('yt_queue_add_desc', title=title, guild_id=interaction.guild.id), color=discord.Color.blue())
                embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
                embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
                await interaction.followup.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(title=t('yt_error_title', guild_id=interaction.guild.id), description=t('yt_error_general', error=str(e), guild_id=interaction.guild.id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="msearch", description="Search for a video or audio (YouTube, TikTok, X, etc.)")
    @app_commands.describe(query="Search (title, artist, etc.)")
    async def msearch(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice:
            guild_id = interaction.guild.id if interaction.guild else None
            embed = discord.Embed(title=t('yt_error_title', guild_id=guild_id), description=t('yt_error_not_in_voice', guild_id=guild_id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            return await interaction.response.send_message(embed=embed, ephemeral=True)
            
        await interaction.response.defer(ephemeral=False)
        voice = await self.audio_service.connect_to_vocal(interaction.user.voice.channel)
        if not voice: return

        search_options = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'noplaylist': True,
            'js_runtimes': {'node': {'path': self.client.paths['node_exe']}}
        }
        play_options = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'skip_unavailable_fragments': True,
            'noplaylist': True,
            'js_runtimes': {'node': {'path': self.client.paths['node_exe']}}
        }

        try:
            with YoutubeDL(search_options) as ydl:
                info = ydl.extract_info(f'ytsearch10:{query}', download=False)
            
            if not info or 'entries' not in info:
                embed = discord.Embed(title=t('yt_search_results_title', guild_id=interaction.guild.id), description=t('yt_search_no_results', guild_id=interaction.guild.id), color=discord.Color.orange())
                embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
                embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
                return await interaction.followup.send(embed=embed, ephemeral=True)

            videos = [v for v in info.get('entries', []) if v]
            
            if not videos:
                embed = discord.Embed(title=t('yt_search_results_title', guild_id=interaction.guild.id), description=t('yt_search_invalid_video', guild_id=interaction.guild.id), color=discord.Color.orange())
                embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
                embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
                return await interaction.followup.send(embed=embed, ephemeral=True)


            await interaction.followup.send(
                content=t('yt_search_results_title', guild_id=interaction.guild.id),
                view=YoutubeSearchSelectView(videos, self),
                ephemeral=True
            )

        except Exception as e:
            embed = discord.Embed(title=t('yt_error_title', guild_id=interaction.guild.id if interaction.guild else None), description=t('yt_search_error_general', error=str(e), guild_id=interaction.guild.id if interaction.guild else None), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id if interaction.guild else None), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id if interaction.guild else None))
            await interaction.followup.send(embed=embed, ephemeral=True)
            print(t('log_err_search', error=e, guild_id=interaction.guild.id if interaction.guild else None))

    @app_commands.command(name="mskip", description="Skip the current video/audio")
    async def mskip(self, interaction: discord.Interaction):
        if self.audio_service.is_playing(interaction.guild) or self.audio_service.is_paused(interaction.guild):
            # Cancel progress task
            if interaction.guild.id in self.progress_tasks:
                self.progress_tasks[interaction.guild.id].cancel()
                del self.progress_tasks[interaction.guild.id]

            # Delete active message if tracked
            if interaction.guild.id in self.active_messages:
                try:
                    await self.active_messages[interaction.guild.id].delete()
                except:
                    pass
                del self.active_messages[interaction.guild.id]

            # Stop and get next
            voice = discord.utils.get(self.client.voice_clients, guild=interaction.guild)
            if voice:
                voice.stop()
            
            queue = self.audio_service.get_queue(interaction.guild.id)
            next_track = queue[0] if queue else None
            desc = t('yt_skip_next', title=next_track['title'], guild_id=interaction.guild.id) if next_track else t('yt_skip_none', guild_id=interaction.guild.id)
            
            embed = discord.Embed(title=t('yt_skip_title', guild_id=interaction.guild.id), description=desc, color=discord.Color.orange())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title=t('yt_error_title', guild_id=interaction.guild.id), description=t('yt_error_playing_none', guild_id=interaction.guild.id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="mstop", description="Stop playback")
    async def mstop(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        if self.audio_service.is_playing(interaction.guild) or self.audio_service.is_paused(interaction.guild):
            if guild_id in self.progress_tasks:
                self.progress_tasks[guild_id].cancel()
                del self.progress_tasks[guild_id]

            self.audio_service.stop(interaction.guild)
            
            # Delete active message if tracked
            if guild_id in self.active_messages:
                try:
                    await self.active_messages[guild_id].delete()
                except:
                    pass
                del self.active_messages[guild_id]

            embed = discord.Embed(title=t('yt_stop_title', guild_id=guild_id), description=t('yt_stop_desc', guild_id=guild_id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(t('music_btn_nothing_playing', guild_id=guild_id), ephemeral=True)

    @app_commands.command(name="mpause", description="Pause the video/audio")
    async def mpause(self, interaction: discord.Interaction):
        if self.audio_service.pause(interaction.guild):
            embed = discord.Embed(title=t('yt_pause_title', guild_id=interaction.guild.id), description=t('yt_pause_desc', guild_id=interaction.guild.id), color=discord.Color.orange())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title=t('yt_error_title', guild_id=interaction.guild.id), description=t('yt_error_already_paused', guild_id=interaction.guild.id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="mresume", description="Resume the video/audio")
    async def mresume(self, interaction: discord.Interaction):
        if self.audio_service.resume(interaction.guild):
            embed = discord.Embed(title=t('yt_resume_title', guild_id=interaction.guild.id), description=t('yt_resume_desc', guild_id=interaction.guild.id), color=discord.Color.green())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title=t('yt_error_title', guild_id=interaction.guild.id), description=t('yt_error_not_paused', guild_id=interaction.guild.id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="mqueue", description="Display the queue")
    async def mqueue(self, interaction: discord.Interaction):
        queue = self.audio_service.get_queue(interaction.guild.id)
        if not queue:
            embed = discord.Embed(title=t('yt_queue_add_title', guild_id=interaction.guild.id), description=t('yt_queue_empty', guild_id=interaction.guild.id), color=discord.Color.orange())
        else:
            queue_list = "\n".join([f"**{i+1}.** {v['title']}" for i, v in enumerate(queue)])
            embed = discord.Embed(title=t('yt_queue_list_title', guild_id=interaction.guild.id), description=t('yt_queue_list_desc', list=queue_list, guild_id=interaction.guild.id), color=discord.Color.blue())
        
        embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
        embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="mclearqueue", description="Clear the queue")
    async def mclearqueue(self, interaction: discord.Interaction):
        self.audio_service.clear_queue(interaction.guild.id)
        embed = discord.Embed(title=t('yt_queue_add_title', guild_id=interaction.guild.id), description=t('yt_queue_cleared', guild_id=interaction.guild.id), color=discord.Color.green())
        embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
        embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
        await interaction.response.send_message(embed=embed)


    @app_commands.command(name="mloop", description="Toggle loop mode for current video/audio")
    async def mloop(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        self.audio_service.loop_states[guild_id] = not self.audio_service.loop_states.get(guild_id, False)
        is_loop = self.audio_service.loop_states[guild_id]
        embed = discord.Embed(title=t('yt_loop_title', guild_id=guild_id), description=t('yt_loop_enabled', guild_id=guild_id) if is_loop else t('yt_loop_disabled', guild_id=guild_id), color=discord.Color.green() if is_loop else discord.Color.red())
        embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=guild_id), icon_url=interaction.user.avatar)
        embed.set_footer(text=get_current_version(self.client, guild_id=guild_id))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="maddqueue", description="Add a song to the queue without playing it")
    @app_commands.describe(url="Video or audio link (YouTube, TikTok, X, etc.)")
    async def maddqueue(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(ephemeral=False)

        ydl_options = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'js_runtimes': {'node': {'path': self.client.paths['node_exe']}}
        }
        try:
            with YoutubeDL(ydl_options) as ydl:
                info = ydl.extract_info(url, download=False)
            audio_url = info['url']
            title = info.get('title', url)

            queue = self.audio_service.get_queue(interaction.guild.id)
            queue.append({'title': title, 'url': audio_url})

            embed = discord.Embed(title=t('music_addqueue_title', guild_id=interaction.guild.id), description=t('music_addqueue_desc', title=title, position=len(queue), guild_id=interaction.guild.id), color=discord.Color.blue())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
            await interaction.followup.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(title=t('yt_error_title', guild_id=interaction.guild.id), description=t('yt_error_general', error=str(e), guild_id=interaction.guild.id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="mremovequeue", description="Remove a song from the queue")
    @app_commands.describe(position="Position in queue (1 for first song)")
    async def mremovequeue(self, interaction: discord.Interaction, position: int):
        queue = self.audio_service.get_queue(interaction.guild.id)
        if not queue:
            embed = discord.Embed(title=t('yt_queue_add_title', guild_id=interaction.guild.id), description=t('yt_queue_empty', guild_id=interaction.guild.id), color=discord.Color.orange())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if position < 1 or position > len(queue):
            embed = discord.Embed(title=t('music_removequeue_title', guild_id=interaction.guild.id), description=t('music_removequeue_error_invalid', count=len(queue), guild_id=interaction.guild.id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        removed = queue.pop(position - 1)
        embed = discord.Embed(title=t('music_removequeue_title', guild_id=interaction.guild.id), description=t('music_removequeue_desc', title=removed['title'], guild_id=interaction.guild.id), color=discord.Color.green())
        embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
        embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="mseek", description="Seek to a specific time in the current track")
    @app_commands.describe(minutes="Minutes to seek to", seconds="Seconds to seek to")
    async def mseek(self, interaction: discord.Interaction, minutes: int = 0, seconds: int = 0):
        total_seconds = (minutes * 60) + seconds
        if not self.audio_service.is_playing(interaction.guild) and not self.audio_service.is_paused(interaction.guild):
            embed = discord.Embed(title=t('yt_error_title', guild_id=interaction.guild.id), description=t('yt_error_playing_none', guild_id=interaction.guild.id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        await interaction.response.defer()
        
        # Check if requested time is within track duration
        track = self.audio_service.current_track.get(interaction.guild.id)
        if track and track.get('duration') and total_seconds > track['duration']:
            embed = discord.Embed(title=t('yt_error_title', guild_id=interaction.guild.id), description=t('music_seek_error_duration', duration=self.audio_service.format_time(track['duration']), guild_id=interaction.guild.id), color=discord.Color.red())
            return await interaction.followup.send(embed=embed, ephemeral=True)

        await self.audio_service.seek(interaction.guild, total_seconds, lambda e: self.check_queue(interaction))
        
        embed = discord.Embed(title=t('music_seek_title', guild_id=interaction.guild.id), description=t('music_seek_desc', time=self.audio_service.format_time(total_seconds), guild_id=interaction.guild.id), color=discord.Color.green())
        embed.add_field(name=t('yt_progress', guild_id=interaction.guild.id), value=self.audio_service.create_progress_bar(interaction.guild.id), inline=False)
        embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
        embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="mprevious", description="Play the previous track")
    async def mprevious(self, interaction: discord.Interaction):
        await interaction.response.defer()
        previous = self.audio_service.get_previous(interaction.guild.id)
        if previous:
            await self.audio_service.play_audio(
                interaction.guild, previous['url'], after_cb=lambda e: self.check_queue(interaction),
                title=previous['title']
            )
            embed = discord.Embed(title=t('music_previous_title', guild_id=interaction.guild.id), description=t('music_previous_desc', title=previous['title'], guild_id=interaction.guild.id), color=discord.Color.green())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(title=t('music_previous_title', guild_id=interaction.guild.id), description=t('music_previous_error', guild_id=interaction.guild.id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="mvolume", description="Set the music volume")
    @app_commands.describe(volume="Volume level (0-200, default is 100)")
    async def mvolume(self, interaction: discord.Interaction, volume: int):
        if volume < 0 or volume > 200:
            embed = discord.Embed(title=t('music_volume_error_title', guild_id=interaction.guild.id), description=t('music_volume_error_range', guild_id=interaction.guild.id), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        volume_float = volume / 100.0
        self.audio_service.set_volume(interaction.guild.id, volume_float)

        embed = discord.Embed(title=t('music_volume_title', guild_id=interaction.guild.id), description=t('music_volume_desc', volume=volume, guild_id=interaction.guild.id), color=discord.Color.green())
        embed.set_author(name=t('help_requested_by', user=interaction.user.name, guild_id=interaction.guild.id), icon_url=interaction.user.avatar)
        embed.set_footer(text=get_current_version(self.client, guild_id=interaction.guild.id))
        await interaction.response.send_message(embed=embed)


async def setup(client):
    await client.add_cog(Video_slash(client))
