from discord.ext import commands
from json import loads
from discord import Embed
from datetime import datetime
from aiohttp import ClientSession


class API(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = None

    async def cog_before_invoke(self, ctx):
        self.session = ClientSession()
        # Check if module enabled

    async def cog_after_invoke(self, ctx):
        await self.session.close()

    async def get_json_content(self, url):
        async with self.session.get(url) as resp:
            print("Response:" + str(resp.status))
            json_string = await resp.text()
        return loads(json_string)

    @commands.command()
    async def gif(self, ctx, *, search=None):
        """Posts a random gif from the tags you enter.

        gif --> completely random gif.
        gif <tags<>> --> narrows down the search to specific things.
        """

        url = "http://api.giphy.com/v1/gifs/random?api_key={0}&tag={1}".format(self.bot.giphy_api_key, search or "")
        content = await self.get_json_content(url)

        if not content['data']:
            em = Embed(title="Not Found 😕", description="We couldn't find a gif that matched the tags you entered.")
        else:
            if search is not None:
                search = search.replace(" ", ", ")

            em = Embed(color=0x8B008B, title="🔎 Tags: {0}".format(search or "🎲"),
                       description="[Original]({0})".format(content['data']['image_url']))
            em.set_image(url=content['data']['image_url'])
            em.set_footer(text="Dimensions: {0}x{1} | Frames: {2} | Size: {3}kb"
                          .format(content['data']['image_width'],
                                  content['data']['image_height'],
                                  content['data']['image_frames'],
                                  int(content['data']['images']['original']['mp4_size']) // 1024))
        em.set_author(name="Gif Search", icon_url=ctx.message.author.avatar_url)

        await ctx.channel.send(embed=em)

    @commands.command(pass_context=True)
    async def steam(self, ctx, *, steam_id):
        """Returns information about a steam profile, given the id or vanity id.

        steam [id] --> returns publicly available steam account info.
        """

        url_part = "http://api.steampowered.com/ISteamUser/"
        url = "{0}GetPlayerSummaries/v0002/?key={1}&steamids={2}".format(url_part, self.bot.steam_api_key, steam_id)
        content = await self.get_json_content(url)

        if not content['response']['players']:
            # Try searching for VanityURL
            url = "{0}ResolveVanityURL/v0001/?key={1}&vanityurl={2}".format(url_part, self.bot.steam_api_key, steam_id)
            content = await self.get_json_content(url)

            if content['response']['success'] != 1:
                em = Embed(title="Not Found 😕", description="Your ID search doesn't link to any profile.")
                await ctx.channel.send(embed=em)
                return

            steam_id = content['response']['steamid']
            url = "{0}GetPlayerSummaries/v0002/?key={1}&steamids={2}".format(url_part, self.bot.steam_api_key, steam_id)
            content = await self.get_json_content(url)

        player_content = content['response']['players'][0]

        em = Embed(colour=0x8B008B, title="Profile | " + steam_id, url=player_content['profileurl'],
                   description="More stats at [Steam DB](https://steamdb.info/calculator/{})".format(steam_id))
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
        em.set_footer(text="More information is available for Public profiles. | All times in UTC".format(steam_id))

        url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={}&steamid={}&include_appinfo=1".format(self.bot.steam_api_key, steam_id)
        game_content = await self.get_json_content(url)

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
                    value += "[{0}](https://store.steampowered.com/app/{1}) | {2} Hours\n".format(item[1], item[2], hours)
                em.add_field(name="🕖 Most Played", value=value)

        await ctx.channel.send(embed=em)


def setup(bot):
    bot.add_cog(API(bot))
