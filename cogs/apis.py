# Implements a gif search and steam profile search.
from discord.ext import commands
from json import loads
from discord import Embed
from datetime import datetime
from aiohttp import ClientSession


async def get_json_content(url):
    async with ClientSession() as session:
        async with session.get(url) as resp:
            print("Response:" + str(resp.status))
            json_string = await resp.text()
    return loads(json_string)


class API(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def steam(self, ctx, *, search):
        """Returns information about a steam profile, given the id or vanity id.

        steam [id] --> returns publicly available steam account info.
        """

        base_url = "http://api.steampowered.com/ISteamUser/"
        url = f"{base_url}GetPlayerSummaries/v0002/?key={self.bot.steam_api_key}&steamids={search}"
        response = (await get_json_content(url))['response']

        if not response['players']:
            # Try searching for VanityURL
            url = f"{base_url}ResolveVanityURL/v0001/?key={self.bot.steam_api_key}&vanityurl={search}"
            response = (await get_json_content(url))['response']

            if response['success'] != 1:
                em = Embed(title="Not Found 😕", description="Your ID search doesn't link to any profile.")
                await ctx.channel.send(embed=em)
                return

            search = response['steamid']
            url = f"{base_url}GetPlayerSummaries/v0002/?key={self.bot.steam_api_key}&steamids={search}"
            response = (await get_json_content(url))['response']

        player_content = response['players'][0]

        em = Embed(colour=0x8B008B, title="Profile | " + search, url=player_content['profileurl'],
                   description="More stats at [Steam DB](https://steamdb.info/calculator/{})".format(search))
        em.add_field(name="📝 Username", value=player_content['personaname'])

        if player_content['communityvisibilitystate'] == 1:  # If profile hidden
            em.add_field(name="👀 Profile Visibility", value="Private/Friends Only")
        else:
            em.add_field(name="👀 Profile Visibility", value="Public")
            created = datetime.utcfromtimestamp(player_content['timecreated']).strftime("%H:%M %d/%m/%Y")
            em.add_field(name="⏳ Time Created", value=created)

        poss_status = ["Offline", "Online", "Busy", "Away", "Snooze", "Looking to Trade", "Looking to Play"]
        em.add_field(name="🎮 Current Status", value=poss_status[player_content['personastate']])

        em.set_thumbnail(url=player_content['avatarfull'])
        em.set_author(name="Steam Profile Search", icon_url=ctx.message.author.avatar_url)
        em.set_footer(text="More information is available for Public profiles. | All times in UTC".format(search))

        games_url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
        url = f"{games_url}?key={self.bot.steam_api_key}&steamid={search}&include_appinfo=1"
        game_content = await get_json_content(url)

        game_list = []
        if game_content['response']:
            games_owned = game_content['response']['game_count']

            em.add_field(name="🛒 Games Owned", value=games_owned)

            # Fetch the names and app ids of the Top 6 most played games.
            games = game_content['response']['games']
            unplayed = 0
            for game in games:
                game_list.append([game['playtime_forever'], game['name'], game['appid']])
                if game['playtime_forever'] == 0:
                    unplayed += 1
            if unplayed == games_owned:
                em.add_field(name="🕸️ Unplayed", value="???")
                em.add_field(name="🕖 Most Played", value="Your playtime is private :/")
            else:
                em.add_field(name="🕸️ Unplayed", value="{} ({:.2%})".format(unplayed, unplayed / games_owned))
                # 6n < n log n, so maybe just search through the list linearly
                sorted_games = sorted(game_list)
                if len(sorted_games) > 6:
                    top5 = sorted_games[-6:]
                else:
                    top5 = sorted_games
                top5.reverse()
                print(top5)

                value = ""
                for item in top5:
                    hours = int(round(int(item[0]) / 60))
                    value += f"[{item[1]}](https://store.steampowered.com/app/{item[2]}) | {hours} Hours\n"
                em.add_field(name="🕖 Most Played", value=value)

        await ctx.channel.send(embed=em)

    @commands.command()
    async def wiki(self, ctx, *, search):
        # TODO: Get Wikipedia page associated
        pass

    @commands.command()
    async def reddit(self, ctx, *, search):
        # TODO: Get Reddit Profile/Subreddit Associated
        pass


def setup(bot):
    bot.add_cog(API(bot))
