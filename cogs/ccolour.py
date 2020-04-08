from discord.ext import commands, tasks
from discord import Member, Embed, Role, Colour
from json import load, dumps
from asyncio import TimeoutError
from typing import Optional


def retrieve_setting(reference):
    with open("json/settings.json", "r", encoding="utf-8") as file:
        token_dict = load(file)
    return token_dict[reference]


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
        self.server_id = retrieve_setting("guild_id")  # Guild ID, need to attach to each BoostColour object in future
        self.notify_channel_id = None
        self.role_id = retrieve_setting("boost_id")  # 'Server Booster' role
        self.banned_colours = [(231, 76, 60), (250, 128, 114), (101, 143, 209)]  # In RGB tuple format
        self.max_colours_per_user = 2
        self.colour_store = []

        self.save_colour_store.start()
        self.cleanup_roles.start()

    async def fetch_colour_store(self):
        with open("json/storage.json", "r") as file:
            if file.read() == "":
                return []
            file.seek(0)
            colour_store_json = load(file)
            print(colour_store_json)
        colour_store = []
        guild = self.bot.get_guild(self.server_id)  # If switching to multi-server, put inside the for loop and edit.
        print(guild)
        for colour_dict in colour_store_json:
            from_member = guild.get_member(colour_dict['from_id'])
            if colour_dict['from_id'] == colour_dict['to_id']:
                to_member = from_member
            else:
                to_member = guild.get_member(colour_dict['to_id'])
            role_obj = guild.get_role(colour_dict['role_id'])
            print(f"From: {from_member}")
            colour_store.append(BoostColour(role_obj, from_member, to_member))
        return colour_store

    @tasks.loop(minutes=15)
    async def cleanup_roles(self):
        print("Cleaning up roles...")
        guild = self.bot.get_guild(self.server_id)
        for role in guild.roles:
            if len(role.members) == 0 and "Boost " in role.name:
                print(f"Deleting Role: {role.name}")
                await role.delete()
        print("Finished")
        
    @cleanup_roles.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()
        # Wait for Cache to load in

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

    @commands.Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        before_roles = set(before.roles)
        after_roles = set(after.roles)
        boost_role = before.guild.get_role(self.role_id)  # Doesn't matter if before/after
        if boost_role in (before_roles - after_roles):  # Boost role removed
            print("Boost Role Removed")
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

        elif boost_role in (after_roles - before_roles):  # Boost role added
            print("Role Added")
            # TODO Thank a user for boosting, and notify them about the custom colours
            # This would only apply when the boost colour is given to themselves
            pass

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
            last_word = "accepted. :tada:"
            return_val = True
        else:
            last_word = "denied. :cry:"
            return_val = False
        em = Embed(description=description + last_word, colour=colour_to_object(colour))
        await msg.edit(embed=em)
        await msg.clear_reactions()
        return return_val

    @commands.command()
    async def setcol(self, ctx, target_colour: str = None, target_member: str = None):
        if target_colour is None:
            await ctx.send("This command should be in the format `setcol <target_colour> [target_member]`.\n"
                           "The second parameter can be left blank, and you'll give yourself the custom colour.\n"
                           "Looking to remove a role instead? Try `removecol [target_member]`.")
            return  # Later we'd want to replace with typing the specific help command of this
        colour = get_colour(target_colour.strip("#"))
        if colour is None:
            await ctx.send("Sorry, I can't recognise your colour... Try typing a **Hex Code** or **Colour Name**.")
            return
        elif ctx.author not in ctx.guild.premium_subscribers:
            await ctx.send("Sorry, you need to be boosting the server to use this feature!")
            return
        elif not self.is_colour_valid(colour):
            await ctx.send("That colour's too similar to the staff or bots... try picking another one!")
            return

        if target_member is None:
            member_obj = ctx.author
        else:
            member_obj = get_target_member(ctx, target_member)
            if member_obj is None:
                await ctx.send("Sorry, I don't recognise that person... Try typing in their full username, or user ID.")
                return
            if not await self.request_custom_colour(ctx, colour, member_obj):
                return  # Here the request either timed out or was denied

        # You can give out self.max_colours_per_user many colours
        # Denies the request if from_user has more than that many things
        count = 0
        old_colour_obj = None
        for colour_obj in self.colour_store:
            print(f"From: Searching for {ctx.author}, found {colour_obj.from_member}")
            print(f"To: Searching for {member_obj}, found {colour_obj.to_member}")
            if colour_obj.to_member == member_obj:  # If old colour exists
                old_colour_obj = colour_obj
                if colour_obj.from_member == ctx.author:  # If link is existing
                    count = 0
                    break
            if colour_obj.from_member == ctx.author:
                print("Count incremented")
                count += 1
        if count > self.max_colours_per_user:
            await ctx.send(f"You can only give custom colours to {self.max_colours_per_user} users, including yourself."
                           f"\nUse the `resetcol` command to remove the ones you've already added.")
            return

        # Remove the old colour, if one exists
        if old_colour_obj is not None:
            if len(old_colour_obj.role.members) == 1:
                await old_colour_obj.role.delete()
            else:
                await old_colour_obj.to_member.remove_roles(old_colour_obj.role)
            self.colour_store.remove(old_colour_obj)

        role_name = to_role_name(colour)
        for colour_obj in self.colour_store:
            if colour_obj.role.name == role_name:  # If the role already exists
                role = colour_obj.role
                break
        else:  # If the role doesn't already exist
            role = await ctx.guild.create_role(name=to_role_name(colour), colour=colour_to_object(colour))
            # Moves the new role directly above the booster role.
            boost_role = ctx.guild.get_role(self.role_id)
            print(str(boost_role))
            await role.edit(position=boost_role.position + 1)

        self.colour_store.append(BoostColour(role, ctx.author, member_obj))
        await member_obj.add_roles(role)

        em = Embed(title="Success!", description=f"I've added {member_obj.mention} to the {role.mention} role.")
        await ctx.send(embed=em)

    @commands.command()
    async def getcol(self, ctx, target_member: str = None):
        if target_member is None:
            member_obj = ctx.author
        else:
            member_obj = get_target_member(ctx, target_member)
            if member_obj is None:
                await ctx.send("Sorry, I don't recognise that person... Try typing in their full username, or user ID.")
                return

        for obj in self.colour_store:
            if obj.to_member == member_obj:
                colour_obj = obj
                break
        else:
            await ctx.send("Sorry, that user doesn't have a custom colour.")
            return

        colour = colour_obj.role.colour
        print(str(colour))
        em = Embed(title="🔍 Custom Role Colour", colour=colour)
        em.add_field(name="From", value=colour_obj.from_member.mention)
        em.add_field(name="To", value=member_obj.mention)
        em.add_field(name="Hex Code", value=str(colour))
        await ctx.send(embed=em)
        # Requested

    @commands.command()
    async def removecol(self, ctx, target: Optional[Member] = None):
        for colour_obj in self.colour_store:
            if (ctx.author == colour_obj.to_member and target is None) or (ctx.author == colour_obj.from_member and target == colour_obj.to_member):
                await colour_obj.to_member.remove_roles(colour_obj.role)
                self.colour_store.remove(colour_obj)
        # TODO confirmation

    @commands.command()
    async def mycols(self, ctx):
        colour_desc = ""
        for colour_obj in self.colour_store:
            if ctx.author == colour_obj.from_member and colour_obj.role is not None:
                colour_desc += f"{colour_obj.role.mention} given to {colour_obj.to_member.mention}\n"
        if colour_desc == "":
            colour_desc = "You haven't added any colours yet!"
        em = Embed(title="Your custom colours", description=colour_desc)
        em.set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))
        em.set_footer(text="Type 6th.removecol [member] to remove a specific custom colour.")
        await ctx.send(embed=em)


def setup(bot):
    bot.add_cog(CustomColours(bot))
