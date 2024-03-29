# Uses the OpenTDB API to fetch questions for a multi-round server quiz.
from discord.ext import commands
from discord import Embed, Reaction, Message
from asyncio import sleep
from random import shuffle
from json import loads
from html import unescape
from aiohttp import ClientSession


async def get_json_content(url):
    async with ClientSession() as session:
        async with session.get(url) as resp:
            print("Response:" + str(resp.status))
            json_string = await resp.text()
    return loads(json_string)


async def get_questions(difficulty, amount):
    # Note: Disproportionately large number of questions in the 'Entertainment: Video Games' category
    url = f"https://opentdb.com/api.php?amount={amount}&type=multiple&difficulty={difficulty}"
    data = await get_json_content(url)
    return [quest for quest in data['results']]


class ScoreData:
    def __init__(self):
        self.answered = 0
        self.correct = 0
        self.score = 0
        self.curr_streak = 0
        self.max_streak = 0
        self.streak_reset = False

    def add_correct(self):
        if self.streak_reset:
            self.streak_reset = False
        self.answered += 1
        self.correct += 1
        self.score += 1000 + (self.curr_streak * 50)
        self.curr_streak += 1
        if self.curr_streak > self.max_streak:
            self.max_streak = self.curr_streak

    def add_incorrect(self):
        # streak no longer 'extinguished' if two incorrect in a row.
        if self.streak_reset:
            self.streak_reset = False
        self.answered += 1
        self.score -= 250
        # streak 'extinguished' on an incorrect answer
        if self.curr_streak > 1:
            self.streak_reset = True
        self.curr_streak = 0


class QuizData:
    def __init__(self, message: Message, allowed_emotes: list):
        self.message = message
        self.allowed_emotes = allowed_emotes
        self.current_answers = {}  # {35: "\U0001F1E6", 58: "\U0001F1E8", ...}
        self.player_data = {}

    def _add_user(self, user_id):
        self.player_data[user_id] = ScoreData()
        return self.player_data[user_id]

    def set_answer(self, user_id, emote):
        if emote in self.allowed_emotes:
            self.current_answers[user_id] = emote

    def update_scores(self, correct_emote):
        correct_users = []
        incorrect_users = []

        for user_id, emote in list(self.current_answers.items()):  # The list cast returns a copy, so it can't update.
            if emote == correct_emote:
                self.add_correct(user_id)
                correct_users.append(user_id)
            else:
                self.add_incorrect(user_id)
                incorrect_users.append(user_id)

        self.current_answers = {}  # Reset the chosen answers
        return correct_users, incorrect_users

    def add_correct(self, user_id):
        player_data: ScoreData = self.player_data.get(user_id, None)
        if player_data is None:
            player_data = self._add_user(user_id)
        player_data.add_correct()

    def add_incorrect(self, user_id):
        player_data: ScoreData = self.player_data.get(user_id, None)
        if player_data is None:
            player_data = self._add_user(user_id)
        player_data.add_incorrect()

    def top_scores(self, max_num=None):
        data_by_score = sorted(self.player_data.items(), key=lambda t: t[1].score, reverse=True)
        if max_num is None:
            return data_by_score
        num = min(max_num, len(data_by_score))
        return data_by_score[:num]


