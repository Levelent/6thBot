from discord.ext import commands, tasks
from discord import Member, Embed, Role, Colour, Guild
from json import load, dumps
from asyncio import TimeoutError
from typing import Optional


def to_role_name(colour: int):
    return f"Boost | #{hex(colour)[2:].zfill(6)}"


def default_colours():
    return {"white": 0xffffff, "red": 0xff0000, "orange": 0xff8b00, "yellow": 0xffd700, "green": 0x00ff00,
            "blue": 0x0000ff, "purple": 0x9932cc, "pink": 0xff69b4, "black": 0x000000}


def get_colour(colour_string: str):
    colour_string = colour_string.lower()
    colour_int = None

    # Test for common colours (Red, Orange, Blue, Purple etc)
    try:
        colour_int = default_colours()[colour_string]
        return colour_int
    except KeyError:
        pass

    # Test for Hex Code
    if len(colour_string) > 6:
        return None

    try:
        colour_int = int(colour_string, 16)
    except Exception as e:
        print(e)

    # Fun fact - 0x000000 actually counts as no colour at all, which is weird
    if colour_int == 0:
        colour_int = 1

    return colour_int


def colour_to_rgb(colour_int: int):
    col_b = colour_int & 255  # Takes the last 8 bits
    col_g = (colour_int >> 8) & 255  # Takes the middle 8 bits
    col_r = (colour_int >> 16) & 255  # Takes the first 8 bits
    return col_r, col_g, col_b


def colour_to_object(colour_int: int):
    col_r, col_g, col_b = colour_to_rgb(colour_int)
    return Colour.from_rgb(col_r, col_g, col_b)


class BoostColour:
    def __init__(self, role: Role, from_member: Member, to_member: Member):
        self.role = role
        self.to_member = to_member
        self.from_member = from_member
        # Potential guild attribute


def get_target_member(ctx, user_string: str):
    if len(ctx.message.mentions) != 0:  # If member mentioned
        return ctx.message.mentions[0]

    print(user_string)
    target_member = ctx.guild.get_member_named(user_string)  # By name or name + discriminator
    if target_member is not None:
        return target_member
    try:
        target_member = ctx.guild.get_member(int(user_string))
    except ValueError as e:
        print(e)
    return target_member


