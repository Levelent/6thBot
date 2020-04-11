# TODO (Incomplete) - Welcomes users on join, gives them the filter role and removes after X minutes.
# TODO Implements a manual verification command which stops the automatic removal and places notices in channels.
from discord.ext import commands
from discord import Member, Guild, Message, NotFound
from asyncio import sleep
from util.timeformatter import highest_denom


def get_text(filename):
    with open(f"text/{filename}.txt") as file:
        return file.read()


class Filter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.welcome_msg = get_text("welcome_msg")
        self.man_msg = get_text("man_msg")
        print(self.welcome_msg)
        print(self.man_msg)
        self.welcome_chl_id = 683451235734782010
        self.rules_chl_id = 683484613858820136
        self.years_chl_id = 566264662975315992

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

    def is_manual(self, guild: Guild) -> bool:
        guild_settings = self.bot.guild_settings[str(guild.id)]
        return guild_settings.get("manual", False)
        # could replace presence check with something else?

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        print("Member joined")
        guild: Guild = member.guild

        # Adds the filter role, if one exists
        filter_role = self.get_filter_role(guild)
        if filter_role is None:
            return
        await member.add_roles(filter_role)

        # TODO: Replace all the channel attributes with a lookup in text.
        w_chl = self.bot.get_channel(self.welcome_chl_id)
        r_chl = self.bot.get_channel(self.rules_chl_id)
        y_chl = self.bot.get_channel(self.years_chl_id)
        filter_secs = self.get_filter_time(member.guild)
        is_manual = self.is_manual(member.guild)
        if is_manual:
            dm_msg = self.welcome_msg + "\n\n:warning: Note: We're in manual verification, so you'll need to **__contact a member of staff__** to get verified :warning:"
            next_step = ("We’re currently in **manual verification**, "
                         "so you’ll need to *message an online staff member* to get verified. "
                         f"Check the {r_chl.mention} channel for more information.")
        else:
            dm_msg = self.welcome_msg + "\n\n:warning: Note: We have a **__15 minute wait timer__** as a spam prevention measure. :warning:"
            next_step = ("As a *spam prevention* measure, you won't be able to do anything "
                         f"for the first **{highest_denom(filter_secs)}.** "
                         f"Take some time to read through {r_chl.mention}.")
        await member.send(dm_msg)
        await w_chl.send(f"Hey {member.mention}, Welcome to our **{guild.name}!**\n\n"
                         f"🔸 {next_step}\n\n"
                         f"Then, visit {y_chl.mention} to assign yourself a year! "
                         "We've sent you a message with instructions on how to join channels.")

        if not is_manual:
            await sleep(filter_secs)
            await member.remove_roles(filter_role)
            print(f"Removed filter role from {str(member)}")

    @commands.command()
    @commands.has_guild_permissions(manage_roles=True)
    async def manual(self, ctx, value: bool):
        guild_settings = self.bot.guild_settings[str(ctx.guild.id)]
        r_chl = self.bot.get_channel(self.rules_chl_id)
        if value is True:
            guild_settings['manual'] = True
            man_msg: Message = await r_chl.send(self.man_msg)
            guild_settings['man_msg_id'] = man_msg.id
            await ctx.send("Manual Verification Enabled.")
        else:
            guild_settings.pop('manual', None)
            man_msg_id = guild_settings.pop('man_msg_id', None)
            if man_msg_id is not None:
                try:
                    man_msg = await r_chl.fetch_message(man_msg_id)
                    await man_msg.delete()
                except NotFound:
                    print("Message not found")
            await ctx.send("Manual Verification Disabled.")

    @manual.error
    async def manual_error(self, ctx, error):
        print(error)
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("You haven't specified `on` or `off`!")
        elif isinstance(error, commands.UserInputError):
            await ctx.send("I can't understand whether you want to turn manual mode `on` or `off`.")


def setup(bot):
    bot.add_cog(Filter(bot))
