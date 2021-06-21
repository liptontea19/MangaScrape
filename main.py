# ---------------------------------------------------------------------------------
# This program scrapes Kireicake (a manga translation site) for new chapter updates
# main.py contains the discord bot and database interaction codes while the *Modules
# contain the respective website's scraping code
# ---------------------------------------------------------------------------------
import asyncio

import discord
from pymongo import MongoClient

import KireiCakeModule
import MangaPlusModule

cluster = MongoClient("mongodb+srv://dbAdmin:UQucdAwtZHXY5DPr@cluster0.rolmr.mongodb.net/test")

db = cluster["MangaScrapeDB"]

collection = db["UserData"]

# MangaPlusModule.chapter_search("Jujutsu Kaisen", "#152", "https://mangaplus.shueisha.co.jp/titles/100034")

helpmanual = "Here's a  list of commands that MangaScrapeBot can do!\n" \
             "$hello: displays a greeting message\n" \
             "$mangalist: displays your current list of manga stored on the database\n"

helpmanual_adding = ("Adding a manga is an easy and simple task. For example, if you would like to add the manga, "
                     "*One Piece*, from "
                     "the *MANGA Plus by SHUEISHA* website to your manga reading list, you would need 4 things: the "
                     "manga's title, name of the web source, chapter title and link to the manga.\n"
                     "Input: One Piece, MANGA Plus by SHUEISHA, #186, https://mangaplus.shueisha.co.jp/titles/100020\n"
                     "Do note that the bot's search capabilities are limited to the Kirei Cake website currently.")

client = discord.Client()


def display_mangas_in_list(mangalist, curr_index: int, size: int):  # size refers to the number of items in the list to display
    list_text = "**No.** | **Title** :arrow_down_small:| **Chapter** | **Source**\n"
    for x in range(curr_index, curr_index + size - 1):
        list_text = list_text + f"{str(x + 1)} | {mangalist[x]['title']} | {mangalist[x]['chapter_read']} | {mangalist[x]['source']}\n"
    return list_text


