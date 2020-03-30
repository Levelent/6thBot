# Generates a collage of size @canvas_w@ * @canvas_h@ with @count@ as an upper bound for the number of members
from discord.ext import commands
from discord import File, errors
from PIL import Image
from random import shuffle
from io import BytesIO
from math import sqrt, ceil, floor


class Collage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(timeout=300.0)
    async def collage(self, ctx, count=None, canvas_w=1920, canvas_h=1080):
        if count is None:
            count = ctx.guild.member_count // 2
        for param in [count, canvas_w, canvas_h]:
            if not str(param).isdigit() or int(param) < 1:
                await ctx.send("Your parameters have to be positive integers.")
                return
        if int(count) > ctx.guild.member_count:
            await ctx.send("Your count parameter is greater than the number of members in the server!")
            return

        count = int(count)
        canvas_w = int(canvas_w)
        canvas_h = int(canvas_h)
        canvas = Image.new('RGBA', (canvas_w, canvas_h))
        step_size = ceil(sqrt((canvas_w * canvas_h) / count))
        img_num_w = floor(canvas_w / step_size)
        img_num_h = floor(canvas_h / step_size)
        actual_count = img_num_w * img_num_h
        actual_width = img_num_w * step_size
        actual_height = img_num_h * step_size

        await ctx.send("Generating a collage of size {}x{}, containing {} profile pictures.".format(actual_width, actual_height, actual_count))

        power_of_two = 8
        while step_size > power_of_two:
            power_of_two *= 2
        size = power_of_two

        members = ctx.guild.members
        shuffle(members)

        left = 0
        top = 0
        async with ctx.channel.typing():
            for user in members:
                if user.bot:  # We don't care about showing bots
                    continue

                # Get the image
                img_asset = user.avatar_url_as(size=size)
                if "embed" in str(img_asset):
                    continue  # Ignores ones with embed
                try:
                    img = Image.open(BytesIO(await img_asset.read()))  # Sets the image
                except errors.NotFound:
                    print("This user does not have an avatar.")
                    continue

                if step_size < size:  # If the image is too big, we want to resize it.
                    img = img.resize((step_size, step_size))

                canvas.paste(img, (left, top))  # Adds the image to the canvas
                # print("Top-left corner at ({}, {})".format(left, top))

                left += step_size
                if left + step_size > canvas_w:
                    if top == 0:
                        left_crop = left
                    left = 0
                    top += step_size
                    if top + step_size > canvas_h:
                        break  # Stop the loop early

            if top == 0:
                left_crop = left
            top_crop = top

            canvas = canvas.crop((0, 0, left_crop, top_crop))
            canvas.save("collages/{}.png".format(ctx.message.guild.id))
            await ctx.channel.send(file=File("collages/{}.png".format(ctx.message.guild.id)))


def setup(bot):
    bot.add_cog(Collage(bot))
