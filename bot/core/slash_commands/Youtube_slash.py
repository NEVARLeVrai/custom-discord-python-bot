import discord
from discord import app_commands
from discord.ext import commands
from yt_dlp import YoutubeDL
import asyncio
from lang.lang_utils import t
from services.version_service import get_current_version

class Youtube_slash(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.audio_service = client.audio_service
    
    def check_queue(self, interaction: discord.Interaction):
        async def inner_check_queue():
            queue = self.audio_service.get_queue(interaction.guild.id)
            if queue:
                next_video = queue.pop(0)
                await self.audio_service.play_audio(interaction.guild, next_video['url'], after_cb=lambda e: self.check_queue(interaction))
                
                # Auto disconnect check
                asyncio.create_task(self.audio_service.dc_if_empty(discord.utils.get(self.client.voice_clients, guild=interaction.guild)))
                
                embed = discord.Embed(title=t('yt_queue_add_title'), description=t('yt_queue_next_desc', title=next_video["title"]), color=discord.Color.blue())
                embed.set_footer(text=get_current_version(self.client))
                await interaction.channel.send(embed=embed, delete_after=10)

        self.client.loop.create_task(inner_check_queue())

    @app_commands.command(name="play", description="Play a YouTube video")
    @app_commands.describe(url="The YouTube video URL")
    async def play(self, interaction: discord.Interaction, url: str):
        if not (url.startswith('https://www.youtube.com/') or url.startswith('https://youtu.be/')):
            embed = discord.Embed(title=t('yt_error_title'), description=t('yt_play_error_only_youtube'), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if not interaction.user.voice:
            embed = discord.Embed(title=t('yt_error_title'), description=t('yt_error_not_in_voice'), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        await interaction.response.defer(ephemeral=False)
        
        voice = await self.audio_service.connect_to_vocal(interaction.user.voice.channel)
        if not voice: return

        ydl_options = {
            'format': 'bestaudio',
            'noplaylist': True,
            'js_runtimes': {'node': {'path': self.client.paths['node_exe']}}
        }
        try:
            with YoutubeDL(ydl_options) as ydl:
                info = ydl.extract_info(url, download=False)
            audio_url = info['url']
            title = info['title']
            
            queue = self.audio_service.get_queue(interaction.guild.id)
            
            if (self.audio_service.is_playing(interaction.guild) or self.audio_service.is_paused(interaction.guild)) and len(queue) > 0:
                queue.append({'title': title, 'url': audio_url})
                embed = discord.Embed(title=t('yt_queue_add_title'), description=t('yt_queue_add_desc', title=title), color=discord.Color.blue())
            else:
                await self.audio_service.play_audio(interaction.guild, audio_url, after_cb=lambda e: self.check_queue(interaction))
                embed = discord.Embed(title=t('yt_play_title'), description=t('yt_playing_desc', title=title), color=discord.Color.green())
            
            embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            embed = discord.Embed(title=t('yt_error_title'), description=t('yt_error_general', error=str(e)), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="search", description="Search for a YouTube video")
    @app_commands.describe(query="The search query", choice="Video number to play (1-10)")
    async def search(self, interaction: discord.Interaction, query: str, choice: int = None):
        if not interaction.user.voice:
            embed = discord.Embed(title=t('yt_error_title'), description=t('yt_error_not_in_voice'), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
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
            'format': 'bestaudio',
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
                embed = discord.Embed(title=t('yt_search_results_title'), description=t('yt_search_no_results'), color=discord.Color.orange())
                embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
                embed.set_footer(text=get_current_version(self.client))
                return await interaction.followup.send(embed=embed, ephemeral=True)

            videos = [v for v in info.get('entries', []) if v]
            
            if not videos:
                embed = discord.Embed(title=t('yt_search_results_title'), description=t('yt_search_invalid_video'), color=discord.Color.orange())
                embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
                embed.set_footer(text=get_current_version(self.client))
                return await interaction.followup.send(embed=embed, ephemeral=True)

            if choice is not None:
                if 1 <= choice <= len(videos):
                    selected = videos[choice - 1]
                    video_url = f"https://www.youtube.com/watch?v={selected['id']}"
                    with YoutubeDL(play_options) as ydl:
                        v_info = ydl.extract_info(video_url, download=False)
                    audio_url = v_info['url']
                    title = v_info.get('title', selected['title'])
                    
                    queue = self.audio_service.get_queue(interaction.guild.id)
                    if (self.audio_service.is_playing(interaction.guild) or self.audio_service.is_paused(interaction.guild)) and len(queue) > 0:
                        queue.append({'title': title, 'url': audio_url})
                        embed = discord.Embed(title=t('yt_queue_add_title'), description=t('yt_queue_add_desc', title=title), color=discord.Color.blue())
                    else:
                        await self.audio_service.play_audio(interaction.guild, audio_url, after_cb=lambda e: self.check_queue(interaction))
                        embed = discord.Embed(title=t('yt_play_title'), description=t('yt_playing_desc_quoted', title=title), color=discord.Color.green())
                    
                    embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
                    embed.set_footer(text=get_current_version(self.client))
                    return await interaction.followup.send(embed=embed)
                else:
                    embed = discord.Embed(title=t('yt_error_title'), description=t('yt_error_choice_invalid', max=len(videos)), color=discord.Color.red())
                    embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
                    embed.set_footer(text=get_current_version(self.client))
                    return await interaction.followup.send(embed=embed, ephemeral=True)

            result_text = "\n".join([f"**{i+1}.** {v['title']}" for i, v in enumerate(videos)])
            embed = discord.Embed(title=t('yt_search_results_title'), description=t('yt_search_results_desc', query=query, results=result_text), color=discord.Color.blue())
            embed.add_field(name=t('yt_search_choice_title'), value=t('yt_search_choice_slash_desc', query=query))
            embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.followup.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(title=t('yt_error_title'), description=t('yt_search_error_general', error=str(e)), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.followup.send(embed=embed, ephemeral=True)
            print(t('log_err_search', error=e))

    @app_commands.command(name="skip", description="Skip the current video")
    async def skip(self, interaction: discord.Interaction):
        if self.audio_service.is_playing(interaction.guild):
            queue = self.audio_service.get_queue(interaction.guild.id)
            next_v = queue[0] if queue else None
            discord.utils.get(self.client.voice_clients, guild=interaction.guild).stop()
            
            desc = t('yt_skip_next', title=next_v['title']) if next_v else t('yt_skip_none')
            embed = discord.Embed(title=t('yt_skip_title'), description=desc, color=discord.Color.green())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title=t('yt_error_title'), description=t('yt_error_playing_none'), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="stopm", description="Stop playback")
    async def stopm(self, interaction: discord.Interaction):
        if self.audio_service.is_playing(interaction.guild):
            self.audio_service.stop(interaction.guild)
            embed = discord.Embed(title=t('yt_stop_title'), description=t('yt_stop_desc'), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title=t('yt_error_title'), description=t('yt_error_playing_none'), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="pause", description="Pause the video")
    async def pause(self, interaction: discord.Interaction):
        if self.audio_service.pause(interaction.guild):
            embed = discord.Embed(title=t('yt_pause_title'), description=t('yt_pause_desc'), color=discord.Color.orange())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title=t('yt_error_title'), description=t('yt_error_already_paused'), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="resume", description="Resume the video")
    async def resume(self, interaction: discord.Interaction):
        if self.audio_service.resume(interaction.guild):
            embed = discord.Embed(title=t('yt_resume_title'), description=t('yt_resume_desc'), color=discord.Color.green())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title=t('yt_error_title'), description=t('yt_error_not_paused'), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="queue", description="Display the queue")
    async def queue(self, interaction: discord.Interaction):
        queue = self.audio_service.get_queue(interaction.guild.id)
        if not queue:
            embed = discord.Embed(title=t('yt_queue_add_title'), description=t('yt_queue_empty'), color=discord.Color.orange())
        else:
            queue_list = "\n".join([f"**{i+1}.** {v['title']}" for i, v in enumerate(queue)])
            embed = discord.Embed(title=t('yt_queue_list_title'), description=t('yt_queue_list_desc', list=queue_list), color=discord.Color.blue())
        
        embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
        embed.set_footer(text=get_current_version(self.client))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clearq", description="Clear the queue")
    async def clearq(self, interaction: discord.Interaction):
        self.audio_service.clear_queue(interaction.guild.id)
        embed = discord.Embed(title=t('yt_queue_add_title'), description=t('yt_queue_cleared'), color=discord.Color.green())
        embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
        embed.set_footer(text=get_current_version(self.client))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leave", description="Disconnect the bot from voice")
    async def leave(self, interaction: discord.Interaction):
        voice = discord.utils.get(self.client.voice_clients, guild=interaction.guild)
        if voice:
            await voice.disconnect()
            embed = discord.Embed(title=t('yt_leave_title'), description=t('yt_leave_desc'), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(title=t('yt_error_title'), description=t('yt_error_not_connected'), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="loop", description="Toggle loop")
    async def loop(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        self.audio_service.loop_states[guild_id] = not self.audio_service.loop_states.get(guild_id, False)
        is_loop = self.audio_service.loop_states[guild_id]
        embed = discord.Embed(title=t('yt_loop_title'), description=t('yt_loop_enabled') if is_loop else t('yt_loop_disabled'), color=discord.Color.green() if is_loop else discord.Color.red())
        embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
        embed.set_footer(text=get_current_version(self.client))
        await interaction.response.send_message(embed=embed)


async def setup(client):
    await client.add_cog(Youtube_slash(client))
