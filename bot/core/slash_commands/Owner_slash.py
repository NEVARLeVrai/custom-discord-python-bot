import discord
from discord import app_commands
from discord.ext import commands
import io
import asyncio
from services.version_service import get_current_version
from lang.lang_utils import t

async def async_is_owner_check(client, user: discord.User) -> bool:
    """Full async owner check"""
    # Method 1: Use native discord.py method
    try:
        if await client.is_owner(user):
            return True
    except:
        pass
    
    # Method 2: Check via application_info (for team bots)
    try:
        app_info = await client.application_info()
        if isinstance(app_info.owner, discord.Team):
            # If bot belongs to a team, check if user is in the team
            return user.id in [member.id for member in app_info.owner.members]
        else:
            # If it's a single owner
            return user.id == app_info.owner.id
    except:
        pass
    
    # Method 3: Check via ID in config (fallback)
    if hasattr(client, 'config') and 'target_user_id' in client.config:
        return user.id == client.config['target_user_id']
    
    return False

class Owner_slash(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="stop", description="Stops the bot (owner only)")
    async def stop(self, interaction: discord.Interaction):
        """Stops the bot"""
        # Check if user is owner
        if not await async_is_owner_check(self.client, interaction.user):
            await interaction.response.send_message(t('err_not_owner_desc'), ephemeral=True)
            return
        
        bot_latency = round(self.client.latency * 1000)
        embed = discord.Embed(title=t('owner_stop_title'), description=t('owner_stop_desc', latency=bot_latency), color=discord.Color.red())
        embed.set_footer(text=get_current_version(self.client))
        with open(self.client.paths['hilaire2_png'], "rb") as f:
            image_data = f.read()
        embed.set_thumbnail(url="attachment://hilaire2.png")
        if interaction.guild:
            embed.set_image(url=interaction.guild.icon)
        await interaction.response.send_message(embed=embed, file=discord.File(io.BytesIO(image_data), "hilaire2.png"))
        print("")
        print(t('owner_stop_log'))
        print("")
        await self.client.close()

    @app_commands.command(name="sync", description="Re-sync slash commands (owner only)")
    async def sync_commands(self, interaction: discord.Interaction):
        """Re-syncs slash commands"""
        # Check if user is owner
        if not await async_is_owner_check(self.client, interaction.user):
            await interaction.response.send_message(t('err_not_owner_desc'), ephemeral=True)
            return
        
        # Intermediate message
        status_msg = None
        try:
            embed = discord.Embed(
                title=t('owner_sync_loading_title'),
                description=t('owner_sync_loading_desc'),
                color=discord.Color.orange()
            )
            embed.set_footer(text=get_current_version(self.client))
            await interaction.response.defer(ephemeral=False)
            status_msg = await interaction.followup.send(embed=embed, wait=True)
            
            # Sync to current guild
            synced_guild = await self.client.tree.sync(guild=interaction.guild)
            # Sync globally
            synced_global = await self.client.tree.sync()
            
            success_embed = discord.Embed(
                title=t('owner_sync_success_title'),
                description=t('owner_sync_success_desc', guild=interaction.guild.name),
                color=discord.Color.green()
            )
            
            if synced_guild or synced_global:
                count = len(synced_guild) if synced_guild else len(synced_global) if synced_global else 0
                success_embed.add_field(
                    name=t('owner_sync_count_field'),
                    value=t('owner_sync_count_value', count=count),
                    inline=False
                )
            
            success_embed.set_footer(text=get_current_version(self.client))
            if status_msg:
                await status_msg.edit(embed=success_embed)
            else:
                await interaction.followup.send(embed=success_embed, ephemeral=False)
                
        except Exception as e:
            error_embed = discord.Embed(
                title=t('owner_sync_error_title'),
                description=f"{t('error')}: {str(e)}",
                color=discord.Color.red()
            )
            error_embed.set_footer(text=get_current_version(self.client))
            if status_msg:
                await status_msg.edit(embed=error_embed)
            else:
                await interaction.followup.send(embed=error_embed, ephemeral=False)

    @app_commands.command(name="slashinfo", description="Displays diagnostic info about slash commands (owner only)")
    async def slash_info(self, interaction: discord.Interaction):
        """Displays diagnostic info about slash commands"""
        # Check if user is owner
        if not await async_is_owner_check(self.client, interaction.user):
            await interaction.response.send_message(t('err_not_owner_desc'), ephemeral=True)
            return
        
        embed = discord.Embed(
            title=t('owner_slashinfo_title'),
            color=discord.Color.blue()
        )
        
        # Bot info
        embed.add_field(
            name=t('owner_slashinfo_bot_info_field'),
            value=t('owner_slashinfo_bot_info_value', name=self.client.user.name, id=self.client.user.id),
            inline=False
        )
        
        # Local commands
        local_commands = []
        try:
            commands_list = self.client.tree.get_commands()
            for cmd in commands_list:
                local_commands.append(cmd.name)
        except:
            pass
        
        cmd_list_str = ', '.join([f'`/{cmd}`' for cmd in local_commands]) if local_commands else t('owner_slashinfo_no_commands')
        embed.add_field(
            name=t('owner_slashinfo_registered_field'),
            value=t('owner_slashinfo_registered_value', count=len(local_commands), commands=cmd_list_str), 
            inline=False
        )
        
        # Invite link
        invite_url = f"https://discord.com/api/oauth2/authorize?client_id={self.client.user.id}&permissions=8&scope=bot%20applications.commands"
        embed.add_field(
            name=t('owner_slashinfo_invite_field'),
            value=t('owner_slashinfo_invite_value', url=invite_url),
            inline=False
        )
        
        embed.set_footer(text=get_current_version(self.client))
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="clearslash", description="Clears all slash commands from Discord (owner only)")
    async def clear_slash_commands(self, interaction: discord.Interaction):
        """Clears all slash commands from Discord"""
        # Check if user is owner
        if not await async_is_owner_check(self.client, interaction.user):
            await interaction.response.send_message(t('err_not_owner_desc'), ephemeral=True)
            return
        
        status_msg = None
        try:
            # Intermediate message
            embed = discord.Embed(
                title=t('owner_clearslash_title'),
                description=t('owner_clearslash_loading'),
                color=discord.Color.orange()
            )
            embed.set_footer(text=get_current_version(self.client))
            await interaction.response.defer(ephemeral=False)
            status_msg = await interaction.followup.send(embed=embed, wait=True)
            
            # Get application ID to count commands before deletion
            app_info = await self.client.application_info()
            application_id = app_info.id
            
            # Count commands before deletion
            try:
                global_commands_before = await self.client.http.get_global_commands(application_id)
                count_global_before = len(global_commands_before)
            except:
                count_global_before = 0
            
            guild_counts_before = {}
            for guild in self.client.guilds:
                try:
                    guild_commands = await self.client.http.get_guild_commands(application_id, guild.id)
                    guild_counts_before[guild.id] = len(guild_commands)
                except:
                    guild_counts_before[guild.id] = 0
            
            # Recommended method: clear_commands() then sync()
            # 1. Clear global commands
            self.client.tree.clear_commands(guild=None)
            await self.client.tree.sync(guild=None)
            
            # 2. Clear guild commands
            synced_guilds = 0
            for guild in self.client.guilds:
                try:
                    self.client.tree.clear_commands(guild=guild)
                    await self.client.tree.sync(guild=guild)
                    synced_guilds += 1
                except Exception:
                    continue
            
            # Verify commands were deleted
            try:
                global_commands_after = await self.client.http.get_global_commands(application_id)
                count_global_after = len(global_commands_after)
            except:
                count_global_after = 0
            
            total_deleted_global = count_global_before - count_global_after
            total_deleted_guild = sum(guild_counts_before.values())
            
            # Create result embed
            success_embed = discord.Embed(
                title=t('owner_clearslash_success_title'),
                description=t('owner_clearslash_success_desc'),
                color=discord.Color.green()
            )
            
            if count_global_before > 0:
                success_embed.add_field(
                    name=t('owner_clearslash_global_field'),
                    value=t('owner_clearslash_global_value', before=count_global_before, after=count_global_after, deleted=total_deleted_global),
                    inline=False
                )
            
            if sum(guild_counts_before.values()) > 0:
                success_embed.add_field(
                    name=t('owner_clearslash_guild_field'),
                    value=t('owner_clearslash_guild_value', count=synced_guilds),
                    inline=False
                )
            
            success_embed.add_field(
                name=t('owner_clearslash_warning_title'),
                value=t('owner_clearslash_warning_value'),
                inline=False
            )
            
            success_embed.set_footer(text=get_current_version(self.client))
            if status_msg:
                await status_msg.edit(embed=success_embed)
            else:
                await interaction.followup.send(embed=success_embed, ephemeral=False)
            
        except Exception as e:
            error_embed = discord.Embed(
                title=t('owner_clearslash_error_title'),
                description=f"{t('error')}: {str(e)}",
                color=discord.Color.red()
            )
            error_embed.set_footer(text=get_current_version(self.client))
            if status_msg:
                await status_msg.edit(embed=error_embed)
            else:
                await interaction.followup.send(embed=error_embed, ephemeral=False)


    @app_commands.command(name="setlang", description="Change the bot language (owner only)")
    @app_commands.describe(lang="The language code (e.g. fr, en)")
    async def set_lang(self, interaction: discord.Interaction, lang: str):
        """Changes bot language"""
        # Check if user is owner
        if not await async_is_owner_check(self.client, interaction.user):
            await interaction.response.send_message(t('err_not_owner_desc'), ephemeral=True)
            return
            
        from lang.lang_utils import set_language, get_available_languages
        
        if set_language(lang):
            # Reload commands to update descriptions if needed (though descriptions are static here)
            # In reality, we should restart or reload cogs for everything to take effect everywhere,
            # but set_language changes the global variable so subsequent t() calls will use the new language.
            
            embed = discord.Embed(
                title=t('mods_success_title'),
                description=t('lang_set_success', lang=lang),
                color=discord.Color.green()
            )
            embed.set_footer(text=get_current_version(self.client))
            await interaction.response.send_message(embed=embed)
        else:
            available = ", ".join(get_available_languages())
            embed = discord.Embed(
                title=t('error'),
                description=t('lang_invalid', langs=available),
                color=discord.Color.red()
            )
            embed.set_footer(text=get_current_version(self.client))
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(client):
    await client.add_cog(Owner_slash(client))

