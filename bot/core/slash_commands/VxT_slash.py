import discord
from discord import app_commands
from discord.ext import commands
import typing
import re
import langcodes
import pycountry
from services.vxt_service import vxt_service_global as vxt_service
from lang.lang_utils import t

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
        status = t('vxt_status_on', guild_id=interaction.guild_id) if temp_toggle_list[interaction.guild_id][type] else t('vxt_status_off', guild_id=interaction.guild_id)
        tr_type = t(f'vxt_val_{type}', guild_id=interaction.guild_id)
        await interaction.response.send_message(t('vxt_toggle_success', type=tr_type, status=status, guild_id=interaction.guild_id))

    # --- Direct-Media Commands ---
    @vxt_direct_media.command(name="toggle", description="Toggle subdomain addition for Twitter links.")
    @app_commands.describe(type="The types of tweets to be converted.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def dm_toggle(self, interaction: discord.Interaction, type: typing.Literal["images", "videos"]) -> None:
        temp_dm_list = vxt_service.read_file_content("direct-media-list", {interaction.guild_id: vxt_service.default_settings["direct-media-list"]})
        temp_dm_list[interaction.guild_id]["toggle"][type] = not temp_dm_list[interaction.guild_id]["toggle"][type]
        await vxt_service.write_file_content("direct-media-list", temp_dm_list)
        status = t('vxt_status_on', guild_id=interaction.guild_id) if temp_dm_list[interaction.guild_id]["toggle"][type] else t('vxt_status_off', guild_id=interaction.guild_id)
        tr_type = t(f'vxt_val_{type}', guild_id=interaction.guild_id)
        await interaction.response.send_message(t('vxt_dm_toggle_success', type=tr_type, status=status, guild_id=interaction.guild_id))

    @vxt_direct_media.command(name="channel", description="Change permissions for which channels to convert in.")
    @app_commands.describe(action="The action to be performed.", channel="The channel to allow or prohibit.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def dm_channel(self, interaction: discord.Interaction, action: typing.Literal["list", "allow", "prohibit", "allow all", "prohibit all"], channel: typing.Optional[discord.abc.GuildChannel]):
        temp_dm_list = vxt_service.read_file_content("direct-media-list", {interaction.guild_id: vxt_service.default_settings["direct-media-list"]})
        if action == "list":
            chnl_list = temp_dm_list[interaction.guild_id]["channel"]
            if "allow" in chnl_list or "prohibit" in chnl_list:
                state = t('vxt_status_allowed', guild_id=interaction.guild_id) if "allow" in chnl_list else t('vxt_status_prohibited', guild_id=interaction.guild_id)
                return await interaction.response.send_message(t('vxt_dm_channels_all', state=state, guild_id=interaction.guild_id))
            
            allowed = "\n".join([f"- {c[1]}" for c in chnl_list if isinstance(c, list) and c[0] == "allow"])
            prohibited = "\n".join([f"- {c[1]}" for c in chnl_list if isinstance(c, list) and c[0] == "prohibit"])
            await interaction.response.send_message(t('vxt_dm_channels_list', allowed=allowed, prohibited=prohibited, guild_id=interaction.guild_id))
        
        elif action in ["allow", "prohibit"]:
            if not channel: return await interaction.response.send_message(t('vxt_error_select_channel', guild_id=interaction.guild_id))
            entry = [action, channel.mention]
            chnl_list = temp_dm_list[interaction.guild_id]["channel"]
            if entry in chnl_list or action in chnl_list:
                tr_action = t(f'vxt_val_{action}', guild_id=interaction.guild_id)
                return await interaction.response.send_message(t('vxt_dm_channel_already', channel=channel.mention, action=tr_action, guild_id=interaction.guild_id))
            
            opp = "prohibit" if action == "allow" else "allow"
            chnl_list = [item for item in chnl_list if item != [opp, channel.mention]]
            if opp in chnl_list: chnl_list.remove(opp)
            chnl_list.append(entry)
            temp_dm_list[interaction.guild_id]["channel"] = chnl_list
            await vxt_service.write_file_content("direct-media-list", temp_dm_list)
            tr_action = t(f'vxt_val_{action}', guild_id=interaction.guild_id)
            await interaction.response.send_message(t('vxt_dm_channel_success', channel=channel.mention, action=tr_action, guild_id=interaction.guild_id))
        
        elif action in ["allow all", "prohibit all"]:
            key = t('vxt_status_allowed', guild_id=interaction.guild_id) if action == "allow all" else t('vxt_status_prohibited', guild_id=interaction.guild_id)
            temp_dm_list[interaction.guild_id]["channel"] = ["allow" if action == "allow all" else "prohibit"]
            await vxt_service.write_file_content("direct-media-list", temp_dm_list)
            await interaction.response.send_message(t('vxt_dm_channels_all_success', key=key, guild_id=interaction.guild_id))

    @vxt_direct_media.command(name="multiple-images", description="Configure behavior for multiple images.")
    @app_commands.describe(option="Select an option.")
    @app_commands.choices(option=[app_commands.Choice(name="convert", value="convert"), app_commands.Choice(name="replace with mosaic", value="replace_with_mosaic")])
    @app_commands.checks.has_permissions(manage_guild=True)
    async def dm_multi(self, interaction: discord.Interaction, option: app_commands.Choice[str]):
        temp_dm_list = vxt_service.read_file_content("direct-media-list", {interaction.guild_id: vxt_service.default_settings["direct-media-list"]})
        temp_dm_list[interaction.guild_id]["multiple_images"][option.value] = not temp_dm_list[interaction.guild_id]["multiple_images"][option.value]
        await vxt_service.write_file_content("direct-media-list", temp_dm_list)
        status = t('vxt_status_on', guild_id=interaction.guild_id) if temp_dm_list[interaction.guild_id]["multiple_images"][option.value] else t('vxt_status_off', guild_id=interaction.guild_id)
        tr_option = t(f'vxt_val_{option.value}', guild_id=interaction.guild_id)
        await interaction.response.send_message(t('vxt_dm_multi_image_success', option=tr_option, status=status, guild_id=interaction.guild_id))

    @vxt_direct_media.command(name="quote-tweet", description="Configure behavior for quote tweets in direct media.")
    @app_commands.describe(option="Select an option.")
    @app_commands.choices(option=[app_commands.Choice(name="convert", value="convert"), app_commands.Choice(name="prefer quoted tweet", value="prefer_quoted_tweet")])
    @app_commands.checks.has_permissions(manage_guild=True)
    async def dm_quote(self, interaction: discord.Interaction, option: app_commands.Choice[str]):
        temp_dm_list = vxt_service.read_file_content("direct-media-list", {interaction.guild_id: vxt_service.default_settings["direct-media-list"]})
        temp_dm_list[interaction.guild_id]["quote_tweet"][option.value] = not temp_dm_list[interaction.guild_id]["quote_tweet"][option.value]
        await vxt_service.write_file_content("direct-media-list", temp_dm_list)
        status = t('vxt_status_on', guild_id=interaction.guild_id) if temp_dm_list[interaction.guild_id]["quote_tweet"][option.value] else t('vxt_status_off', guild_id=interaction.guild_id)
        tr_option = t(f'vxt_val_{option.value}', guild_id=interaction.guild_id)
        await interaction.response.send_message(t('vxt_dm_quote_success', option=tr_option, status=status, guild_id=interaction.guild_id))

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
        status = t('vxt_status_on', guild_id=interaction.guild_id) if temp[interaction.guild_id]['toggle'] else t('vxt_status_off', guild_id=interaction.guild_id)
        await interaction.response.send_message(t('vxt_translate_toggle_success', status=status, guild_id=interaction.guild_id))

    @vxt_translate.command(name="language", description="Change target language.")
    @app_commands.describe(language="ISO code or full name.")
    @app_commands.autocomplete(language=lang_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def trans_lang(self, interaction: discord.Interaction, language: str):
        await interaction.response.defer()
        lang_map = {i.name: i.alpha_2 for i in list(pycountry.languages) if hasattr(i, "alpha_2")}
        if language not in lang_map:
            return await interaction.edit_original_response(content=t('vxt_translate_lang_error', guild_id=interaction.guild_id))
        
        temp = vxt_service.read_file_content("translate-list", {interaction.guild_id: vxt_service.default_settings["translate-list"]})
        temp[interaction.guild_id]["language"] = lang_map[language]
        await vxt_service.write_file_content("translate-list", temp)
        await interaction.edit_original_response(content=t('vxt_translate_lang_success', language=language, guild_id=interaction.guild_id))

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
            msg = t('vxt_blacklist_add_success', guild_id=interaction.guild_id)
        elif action == "remove":
            if user and user.id in u_set: u_set.remove(user.id)
            if role and role.id in r_set: r_set.remove(role.id)
            msg = t('vxt_blacklist_remove_success', guild_id=interaction.guild_id)
        elif action == "list":
            u_str = "\n".join([f"- <@{i}>" for i in u_set])
            r_str = "\n".join([f"- <@&{i}>" for i in r_set])
            return await interaction.response.send_message(t('vxt_blacklist_list', u_str=u_str, r_str=r_str, guild_id=interaction.guild_id))
        elif action == "clear":
            u_set.clear(); r_set.clear()
            msg = t('vxt_blacklist_clear_success', guild_id=interaction.guild_id)
        
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
            return await interaction.response.send_message(t('vxt_mentions_list', listing=listing, guild_id=interaction.guild_id))
        elif action == "clear":
            m_set.clear()
        
        temp[interaction.guild_id] = list(m_set)
        await vxt_service.write_file_content("mention-remove-list", temp)
        await interaction.response.send_message(t('vxt_mentions_updated', guild_id=interaction.guild_id))

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
        tr_groups = t(f'vxt_val_{groups}', guild_id=interaction.guild_id)
        await interaction.response.send_message(t('vxt_mentions_toggle_success', groups=tr_groups, guild_id=interaction.guild_id))

    # --- Conversion-List Commands ---
    async def conv_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        temp = vxt_service.read_file_content("conversion-list", {interaction.guild_id: vxt_service.default_settings["conversion-list"]})
        choices = [app_commands.Choice(name=f"{k} -> {v}", value=k) for k, v in temp[interaction.guild_id].items() if current.lower() in k.lower()]
        return choices[:25]

    @vxt_conversion.command(name="add", description="Add a domain conversion.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def conv_add(self, interaction: discord.Interaction, original: str, converted: str):
        if not re.match(domain_pattern, original) or not re.match(domain_pattern, converted):
            return await interaction.response.send_message(t('vxt_conv_format_error', guild_id=interaction.guild_id))
        temp = vxt_service.read_file_content("conversion-list", {interaction.guild_id: vxt_service.default_settings["conversion-list"]})
        temp[interaction.guild_id][original] = converted
        await vxt_service.write_file_content("conversion-list", temp)
        await interaction.response.send_message(t('vxt_conv_add_success', original=original, converted=converted, guild_id=interaction.guild_id))

    @vxt_conversion.command(name="update", description="Update a domain conversion.")
    @app_commands.autocomplete(original=conv_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def conv_update(self, interaction: discord.Interaction, original: str, updated: str):
        temp = vxt_service.read_file_content("conversion-list", {interaction.guild_id: vxt_service.default_settings["conversion-list"]})
        if original in temp[interaction.guild_id]:
            temp[interaction.guild_id][original] = updated
            await vxt_service.write_file_content("conversion-list", temp)
            await interaction.response.send_message(t('vxt_conv_update_success', original=original, updated=updated, guild_id=interaction.guild_id))
        else:
            await interaction.response.send_message(t('vxt_error_domain_not_found', guild_id=interaction.guild_id))

    @vxt_conversion.command(name="remove", description="Remove a domain conversion.")
    @app_commands.autocomplete(original=conv_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def conv_remove(self, interaction: discord.Interaction, original: str):
        temp = vxt_service.read_file_content("conversion-list", {interaction.guild_id: vxt_service.default_settings["conversion-list"]})
        if original in temp[interaction.guild_id]:
            del temp[interaction.guild_id][original]
            await vxt_service.write_file_content("conversion-list", temp)
            await interaction.response.send_message(t('vxt_conv_remove_success', original=original, guild_id=interaction.guild_id))
        else:
            await interaction.response.send_message(t('vxt_error_domain_not_found', guild_id=interaction.guild_id))

    @vxt_conversion.command(name="list", description="List all domain conversions.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def conv_list(self, interaction: discord.Interaction):
        temp = vxt_service.read_file_content("conversion-list", {interaction.guild_id: vxt_service.default_settings["conversion-list"]})
        listing = "\n".join([f"- {k} : {v}" for k, v in temp[interaction.guild_id].items()])
        await interaction.response.send_message(t('vxt_conv_list', listing=listing, guild_id=interaction.guild_id))

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
        tr_type = t(f'vxt_val_{type}', guild_id=interaction.guild_id)
        await interaction.response.send_message(t('vxt_quote_toggle_success', type=tr_type, guild_id=interaction.guild_id))

    @vxt_quote_tweet.command(name="remove-quoted-tweet", description="Toggle removal of the original quoted tweet.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def qt_rem(self, interaction: discord.Interaction):
        temp = vxt_service.read_file_content("quote-tweet-list", {interaction.guild_id: vxt_service.default_settings["quote-tweet-list"]})
        temp[interaction.guild_id]["remove quoted tweet"] = not temp[interaction.guild_id]["remove quoted tweet"]
        await vxt_service.write_file_content("quote-tweet-list", temp)
        status = t('vxt_status_on', guild_id=interaction.guild_id) if temp[interaction.guild_id]['remove quoted tweet'] else t('vxt_status_off', guild_id=interaction.guild_id)
        await interaction.response.send_message(t('vxt_quote_remove_toggle_success', status=status, guild_id=interaction.guild_id))

    # --- Other Top-Level Commands ---
    @app_commands.command(name="vxt-message", description="Configure message deletion and webhook behavior.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def vxt_message(self, interaction: discord.Interaction, delete_original: typing.Optional[bool], other_webhooks: typing.Optional[bool]):
        temp = vxt_service.read_file_content("message-list", {interaction.guild_id: vxt_service.default_settings["message-list"]})
        if delete_original is not None: temp[interaction.guild_id]["delete_original"] = delete_original
        if other_webhooks is not None: temp[interaction.guild_id]["other_webhooks"] = other_webhooks
        await vxt_service.write_file_content("message-list", temp)
        await interaction.response.send_message(t('vxt_message_updated', guild_id=interaction.guild_id))

    @app_commands.command(name="vxt-retweet", description="Toggle original deletion for retweets.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def vxt_retweet(self, interaction: discord.Interaction, delete_original: bool):
        temp = vxt_service.read_file_content("retweet-list", {interaction.guild_id: vxt_service.default_settings["retweet-list"]})
        temp[interaction.guild_id]["delete_original_tweet"] = delete_original
        await vxt_service.write_file_content("retweet-list", temp)
        status = t('vxt_status_on', guild_id=interaction.guild_id) if delete_original else t('vxt_status_off', guild_id=interaction.guild_id)
        await interaction.response.send_message(t('vxt_retweet_success', status=status, guild_id=interaction.guild_id))

    @app_commands.command(name="vxt-webhooks", description="Configure webhook vs reply preference.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def vxt_webhooks(self, interaction: discord.Interaction, preference: typing.Literal["webhooks", "replies"], reply: bool):
        temp = vxt_service.read_file_content("webhook-list", {interaction.guild_id: vxt_service.default_settings["webhook-list"]})
        temp[interaction.guild_id]["preference"] = preference
        temp[interaction.guild_id]["reply"] = reply
        await vxt_service.write_file_content("webhook-list", temp)
        await interaction.response.send_message(t('vxt_webhook_updated', guild_id=interaction.guild_id))

    @app_commands.command(name="vxt-delete-bot-message", description="Configure bot message deletion via reactions.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def vxt_delete_bot_msg(self, interaction: discord.Interaction, toggle: bool, reaction_count: int):
        temp = vxt_service.read_file_content("delete-bot-message-list", {interaction.guild_id: vxt_service.default_settings["delete-bot-message-list"]})
        temp[interaction.guild_id]["toggle"] = toggle
        temp[interaction.guild_id]["number"] = reaction_count
        await vxt_service.write_file_content("delete-bot-message-list", temp)
        await interaction.response.send_message(t('vxt_bot_del_success', toggle=toggle, count=reaction_count, guild_id=interaction.guild_id))

    @app_commands.command(name="vxt-name-preference", description="Configure display name vs username preference.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def vxt_name_pref(self, interaction: discord.Interaction, preference: typing.Literal["display name", "username"]):
        temp = vxt_service.read_file_content("name-preference-list", {interaction.guild_id: vxt_service.default_settings["name-preference-list"]})
        temp[interaction.guild_id] = preference
        await vxt_service.write_file_content("name-preference-list", temp)
        tr_preference = t(f'vxt_val_{preference.replace(" ", "_")}', guild_id=interaction.guild_id)
        await interaction.response.send_message(t('vxt_name_pref_success', preference=tr_preference, guild_id=interaction.guild_id))

    @app_commands.command(name="vxt-reset-settings", description="Reset all VxT settings to default.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def vxt_reset(self, interaction: discord.Interaction):
        for key in vxt_service.default_settings:
            temp = vxt_service.read_file_content(key, {})
            temp[interaction.guild_id] = vxt_service.default_settings[key]
            await vxt_service.write_file_content(key, temp)
        await interaction.response.send_message(t('vxt_reset_success', guild_id=interaction.guild_id))

    @app_commands.command(name="vxt-error-list", description="List recent conversion errors.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def vxt_err_list(self, interaction: discord.Interaction):
        await interaction.response.send_message(t('vxt_error_none_logged', guild_id=interaction.guild_id))

async def setup(bot):
    await bot.add_cog(VxT_slash(bot))
