from discord.ext import commands
from datetime import timedelta, time, datetime
from asyncio import sleep


class AutoRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_id = 606791111083556885  # 'Spam Filter' role
        self.remove_time = timedelta(minutes=15)
        self.start_manual = time(hour=1)
        self.end_manual_hour = time(hour=7)

    async def message_react_count_update(self, message, number):
        pass

    @commands.Cog.listener()
    async def on_member_join(self, member):
        role = member.guild.get_role(self.role_id)
        await member.add_roles([role])
        current_datetime = datetime.now()
        start_datetime = datetime.now().replace(hour=self.start_manual.hour, minute=self.start_manual.minute, second=self.start_manual.second)
        end_datetime = datetime.now().replace(hour=self.end_manual.hour, minute=self.end_manual.minute, second=self.end_manual.second)
        current_hour = datetime.now().hour
        if start_datetime < current_datetime or current_datetime < end_datetime:  # Not manual
            await sleep(self.remove_time.total_seconds())
        else:

            await sleep()
        await member.remove_roles([role])


def setup(bot):
    bot.add_cog(AutoRole(bot))
