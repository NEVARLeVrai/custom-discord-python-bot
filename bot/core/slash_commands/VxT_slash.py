import discord
from discord import app_commands
from discord.ext import commands
import typing
import re
import langcodes
import pycountry
from services.vxt_service import vxt_service_global as vxt_service

# Domain pattern for conversion-list
domain_pattern = r"^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$"

class VxT_slash(commands.Cog):
    def __init__(self, client):
        self.client = client

    # --- Top-Level Groups (Unbundled) ---
    vxt_direct_media = app_commands.Group(name="vxt-direct-media", description="Change behaviour for direct media conversions.")
    vxt_translate = app_commands.Group(name="vxt-translate", description="Change translation behaviour")
    vxt_mention = app_commands.Group(name="vxt-mention", description="Add or remove mentions to ignore.")
    vxt_conversion = app_commands.Group(name="vxt-conversion-list", description="Manage custom domain conversions")
    vxt_quote_tweet = app_commands.Group(name="vxt-quote-tweet", description="Change behaviour for quote tweets.")

    # --- Toggle Command ---
    @app_commands.command(name="vxt-toggle", description="Toggle link conversions for specific message types.")
    @app_commands.describe(type="The type of messages to toggle.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def vxt_toggle(self, interaction: discord.Interaction, type: typing.Literal["all", "text", "images", "videos", "polls"]) -> None:
        temp_toggle_list = vxt_service.read_file_content("toggle-list", {interaction.guild_id: vxt_service.default_settings["toggle-list"]})
        if type == "all":
            new_val = not temp_toggle_list[interaction.guild_id]["all"]
            for key in temp_toggle_list[interaction.guild_id]:
                temp_toggle_list[interaction.guild_id][key] = new_val
        else:
            temp_toggle_list[interaction.guild_id][type] = not temp_toggle_list[interaction.guild_id][type]
        
        await vxt_service.write_file_content("toggle-list", temp_toggle_list)
        status = "on" if temp_toggle_list[interaction.guild_id][type] else "off"
        await interaction.response.send_message(f"Toggled {type} link conversions {status}.")

    # --- Direct-Media Commands ---
    @vxt_direct_media.command(name="toggle", description="Toggle subdomain addition for Twitter links.")
    @app_commands.describe(type="The types of tweets to be converted.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def dm_toggle(self, interaction: discord.Interaction, type: typing.Literal["images", "videos"]) -> None:
        temp_dm_list = vxt_service.read_file_content("direct-media-list", {interaction.guild_id: vxt_service.default_settings["direct-media-list"]})
        temp_dm_list[interaction.guild_id]["toggle"][type] = not temp_dm_list[interaction.guild_id]["toggle"][type]
        await vxt_service.write_file_content("direct-media-list", temp_dm_list)
        status = "on" if temp_dm_list[interaction.guild_id]["toggle"][type] else "off"
        await interaction.response.send_message(f"Toggled direct media conversion of tweets containing {type} {status}.")

    @vxt_direct_media.command(name="channel", description="Change permissions for which channels to convert in.")
    @app_commands.describe(action="The action to be performed.", channel="The channel to allow or prohibit.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def dm_channel(self, interaction: discord.Interaction, action: typing.Literal["list", "allow", "prohibit", "allow all", "prohibit all"], channel: typing.Optional[discord.abc.GuildChannel]):
        temp_dm_list = vxt_service.read_file_content("direct-media-list", {interaction.guild_id: vxt_service.default_settings["direct-media-list"]})
        if action == "list":
            chnl_list = temp_dm_list[interaction.guild_id]["channel"]
            if "allow" in chnl_list or "prohibit" in chnl_list:
                state = "allowed" if "allow" in chnl_list else "prohibited"
                return await interaction.response.send_message(f"All channels are {state}.")
            
            allowed = "\n".join([f"- {c[1]}" for c in chnl_list if isinstance(c, list) and c[0] == "allow"])
            prohibited = "\n".join([f"- {c[1]}" for c in chnl_list if isinstance(c, list) and c[0] == "prohibit"])
            await interaction.response.send_message(f"Allowed channels:\n{allowed}\nProhibited:\n{prohibited}")
        
        elif action in ["allow", "prohibit"]:
            if not channel: return await interaction.response.send_message("Please select a channel.")
            entry = [action, channel.mention]
            chnl_list = temp_dm_list[interaction.guild_id]["channel"]
            if entry in chnl_list or action in chnl_list:
                return await interaction.response.send_message(f"Channel {channel.mention} is already {action}ed.")
            
            opp = "prohibit" if action == "allow" else "allow"
            chnl_list = [item for item in chnl_list if item != [opp, channel.mention]]
            if opp in chnl_list: chnl_list.remove(opp)
            chnl_list.append(entry)
            temp_dm_list[interaction.guild_id]["channel"] = chnl_list
            await vxt_service.write_file_content("direct-media-list", temp_dm_list)
            await interaction.response.send_message(f"Channel {channel.mention} is now {action}ed.")
        
        elif action in ["allow all", "prohibit all"]:
            key = "allow" if action == "allow all" else "prohibit"
            temp_dm_list[interaction.guild_id]["channel"] = [key]
            await vxt_service.write_file_content("direct-media-list", temp_dm_list)
            await interaction.response.send_message(f"All channels are now {key}ed.")

    @vxt_direct_media.command(name="multiple-images", description="Configure behavior for multiple images.")
    @app_commands.describe(option="Select an option.")
    @app_commands.choices(option=[app_commands.Choice(name="convert", value="convert"), app_commands.Choice(name="replace with mosaic", value="replace_with_mosaic")])
    @app_commands.checks.has_permissions(manage_guild=True)
    async def dm_multi(self, interaction: discord.Interaction, option: app_commands.Choice[str]):
        temp_dm_list = vxt_service.read_file_content("direct-media-list", {interaction.guild_id: vxt_service.default_settings["direct-media-list"]})
        temp_dm_list[interaction.guild_id]["multiple_images"][option.value] = not temp_dm_list[interaction.guild_id]["multiple_images"][option.value]
        await vxt_service.write_file_content("direct-media-list", temp_dm_list)
        status = "on" if temp_dm_list[interaction.guild_id]["multiple_images"][option.value] else "off"
        await interaction.response.send_message(f"Multiple images {option.name} is now {status}.")

    @vxt_direct_media.command(name="quote-tweet", description="Configure behavior for quote tweets in direct media.")
    @app_commands.describe(option="Select an option.")
    @app_commands.choices(option=[app_commands.Choice(name="convert", value="convert"), app_commands.Choice(name="prefer quoted tweet", value="prefer_quoted_tweet")])
    @app_commands.checks.has_permissions(manage_guild=True)
    async def dm_quote(self, interaction: discord.Interaction, option: app_commands.Choice[str]):
        temp_dm_list = vxt_service.read_file_content("direct-media-list", {interaction.guild_id: vxt_service.default_settings["direct-media-list"]})
        temp_dm_list[interaction.guild_id]["quote_tweet"][option.value] = not temp_dm_list[interaction.guild_id]["quote_tweet"][option.value]
        await vxt_service.write_file_content("direct-media-list", temp_dm_list)
        status = "on" if temp_dm_list[interaction.guild_id]["quote_tweet"][option.value] else "off"
        await interaction.response.send_message(f"Direct media quote tweet {option.name} is now {status}.")

    # --- Translate Commands ---
    async def lang_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        langs = [item.name for item in list(pycountry.languages) if hasattr(item, "alpha_2")]
        return [app_commands.Choice(name=l, value=l) for l in langs if current.lower() in l.lower()][:25]

    @vxt_translate.command(name="toggle", description="Toggle tweet translation.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def trans_toggle(self, interaction: discord.Interaction):
        temp = vxt_service.read_file_content("translate-list", {interaction.guild_id: vxt_service.default_settings["translate-list"]})
        temp[interaction.guild_id]["toggle"] = not temp[interaction.guild_id]["toggle"]
        await vxt_service.write_file_content("translate-list", temp)
        await interaction.response.send_message(f"Translation is now {'on' if temp[interaction.guild_id]['toggle'] else 'off'}.")

    @vxt_translate.command(name="language", description="Change target language.")
    @app_commands.describe(language="ISO code or full name.")
    @app_commands.autocomplete(language=lang_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def trans_lang(self, interaction: discord.Interaction, language: str):
        await interaction.response.defer()
        lang_map = {i.name: i.alpha_2 for i in list(pycountry.languages) if hasattr(i, "alpha_2")}
        if language not in lang_map:
            return await interaction.edit_original_response(content="Please select a language from the options.")
        
        temp = vxt_service.read_file_content("translate-list", {interaction.guild_id: vxt_service.default_settings["translate-list"]})
        temp[interaction.guild_id]["language"] = lang_map[language]
        await vxt_service.write_file_content("translate-list", temp)
        await interaction.edit_original_response(content=f"Translation language set to {language}.")

    # --- Blacklist Command ---
    @app_commands.command(name="vxt-blacklist", description="Blacklist users or roles from conversions.")
    @app_commands.describe(action="The action to be performed.", user="Select a user.", role="Select a role.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def vxt_blacklist(self, interaction: discord.Interaction, action: typing.Literal["add", "remove", "list", "clear"], user: typing.Optional[discord.User], role: typing.Optional[discord.Role]):
        temp = vxt_service.read_file_content("blacklist-list", {interaction.guild_id: vxt_service.default_settings["blacklist-list"]})
        u_set = set(temp[interaction.guild_id]["users"])
        r_set = set(temp[interaction.guild_id]["roles"])

        if action == "add":
            if user: u_set.add(user.id)
            if role: r_set.add(role.id)
            msg = f"Added to blacklist."
        elif action == "remove":
            if user and user.id in u_set: u_set.remove(user.id)
            if role and role.id in r_set: r_set.remove(role.id)
            msg = f"Removed from blacklist."
        elif action == "list":
            u_str = "\n".join([f"- <@{i}>" for i in u_set])
            r_str = "\n".join([f"- <@&{i}>" for i in r_set])
            return await interaction.response.send_message(f"Users:\n{u_str}\nRoles:\n{r_str}")
        elif action == "clear":
            u_set.clear(); r_set.clear()
            msg = "Blacklist cleared."
        
        temp[interaction.guild_id]["users"] = list(u_set)
        temp[interaction.guild_id]["roles"] = list(r_set)
        await vxt_service.write_file_content("blacklist-list", temp)
        await interaction.response.send_message(msg)

    # --- Mention Commands ---
    @vxt_mention.command(name="remove", description="Manage mentions to ignore.")
    @app_commands.describe(action="The action to be performed.", mention="Select a user or role.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def mention_rem_cmd(self, interaction: discord.Interaction, action: typing.Literal["add", "remove", "list", "clear"], mention: typing.Optional[typing.Union[discord.User, discord.Role]]):
        temp = vxt_service.read_file_content("mention-remove-list", {interaction.guild_id: vxt_service.default_settings["mention-remove-list"]})
        m_set = set(temp[interaction.guild_id])
        
        if action == "add" and mention: m_set.add(mention.mention)
        elif action == "remove" and mention and mention.mention in m_set: m_set.remove(mention.mention)
        elif action == "list":
            listing = "\n".join([f"- {i}" for i in m_set])
            return await interaction.response.send_message(f"Ignored mentions:\n{listing}")
        elif action == "clear":
            m_set.clear()
        
        temp[interaction.guild_id] = list(m_set)
        await vxt_service.write_file_content("mention-remove-list", temp)
        await interaction.response.send_message(f"Mention list updated.")

    @vxt_mention.command(name="remove-all", description="Toggle all, roles or users mentions removal.")
    @app_commands.describe(groups="Target group.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def mention_rem_all(self, interaction: discord.Interaction, groups: typing.Literal["all", "roles", "users"]):
        temp = vxt_service.read_file_content("mention-remove-list", {interaction.guild_id: vxt_service.default_settings["mention-remove-list"]})
        m_set = set(temp[interaction.guild_id])
        if groups in m_set: m_set.remove(groups)
        else: m_set.add(groups)
        temp[interaction.guild_id] = list(m_set)
        await vxt_service.write_file_content("mention-remove-list", temp)
        await interaction.response.send_message(f"Toggled removal of {groups}.")

    # --- Conversion-List Commands ---
    async def conv_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        temp = vxt_service.read_file_content("conversion-list", {interaction.guild_id: vxt_service.default_settings["conversion-list"]})
        choices = [app_commands.Choice(name=f"{k} -> {v}", value=k) for k, v in temp[interaction.guild_id].items() if current.lower() in k.lower()]
        return choices[:25]

    @vxt_conversion.command(name="add", description="Add a domain conversion.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def conv_add(self, interaction: discord.Interaction, original: str, converted: str):
        if not re.match(domain_pattern, original) or not re.match(domain_pattern, converted):
            return await interaction.response.send_message("Please use 'domain.com' format.")
        temp = vxt_service.read_file_content("conversion-list", {interaction.guild_id: vxt_service.default_settings["conversion-list"]})
        temp[interaction.guild_id][original] = converted
        await vxt_service.write_file_content("conversion-list", temp)
        await interaction.response.send_message(f"Added conversion: {original} -> {converted}")

    @vxt_conversion.command(name="update", description="Update a domain conversion.")
    @app_commands.autocomplete(original=conv_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def conv_update(self, interaction: discord.Interaction, original: str, updated: str):
        temp = vxt_service.read_file_content("conversion-list", {interaction.guild_id: vxt_service.default_settings["conversion-list"]})
        if original in temp[interaction.guild_id]:
            temp[interaction.guild_id][original] = updated
            await vxt_service.write_file_content("conversion-list", temp)
            await interaction.response.send_message(f"Updated {original} to {updated}.")
        else:
            await interaction.response.send_message("Domain not found.")

    @vxt_conversion.command(name="remove", description="Remove a domain conversion.")
    @app_commands.autocomplete(original=conv_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def conv_remove(self, interaction: discord.Interaction, original: str):
        temp = vxt_service.read_file_content("conversion-list", {interaction.guild_id: vxt_service.default_settings["conversion-list"]})
        if original in temp[interaction.guild_id]:
            del temp[interaction.guild_id][original]
            await vxt_service.write_file_content("conversion-list", temp)
            await interaction.response.send_message(f"Removed {original}.")
        else:
            await interaction.response.send_message("Domain not found.")

    @vxt_conversion.command(name="list", description="List all domain conversions.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def conv_list(self, interaction: discord.Interaction):
        temp = vxt_service.read_file_content("conversion-list", {interaction.guild_id: vxt_service.default_settings["conversion-list"]})
        listing = "\n".join([f"- {k} : {v}" for k, v in temp[interaction.guild_id].items()])
        await interaction.response.send_message(f"Conversions:\n{listing}")

    # --- Quote-Tweet Commands ---
    @vxt_quote_tweet.command(name="link-conversion", description="Toggle quote tweet link conversion details.")
    @app_commands.describe(type="The type of tweet content.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def qt_link(self, interaction: discord.Interaction, type: typing.Literal["text", "images", "videos", "polls", "all", "follow tweets"]):
        temp = vxt_service.read_file_content("quote-tweet-list", {interaction.guild_id: vxt_service.default_settings["quote-tweet-list"]})
        if type == "all":
            new_val = not temp[interaction.guild_id]["link_conversion"]["all"]
            for k in ["text", "images", "videos", "polls", "all"]: temp[interaction.guild_id]["link_conversion"][k] = new_val
            temp[interaction.guild_id]["link_conversion"]["follow tweets"] = False
        else:
            temp[interaction.guild_id]["link_conversion"][type] = not temp[interaction.guild_id]["link_conversion"][type]
        await vxt_service.write_file_content("quote-tweet-list", temp)
        await interaction.response.send_message(f"Toggled {type} for quote tweets.")

    @vxt_quote_tweet.command(name="remove-quoted-tweet", description="Toggle removal of the original quoted tweet.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def qt_rem(self, interaction: discord.Interaction):
        temp = vxt_service.read_file_content("quote-tweet-list", {interaction.guild_id: vxt_service.default_settings["quote-tweet-list"]})
        temp[interaction.guild_id]["remove quoted tweet"] = not temp[interaction.guild_id]["remove quoted tweet"]
        await vxt_service.write_file_content("quote-tweet-list", temp)
        await interaction.response.send_message(f"Quoted tweet removal toggled {'on' if temp[interaction.guild_id]['remove quoted tweet'] else 'off'}.")

    # --- Other Top-Level Commands ---
    @app_commands.command(name="vxt-message", description="Configure message deletion and webhook behavior.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def vxt_message(self, interaction: discord.Interaction, delete_original: typing.Optional[bool], other_webhooks: typing.Optional[bool]):
        temp = vxt_service.read_file_content("message-list", {interaction.guild_id: vxt_service.default_settings["message-list"]})
        if delete_original is not None: temp[interaction.guild_id]["delete_original"] = delete_original
        if other_webhooks is not None: temp[interaction.guild_id]["other_webhooks"] = other_webhooks
        await vxt_service.write_file_content("message-list", temp)
        await interaction.response.send_message("Message configuration updated.")

    @app_commands.command(name="vxt-retweet", description="Toggle original deletion for retweets.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def vxt_retweet(self, interaction: discord.Interaction, delete_original: bool):
        temp = vxt_service.read_file_content("retweet-list", {interaction.guild_id: vxt_service.default_settings["retweet-list"]})
        temp[interaction.guild_id]["delete_original_tweet"] = delete_original
        await vxt_service.write_file_content("retweet-list", temp)
        await interaction.response.send_message(f"Retweet original deletion set to {delete_original}.")

    @app_commands.command(name="vxt-webhooks", description="Configure webhook vs reply preference.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def vxt_webhooks(self, interaction: discord.Interaction, preference: typing.Literal["webhooks", "replies"], reply: bool):
        temp = vxt_service.read_file_content("webhook-list", {interaction.guild_id: vxt_service.default_settings["webhook-list"]})
        temp[interaction.guild_id]["preference"] = preference
        temp[interaction.guild_id]["reply"] = reply
        await vxt_service.write_file_content("webhook-list", temp)
        await interaction.response.send_message("Webhook/Reply preferences updated.")

    @app_commands.command(name="vxt-delete-bot-message", description="Configure bot message deletion via reactions.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def vxt_delete_bot_msg(self, interaction: discord.Interaction, toggle: bool, reaction_count: int):
        temp = vxt_service.read_file_content("delete-bot-message-list", {interaction.guild_id: vxt_service.default_settings["delete-bot-message-list"]})
        temp[interaction.guild_id]["toggle"] = toggle
        temp[interaction.guild_id]["number"] = reaction_count
        await vxt_service.write_file_content("delete-bot-message-list", temp)
        await interaction.response.send_message(f"Bot message deletion configured (Toggle: {toggle}, Count: {reaction_count}).")

    @app_commands.command(name="vxt-name-preference", description="Configure display name vs username preference.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def vxt_name_pref(self, interaction: discord.Interaction, preference: typing.Literal["display name", "username"]):
        temp = vxt_service.read_file_content("name-preference-list", {interaction.guild_id: vxt_service.default_settings["name-preference-list"]})
        temp[interaction.guild_id] = preference
        await vxt_service.write_file_content("name-preference-list", temp)
        await interaction.response.send_message(f"Name preference set to {preference}.")

    @app_commands.command(name="vxt-reset-settings", description="Reset all VxT settings to default.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def vxt_reset(self, interaction: discord.Interaction):
        for key in vxt_service.default_settings:
            temp = vxt_service.read_file_content(key, {})
            temp[interaction.guild_id] = vxt_service.default_settings[key]
            await vxt_service.write_file_content(key, temp)
        await interaction.response.send_message("All VxT settings have been reset to default for this server.")

    @app_commands.command(name="vxt-error-list", description="List recent conversion errors.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def vxt_err_list(self, interaction: discord.Interaction):
        await interaction.response.send_message("No recent errors logged.")

async def setup(bot):
    await bot.add_cog(VxT_slash(bot))
