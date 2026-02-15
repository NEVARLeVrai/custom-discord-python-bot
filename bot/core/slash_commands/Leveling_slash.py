import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio
from services.version_service import get_current_version
from lang.lang_utils import t

class Leveling_slash(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.leveling_service = client.leveling_service
    
    @app_commands.command(name="level", description="Displays a user's level")
    @app_commands.describe(member="The user whose level you want to see (optional)")
    async def level(self, interaction: discord.Interaction, member: discord.Member = None):
        """Displays a user's level"""
        member = member or interaction.user
        stats = self.leveling_service.get_stats(member.id)
        
        level = stats['level']
        experience = stats['experience']
        
        if level == 0 and experience == 0 and member.id != interaction.user.id:
             embed = discord.Embed(title=t('lvl_user_no_level', user=member.display_name), color=discord.Color.red())
             embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
             embed.set_footer(text=get_current_version(self.client))
             await interaction.response.send_message(embed=embed, ephemeral=False)
             return

        exp_needed = (level + 1) ** 2 - experience

        embed = discord.Embed(title=t('lvl_level_title', user=member.display_name), color=discord.Color.random())
        embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
        embed.add_field(name=t('lvl_level_header'), value=level)
        embed.add_field(name=t('lvl_exp_header'), value=f"{experience}/{(level + 1) ** 2}")
        embed.add_field(name=t('lvl_exp_needed_header'), value=exp_needed)
        embed.set_footer(text=get_current_version(self.client))

        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="resetlevel", description="Reset all levels")
    @app_commands.describe(confirm="Type 'oui' to confirm (required)")
    @app_commands.default_permissions(manage_messages=True)
    async def resetlevel(self, interaction: discord.Interaction, confirm: str):
        """Reset all levels"""
        # Check permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(t('mods_no_permission'), ephemeral=True)
            return
        
        if confirm.lower() != t('lvl_yes').lower():
            embed = discord.Embed(title=t('lvl_reset_cancel_title'), description=t('lvl_reset_confirm_desc'), color=discord.Color.red())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        self.leveling_service.reset_all()
        
        embed = discord.Embed(title=t('lvl_reset_success_title'), description=t('lvl_reset_success_desc'), color=discord.Color.yellow())
        embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
        embed.set_footer(text=get_current_version(self.client))
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="levelsettings", description="Toggle leveling system on/off")
    @app_commands.default_permissions(administrator=True)
    async def levelsettings(self, interaction: discord.Interaction):
        """Toggle leveling system on/off"""
        # Check permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(t('vocal_kick_admin_error'), ephemeral=True)
            return
        
        is_enabled = self.leveling_service.toggle_system()
        
        if is_enabled:
            embed = discord.Embed(title=t('lvl_settings_title'), description=t('lvl_settings_enabled'), color=discord.Color.green())
        else:
            embed = discord.Embed(title=t('lvl_settings_title'), description=t('lvl_settings_disabled'), color=discord.Color.red())
            
        embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
        embed.set_footer(text=get_current_version(self.client))
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="levelboard", description="Displays the level leaderboard")
    async def levelboard(self, interaction: discord.Interaction):
        """Displays the level leaderboard"""
        levels = self.leveling_service.levels
        
        if not levels:
            embed = discord.Embed(title=t('lvl_lb_title'), description=t('lvl_lb_empty'), color=discord.Color.blue())
            embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return
        
        await interaction.response.defer(ephemeral=False)
        
        # Get all users with their levels and sort them
        level_list = []
        for user_id, level_data in levels.items():
            level = level_data.get("level", 0)
            experience = level_data.get("experience", 0)
            if level > 0 or experience > 0:
                member = interaction.guild.get_member(int(user_id))
                level_list.append((member, level, experience, user_id))
        
        # Sort by level descending, then by experience descending
        level_list.sort(key=lambda x: (x[1], x[2]), reverse=True)
        
        # Take top 10
        top_levels = level_list[:10]
        
        # Create embed
        embed = discord.Embed(title=t('lvl_lb_title'), description=t('lvl_lb_desc'), color=discord.Color.blue())
        embed.set_author(name=t('help_requested_by', user=interaction.user.name), icon_url=interaction.user.avatar)
        embed.set_footer(text=get_current_version(self.client))
        
        # Add results
        if top_levels:
            leaderboard_text = ""
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            
            for idx, entry in enumerate(top_levels):
                medal = medals[idx] if idx < len(medals) else f"{idx+1}."
                member, lvl, exp, u_id = entry
                if member: user_display = f"**{member.display_name}**"
                else: user_display = f"**{t('lvl_lb_unknown_user')}** ({t('lvl_lb_unknown_id', id=u_id)})"
                
                leaderboard_text += f"{medal} {user_display} - {t('lvl_level_header')} {lvl} ({exp} {t('lvl_exp_unit')})\n"
            
            embed.add_field(name=t('lvl_lb_rank_header'), value=leaderboard_text, inline=False)
        else:
            embed.add_field(name=t('lvl_lb_rank_header'), value=t('lvl_lb_empty'), inline=False)
        
        await interaction.followup.send(embed=embed)


async def setup(client):
    await client.add_cog(Leveling_slash(client))

