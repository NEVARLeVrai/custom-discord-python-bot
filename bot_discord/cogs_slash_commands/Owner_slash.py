import discord
from discord import app_commands
from discord.ext import commands
import io
import asyncio
from cogs import Help
from cogs.Help import get_current_version

async def async_is_owner_check(client, user: discord.User) -> bool:
    """Vérification async complète du propriétaire"""
    # Méthode 1: Utiliser la méthode native de discord.py
    try:
        if await client.is_owner(user):
            return True
    except:
        pass
    
    # Méthode 2: Vérifier via application_info (pour les bots en équipe)
    try:
        app_info = await client.application_info()
        if isinstance(app_info.owner, discord.Team):
            # Si le bot appartient à une équipe, vérifier si l'utilisateur est dans l'équipe
            return user.id in [member.id for member in app_info.owner.members]
        else:
            # Si c'est un propriétaire unique
            return user.id == app_info.owner.id
    except:
        pass
    
    # Méthode 3: Vérifier via l'ID dans la config (fallback)
    if hasattr(client, 'config') and 'target_user_id' in client.config:
        return user.id == client.config['target_user_id']
    
    return False

class Owner_slash(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="stop", description="Arrête le bot (owner only)")
    async def stop(self, interaction: discord.Interaction):
        """Arrête le bot"""
        # Vérifier si l'utilisateur est le propriétaire
        if not await async_is_owner_check(self.client, interaction.user):
            await interaction.response.send_message("Cette commande est réservée au propriétaire du bot.", ephemeral=True)
            return
        
        bot_latency = round(self.client.latency * 1000)
        embed = discord.Embed(title="Arrêt", description=f"Le Bot s'arrête Ping {bot_latency} ms.", color=discord.Color.red())
        embed.set_footer(text=get_current_version(self.client))
        with open(self.client.paths['hilaire2_png'], "rb") as f:
            image_data = f.read()
        embed.set_thumbnail(url="attachment://hilaire2.png")
        if interaction.guild:
            embed.set_image(url=interaction.guild.icon)
        await interaction.response.send_message(embed=embed, file=discord.File(io.BytesIO(image_data), "hilaire2.png"))
        print("")
        print("Arrêté par l'utilisateur")
        print("")
        await self.client.close()

    @app_commands.command(name="sync", description="Re-synchronise les commandes slash (owner only)")
    async def sync_commands(self, interaction: discord.Interaction):
        """Re-synchronise les commandes slash"""
        # Vérifier si l'utilisateur est le propriétaire
        if not await async_is_owner_check(self.client, interaction.user):
            await interaction.response.send_message("Cette commande est réservée au propriétaire du bot.", ephemeral=True)
            return
        
        # Message intermédiaire
        status_msg = None
        try:
            embed = discord.Embed(
                title="🔄 Synchronisation en cours...",
                description="Synchronisation des commandes slash...",
                color=discord.Color.orange()
            )
            embed.set_footer(text=get_current_version(self.client))
            await interaction.response.defer(ephemeral=False)
            status_msg = await interaction.followup.send(embed=embed, wait=True)
            
            # Synchroniser sur le serveur actuel
            synced_guild = await self.client.tree.sync(guild=interaction.guild)
            # Synchroniser globalement
            synced_global = await self.client.tree.sync()
            
            success_embed = discord.Embed(
                title="✓ Synchronisation réussie",
                description=f"Commandes synchronisées sur '{interaction.guild.name}'",
                color=discord.Color.green()
            )
            
            if synced_guild or synced_global:
                count = len(synced_guild) if synced_guild else len(synced_global) if synced_global else 0
                success_embed.add_field(
                    name="Commandes synchronisées",
                    value=f"{count} commande(s) disponible(s)",
                    inline=False
                )
            
            success_embed.set_footer(text=get_current_version(self.client))
            if status_msg:
                await status_msg.edit(embed=success_embed)
            else:
                await interaction.followup.send(embed=success_embed, ephemeral=False)
                
        except Exception as e:
            error_embed = discord.Embed(
                title="✗ Erreur de synchronisation",
                description=f"Erreur: {str(e)}",
                color=discord.Color.red()
            )
            error_embed.set_footer(text=get_current_version(self.client))
            if status_msg:
                await status_msg.edit(embed=error_embed)
            else:
                await interaction.followup.send(embed=error_embed, ephemeral=False)

    @app_commands.command(name="slashinfo", description="Affiche des informations de diagnostic sur les commandes slash (owner only)")
    async def slash_info(self, interaction: discord.Interaction):
        """Affiche des informations de diagnostic sur les commandes slash"""
        # Vérifier si l'utilisateur est le propriétaire
        if not await async_is_owner_check(self.client, interaction.user):
            await interaction.response.send_message("Cette commande est réservée au propriétaire du bot.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔍 Diagnostic des Commandes Slash",
            color=discord.Color.blue()
        )
        
        # Informations du bot
        embed.add_field(
            name="Bot Information",
            value=f"**Nom:** {self.client.user.name}\n**ID:** {self.client.user.id}",
            inline=False
        )
        
        # Commandes locales
        local_commands = []
        try:
            commands_list = self.client.tree.get_commands()
            for cmd in commands_list:
                local_commands.append(cmd.name)
        except:
            pass
        
        embed.add_field(
            name="Commandes Enregistrées",
            value=f"{len(local_commands)} commande(s): {', '.join([f'`/{cmd}`' for cmd in local_commands]) if local_commands else 'Aucune'}", 
            inline=False
        )
        
        # Lien d'invitation
        invite_url = f"https://discord.com/api/oauth2/authorize?client_id={self.client.user.id}&permissions=8&scope=bot%20applications.commands"
        embed.add_field(
            name="🔗 Lien d'Invitation",
            value=f"[Cliquez ici]({invite_url})",
            inline=False
        )
        
        embed.set_footer(text=get_current_version(self.client))
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="clearslash", description="Efface toutes les commandes slash de Discord (owner only)")
    async def clear_slash_commands(self, interaction: discord.Interaction):
        """Efface toutes les commandes slash de Discord"""
        # Vérifier si l'utilisateur est le propriétaire
        if not await async_is_owner_check(self.client, interaction.user):
            await interaction.response.send_message("Cette commande est réservée au propriétaire du bot.", ephemeral=True)
            return
        
        status_msg = None
        try:
            # Message intermédiaire
            embed = discord.Embed(
                title="🗑️ Suppression des commandes slash",
                description="Suppression en cours...",
                color=discord.Color.orange()
            )
            embed.set_footer(text=get_current_version(self.client))
            await interaction.response.defer(ephemeral=False)
            status_msg = await interaction.followup.send(embed=embed, wait=True)
            
            # Obtenir l'application ID pour compter les commandes avant suppression
            app_info = await self.client.application_info()
            application_id = app_info.id
            
            # Compter les commandes avant suppression
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
            
            # Méthode recommandée : clear_commands() puis sync()
            # 1. Effacer les commandes globales
            self.client.tree.clear_commands(guild=None)
            await self.client.tree.sync(guild=None)
            
            # 2. Effacer les commandes par serveur
            synced_guilds = 0
            for guild in self.client.guilds:
                try:
                    self.client.tree.clear_commands(guild=guild)
                    await self.client.tree.sync(guild=guild)
                    synced_guilds += 1
                except Exception:
                    continue
            
            # Vérifier que les commandes ont bien été supprimées
            try:
                global_commands_after = await self.client.http.get_global_commands(application_id)
                count_global_after = len(global_commands_after)
            except:
                count_global_after = 0
            
            total_deleted_global = count_global_before - count_global_after
            total_deleted_guild = sum(guild_counts_before.values())
            
            # Créer l'embed de résultat
            success_embed = discord.Embed(
                title="✅ Commandes slash supprimées",
                description="Toutes les commandes slash ont été supprimées.",
                color=discord.Color.green()
            )
            
            if count_global_before > 0:
                success_embed.add_field(
                    name="Commandes globales",
                    value=f"{count_global_before} → {count_global_after} (supprimées: {total_deleted_global})",
                    inline=False
                )
            
            if sum(guild_counts_before.values()) > 0:
                success_embed.add_field(
                    name="Commandes par serveur",
                    value=f"Supprimées de {synced_guilds} serveur(s)",
                    inline=False
                )
            
            success_embed.add_field(
                name="⚠️ Important",
                value="Les commandes ont été supprimées. **Redémarrez Discord** ou attendez quelques minutes pour que les changements soient visibles. Les commandes peuvent rester en cache côté client Discord.",
                inline=False
            )
            
            success_embed.set_footer(text=get_current_version(self.client))
            if status_msg:
                await status_msg.edit(embed=success_embed)
            else:
                await interaction.followup.send(embed=success_embed, ephemeral=False)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="✗ Erreur de suppression",
                description=f"Erreur: {str(e)}",
                color=discord.Color.red()
            )
            error_embed.set_footer(text=get_current_version(self.client))
            if status_msg:
                await status_msg.edit(embed=error_embed)
            else:
                await interaction.followup.send(embed=error_embed, ephemeral=False)


async def setup(client):
    await client.add_cog(Owner_slash(client))

