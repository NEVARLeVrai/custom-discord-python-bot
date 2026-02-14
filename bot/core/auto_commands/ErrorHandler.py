import discord
from discord.ext import commands
from discord import app_commands
import traceback
import logging
from services.version_service import get_current_version
from lang.lang_utils import t

class ErrorHandler(commands.Cog):
    logger = logging.getLogger('discord_bot.errorhandler')
    """Global error handler for prefix and slash commands"""
    def __init__(self, client):
        self.client = client
    
    # Error handler for prefix commands
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # Delete command message if it's a text channel
        if isinstance(ctx.channel, discord.TextChannel):
            try:
                await ctx.message.delete()
            except:
                pass
        
        # Unknown command
        if isinstance(error, commands.CommandNotFound):
            embed = discord.Embed(
                title=t('err_unknown_command_title'),
                description=t('err_unknown_command_desc'),
                color=discord.Color.red()
            )
            if ctx.guild:
                embed.set_image(url=ctx.guild.icon)
            embed.set_footer(text=get_current_version(self.client))
            await ctx.send(embed=embed, delete_after=10)
            return
        
        # Missing permissions for user
        if isinstance(error, commands.MissingPermissions):
            missing_perms = [perm.replace('_', ' ').title() for perm in error.missing_permissions]
            perms_text = ", ".join(missing_perms)
            embed = discord.Embed(
                title=t('err_missing_perms_user_title'),
                description=t('err_missing_perms_user_desc', perms=perms_text),
                color=discord.Color.red()
            )
            embed.set_footer(text=get_current_version(self.client))
            await ctx.send(embed=embed, delete_after=10)
            return
        
        # Missing permissions for bot
        if isinstance(error, commands.BotMissingPermissions):
            missing_perms = [perm.replace('_', ' ').title() for perm in error.missing_permissions]
            perms_text = ", ".join(missing_perms)
            embed = discord.Embed(
                title=t('err_missing_perms_bot_title'),
                description=t('err_missing_perms_bot_desc', perms=perms_text),
                color=discord.Color.red()
            )
            embed.set_footer(text=get_current_version(self.client))
            await ctx.send(embed=embed, delete_after=10)
            return
        
        # Missing required argument
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title=t('err_missing_arg_title'),
                description=t('err_missing_arg_desc', command=ctx.command.name, param=error.param.name),
                color=discord.Color.red()
            )
            embed.set_footer(text=get_current_version(self.client))
            await ctx.send(embed=embed, delete_after=10)
            return
        
        # Invalid argument
        if isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title=t('err_bad_arg_title'),
                description=t('err_bad_arg_desc', command=ctx.command.name),
                color=discord.Color.red()
            )
            embed.set_footer(text=get_current_version(self.client))
            await ctx.send(embed=embed, delete_after=10)
            return
        
        # Command on cooldown
        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title=t('err_cooldown_title'),
                description=t('err_cooldown_desc', time=round(error.retry_after, 1)),
                color=discord.Color.orange()
            )
            embed.set_footer(text=get_current_version(self.client))
            await ctx.send(embed=embed, delete_after=error.retry_after)
            return
        
        # Owner only command
        if isinstance(error, commands.NotOwner):
            embed = discord.Embed(
                title=t('err_not_owner_title'),
                description=t('err_not_owner_desc'),
                color=discord.Color.red()
            )
            embed.set_footer(text=get_current_version(self.client))
            await ctx.send(embed=embed, delete_after=10)
            return
        
        # Guild only command
        if isinstance(error, commands.NoPrivateMessage):
            embed = discord.Embed(
                title=t('err_no_private_title'),
                description=t('err_no_private_desc'),
                color=discord.Color.red()
            )
            embed.set_footer(text=get_current_version(self.client))
            await ctx.send(embed=embed, delete_after=10)
            return
        
        # Check failure (for custom checks)
        if isinstance(error, commands.CheckFailure):
            embed = discord.Embed(
                title=t('err_check_failure_title'),
                description=t('err_check_failure_desc'),
                color=discord.Color.red()
            )
            embed.set_footer(text=get_current_version(self.client))
            await ctx.send(embed=embed, delete_after=10)
            return
        
        # Invocation error (general command errors)
        if isinstance(error, commands.CommandInvokeError):
            original_error = error.original
            # Handle specific Discord errors
            if isinstance(original_error, discord.Forbidden):
                embed = discord.Embed(
                    title=t('err_forbidden_title'),
                    description=t('err_forbidden_desc'),
                    color=discord.Color.red()
                )
                embed.set_footer(text=get_current_version(self.client))
                try:
                    await ctx.send(embed=embed, delete_after=10)
                except:
                    pass
                return
            elif isinstance(original_error, discord.NotFound):
                embed = discord.Embed(
                    title=t('err_not_found_title'),
                    description=t('err_not_found_desc'),
                    color=discord.Color.red()
                )
                embed.set_footer(text=get_current_version(self.client))
                try:
                    await ctx.send(embed=embed, delete_after=10)
                except:
                    pass
                return
            else:
                # Other errors - show generic message
                embed = discord.Embed(
                    title=t('err_invoke_title'),
                    description=t('err_invoke_desc'),
                    color=discord.Color.red()
                )
                embed.set_footer(text=get_current_version(self.client))
                try:
                    await ctx.send(embed=embed, delete_after=10)
                except:
                    pass
                # Log error for debug
                command_name = ctx.command.name if ctx.command else t('err_unknown')
                self.logger.error(t('log_err_command', command=command_name))
                self.logger.error(''.join(traceback.format_exception(type(original_error), original_error, original_error.__traceback__)))
                return
        
        # For all other unhandled errors
        command_name = ctx.command.name if ctx.command else t('err_unknown')
        self.logger.error(t('log_err_unhandled', command=command_name))
        self.logger.error(''.join(traceback.format_exception(type(error), error, error.__traceback__)))
    
    # Method to handle slash command errors (called from main.py)
    async def handle_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Global error handler for slash commands"""
        # Helper function to respond to interaction with fallback
        async def send_error_embed(embed, use_channel_fallback=True):
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, ephemeral=True, wait=False)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            except (discord.NotFound, discord.HTTPException):
                # Expired webhook or HTTP error - try followup if not already done
                if not interaction.response.is_done():
                    try:
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                    except:
                        pass
                
                # If fallback is enabled and channel is available, send normal message
                if use_channel_fallback and interaction.channel:
                    try:
                        await interaction.channel.send(embed=embed, delete_after=10)
                    except:
                        pass
            except Exception:
                # Last attempt with channel if available
                if use_channel_fallback and interaction.channel:
                    try:
                        await interaction.channel.send(embed=embed, delete_after=10)
                    except:
                        pass
        
        command_name = interaction.command.name if interaction.command else t('err_unknown')
        
        # Missing permissions for user
        if isinstance(error, app_commands.MissingPermissions):
            missing_perms = [perm.replace('_', ' ').title() for perm in error.missing_permissions]
            perms_text = ", ".join(missing_perms)
            embed = discord.Embed(
                title=t('err_missing_perms_user_title'),
                description=t('err_missing_perms_user_desc', perms=perms_text),
                color=discord.Color.red()
            )
            embed.set_footer(text=get_current_version(self.client))
            await send_error_embed(embed)
            return
        
        # Missing permissions for bot
        if isinstance(error, app_commands.BotMissingPermissions):
            missing_perms = [perm.replace('_', ' ').title() for perm in error.missing_permissions]
            perms_text = ", ".join(missing_perms)
            embed = discord.Embed(
                title=t('err_missing_perms_bot_title'),
                description=t('err_missing_perms_bot_desc', perms=perms_text),
                color=discord.Color.red()
            )
            embed.set_footer(text=get_current_version(self.client))
            await send_error_embed(embed)
            return
        
        # Command on cooldown
        if isinstance(error, app_commands.CommandOnCooldown):
            embed = discord.Embed(
                title=t('err_cooldown_title'),
                description=t('err_cooldown_desc', time=round(error.retry_after, 1)),
                color=discord.Color.orange()
            )
            embed.set_footer(text=get_current_version(self.client))
            await send_error_embed(embed)
            return
        
        # Check failure
        if isinstance(error, app_commands.CheckFailure):
            embed = discord.Embed(
                title=t('err_check_failure_title'),
                description=t('err_check_failure_desc'),
                color=discord.Color.red()
            )
            embed.set_footer(text=get_current_version(self.client))
            await send_error_embed(embed)
            return
        
        # Invocation error
        if isinstance(error, app_commands.CommandInvokeError):
            original_error = error.original
            
            # Handle specific Discord errors
            if isinstance(original_error, discord.Forbidden):
                embed = discord.Embed(
                    title=t('err_forbidden_title'),
                    description=t('err_forbidden_desc'),
                    color=discord.Color.red()
                )
                embed.set_footer(text=get_current_version(self.client))
                await send_error_embed(embed)
                return
            elif isinstance(original_error, discord.NotFound):
                # 404 Error - may be due to expired webhook or deleted resource
                error_code = getattr(original_error, 'code', None)
                if error_code == 10008:
                    # Expired webhook - do not show error as command likely succeeded
                    print(t('log_err_webhook_expired', command=command_name))
                    return
                else:
                    embed = discord.Embed(
                        title=t('err_not_found_title'),
                        description=t('err_not_found_desc'),
                        color=discord.Color.red()
                    )
                    embed.set_footer(text=get_current_version(self.client))
                    await send_error_embed(embed, use_channel_fallback=True)
                    return
            elif isinstance(original_error, discord.HTTPException):
                embed = discord.Embed(
                    title=t('err_http_title'),
                    description=t('err_http_desc', error=str(original_error)),
                    color=discord.Color.red()
                )
                embed.set_footer(text=get_current_version(self.client))
                await send_error_embed(embed)
                print(t('log_err_slash_http', command=command_name))
                traceback.print_exception(type(original_error), original_error, original_error.__traceback__)
                return
            elif isinstance(original_error, (ValueError, TypeError, AttributeError, KeyError, FileNotFoundError)):
                error_type = type(original_error).__name__
                error_keys = {
                    'ValueError': 'err_value_error',
                    'TypeError': 'err_type_error',
                    'AttributeError': 'err_attribute_error',
                    'KeyError': 'err_key_error',
                    'FileNotFoundError': 'err_file_not_found'
                }
                embed = discord.Embed(
                    title=error_type,
                    description=t(error_keys.get(error_type, 'err_invoke_desc')),
                    color=discord.Color.red()
                )
                embed.set_footer(text=get_current_version(self.client))
                await send_error_embed(embed)
                if error_type in ['ValueError', 'TypeError', 'AttributeError', 'KeyError', 'FileNotFoundError']:
                    print(t('log_err_slash_type', type=error_type, command=command_name))
                    traceback.print_exception(type(original_error), original_error, original_error.__traceback__)
                return
            else:
                # Other errors
                embed = discord.Embed(
                    title=t('err_invoke_title'),
                    description=t('err_invoke_desc'),
                    color=discord.Color.red()
                )
                embed.set_footer(text=get_current_version(self.client))
                await send_error_embed(embed)
                # Log error for debug
                self.logger.error(t('log_err_slash_general', command=command_name))
                self.logger.error(''.join(traceback.format_exception(type(original_error), original_error, original_error.__traceback__)))
                return
        
        # For all other unhandled errors
        embed = discord.Embed(
            title=t('error'),
            description=t('mods_unexpected_error', error=str(error)),
            color=discord.Color.red()
        )
        embed.set_footer(text=get_current_version(self.client))
        await send_error_embed(embed)
        self.logger.error(t('log_err_slash_unhandled', command=command_name))
        self.logger.error(''.join(traceback.format_exception(type(error), error, error.__traceback__)))

async def setup(client):
    await client.add_cog(ErrorHandler(client))