class CustomColours(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.notify_channel_id = None
        self.banned_colours = [(231, 76, 60), (250, 128, 114), (101, 143, 209)]  # In RGB tuple format
        self.colour_store = []

        self.save_colour_store.start()
        self.cleanup_roles.start()

    async def fetch_colour_store(self):
        with open("json/storage.json", "r") as file:
            if file.read() == "":
                return []
            file.seek(0)
            colour_store_json = load(file)
        colour_store = []
        # If switching to multi-server, put inside the for loop and edit.
        for server_str in self.bot.guild_settings:
            guild = self.bot.get_guild(int(server_str))
            for colour_dict in colour_store_json:
                from_member = guild.get_member(colour_dict['from_id'])
                if colour_dict['from_id'] == colour_dict['to_id']:
                    to_member = from_member
                else:
                    to_member = guild.get_member(colour_dict['to_id'])
                role_obj = guild.get_role(colour_dict['role_id'])
                colour_store.append(BoostColour(role_obj, from_member, to_member))
        return colour_store

    @tasks.loop(minutes=15)
    async def cleanup_roles(self):
        print("Cleaning up roles...")
        for server_str in self.bot.guild_settings:
            guild = self.bot.get_guild(int(server_str))
            for role in guild.roles:
                if len(role.members) == 0 and "Boost " in role.name:
                    print(f"Deleting Role: {role.name}")
                    await role.delete()
        print("Finished")
        
    @cleanup_roles.before_loop
    async def before_cleanup(self):
        # Wait for server data to load in
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=10)
    async def save_colour_store(self):
        print("Saving Custom Colours to file...")
        colour_store_json = []
        for colour_obj in self.colour_store:
            colour_store_json.append({'role_id': colour_obj.role.id,
                                      'from_id': colour_obj.from_member.id,
                                      'to_id': colour_obj.to_member.id})
        print(colour_store_json)
        with open("json/storage.json", "w") as file:
            file.write(dumps(colour_store_json))

    @save_colour_store.before_loop
    async def before_save(self):
        await self.bot.wait_until_ready()
        self.colour_store = await self.fetch_colour_store()
        print(self.colour_store)

    def is_colour_valid(self, colour_int: int):
        threshold = 1000  # Distance of just over 30
        col_r, col_g, col_b = colour_to_rgb(colour_int)

        for test_col in self.banned_colours:
            dist_r = abs(col_r - test_col[0])
            dist_g = abs(col_g - test_col[1])
            dist_b = abs(col_b - test_col[2])
            dist_squared = (dist_r ** 2) + (dist_g ** 2) + (dist_b ** 2)
            if dist_squared < threshold:
                return False
        return True

    def get_colour_role(self, guild: Guild):
        """
        Fetches the colour role for the specified server, if the setting exists
        :param guild: a discord.Guild object
        :return: either a discord.Role object, or None
        """
        guild_settings = self.bot.guild_settings[str(guild.id)]
        colour_role_id = guild_settings.get("colour_role_id", None)
        if colour_role_id is None:
            return None
        return guild.get_role(colour_role_id)

    def get_max_colours(self, guild: Guild) -> int:
        """
        Fetches the maximum number of colours that can be given by a member (Defaults to 2)
        :param guild: a discord.Guild object
        :return: a positive integer
        """
        guild_settings = self.bot.guild_settings[str(guild.id)]
        return guild_settings.get("max_colours", 2)

    @commands.Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        before_roles = set(before.roles)
        after_roles = set(after.roles)

        # Get the colour role for the server, if it exists.
        max_colours = self.get_max_colours(before.guild)
        colour_role = self.get_colour_role(before.guild)
        if colour_role is None:
            return
        elif colour_role in (after_roles - before_roles):  # Colour enabling role added
            print(f"+ {after} can now use custom colours.")
            await after.send(
                "Just to let you know, you now have access to **custom colours**!\n"
                "You can use either a colour name, or hex code. For example:\n"
                "`6.setcol orange` gives you an orange role colour.\n"
                "`6.setcol #ff00ff` gives you a colour with the hex code #ff00ff.\n"
                "`6.setcol yellow Bob#0001` gives Bob#0001 a yellow role colour, if they accept.\n"
                f"You can give out a maximum of {max_colours} colours.\n"
            )
        elif colour_role in (before_roles - after_roles):  # Colour enabling role removed
            print(f"- {after} can no longer use custom colours.")
            # Finds the colours they gave out, and removes them.
            removed_roles = set()
            for colour_obj in self.colour_store:
                if colour_obj.from_member == after:
                    removed_roles.add(colour_obj.role)
                    await colour_obj.to_member.remove_roles(colour_obj.role)
                    self.colour_store.remove(colour_obj)

            # When done, check the colours and delete every role with no users.
            for role in removed_roles:
                if len(role.members) == 0:
                    print("Removed completely")
                    await role.delete()

    async def request_custom_colour(self, ctx, colour, member_obj):
        if member_obj is None:
            await ctx.send("Sorry, I don't recognise that person... Try typing in their full username, or user ID.")
            return False
        if ctx.author == member_obj:
            return True
        em = Embed(title="You've been gifted a custom role colour!", colour=colour_to_object(colour),
                   description=f"Would you like to accept? Your name will have a new colour in chat.")
        em.set_footer(text="This request will time out after 30 seconds.")
        em.add_field(name="Hex Code", value=f"#{hex(colour)[2:].zfill(6)}")
        em.add_field(name="From", value=ctx.author.mention)
        em.add_field(name="To", value=member_obj.mention)
        msg = await ctx.send(member_obj.mention, embed=em)
        await msg.add_reaction('👍')
        await msg.add_reaction('👎')

        def check(msg_react, msg_user):
            return msg_user == member_obj and msg_react.message.id == msg.id and msg_react.emoji in ['👍', '👎']

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30, check=check)
        except TimeoutError:
            await msg.clear_reactions()
            em = Embed(title="You've been gifted a custom role colour!",
                       description="...but the request timed out, you didn't respond in time :/")
            await msg.edit(embed=em)
            return False

        description = f"The role colour sent by {ctx.author.mention} was "
        if str(reaction.emoji) == '👍':
            last_word = "accepted. 🎉"
            return_val = True
        else:
            last_word = "denied. 😢"
            return_val = False
        em = Embed(description=description + last_word, colour=colour_to_object(colour))
        await msg.edit(embed=em)
        await msg.clear_reactions()
        return return_val

    @commands.command()
    async def setcol(self, ctx, target_colour: str = None, target_member: str = None):
        colour_role: Role = self.get_colour_role(ctx.guild)
        print(colour_role)
        if colour_role is None:
            await ctx.send("Sorry, this server doesn't have a colour role set up...")
            return
        if target_colour is None:
            await ctx.send("This command should be in the format `setcol <target_colour> [target_member]`.\n"
                           "The second parameter can be left blank, and you'll give yourself the custom colour.\n"
                           "Looking to remove a role instead? Try `removecol [target_member]`.")
            return  # Later we'd want to replace with typing the specific help command of this
        colour = get_colour(target_colour.strip("#"))
        if colour is None:
            await ctx.send("Sorry, I can't recognise your colour... Try typing a **Hex Code** or **Colour Name**.")
            return
        if ctx.author not in colour_role.members:
            await ctx.send("Sorry, you need to be boosting the server to use this feature!")
            return
        if not self.is_colour_valid(colour):
            await ctx.send("That colour's too similar to the staff or bots... try picking another one!")
            return
        print("Test 1")
        if target_member is None:
            member_obj = ctx.author
        else:
            member_obj = get_target_member(ctx, target_member)
            if member_obj is None:
                await ctx.send("Sorry, I don't recognise that person... Try typing in their full username, or user ID.")
                return
            elif not await self.request_custom_colour(ctx, colour, member_obj):
                return  # Here the request either timed out or was denied
        print("Test")
        # You can give out self.max_colours_per_user many colours
        # Denies the request if from_user has more than that many things
        # TODO not 100% sure that this works correctly with the max_colours.
        count = 0
        max_colours = self.get_max_colours(ctx.guild)
        old_colour_obj = None
        for colour_obj in self.colour_store:
            print(f"From: Searching for {ctx.author}, found {colour_obj.from_member}")
            print(f"To: Searching for {member_obj}, found {colour_obj.to_member}")
            if colour_obj.to_member == member_obj:  # If old colour exists
                old_colour_obj = colour_obj
                if colour_obj.from_member == ctx.author:  # If link is existing
                    break
            if colour_obj.from_member == ctx.author:
                print("Count incremented")
                count += 1
                if count >= max_colours:
                    await ctx.send(f"You can only give custom colours to {max_colours} users, including yourself.\n"
                                   "Use the `removecol` command to remove the ones you've already added.")
                    return
        print(count)
        # Remove the old colour, if one exists
        if old_colour_obj is not None:
            await old_colour_obj.to_member.remove_roles(old_colour_obj.role)
            self.colour_store.remove(old_colour_obj)

        role_name = to_role_name(colour)
        for colour_obj in self.colour_store:
            if colour_obj.role.name == role_name:  # If the role colour already exists
                role = colour_obj.role
                break
        else:
            role = await ctx.guild.create_role(name=to_role_name(colour), colour=colour_to_object(colour))
            # Moves the new role directly above the colour role.
            await role.edit(position=colour_role.position + 1)

        self.colour_store.append(BoostColour(role, ctx.author, member_obj))
        await member_obj.add_roles(role)

        em = Embed(title="Success!", description=f"I've added {member_obj.mention} to the {role.mention} role.")
        await ctx.send(embed=em)

    @commands.command()
    async def removecol(self, ctx, target: Member = None):
        if target is None:
            for colour_obj in self.colour_store:
                if ctx.author == colour_obj.to_member:
                    await ctx.author.remove_roles(colour_obj.role)
                    self.colour_store.remove(colour_obj)
                    await ctx.send("Your role colour has been removed.")
                    break
            else:
                await ctx.send("You don't have a role colour, so there was nothing to remove.")
            return

        for colour_obj in self.colour_store:
            if target == colour_obj.to_member and ctx.author == colour_obj.from_member:
                await colour_obj.to_member.remove_roles(colour_obj.role)
                self.colour_store.remove(colour_obj)
                await ctx.send("Role colour removed successfully.")
                break
        else:
            await ctx.send("This user doesn't have any of your role colours.")

    @commands.command()
    async def cols(self, ctx, target: Member = None):
        if target is None:
            target = ctx.author
        print(target)
        # Builds string of all custom colours given and received
        colour_desc = ""
        for colour_obj in self.colour_store:
            if ctx.author in colour_obj.from_member and colour_obj.role is not None:
                colour_desc += f"{colour_obj.role.mention} given to {colour_obj.to_member.mention}\n"
        for colour_obj in self.colour_store:
            if ctx.author in colour_obj.to_member and colour_obj.role is not None:
                colour_desc += f"\nUser has {colour_obj.role.mention} given by {colour_obj.from_member.mention}"
                break
        if colour_desc == "":
            colour_desc = "No custom colours found."

        em = Embed(title=f"{str(target)}'s custom colours", description=colour_desc)
        em.set_thumbnail(url=str(target.avatar_url))
        em.set_author(name=f"Requested by {str(ctx.author)}", icon_url=str(ctx.author.avatar_url))
        em.set_footer(text="Try `removecol [member]` to remove a specific custom colour.")
        await ctx.send(embed=em)

    @commands.command()
    @commands.has_guild_permissions(manage_roles=True)
    async def maxcols(self, ctx, num: int):
        if num <= 0:
            await ctx.send("Try to set the limit to a positive integer.")
            return
        self.bot.guild_settings[str(ctx.guild.id)]["max_colours"] = num
        await ctx.send(f"Max colours set to {num}")




def setup(bot):
    bot.add_cog(CustomColours(bot))