async def message_wait(ctx, check_con, time_window):
    try:
        msg = await client.wait_for('message', check=check_con, timeout=time_window)
        message = msg.content
    except asyncio.TimeoutError:
        message = "NaN"
        await ctx.author.send("Your request has timed out, please try again.")
    return message


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(ctx):
    print(f"{ctx.channel}: {ctx.author}: {ctx.author.name}: {ctx.content}")
    if ctx.author == client.user:
        return

    if ctx.content.startswith('$help'):
        await ctx.author.send(helpmanual)
    elif ctx.content.startswith('$h addmanga'):
        await ctx.author.send(helpmanual_adding)

    myquery = {"_id": ctx.author.id}
    if collection.count_documents(myquery) == 0:  # checks if the user has an account on the database
        if ctx.content.startswith('$hello'):
            await ctx.channel.send(f'Hello new user {ctx.author.name}! If you require assistance, just type in $help')
        elif ctx.content.startswith('$mangalist'):
            await ctx.channel.send('You currently do not have any manga on the database yet. '
                                   'You can add manga into your list using the $add command.')

    else:  # commands that only work if the user has an existing record (document) in the database
        if ctx.content.startswith('$hello'):
            await ctx.channel.send(f'Welcome back {ctx.author.name}!')
        elif "$mangalist" in str(ctx.content.lower()):
            user = collection.find(myquery)
            for result in user:
                mangalist = result["mangalist"]
                mangalist.sort(key=lambda x: x['title'])  # alphabetically sorts the mangas by title for displaying
                output_text = "**Title** :arrow_down_small:| **Website** | **Chapter**\n" + \
                              '\n'.join((manga['title'] + ' | ' + manga['source'] + ' | ' + manga['chapter_read'])
                                        for manga in mangalist)
                print(output_text)
                output = await ctx.author.send(output_text)
                await output.add_reaction("✔")
        elif "$updates" in str(ctx.content.lower()):  # do not test until AIOHTTP port is in place!!!
            user = collection.find(myquery)
            for result in user:
                mangalist = result["mangalist"]
                mangalist.sort(key=lambda x: x['title'])
                for manga in mangalist:
                    title = manga['title']
                    source = manga['source']
                    chapter_read = manga['chapter_read']
                    link = manga['link']
                    print(f"Looking up {title} on {source}")
                    if source == "Kirei Cake":
                        KireiCakeModule.chapter_search(title, chapter_read, link)
                    elif source == "MANGA Plus by SHUEISHA":
                        MangaPlusModule.chapter_search(title, chapter_read, link)
        elif ctx.content.startswith('$editlist'):
            user = collection.find(myquery)
            for result in user:
                mangalist = result["mangalist"]
                mangalist.sort(key=lambda x: x['title'])
                count = 0
                output = await ctx.author.send("Enter the index number of the manga you would like to edit in the "
                                               "list\n" + display_mangas_in_list(mangalist, count, 5))
                await output.add_reaction("⬇")

                def check(m):
                    return ctx.author == m.author

                try:
                    msg = await client.wait_for('message', check=check, timeout=30)
                except asyncio.TimeoutError:
                    await ctx.author.send("Your request has timed out, please try again.")
                else:
                    chosen_index = int(msg.content) - 1
                    question_text = "What would you like to modify?\nTitle: :regional_indicator_t:\nChapter Progress: " \
                                    ":regional_indicator_c:\nWeb Source: :regional_indicator_s:\nLink: " \
                                    ":regional_indicator_l:"
                    output = await ctx.author.send(f"You have chosen manga number **{msg.content}**.\n{question_text}")

                    await output.add_reaction("🇹")  # T emote
                    await output.add_reaction("🇨")  # C emote
                    await output.add_reaction("🇸")  # S emote
                    await output.add_reaction("🇱")  # L emote
                    print("Editing: " + mangalist[chosen_index]['title'] + " entry currently.")

                    # def emojicheck(reaction, user):
                    # return user == ctx.author and str(reaction) in ["🇹", "🇨", "🇸",
                    # "🇱"] and reaction.message == msg

                    try:
                        # reaction, user = await client.wait_for('reaction_add', check=emojicheck, timeout=30)
                        msg = await client.wait_for('message', check=check, timeout=30)
                    except asyncio.TimeoutError:
                        await ctx.author.send("Your request has timed out, please try again.")
                    else:
                        if msg.content == "T":
                            edit_field = 'title'
                        elif msg.content == "C":
                            edit_field = 'chapter_read'
                        elif msg.content == "S":
                            edit_field = 'source'
                        elif msg.content == "L":
                            edit_field = 'link'
                        await ctx.author.send('Type in the new ' + edit_field)
                        """
                        if str(reaction.emoji) == "🇹":  # the reaction implementation
                            await ctx.author.send('Type in the new title.')
                        elif str(reaction.emoji) == "🇨":
                            await ctx.author.send('Type in the new chapter number')
                        """
                        new_val = await message_wait(ctx, check, 30)
                        if new_val != "NaN":
                            mangalist[chosen_index][edit_field] = new_val
                            collection.update_one({"_id": ctx.author.id}, {"$set": {"mangalist": mangalist}})

                            await ctx.author.send("Manga List entry has been updated. Here is the new one:\n" +
                                                  f"{mangalist[chosen_index]['title']} | "
                                                  f"{mangalist[chosen_index]['chapter_read']} | "
                                                  f"{mangalist[chosen_index]['source']} | "
                                                  f"{mangalist[chosen_index]['link']}")
                        else:
                            await ctx.author.send("Something went wrong please try again.")
        elif ctx.content.startswith('$delmanga'):
            user = collection.find(myquery)
            for result in user:
                mangalist = result["mangalist"]
                mangalist.sort(key=lambda x: x['title'])
                count = 0
                output = await ctx.author.send("Enter the index number of the manga you would like to delete from the "
                                               "list\n" + display_mangas_in_list(mangalist, count, 5))
                await output.add_reaction("⬇")

                def check(m):
                    return ctx.author == m.author

                try:
                    msg = await client.wait_for('message', check=check, timeout=30)
                except asyncio.TimeoutError:
                    await ctx.author.send("Your request has timed out, please try again.")
                else:
                    index_num = int(msg.content) - 1
                    print(index_num)
                    del mangalist[index_num]
                    collection.update_one({"_id": ctx.author.id}, {"$set": {"mangalist": mangalist}})
                    await ctx.author.send(display_mangas_in_list(mangalist, 0, len(mangalist) + 1))

    if "$addmanga" in str(ctx.content.lower()):
        await ctx.author.send("Please type in the title, website source, chapter and link to the manga you "
                              "would like to add to your mangalist, separated by commas.\nFormat: <manga title>, "
                              "<source>, <chapter>, <link>\nIf you are unsure how to proceed, type `$h addmanga`.")

        def check(msg):
            return ctx.author == msg.author

        try:
            msg = await client.wait_for('message', check=check, timeout=60)
        except asyncio.TimeoutError:
            print("addmanga input timed out, command has been cancelled.")
            await ctx.author.send("Your request has timed out, please try again.")
        else:
            try:
                title, source, chapter, link = msg.content.split(", ")
            except:
                await ctx.author.send(
                    "There seems to be something wrong with the information that you added, did you miss "
                    "a comma or field of information?")
            else:
                print(f"Adding manga Title: {title}, Source: {source}, Chapter: {chapter}, Link: {link}")
                if collection.count_documents(myquery) == 0:
                    post = {"_id": ctx.author.id,
                            "mangalist": {"title": title, "source": source, "chapter_read": chapter,
                                          "link": link}}
                    collection.insert_one(post)
                else:
                    user = collection.find(myquery)
                    for result in user:
                        mangalist = result["mangalist"]
                    mangalist.append({"title": title, "source": source, "chapter_read": chapter, "link": link})
                    collection.update_one({"_id": ctx.author.id}, {"$set": {"mangalist": mangalist}})
                await ctx.author.send("Added the new manga to the list.")


async def on_reaction_add(reaction, user):
    if user == client.user:
        return

    if reaction.emoji == "✔":
        await print("Acknowledged reaction.")

    if reaction.emoji == "😘":
        await print("Reaction")


client.run("ODU1MDMwMzk5MTA4MzgyNzUx.YMsjHA.zKWpJFJ4l_ZA8lR96OZdnoFNiyY")  # discord bot credentials
