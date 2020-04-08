from discord.ext import commands
from discord import Member, Embed
from typing import Optional
from datetime import timedelta, datetime


def time2string(time: timedelta):
    """Converts to highest time denomination, rounded down."""
    multipliers = [60, 60, 24, 7, 52]
    denominations = ["seconds", "minutes", "hours", "days", "weeks", "years"]

    mp = 1
    seconds = time.total_seconds()
    print(seconds)
    for num in range(6):
        diff = seconds // mp
        if num < 5 and diff >= multipliers[num]:
            mp *= multipliers[num]
        else:
            diff_round = int(abs(diff))
            if diff_round == 1:
                denominations[num] = denominations[num][:-1]
            return f"{diff_round} {denominations[num]}"


class Inspect(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def profile(self, ctx, target: Optional[Member] = None):
        if target is None:
            target = ctx.author
        create_now_diff = datetime.utcnow() - target.created_at
        if create_now_diff.days < 7:
            colour = 0xEED202
        else:
            colour = 0x8B008B

        created_str = target.created_at.strftime("%H:%M %d/%m/%y")
        joined_str = target.joined_at.strftime("%H:%M %d/%m/%y")

        em = Embed(title=str(target), colour=colour, url=str(target.avatar_url))
        em.set_thumbnail(url=str(target.avatar_url))
        em.add_field(name="User ID", value=target.id)
        em.add_field(name="Display Name", value=target.display_name)
        em.set_author(name=f"Requested by {str(ctx.author)}", icon_url=str(ctx.author.avatar_url))
        create_join_diff = target.joined_at - target.created_at

        notes = [f"Account is about {time2string(create_now_diff)} old.",
                 f"Joined about {time2string(create_join_diff)} after account creation."]
        if target.premium_since is not None:
            boost_now_diff = datetime.utcnow() - target.premium_since
            notes.append(f"Has been boosting for about {time2string(boost_now_diff)}.")

        em.add_field(name="Notes:", inline=False, value="\n".join(notes))

        em.add_field(name="Created At", value=created_str)
        em.add_field(name="Joined At", value=joined_str)

        sorted_members = sorted(target.guild.members, key=lambda x: x.joined_at)
        pos = sorted_members.index(target) + 1
        em.add_field(name="Join Position", value=f"{pos}/{len(target.guild.members)}")

        mention_list = [role.mention for role in reversed(target.roles[1:])]
        if mention_list:
            role_str = " ".join(mention_list)
        else:
            role_str = "No Additional Roles."

        em.add_field(name="Roles", value=role_str, inline=False)
        em.set_footer(text="All times in UTC | Date format: dd/mm/yy")
        await ctx.send(embed=em)


def setup(bot):
    bot.add_cog(Inspect(bot))
