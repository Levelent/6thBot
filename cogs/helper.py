import discord
from discord.ext import commands


class Manager(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="roleshift")
    @commands.has_guild_permissions(manage_guild=True)
    async def role_shift(self, ctx, old: commands.Greedy[discord.Role], flag: str, new: commands.Greedy[discord.Role]):
        """Moves all members that have at least one of the specified roles role to the other.
        using `>` removes the old role.
        using `+` maintains it."""

        valid_flags = [">", "+"]
        if flag not in valid_flags:
            await ctx.send(f"Make sure to use one of the following flags: `{'`,`'.join(valid_flags)}`")
            return

        old_members = []
        for role in old:
            for member in role.members:
                if member not in old_members:
                    old_members.append(member)
        print(old_members)

        msg = await ctx.send("Shifting member roles...")
        total = len(old_members)
        for num, member in enumerate(old_members):
            if flag in [">", "+"]:
                await member.add_roles(*new)
            if flag == ">":
                await member.remove_roles(*old)
            await msg.edit(content=f"Shifting member roles... [{num}/{total}]")
        await msg.edit(content=f"Shifted Roles for {total} members.")

    @commands.command(name="clearreact")
    @commands.has_guild_permissions(manage_guild=True)
    async def clear_react(self, ctx, message: discord.Message, emoji):
        await message.clear_reaction(emoji)
        await ctx.send("Reaction cleared.")


def setup(bot):
    bot.add_cog(Manager(bot))