class Quiz(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.option_emojis = ["🇦", "🇧", "🇨", "🇩"]  # Note: These are regional indicator emojis
        self.active_quiz_data = {}  # {[svr_id]: QuizData}

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: Reaction, user):
        if user.bot:
            return
        guild_quiz_data: QuizData = self.active_quiz_data.get(reaction.message.guild.id, None)

        # Checks if a quiz is running, and that this is the correct message
        if guild_quiz_data is None:
            return
        elif guild_quiz_data.message.id != reaction.message.id:
            return

        guild_quiz_data.set_answer(user.id, reaction.emoji)  # change emote
        await reaction.remove(user)

    async def setup_quiz(self, ctx, rounds: int) -> QuizData:
        em = Embed(
            title="A Quiz will start in 10 seconds.",
            description=(
                "A series of multiple choice questions will be displayed here.\n"
                "Add one of the **A, B, C or D** reactions to answer within the time limit.\n\n"
                "🔹 Correct answers gain **1000** points\n"
                "🔸 Incorrect ones lose **250** points\n"
                "🔥 Get an answer **streak** for bonus points\n\n"
                "Good Luck!"
            )
        )
        em.set_footer(text=f"This Quiz will have {rounds} questions | Sourced from the OpenTDB API")
        quiz_msg: Message = await ctx.channel.send(embed=em)

        quiz_data = QuizData(quiz_msg, self.option_emojis)
        self.active_quiz_data[ctx.guild.id] = quiz_data
        return quiz_data

    async def serve_question(self, ctx, question, question_no, rounds):
        quiz_msg = self.active_quiz_data[ctx.guild.id].message
        em = Embed(
            colour=0xFA8072, title=unescape(question['question'])
        )
        em.set_footer(text=f"Question {question_no + 1} of {rounds} | {15} seconds per question")
        em.set_author(
            name=f"{question['difficulty'].title()} | {question['category']}",
            icon_url=ctx.me.avatar_url
        )

        options = question['incorrect_answers']
        options.append(question['correct_answer'])
        shuffle(options)

        # determine correct answer index after shuffle, while constructing question
        correct_idx = 0
        for i in range(len(options)):
            em.add_field(name=self.option_emojis[i], value=unescape(options[i]), inline=False)
            if options[i] == question['correct_answer']:
                correct_idx = i
            await quiz_msg.add_reaction(self.option_emojis[i])

        # 5 second decrements give rough indicator of time remaining - frequent edits would increase latency.
        for i in range(3):
            await quiz_msg.edit(
                content=f":alarm_clock: You have {15 - (i * 5)} Seconds to answer this question",
                embed=em
            )
            await sleep(5)
        await quiz_msg.edit(content="\n:alarm_clock: Time's up!")
        return correct_idx

    async def update_standings(self, ctx, correct_idx, correct_ans, question_no, rounds):
        quiz_data = self.active_quiz_data[ctx.guild.id]
        correct_ids, incorrect_ids = quiz_data.update_scores(self.option_emojis[correct_idx])

        correct_mentions = [ctx.guild.get_member(user_id).mention for user_id in correct_ids]
        incorrect_mentions = [ctx.guild.get_member(user_id).mention for user_id in incorrect_ids]

        if len(correct_mentions) == 0:
            correct_text = "Looks like no-one got it right this round!"
        else:
            correct_text = " ".join(correct_mentions) + " | Correct!"

        if len(incorrect_mentions) == 0:
            incorrect_text = "No incorrect answers."
        else:
            incorrect_text = " ".join(incorrect_mentions) + " | Incorrect..."

        # Fetches the top 10 users and their score data.
        pos = 1
        slots = []
        for user_id, score_data in quiz_data.top_scores(10):
            member = ctx.guild.get_member(user_id)
            slot = f"{member.mention} | {score_data.score} "
            if score_data.curr_streak > 1:
                slot += f" **🔥 {score_data.curr_streak}**"
            elif score_data.streak_reset:
                slot += f" **🧯 0**"
            slots.append(slot)
            pos += 1

        em = Embed(
            title=f"Answer | **{self.option_emojis[correct_idx]} {correct_ans}**",
            description=f"{correct_text}\n{incorrect_text}"
        )
        em.add_field(
            name="Current Standings:",
            value="\n".join(slots) or "No-one has answered yet :("
        )
        em.set_footer(text=f"{rounds - question_no - 1} questions remain | Advancing in 5 seconds")

        # Get message by id again, as reaction data is not updated
        quiz_msg = await ctx.channel.fetch_message(quiz_data.message.id)
        await quiz_msg.clear_reactions()
        await quiz_msg.edit(embed=em)
        await sleep(5)

    async def final_standings(self, ctx, rounds):
        quiz_data = self.active_quiz_data[ctx.guild.id]
        pos = 1
        last_pos = 1
        last_score = 0
        slots = []
        url = None
        for user_id, score_data in quiz_data.top_scores():
            member = ctx.guild.get_member(user_id)

            # First place member has their picture at the top.
            if pos == 1:
                url = str(member.avatar_url)

            if last_score == score_data.score:
                used_pos = last_pos
            else:
                used_pos = pos

            slot = f"#{used_pos} | {member.mention} | {score_data.correct}/{score_data.answered} | {score_data.score} "
            if score_data.max_streak > 1:
                slot += f"**🔥 {score_data.max_streak}** Max"
            slots.append(slot)

            last_pos = used_pos
            last_score = score_data.score
            pos += 1

        em = Embed(title="Final Scores", colour=0xFA8072, description="\n".join(slots) or "Hello? Anyone there?")
        em.set_footer(text=f"Lasted {rounds} rounds. | Play again?")
        em.set_author(name="Quiz Complete | Thanks for playing!", icon_url=ctx.me.avatar_url)
        if url is not None:
            em.set_thumbnail(url=url)

        await quiz_data.message.edit(embed=em)

    @commands.command()
    @commands.max_concurrency(1, per=commands.BucketType.guild)
    async def quiz(self, ctx, rounds: int = 5):
        if not 1 <= rounds <= 15:
            # Technically 150 is the limit, but it gets very boring.
            await ctx.channel.send("You can have between 1-15 questions per quiz.")
            return

        # Tries to fetch similar number of questions for each difficulty. Remainder precedence Medium, Hard, Easy
        questions = []
        quotient, remainder = divmod(rounds, 3)
        questions += await get_questions("easy", quotient)
        questions += await get_questions("medium", quotient + (remainder != 0))
        questions += await get_questions("hard", quotient + (remainder == 2))

        await self.setup_quiz(ctx, rounds)
        await sleep(10)

        for question_no in range(rounds):
            question = questions[question_no]
            correct_idx = await self.serve_question(ctx, question, question_no, rounds)
            await self.update_standings(ctx, correct_idx, unescape(question['correct_answer']), question_no, rounds)

        await self.final_standings(ctx, rounds)

    @quiz.error
    async def quiz_error(self, ctx, error):
        if isinstance(error, commands.MaxConcurrencyReached):
            message = self.active_quiz_data[ctx.guild.id].message
            await ctx.send(f"Only one quiz can be active at once. "
                           f"You can find the current game here:\n{message.jump_url}", delete_after=30.0)
        elif isinstance(error, commands.UserInputError):
            await ctx.send("Make sure to specify a *positive number* of rounds.")
        else:
            print(error)


def setup(bot):
    bot.add_cog(Quiz(bot))
