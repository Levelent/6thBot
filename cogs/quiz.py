# Uses the OpenTDB API to fetch questions for a multi-round server quiz.
from discord.ext import commands
from discord import Embed
from asyncio import sleep
from random import shuffle
from json import loads
from html import unescape
from aiohttp import ClientSession


class Quiz(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.active_quiz = None

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
    @commands.max_concurrency(1, per=commands.BucketType.guild)
    async def quiz(self, ctx, rounds: int = 5):
        if rounds > 50:
            await ctx.channel.send("The maximum number of questions in one quiz is 50.")  # Technically 150 is the limit
            return

        # Tries to fetch equal number of questions for each difficulty. Remainder precedence Medium, Hard, Easy
        questions = []
        for diff in ["easy", "medium", "hard"]:
            diff_amount = rounds // 3
            if diff == "medium" and rounds % 3 != 0:  # remainder 1 or 2
                diff_amount += 1
            if diff == "hard" and rounds % 3 == 2:  # remainder 2
                diff_amount += 1
            url = f"https://opentdb.com/api.php?amount={diff_amount}&type=multiple&difficulty={diff}"
            data = await self.get_json_content(url)
            for question in data['results']:
                questions.append(question)
        print(questions)
        # Note that there's a disproportionately large number of questions in the 'Entertainment: Video Games' category

        players = {}
        em = Embed(
            title="A Quiz will start in 15 seconds.",
            description=(
                "- A series of multiple choice questions will be displayed here.\n"
                "- Add one of the **A, B, C or D** reactions to answer within the time limit.\n"
                "- Correct answers get **+1000** points, but incorrect ones get **-250**.\n"
                "Good Luck!"
            )
        )
        em.set_footer(text=f"This Quiz will have {rounds} questions | Sourced from the OpenTDB API")
        q_message = await ctx.channel.send(embed=em)
        self.active_quiz = q_message.jump_url

        ordered_players = []
        await sleep(5)
        for question_no in range(rounds):
            q_data = questions[question_no]

            em = Embed(colour=0x8B008B, title=unescape(q_data['question']))
            em.set_footer(text=f"Question {question_no + 1} of {rounds} | {15} seconds per question")
            em.set_author(name=f"{q_data['difficulty'].title()} | {q_data['category']}",
                          icon_url=ctx.me.avatar_url)

            options = q_data['incorrect_answers']
            options.append(q_data['correct_answer'])
            shuffle(options)

            letter_blocks = ["\U0001F1E6", "\U0001F1E7", "\U0001F1E8", "\U0001F1E9"]
            corr_index = 0
            for i in range(len(options)):
                em.add_field(name=letter_blocks[i], value=unescape(options[i]), inline=False)
                if options[i] == q_data['correct_answer']:
                    corr_index = i
                await q_message.add_reaction(letter_blocks[i])
            for i in range(3):
                await q_message.edit(content=f":alarm_clock: You have {15 - (i * 5)} Seconds to answer this question", embed=em)
                await sleep(5)
            await q_message.edit(content="\n:alarm_clock: Time's up!")

            corr_users = set()
            incorr_users = set()
            # Get message by id again, as reaction data is not updated
            q_message = await ctx.channel.fetch_message(q_message.id)

            for i in range(len(q_message.reactions)):
                reaction = q_message.reactions[i]
                if reaction.emoji in letter_blocks:
                    if i == corr_index:
                        corr_users = set(await reaction.users().flatten()) - {ctx.me}
                    else:
                        async for elem in reaction.users():
                            if elem != ctx.me:
                                incorr_users.add(elem)

            await q_message.clear_reactions()

            for user in (corr_users | incorr_users):
                if user.id not in players:
                    players[user.id] = {"score": 0, "correct": 0, "incorrect": 0}

            corr_results = ""
            for user in (corr_users - incorr_users):
                corr_results += (user.mention + " ")
                players[user.id]["score"] += 1000
                players[user.id]["correct"] += 1

            if corr_results != "":
                corr_text = corr_results + "| Correct!"
            else:
                corr_text = "Looks like no-one got it right this round!"

            incorr_results = ""
            for user in incorr_users:
                incorr_results += (user.mention + " ")
                players[user.id]["score"] -= 250
                players[user.id]["incorrect"] += 1

            if incorr_results != "":
                incorr_text = incorr_results + "| Incorrect..."
            else:
                incorr_text = "No Incorrect Answers."

            # TODO: Remove the need for this, if possible
            # Turns each {'id': {'item1': 0, 'item2': 0},} into [('id',{'item1': 0, 'item2': 0}),]
            ordered_players = sorted(players.items(), key=lambda k: k[1]["score"], reverse=True)
            value = ""
            for num in range(len(ordered_players)):
                player = ordered_players[num]
                user = await self.bot.fetch_user(player[0])
                value += f"#{num + 1} | {user.mention} | {player[1]['score']}\n"
            em = Embed(
                title=f"Answer | **{letter_blocks[corr_index]} {unescape(q_data['correct_answer'])}**",
                description=f"{corr_text}\n{incorr_text}"
            )
            em.add_field(name="Current Standings:", value=value)
            em.set_footer(text=f"{rounds - question_no - 1} questions remain | Advancing in 5 seconds")
            await q_message.edit(embed=em)
            await sleep(5)

        value = ""
        for num in range(len(ordered_players)):
            player = ordered_players[num]
            user = await self.bot.fetch_user(player[0])
            value += f"#{num+1} | {user.mention} | {player[1]['correct']}/{player[1]['incorrect']} | {player[1]['score']}\n"
        em = Embed(title="Final Scores", colour=0x8B008B, description=value)
        em.set_footer(text=f"Lasted {rounds} rounds.")
        em.set_author(name="Quiz Complete | Type `6th.quiz` for another one!", icon_url=ctx.me.avatar_url)
        await q_message.edit(embed=em)

    @quiz.error
    async def quiz_error(self, ctx, error):
        print(error)
        if isinstance(error, commands.MaxConcurrencyReached):
            await ctx.send(f"Only one quiz can be active at once. "
                           f"You can find the current game here:\n{self.active_quiz}")
        elif isinstance(error, commands.UserInputError):
            await ctx.send("Make sure to specify a *positive number* of rounds.")


def setup(bot):
    bot.add_cog(Quiz(bot))
