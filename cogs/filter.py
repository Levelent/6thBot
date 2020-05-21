from discord.ext import commands
from discord import Member, Guild, Message, NotFound, TextChannel, Embed, Role
from datetime import datetime
from asyncio import sleep
from util.timeformatter import highest_denom
from typing import Union


class Filter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_filter_time(self, guild: Guild) -> int:
        """
        :param guild: a discord.Guild object
        :return: the filter time, in seconds.
        """
        guild_settings = self.bot.guild_settings[str(guild.id)]
        return 60 * guild_settings.get("filter_time", 15)

    def get_filter_role(self, guild: Guild):
        guild_settings = self.bot.guild_settings[str(guild.id)]
        filter_role_id = guild_settings.get("filter_role_id", None)
        if filter_role_id is None:
            return None
        return guild.get_role(filter_role_id)

    def get_new_acc_role(self, guild: Guild):
        guild_settings = self.bot.guild_settings[str(guild.id)]
        new_acc_role_id = guild_settings.get("new_acc_role_id", None)
        if new_acc_role_id is None:
            return None
        return guild.get_role(new_acc_role_id)

    def get_manual_chl(self, guild: Guild):
        guild_settings = self.bot.guild_settings[str(guild.id)]
        manual_chl_id = guild_settings.get("manual_chl_id", None)
        if manual_chl_id is None:
            return None
        return guild.get_channel(manual_chl_id)

    def get_manual_content(self, guild: Guild):
        guild_settings = self.bot.guild_settings[str(guild.id)]
        return guild_settings.get("manual_content", None)

    def get_welcome_chl(self, guild: Guild):
        guild_settings = self.bot.guild_settings[str(guild.id)]
        welcome_chl_id = guild_settings.get("welcome_chl_id", None)
        if welcome_chl_id is None:
            return None
        return guild.get_channel(welcome_chl_id)

    def is_manual(self, guild: Guild) -> bool:
        guild_settings = self.bot.guild_settings[str(guild.id)]
        return guild_settings.get("manual", False)
        # could replace presence check with something else?

    async def send_welcomes(self, member):
        guild_settings = self.bot.guild_settings[str(member.guild.id)]
        welcome_messages: dict = guild_settings['welcome_messages']

        filter_secs = self.get_filter_time(member.guild)
        # Manual verification text
        if self.is_manual(member.guild):
            text = "We're in manual verification, so you'll need to **__contact a member of staff__** to get verified."
        else:

            text = f"You'll have to wait **__{highest_denom(filter_secs)}__** as a spam prevention measure."

        for name, msg_dict in welcome_messages.items():
            # destination is either a Member or TextChannel
            chl_id = msg_dict['chl_id']
            if chl_id == "dm":
                destination = member
            else:
                destination = member.guild.get_channel(chl_id)
                if destination is None:
                    continue

            content: str = msg_dict['content']
            # Replace keywords
            content = content.replace("<user>", member.mention)
            content = content.replace("<timer>", highest_denom(filter_secs))
            content = content.replace("<verification>", text)

            await destination.send(content)

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        print("Member joined")
        guild: Guild = member.guild

        # Adds the filter role, if one exists
        filter_role = self.get_filter_role(guild)
        if filter_role is None:
            return
        await member.add_roles(filter_role)

        create_now_diff = datetime.utcnow() - member.created_at
        if create_now_diff.days < 14:
            new_acc_role = self.get_new_acc_role(guild)
            if new_acc_role is not None:
                await member.add_roles(new_acc_role)

        await self.send_welcomes(member)

        if not self.is_manual(guild):
            # Schedule Role removal
            filter_secs = self.get_filter_time(member.guild)
            await sleep(filter_secs)
            await member.remove_roles(filter_role)
            print(f"Removed {filter_role.name} role from {str(member)}")

    @commands.group(invoke_without_command=True)
    @commands.has_guild_permissions(manage_roles=True)
    async def manual(self, ctx):
        if self.is_manual(ctx.guild):
            toggle_text = "Enabled"
        else:
            toggle_text = "Disabled"

        man_chl = self.get_manual_chl(ctx.guild)
        if man_chl is None:
            chl_text = "None set."
        else:
            chl_text = man_chl.mention
        em = Embed(title="Manual Verification Settings", colour=0xFA8072)
        em.set_author(name=f"Requested by {str(ctx.author)}", icon_url=str(ctx.author.avatar_url))
        em.add_field(name="Status", value=toggle_text)
        em.add_field(name="Notify Channel", value=chl_text)
        em.set_footer(text="Sub-commands: on | off | set | message")
        em.set_thumbnail(url=str(ctx.guild.icon_url))
        await ctx.send(embed=em)

    @manual.command(name="on")
    @commands.has_guild_permissions(manage_roles=True)
    async def manual_on(self, ctx):
        guild_settings = self.bot.guild_settings[str(ctx.guild.id)]

        man_chl = self.get_manual_chl(ctx.guild)
        if man_chl is None:
            ctx.send("No manual channel has been set.")
            return
        content = self.get_manual_content(ctx.guild)
        if content is None:
            ctx.send("No manual message has been set.")
            return
        guild_settings['manual'] = True
        sent = await man_chl.send(content)
        guild_settings['man_msg_id'] = sent.id
        await ctx.send("Manual Verification Enabled.")

    @manual.command(name="off")
    @commands.has_guild_permissions(manage_roles=True)
    async def manual_off(self, ctx):
        guild_settings = self.bot.guild_settings[str(ctx.guild.id)]
        man_chl = self.get_manual_chl(ctx.guild)
        guild_settings.pop('manual', None)
        man_msg_id = guild_settings.pop('man_msg_id', None)
        if man_msg_id is not None:
            try:
                man_msg = await man_chl.fetch_message(man_msg_id)
                await man_msg.delete()
            except NotFound:
                print("Message not found")
        await ctx.send("Manual Verification Disabled.")

    @manual.command(name="set")
    @commands.has_guild_permissions(manage_roles=True)
    async def manual_set(self, ctx, message: Message, channel: TextChannel):
        print("Manual Set")
        guild_settings: dict = self.bot.guild_settings[str(ctx.guild.id)]
        guild_settings['manual_chl_id'] = channel.id
        guild_settings['manual_content'] = message.content
        await ctx.send(f"Set manual verification notice for {channel.mention}")

    @manual.command(name="message")
    @commands.has_guild_permissions(manage_roles=True)
    async def manual_message(self, ctx):
        content = self.get_manual_content(ctx.guild)
        if content is None:
            ctx.send("No manual message has been set.")
            return
        await ctx.send(content)

    @commands.group(invoke_without_command=True)
    @commands.has_guild_permissions(manage_roles=True)
    async def welcome(self, ctx, name: str = None):
        guild_settings: dict = self.bot.guild_settings[str(ctx.guild.id)]
        welcome_messages: dict = guild_settings.get("welcome_messages", {})

        # Name specified
        if name is not None:
            welcome_msg = welcome_messages.get(name, None)
            if welcome_msg is None:
                await ctx.send("Couldn't find a welcome message with this name...")
            else:
                await ctx.send(welcome_msg['content'])
            return

        # No name specified
        welcome_list = []
        for name, data in welcome_messages.items():
            chl_id = data['chl_id']
            if isinstance(chl_id, int):
                channel = ctx.guild.get_channel(chl_id)
                if channel is None:
                    location = None
                else:
                    location = channel.mention
            else:
                location = "DMs"
            welcome_list.append(f"`{name}` in {location}")

        print(welcome_list)

        em = Embed(title="Server Welcome Messages", description="\n".join(welcome_list) or "None set.", colour=0xFA8072)
        em.set_footer(text="Sub-commands: add | remove | filter | restrict | [name]")
        em.set_author(name=f"Requested by {str(ctx.author)}", icon_url=str(ctx.author.avatar_url))
        em.set_thumbnail(url=str(ctx.guild.icon_url))

        filter_role = self.get_filter_role(ctx.guild)
        if filter_role is None:
            role_text = "None set."
        else:
            role_text = filter_role.mention
        em.add_field(name="Filter Role", value=role_text)

        filter_secs = self.get_filter_time(ctx.guild)
        em.add_field(name="Filter Timer", value=highest_denom(filter_secs))

        restrict_role = self.get_new_acc_role(ctx.guild)
        if restrict_role is None:
            role_text = "None set."
        else:
            role_text = restrict_role.mention
        em.add_field(name="New Account Role", value=role_text)
        await ctx.send(embed=em)

    @welcome.command(name="add")
    @commands.has_guild_permissions(manage_roles=True)
    async def welcome_add(self, ctx, message: Message, destination: Union[TextChannel, str], name: str):
        if isinstance(destination, str):
            if destination.lower() != "dm":
                await ctx.send("It looks like you haven't properly specified a channel, or the keyword 'DM'.")
                return
            chl_id = "dm"
        else:
            chl_id = destination.id

        # "welcome_messages": [{'chl_id': 83, 'content': "test"}, {'chl_id': "dm", 'content': "Hi <user>!"}]
        guild_settings: dict = self.bot.guild_settings[str(ctx.guild.id)]
        if 'welcome_messages' not in guild_settings:
            guild_settings['welcome_messages'] = {}
        guild_settings['welcome_messages'][name] = {'chl_id': chl_id, 'content': message.content}

        await ctx.send(f"The following welcome message was added:\n{message.jump_url}")

    @welcome.command(name="remove")
    @commands.has_guild_permissions(manage_roles=True)
    async def welcome_remove(self, ctx, name: str):
        guild_settings: dict = self.bot.guild_settings[str(ctx.guild.id)]
        welcome_messages: dict = guild_settings['welcome_messages']
        welcome_msg = welcome_messages.get(name, None)
        if welcome_msg is None:
            await ctx.send("Couldn't find a welcome message with this name...")
            return
        welcome_messages.pop(name)

        if len(welcome_messages) == 0:
            guild_settings.pop('welcome_messages')
        await ctx.send(f"Welcome message `{name}` removed.")

    @welcome.command(name="filter")
    @commands.has_guild_permissions(manage_roles=True)
    async def welcome_filter(self, ctx, role: Role, filter_minutes: int):
        if filter_minutes < 1:
            await ctx.send("Choose a number of minutes greater than 0.")
            return
        guild_settings: dict = self.bot.guild_settings[str(ctx.guild.id)]
        guild_settings['filter_role_id'] = role.id
        guild_settings['filter_time'] = filter_minutes
        await ctx.send(f"Welcome filter set on {role.mention}, will be removed after {filter_minutes} minutes.")

    @welcome.command(name="restrict")
    @commands.has_guild_permissions(manage_roles=True)
    async def welcome_restrict(self, ctx, role: Role):
        guild_settings: dict = self.bot.guild_settings[str(ctx.guild.id)]
        guild_settings['new_acc_role_id'] = role.id
        await ctx.send(f"Restriction set on {role.mention}, role will be applied to new accounts (<14 days)")


def setup(bot):
    bot.add_cog(Filter(bot))
