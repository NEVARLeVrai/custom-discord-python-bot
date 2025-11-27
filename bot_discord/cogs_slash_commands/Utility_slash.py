import discord
from discord import app_commands
from discord.ext import commands
import random
import io
import asyncio
import traceback
from cogs import Help
from cogs.Help import get_current_version
import datetime
from openai import OpenAI
from typing import Union

class Utility_slash(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.reponse_en_cours = False
        gpt_token_path = client.paths['gpt_token_file']
        with open(gpt_token_path, "r") as f:
            GPT_API_KEY = f.read().strip()
        self.openai_client = OpenAI(api_key=GPT_API_KEY)
        self.rate_limit_delay = 1
    
    def is_bot_dm(self, message):
        return message.author == self.client.user and isinstance(message.channel, discord.DMChannel)

    async def send_tts(self, vc, lang, vol, text):
        """Envoie un texte en TTS"""
        max_length = 200
        text_parts = [text[i:i+max_length] for i in range(0, len(text), max_length)]
        ffmpeg_path = self.client.paths['ffmpeg_exe']

        for part in text_parts:
            vc.play(discord.FFmpegPCMAudio(
                executable=ffmpeg_path,
                source=f"http://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl={lang}&q={part}",
                options=f"-af volume={vol}"
            ))
            while vc.is_playing():
                await asyncio.sleep(1)

    @app_commands.command(name="tts", description="Fait parler le bot")
    @app_commands.describe(lang="Langue du TTS (défaut: fr)", vol="Volume du TTS (défaut: 3.0)", text="Texte à dire")
    async def tts(self, interaction: discord.Interaction, text: str, lang: str = "fr", vol: str = "3.0"):
        """Commande TTS en slash"""
        await interaction.response.defer(ephemeral=False)
        
        vc = None
        try:
            if not interaction.user.voice:
                embed = discord.Embed(title="TTS - Erreur", description="Vous devez être dans un salon vocal pour utiliser cette commande.", color=discord.Color.red())
                embed.set_author(name=f"Demandé par {interaction.user.name}", icon_url=interaction.user.avatar)
                embed.set_footer(text=get_current_version(self.client))
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            channel = interaction.user.voice.channel
            voice = discord.utils.get(self.client.voice_clients, guild=interaction.guild)
            
            if voice and voice.is_connected():
                if voice.is_playing():
                    voice.stop()
                    youtube_cog = self.client.get_cog('Youtube')
                    if youtube_cog and hasattr(youtube_cog, 'queue'):
                        youtube_cog.queue.clear()
                    await asyncio.sleep(0.5)
                
                if voice.channel == channel:
                    vc = voice
                else:
                    try:
                        await voice.move_to(channel)
                        vc = voice
                    except discord.errors.ClientException as e:
                        embed = discord.Embed(title="TTS - Erreur", description=f"Conflit de connexion vocale. Le bot est peut-être utilisé par une autre fonctionnalité.", color=discord.Color.red())
                        embed.set_author(name=f"Demandé par {interaction.user.name}", icon_url=interaction.user.avatar)
                        embed.set_footer(text=get_current_version(self.client))
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        return
                    except Exception as e:
                        embed = discord.Embed(title="TTS - Erreur", description=f"Impossible de se déplacer vers le canal vocal: {str(e)}", color=discord.Color.red())
                        embed.set_author(name=f"Demandé par {interaction.user.name}", icon_url=interaction.user.avatar)
                        embed.set_footer(text=get_current_version(self.client))
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        return
            else:
                try:
                    vc = await channel.connect()
                except discord.errors.ClientException as e:
                    embed = discord.Embed(title="TTS - Erreur", description=f"Conflit de connexion vocale. Le bot est peut-être utilisé par une autre fonctionnalité.", color=discord.Color.red())
                    embed.set_author(name=f"Demandé par {interaction.user.name}", icon_url=interaction.user.avatar)
                    embed.set_footer(text=get_current_version(self.client))
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                except Exception as e:
                    embed = discord.Embed(title="TTS - Erreur", description=f"Impossible de se connecter au canal vocal: {str(e)}", color=discord.Color.red())
                    embed.set_author(name=f"Demandé par {interaction.user.name}", icon_url=interaction.user.avatar)
                    embed.set_footer(text=get_current_version(self.client))
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return

            embed = discord.Embed(title="TTS Play", description=f"Volume: **{vol}**\nLangue: **{lang}**\nDit: **{text}**", color=discord.Color.green())
            embed.set_author(name=f"Demandé par {interaction.user.name}", icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.followup.send(embed=embed, ephemeral=False)
            await self.send_tts(vc, lang, vol, text)

        except Exception as e:
            traceback_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            embed = discord.Embed(title="TTS - Erreur", description=f"Une erreur s'est produite lors de la lecture TTS:\n\n```\n{str(e)}\n```", color=discord.Color.red())
            embed.set_author(name=f"Demandé par {interaction.user.name}", icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.followup.send(embed=embed, ephemeral=True)
            print(f"Erreur TTS: {traceback_str}")

    @app_commands.command(name="gpt", description="Utilise GPT pour répondre à une question")
    @app_commands.describe(question="Votre question pour GPT")
    async def gpt(self, interaction: discord.Interaction, question: str):
        """Commande GPT en slash"""
        if self.reponse_en_cours:
            await interaction.response.send_message("Une réponse est déjà en cours de génération. Veuillez patienter.", ephemeral=True)
            return

        self.reponse_en_cours = True
        await interaction.response.defer(ephemeral=False)

        try:
            response = self.gpt_reponse(question)
            if not response:
                await interaction.followup.send("Erreur: Aucune réponse générée.", ephemeral=True)
                return
                
            response = self.nettoyer_texte(response)
            response_with_mention = f"{interaction.user.mention}\n{response}"
            
            if len(response_with_mention) > 2000:
                await self.send_long_message_slash(interaction, response_with_mention)
            else:
                await interaction.followup.send(response_with_mention, ephemeral=False)

            # Logger la requête
            try:
                gpt_logs_path = self.client.paths['gpt_logs']
                with open(gpt_logs_path, "a", encoding='utf-8') as f:
                    current_time = datetime.datetime.now()
                    f.write(f"Date: {current_time.strftime('%Y-%m-%d')}\n")
                    f.write(f"Heure: {current_time.strftime('%H:%M:%S')}\n")
                    f.write(f"User: {interaction.user.mention}\n")                
                    f.write(f"Question: {question}\n")
                    f.write(f"Réponse: {response}\n")
                    f.write("-" * 50 + "\n")
            except Exception as e:
                print(f"Erreur lors de l'écriture du log GPT: {e}")

        except Exception as e:
            error_embed = discord.Embed(title="Erreur GPT", description=f"Une erreur s'est produite: {str(e)}", color=discord.Color.red())
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            print(f"Erreur GPT: {e}")
        finally:
            self.reponse_en_cours = False

    def gpt_reponse(self, question):
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-5-nano",
                messages=[
                    {"role": "system", "content": "Tu es un assistant IA utile et amical. Réponds en français de manière détaillée et complète. N'hésite pas à développer tes réponses."},
                    {"role": "user", "content": question}
                ],
                max_completion_tokens=4000,
                temperature=1
            )
            bot_response = response.choices[0].message.content.strip()
            print("\n\nChat GPT:")
            print(f"Question: {question}")
            print(f"Réponse: {bot_response}")
            return bot_response
        except Exception as e:
            print(f"Erreur GPT: {e}")
            return f"Désolé, une erreur s'est produite lors de la génération de la réponse: {str(e)}"

    def nettoyer_texte(self, texte):
        texte_nettoye = "\n".join(line for line in texte.splitlines() if line.strip())
        return texte_nettoye

    async def send_long_message_slash(self, interaction, message):
        """Divise un message long en plusieurs messages pour respecter la limite de Discord"""
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
                await interaction.followup.send(f"*Suite {i+1}/{len(parts)}:*\n{part}", ephemeral=False)
            await asyncio.sleep(0.5)

    @app_commands.command(name="dalle", description="Génère une image avec DALL-E")
    @app_commands.describe(question="Votre prompt pour DALL-E")
    async def dalle(self, interaction: discord.Interaction, question: str):
        """Commande DALL-E en slash"""
        if self.reponse_en_cours:
            await interaction.response.send_message("Une réponse est déjà en cours de génération. Veuillez patienter.", ephemeral=True)
            return

        self.reponse_en_cours = True
        await interaction.response.defer(ephemeral=False)

        try:
            response = self.dalle_reponse(question)
            if not response:
                await interaction.followup.send("Erreur: Aucune image générée.", ephemeral=True)
                return
                
            response_with_mention = f"{interaction.user.mention}\n{response}"
            await interaction.followup.send(response_with_mention, ephemeral=False)

            # Logger la requête
            try:
                dalle_logs_path = self.client.paths['dalle_logs']
                with open(dalle_logs_path, "a", encoding='utf-8') as f:
                    current_time = datetime.datetime.now()
                    f.write(f"Date: {current_time.strftime('%Y-%m-%d')}\n")
                    f.write(f"Heure: {current_time.strftime('%H:%M:%S')}\n")
                    f.write(f"User: {interaction.user.mention}\n")                
                    f.write(f"Question: {question}\n")
                    f.write(f"Réponse: {response}\n")
                    f.write("-" * 50 + "\n")
            except Exception as e:
                print(f"Erreur lors de l'écriture du log DALL-E: {e}")

        except Exception as e:
            error_embed = discord.Embed(title="Erreur DALL-E", description=f"Une erreur s'est produite: {str(e)}", color=discord.Color.red())
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            print(f"Erreur DALL-E: {e}")
        finally:
            self.reponse_en_cours = False

    def dalle_reponse(self, question):
        try:
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=question,
                n=1,
                size="1024x1024",
                quality="standard"
            )
            bot_response = response.data[0].url
            print("\n\nDall-E:")
            print(f"Question: {question}")
            print(f"Réponse: {bot_response}")
            return bot_response
        except Exception as e:
            print(f"Erreur DALL-E: {e}")
            return f"Désolé, une erreur s'est produite lors de la génération de l'image: {str(e)}"

    @app_commands.command(name="8ball", description="Pose une question à la boule magique")
    @app_commands.describe(question="Votre question")
    async def magicball(self, interaction: discord.Interaction, question: str):
        """Commande 8ball en slash"""
        responses=['Comme je le vois oui.',
                  'Oui.',
                  'Positif',
                  'De mon point de vue, oui',
                  'Convaincu.',
                  'Le plus probable.',
                  'De grandes chances',
                  'Non.',
                  'Négatif.',
                  'Pas convaincu.',
                  'Peut-être.',
                  'Pas certain',
                  'Peut-être',
                  'Je ne peux pas prédire maintenant.',
                  'Je suis trop paresseux pour prédire.',
                  'Je suis fatigué. *continue à dormir*']
        response = random.choice(responses)
        embed=discord.Embed(title="La Boule Magique 8 à parlé!", color=discord.Color.purple())
        embed.set_author(name=f"Demandé par {interaction.user.name}", icon_url=interaction.user.avatar)
        embed.add_field(name='Question: ', value=f'{question}')
        embed.add_field(name='Réponse: ', value=f'{response}')
        embed.set_footer(text=get_current_version(self.client))
        with open(self.client.paths['8ball_png'], "rb") as f:
            image_data = f.read()
        embed.set_thumbnail(url="attachment://8ball.png")
        await interaction.response.send_message(embed=embed, file=discord.File(io.BytesIO(image_data), "8ball.png"), ephemeral=False)

    @app_commands.command(name="hilaire", description="Jeu Hilaire")
    async def hilaire(self, interaction: discord.Interaction):
        """Commande Hilaire en slash"""
        responses = ["le protocole RS232",
                "FTTH",
                "Bit de Start",
                "Bit de parité",
                "Sinusoïdale",
                "RJ45",
                "Trop dbruiiiit!!!!",
                "Raphaël les écouteurs",
                "Can le téléphone",
                "JoOoAnnY",
                "Le théorème de demorgan"]
        response = random.choice(responses)
        embed=discord.Embed(title="Wiliam Hilaire à parlé!", color=discord.Color.purple())
        embed.set_author(name=f"Demandé par {interaction.user.name}", icon_url=interaction.user.avatar)
        embed.add_field(name='Hilaire à dit: ', value=f'{response}')
        embed.set_footer(text=get_current_version(self.client))
        with open(self.client.paths['hilaire_png'], "rb") as f:
            image_data = f.read()
        embed.set_thumbnail(url="attachment://hilaire.png")
        await interaction.response.send_message(embed=embed, file=discord.File(io.BytesIO(image_data), "hilaire.png"), ephemeral=False)

    @app_commands.command(name="say", description="Envoie un message dans un salon")
    @app_commands.describe(channel="Le salon où envoyer le message", message="Le message à envoyer")
    @app_commands.default_permissions(manage_messages=True)
    async def say_channel(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        """Envoie un message dans un salon"""
        # Vérifier que l'utilisateur a les permissions nécessaires
        if not interaction.user.guild_permissions.manage_messages and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Vous n'avez pas la permission d'utiliser cette commande. (Permission requise: Gérer les messages)", ephemeral=True)
            return
        
        # Vérifier que le bot peut envoyer des messages dans le salon
        bot_member = interaction.guild.get_member(self.client.user.id)
        if not channel.permissions_for(bot_member).send_messages:
            await interaction.response.send_message(f"Le bot n'a pas la permission d'envoyer des messages dans {channel.mention}.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=False)
        
        try:
            await channel.send(message)
            embed = discord.Embed(title="Message Envoyé!", description=f"Message envoyé à {channel.mention}", color=discord.Color.green())
            embed.set_author(name=f"Demandé par {interaction.user.name}", icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.followup.send(embed=embed, ephemeral=False)
        except discord.Forbidden:
            embed = discord.Embed(title="Erreur", description=f"Le bot n'a pas la permission d'envoyer des messages dans {channel.mention}.", color=discord.Color.red())
            embed.set_author(name=f"Demandé par {interaction.user.name}", icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.HTTPException as e:
            embed = discord.Embed(title="Erreur", description=f"Erreur HTTP lors de l'envoi du message: {str(e)}", color=discord.Color.red())
            embed.set_author(name=f"Demandé par {interaction.user.name}", icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(title="Erreur", description=f"Impossible d'envoyer le message: {str(e)}", color=discord.Color.red())
            embed.set_author(name=f"Demandé par {interaction.user.name}", icon_url=interaction.user.avatar)
            embed.set_footer(text=get_current_version(self.client))
            await interaction.followup.send(embed=embed, ephemeral=True)
            
    @app_commands.command(name="deldms", description="Supprime tous les DMs du bot")
    @app_commands.default_permissions(administrator=True)
    async def delmp(self, interaction: discord.Interaction):
        """Supprime tous les DMs du bot"""
        await interaction.response.defer(ephemeral=False)
        
        try:
            total_deleted = 0
            embed = discord.Embed(title="Suppression des messages privés en cours...", color=discord.Color.yellow())
            embed.set_footer(text=get_current_version(self.client))
            await interaction.followup.send(embed=embed, ephemeral=False)

            tasks = []
            for member in interaction.guild.members:
                if not member.bot:
                    dm_channel = await member.create_dm()
                    messages_to_delete = [msg async for msg in dm_channel.history() if self.is_bot_dm(msg)]
                    deleted_count = len(messages_to_delete)

                    if deleted_count > 0:
                        tasks.append(dm_channel.send(f"Suppression Terminé!", delete_after=10))
                        tasks.append(asyncio.gather(*[msg.delete() for msg in messages_to_delete]))
                        await asyncio.sleep(self.rate_limit_delay)

                    total_deleted += deleted_count

                    if deleted_count > 0:
                        embed = discord.Embed(title=f"Messages privés de **{member.name}#{member.discriminator}** supprimés !", color=discord.Color.green())
                        embed.add_field(name="Nombre de messages supprimés", value=str(deleted_count))
                        embed.set_footer(text=get_current_version(self.client))
                        tasks.append(interaction.channel.send(embed=embed, delete_after=10))
                        await asyncio.sleep(self.rate_limit_delay)

            await asyncio.gather(*tasks)
            
            if total_deleted > 0:
                embed1 = discord.Embed(title=f"Messages privés supprimés au total.", description=f"{total_deleted}", color=discord.Color.purple())
            else:
                embed1 = discord.Embed(title="Aucun message privé à supprimer.", color=discord.Color.red())
            embed1.set_footer(text=get_current_version(self.client))
            await interaction.followup.send(embed=embed1, ephemeral=False)
            
        except Exception as e:
            embed = discord.Embed(title="Erreur", description=f"Une erreur s'est produite: {str(e)}", color=discord.Color.red())
            embed.set_footer(text=get_current_version(self.client))
            await interaction.followup.send(embed=embed, ephemeral=True)
            import traceback
            traceback.print_exc()
    


async def setup(client):
    await client.add_cog(Utility_slash(client))

