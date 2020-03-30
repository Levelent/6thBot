# TODO (Incomplete) need to have revise command (temp removes year role, adds revision role)
from discord.ext import commands, tasks
from json import loads


class Revise(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_cache = {}
        self.recent_role_update = False
        self.revision_role_id = 633821743156428830  # In the future, should be customisable
        self.revision_channel_id = 633823235808428032
        self.store_role.start()

    @commands.command()
    async def revise_role(self):
        pass

    @commands.command()
    async def revise(self, ctx):
        """Adds user to revision role, removes non-mod roles and stores their references in memory"""
        # Adds revision role
        revise_role = ctx.guild.get_role(self.revision_role_id)
        await ctx.author.addroles([revise_role])

        # Gets all non-moderator roles, stores and removes them.
        remove_list = []
        for role in ctx.author.roles:
            if not role.permissions.manage_messages:
                remove_list.append(role)
        self.role_cache[str(ctx.author.id)] = remove_list
        await ctx.author.removeroles(remove_list)

        await ctx.add_reaction("📚")
        self.recent_role_update = True

    @commands.command()
    async def goback(self, ctx):
        """Removes user from revision role, adds non-mod roles from memory"""
        if ctx.channel.id != self.revision_channel_id:  # #revision-bunker channel id
            return
        # Finds stored roles and gives them back
        role_add = []
        for role in self.role_cache[str(ctx.author.id)]:
            role_add.append(ctx.guild.get_role(role))
        await ctx.author.addroles(self.role_cache[str(ctx.author.id)])

        # Removes revision role
        revise_role = ctx.guild.get_role(self.revision_role_id)
        await ctx.author.removeroles([revise_role])

        await ctx.add_reaction("🖥️")
        self.recent_role_update = True
        return

    @tasks.loop(minutes=1.0)
    async def store_role(self):
        """Every minute, back up stored roles to file using role ID, as memory references are not persistent"""
        if not self.recent_role_update:
            pass

        # open json file
        for user in self.role_cache:
            # declare user dict
            for role in user:
                pass
                # append role id to user dict
            # json write

    @store_role.before_loop
    async def retrieve_role(self):
        """Retrieve all stored roles, should happen on bot reconnection or reboot."""
        with open("json/storage.json", "r", encoding="utf-8") as file:
            role_storage = loads(file.read())
            print(role_storage)
            for guild_id in role_storage:
                guild = self.bot.get_guild(guild_id)
                for user_id in role_storage[guild_id]:
                    role_add = []
                    for role_id in role_storage[guild_id][user_id]:
                        role_add.append(guild.get_role(role_id))
                    role_storage[guild_id][user_id] = role_add
        print(role_storage)
        self.role_cache = role_storage
        pass

    def cog_unload(self):
        self.store_role.cancel()


def setup(bot):
    bot.add_cog(Revise(bot))
