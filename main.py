# The main module. This adds all the other files as cogs, so this should be the code entry point.
import discord
from discord.ext import commands, tasks
from datetime import datetime
from json import load, dump
import asyncio
import os.path
from util.timeformatter import highest_denom

extensions = ["apis", "quiz", "ccolour", "collage", "fun", "filter", "kowalski", "manager"]


def load_json(filename):
    if not os.path.isfile(f"json/{filename}.json"):
        return {}
    with open(f"json/{filename}.json", "r", encoding="utf-8") as file:
        return load(file)


def save_json(filename, data):
    with open(f"json/{filename}.json", "w", encoding="utf-8") as file:
        dump(data, file, ensure_ascii=False)


class Core(commands.Bot):  # discord.ext.commands.Bot is a subclass of discord.Client
    def __init__(self, **options):
        super().__init__(**options)

        token_dict = load_json("api_keys")
        self.discord_api_key = token_dict["discord"]
        self.giphy_api_key = token_dict["giphy"]
        self.steam_api_key = token_dict["steam"]

        self.guild_settings: dict = load_json("guild_settings")
        self.start_time = datetime.utcnow()

    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))
        print("Checking for server changes while offline...")
        guild_ids: set = {str(guild.id) for guild in self.guilds}
        guild_ids_contained: set = {key for key in self.guild_settings}
        for added_guild in guild_ids - guild_ids_contained:
            self.guild_settings[str(added_guild)]: dict = {}
            print(f"+ Added {added_guild}")
        for removed_guild in guild_ids_contained - guild_ids:
            self.guild_settings[str(removed_guild)]: dict = {}
            print(f"- Removed {removed_guild}")
        print("...Done")

        self.save_guild_settings.start()

        print("Loading extensions...")
        total = len(extensions)
        for num, name in enumerate(extensions):
            print(f"[{num+1}/{total}] {name}")
            self.load_extension(f"cogs.{name}")

    async def on_message(self, msg: discord.Message):
        if msg.author.bot:
            return
        if not isinstance(msg.channel, discord.TextChannel):
            await msg.channel.send("Sorry, commands don't work in DMs. Try talking to me on a server instead!")
            return
        if msg.guild.me.name.lower() in msg.content.lower() or msg.guild.me in msg.mentions:
            await msg.add_reaction("👋")  # Adds the wave reaction
        await bot.process_commands(msg)

    # Add empty settings dictionary on join
    async def on_guild_join(self, guild: discord.Guild):
        self.guild_settings[str(guild.id)]: dict = {}

    # Remove settings dictionary on leave
    async def on_guild_remove(self, guild: discord.Guild):
        self.guild_settings.pop(str(guild.id))

    @tasks.loop(minutes=15)
    async def save_guild_settings(self):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, save_json, "guild_settings", self.guild_settings)
        print("Guild Settings Saved")

    @save_guild_settings.before_loop
    async def before_save(self):
        await self.wait_until_ready()

    async def on_command_error(self, ctx, err):
        print(f"Type: {type(err)} | Description: {err}")
        if isinstance(err, commands.CommandNotFound):
            await ctx.message.add_reaction("❓")
        elif isinstance(err, commands.CommandOnCooldown):
            await ctx.send(f"You'll be able to use this command again in **{highest_denom(err.retry_after)}**.",
                           delete_after=5.0)
            try:
                await ctx.message.delete(delay=5.0)
            except discord.NotFound:
                return
        elif isinstance(err, commands.MissingRequiredArgument):
            await ctx.send(f"You haven't specified the following argument: `{err.param.name}`")
        elif isinstance(err, commands.BotMissingPermissions):
            await ctx.send(f"Sorry, I don't have the permissions to do this properly - "
                           f"you need to let me `{'`,`'.join(err.missing_perms)}`")
        elif isinstance(err, commands.MissingPermissions):
            await ctx.send("Sorry, you don't have the required permissions for this command :/")
        elif isinstance(err, discord.Forbidden):
            await ctx.send("Sorry, I'm not allowed to do that properly - have you set up permissions correctly?")
        elif isinstance(err, commands.CommandInvokeError):
            print("Command Invoke Error")
            await self.on_command_error(ctx, err.original)


# Initialise the bot client
bot = Core(
    description="A Bot Designed for the r/6thForm Discord.",
    activity=discord.Game("with you!"),  # "playing" is prefixed at the start of the status
    command_prefix="6."
)
bot.remove_command('help')

# The bot token should be put in api_keys.json
bot.run(bot.discord_api_key)

# Implement shadow-banning (if a user with a certain ID joins, they will immediately be banned)?
