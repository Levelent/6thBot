# The main module. This adds all the other files as cogs, so this should be the code entry point.
from discord.ext import commands, tasks
from discord import Game, Message, Guild, TextChannel
from datetime import datetime
from json import load, dump
import asyncio


def load_json(filename):
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
        self.save_guild_settings.start()

    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))
        print("Checking for server changes while offline...")
        guild_ids: set = {str(guild.id) for guild in self.guilds}
        guild_ids_contained: set = {key for key in self.guild_settings}
        for added_guild in guild_ids - guild_ids_contained:
            await self.on_guild_join(added_guild)
            print(f"+ Added {added_guild.name}")
        for removed_guild in guild_ids_contained - guild_ids:
            await self.on_guild_remove(removed_guild)
            print(f"- Removed {removed_guild.name}")
        print("...Done")

    async def on_message(self, msg: Message):
        if msg.author.bot:
            return
        if not isinstance(msg.channel, TextChannel):
            await msg.channel.send("Sorry, commands don't work in DMs. Try talking to me on a server instead!")
            return
        if msg.guild.me.name.lower() in msg.content.lower() or msg.guild.me in msg.mentions:
            await msg.add_reaction("👋")  # Adds the wave reaction
        await bot.process_commands(msg)

    # Add empty settings dictionary on join
    async def on_guild_join(self, guild: Guild):
        self.guild_settings[str(guild.id)]: dict = {}

    # Remove settings dictionary on leave
    async def on_guild_remove(self, guild: Guild):
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
        if isinstance(err, commands.CommandNotFound):
            await ctx.message.add_reaction("❓")


# Initialise the bot client
bot = Core(
    description="A Bot Designed for the r/6thForm Discord.",
    activity=Game("with you!"),  # "playing" is prefixed at the start of the status
    command_prefix="6."

)
bot.remove_command('help')

# Load Extensions
extensions = ["apis", "quiz", "ccolour", "collage", "fun", "filter", "inspect"]
for ext_name in extensions:
    print(f"Loading {ext_name}")
    bot.load_extension(f"cogs.{ext_name}")
# Other extensions: revise, starboard, wiki, autorole, archive

# The bot token should be put in api_keys.json
bot.run(bot.discord_api_key)

# Implement shadow-banning (if a user with a certain ID joins, they will immediately be banned)?
