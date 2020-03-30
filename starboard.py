from discord.ext import commands
from discord import Embed


class Starboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_store = {}
        self.chl_id = 530763055613607947

    async def message_react_count_update(self, message, number):
        pass

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        print(reaction.emoji)
        if reaction.emoji != "⭐" or self.chl_id is None:
            return
        if reaction.message.id in self.message_store:
            star_msg = await self.bot.get_channel(self.chl_id).fetch_message(self.message_store[reaction.message.id])
            await star_msg.edit(content="⭐ **{}** | {}".format(reaction.count, reaction.message.channel.mention))
        elif reaction.count >= 1:
            em = Embed(colour=0x8B008B,
                       description="[Jump to original]({})\n{}".format(reaction.message.jump_url, reaction.message.content))
            em.set_author(name=str(reaction.message.author), icon_url=reaction.message.author.avatar_url)
            if len(reaction.message.attachments) != 0:
                em.add_field(name="Attachments", value=reaction.message.attachments)
            star_msg = await self.bot.get_channel(self.chl_id).send("⭐**{}** | {}".format(reaction.count, reaction.message.channel.mention), embed=em)
            self.message_store[reaction.message.id] = star_msg.id

    @commands.command()
    async def star_channel(self, ctx, *, target=None):
        if target is None:
            self.chl_id = None
            await ctx.channel.send("Starboard channel removed.")
            return
        if len(ctx.message.channel_mentions) != 1:
            await ctx.channel.send("Channel not found. Make sure you pass through the channel mention, not the name.")
            return
        log_chl = ctx.message.channel_mentions[0]
        self.chl_id = log_chl.id
        await ctx.channel.send("Starboard channel updated to: {}".format(log_chl.mention))

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def threshold(self, ctx, value="5"):
        try:
            value = int(value)
        except ValueError:
            await ctx.send("Hey, uh, you might want to actually use an integer there.")
            return
        if value < 1:
            await ctx.send(f"Ah yes, a threshold of {value} messages. That makes perfect sense.")
            return
        elif value > 9000000000:
            await ctx.send("What you entered there is literally larger than the population of the earth. Get help.")
        self.threshold = value
        await ctx.channel.send(f"Reaction threshold updated to: {value}")

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def emote(self, ctx, emote="⭐"):
        if emote.isdigit():
            e = self.bot.get_emoji(int(emote))
            if e is None:
                await ctx.send("The ID entered does not match any custom emote.")
            self.emote = int(emote)
            await ctx.send(f"Set emote to {str(e)}.")
            return

        try:
            await ctx.message.add_reaction(emote)
            self.emote = emote
            await ctx.send(f"Set emote to {self.emote}.")
        except NotFound:
            await ctx.send("What you entered is neither a standard emote, nor a custom emote id.")



def setup(bot):
    bot.add_cog(Starboard(bot))
