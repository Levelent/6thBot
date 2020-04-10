# TODO (Incomplete) - Welcomes users on join, gives them the filter role and removes after X minutes.
# TODO Implements a manual verification command which stops the automatic removal and places notices in channels.
from discord.ext import commands
from discord import Member, Guild
from asyncio import sleep
from util.timeformatter import highest_denom


class Filter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
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
        if self.manual:
            next_step = ("We’re currently in **manual verification**, "
                         "so you’ll need to *message an online staff member* to get verified. "
                         f"Check the {r_chl.mention} channel for more information.")
        else:
            next_step = ("As a *spam prevention* measure, you won't be able to do anything "
                         f"for the first **{highest_denom(filter_secs)}.** "
                         f"Take some time to read through {r_chl.mention}.")

        await w_chl.send(f"Hey {member.mention}, Welcome to our **{guild.name}!**\n\n"
                         f"🔸 {next_step}\n\n"
                         f"Then, visit {y_chl.mention} to assign yourself a year! "
                         "We've sent you a message with instructions on how to join channels.")

        if not self.manual:
            await sleep(filter_secs)

    @commands.command()
    @commands.has_guild_permissions(manage_roles=True)
    async def manual(self, ctx, value: bool):
        guild_settings = self.bot.guild_settings[str(ctx.guild.id)]
        if value is True:
            guild_settings['manual'] = True
            # TODO: Send rule change message in channel
            r_chl = self.bot.get_channel(self.rules_chl_id)
            # man_msg = await r_chl.send("")
            await ctx.send("Manual Verification Enabled.")
        else:
            guild_settings.remove('manual')
            await ctx.send("Manual Verification Disabled.")





def setup(bot):
    bot.add_cog(Filter(bot))
