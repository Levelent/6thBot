from discord.ext import commands
from discord import Member, Embed
from typing import Optional
from datetime import datetime
from util.timeformatter import highest_denom


class Inspect(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        response = await ctx.send("🏓 Pong!")
        diff = response.created_at - ctx.message.created_at
        milliseconds = int(diff.total_seconds() * 1000)
        print(f"Latency: {milliseconds}ms")
        await response.edit(content=f"🏓 Pong! `{milliseconds}ms`")

    @commands.command()
    async def profile(self, ctx, member: Optional[Member] = None):
        if member is None:
            member = ctx.author

        # Embed colour becomes yellow if the account is less than 7 days old.
        create_now_diff = datetime.utcnow() - member.created_at
        if create_now_diff.days < 7:
            colour = 0xEED202
        else:
            colour = 0xFA8072

        em = Embed(title=str(member), colour=colour, url=str(member.avatar_url))
        em.set_thumbnail(url=str(member.avatar_url))
        em.add_field(name="User ID", value=member.id)
        em.add_field(name="Display Name", value=member.display_name)
        em.set_author(name=f"Requested by {str(ctx.author)}", icon_url=str(ctx.author.avatar_url))
        create_join_diff = member.joined_at - member.created_at

        notes = [f"Account is about {highest_denom(create_now_diff)} old.",
                 f"Joined about {highest_denom(create_join_diff)} after account creation."]
        if member.premium_since is not None:
            boost_now_diff = datetime.utcnow() - member.premium_since
            notes.append(f"Has been boosting for about {highest_denom(boost_now_diff)}.")

        em.add_field(name="Notes:", inline=False, value="\n".join(notes))

        created_str = member.created_at.strftime("%H:%M %d/%m/%y")
        joined_str = member.joined_at.strftime("%H:%M %d/%m/%y")
        em.add_field(name="Created At", value=created_str)
        em.add_field(name="Joined At", value=joined_str)

        sorted_members = sorted(member.guild.members, key=lambda x: x.joined_at)
        pos = sorted_members.index(member) + 1
        em.add_field(name="Join Position", value=f"{pos}/{len(member.guild.members)}")

        mention_list = [role.mention for role in reversed(member.roles[1:])]
        if mention_list:
            role_str = " ".join(mention_list)
        else:
            role_str = "No Additional Roles."

        em.add_field(name="Roles", value=role_str, inline=False)
        em.set_footer(text="All times in UTC | Date format: dd/mm/yy")
        await ctx.send(embed=em)


def setup(bot):
    bot.add_cog(Inspect(bot))
