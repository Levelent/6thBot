# TODO (Incomplete) - Welcomes users on join, gives them the filter role and removes after X minutes.
# TODO Implements a manual verification command which stops the automatic removal and places notices in channels.
from discord.ext import commands
from discord import Member, Guild


class Filter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.welcome_chl_id = 683451235734782010
        self.filter_role_id = 606791111083556885
        self.rules_chl_id = 683484613858820136
        self.years_chl_id = 566264662975315992

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        print("Member joined")
        guild: Guild = member.guild
        filter_role = guild.get_role(self.filter_role_id)
        await member.add_roles(filter_role)
        w_chl = self.bot.get_channel(self.welcome_chl_id)
        r_chl = self.bot.get_channel(self.rules_chl_id)
        y_chl = self.bot.get_channel(self.years_chl_id)
        await w_chl.send(f"Hey {member.mention}, Welcome to our **{guild.name}!**\n\n"
                         "🔸 We’re currently in **manual verification**, "
                         "so you’ll need to *message an online staff member* to get verified. "
                         f"Check the {r_chl.mention} channel for more information.\n\n"
                         f"Then, visit {y_chl.mention} to assign yourself a year! "
                         "We've sent you a message with instructions on how to join channels.")


def setup(bot):
    bot.add_cog(Filter(bot))
