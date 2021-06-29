# ---------------------------------------------------------------------------------
# This program scrapes Kireicake (a manga translation site) for new chapter updates
# main.py contains the discord bot and database interaction codes while the *Modules
# contain the respective website's scraping code
# ---------------------------------------------------------------------------------
import asyncio
import aiohttp
import discord
import json
from pymongo import MongoClient

import CatMangaModule
import GDModule
import KireiCakeModule
import MangaPlusModule

intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.dm_messages = True
intents.dm_reactions = True

with open('token.json') as file:
    token = json.load(file)

cluster = MongoClient(token["mongoDB"])

db = cluster["MangaScrapeDB"]

collection = db["UserData"]

helpmanual = "Here's a list of commands that MangaScrapeBot can do!\n" \
             "As MangaScrapeBot is currently under development, special features such as `$search` and `$updates` " \
             "support a few websites at the moment. Supported websites and features are listed in detail in their " \
             "respective help sections which you can access by typing `$h` before the name of the command.\n" \
             "`$addmanga`:\n" \
             "`$delmanga`:\n" \
             "`$editlist`: modify your manga list details\n" \
             "`$hello`: displays a greeting message\n" \
             "`$mangalist`: displays your current list of manga stored on the database\n" \
             "`$search [link]`: fetches the details of a manga from the link supplied and allows " \
             "you to add the manga to your list\n" \
             "`$updates`: checks websites for any chapter updates for manga currently on your list"

helpmanual_adding = ("Adding a manga is an easy and simple task. For example, if you would like to add the manga, "
                     "*One Piece*, from "
                     "the *MANGA Plus by SHUEISHA* website to your manga reading list, you would need 4 things: the "
                     "manga's title, name of the web source, chapter title and link to the manga.\n"
                     "Input: One Piece, MANGA Plus by SHUEISHA, #186, https://mangaplus.shueisha.co.jp/titles/100020\n"
                     "Do note that the bot's search capabilities are limited to the Kirei Cake website currently.")

client = discord.Client(intents=intents)


def display_mangas_in_list(mangalist, curr_index: int, size: int):
    # size refers to the number of items in the list to display
    list_text = "**No.** | **Title** :arrow_down_small:| **Chapter** | **Source**\n"
    for x in range(curr_index, curr_index + size):
        list_text = list_text + f"{str(x + 1)} | {mangalist[x]['title']} | " \
                                f"{mangalist[x]['chapter_read']} | {mangalist[x]['source']}\n"
        if x + 1 == len(mangalist):
            break
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
    elif ctx.content.startswith('$search'):
        session = aiohttp.ClientSession()
        link = ctx.content.replace("$search ", "")
        source = ""
        manga_found = False
        if "catmanga.org" in link:
            source = "Cat Manga"
            manga = await CatMangaModule.aio_manga_details(session, link)
            if manga['status'] != "Request failed" or manga['status'] != "Unable to gather information from link.":
                manga_found = True
                embed = discord.Embed(title=manga['title'], url=link, description=manga['description'])
                embed.set_thumbnail(url=manga['cover'])
                embed.set_author(name="Cat Manga")
                embed.add_field(name="Total Chapters", value=manga['chapters'], inline=False)
                embed.add_field(name="Status", value=manga['status'], inline=True)
                embed.add_field(name="Manga Author", value=manga['author'], inline=True)
                embed.set_footer(text="Would you like to add this manga to your list? (Y/N)")
                await ctx.author.send(embed=embed)
            else:
                await ctx.author.send(manga['status'])
        else:
            await ctx.author.send("This function only supports Cat Manga at the moment, "
                                  "if you would like your website to be added, message me.")
        await session.close()

        if manga_found:
            def check(msg):
                return ctx.author == msg.author

            try:
                msg = await client.wait_for('message', check=check, timeout=15)
            except asyncio.TimeoutError:
                print("$search command has timed out.")
                await ctx.author.send("Your request has timed out, please try again.")
            else:
                if msg.content == "Y":
                    await ctx.author.send("Type in the latest chapter you have read, leave blank if you're starting a new series.")
                    try:
                        chapter = await client.wait_for('message', check=check, timeout=15)
                    except asyncio.TimeoutError:
                        chapter = "Chapter 1"
                    print("Adding manga to collection.")
                    if collection.count_documents({"_id": ctx.author.id}) == 0:  # first manga being added to list
                        post = {"_id": ctx.author.id,
                                "mangalist": {{"title": manga['title'], "source": source, "chapter_read": chapter,
                                              "link": link}}}
                        collection.insert_one(post)
                    else:
                        user = collection.find({"_id": ctx.author.id})
                        for result in user:
                            mangalist = result["mangalist"]
                            mangalist.append(
                                {"title": manga['title'], "source": source, "chapter_read": chapter, "link": link})
                            collection.update_one({"_id": ctx.author.id}, {"$set": {"mangalist": mangalist}})
                    await ctx.author.send(f"Added {manga['title']} to the list. Currently at " + chapter)

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
            curr_count = 0
            for result in user:
                mangalist = result["mangalist"]
                mangalist.sort(key=lambda x: x['title'])  # alphabetically sorts the mangas by title for displaying
                output_text = display_mangas_in_list(mangalist, curr_count, 10)
                print(output_text)
                output = await ctx.author.send(output_text)
                if len(mangalist) >= 10:
                    await output.add_reaction("\U000027A1")  # rightward pointing arrow

                def check(reaction, user):
                    return user == ctx.author and str(reaction.emoji) in ["\U00002B05", "\U000027A1"]

                while True:
                    try:
                        reaction, user = await client.wait_for("reaction_add", check=check, timeout=15.0)
                    except asyncio.TimeoutError:
                        print("Mangalist command listener ends here.")
                        break
                    else:
                        if str(reaction.emoji) == "\U00002B05":
                            await output.delete()
                            curr_count = curr_count - 10
                            output = await ctx.author.send(display_mangas_in_list(mangalist, curr_count, 10))
                            if curr_count >= 10:
                                await output.add_reaction("\U00002B05")  # leftward pointing arrow
                            if (len(mangalist) - curr_count) >= 10:
                                await output.add_reaction("\U000027A1")  # rightward pointing arrow
                        elif str(reaction.emoji) == "\U000027A1":
                            await output.delete()
                            curr_count = curr_count + 10
                            output = await ctx.author.send(display_mangas_in_list(mangalist, curr_count, 10))
                            if curr_count >= 10:
                                await output.add_reaction("\U00002B05")  # leftward pointing arrow
                            if (len(mangalist) - curr_count) >= 10:
                                await output.add_reaction("\U000027A1")  # rightward pointing arrow
        elif "$updates" in str(ctx.content.lower()):  # todo find a way to handle a massive amount of updates being found at once
            session = aiohttp.ClientSession()
            user = collection.find(myquery)
            updates_text = ""
            for result in user:
                mangalist = result["mangalist"]
                mangalist.sort(key=lambda x: x['title'])
                update_flag = False  # tells the system that there is new info to display and avoid re-displaying old info
                for manga in mangalist:
                    title = manga['title']
                    source = manga['source']
                    link = manga['link']
                    chapter = manga['chapter_read']
                    print(f"Looking up {title} on {source}, {chapter}")
                    if source == "Cat Manga":
                        updates_text = await CatMangaModule.aio_chapter_search(session, title, chapter, link)
                        update_flag = True
                    elif source == "Kirei Cake":
                        updates_text = await KireiCakeModule.aio_chapter_search(session, title, chapter, link)
                        update_flag = True
                    elif source == "MANGA Plus by SHUEISHA":
                        # MangaPlusModule.chapter_search(title, chapter_read, link)
                        print("Manga+ search not supported yet :(.")
                    if updates_text != "" and update_flag:
                        output = await ctx.author.send(updates_text)  # display only 1 thing, updates and nothing else
                        await output.add_reaction("✅")
                        update_flag = False
                    # todo crucial change: the chapter_search functions return multiple values and a type specifier
                    #  such that the system knows how to handle the information i.e. whether to display the information,
                    #  add the ✅ mark, this fix will prevent the error message from having the ✅ mark event from
                    #  occurring on a message it was not intended for

                await session.close()
        elif ctx.content.startswith('$editlist'):
            user = collection.find(myquery)
            for result in user:
                mangalist = result["mangalist"]
                mangalist.sort(key=lambda x: x['title'])
                count = 0
                output = await ctx.author.send("Enter the index number of the manga you would like to edit in the "
                                               "list\n" + display_mangas_in_list(mangalist, count, 10))
                await output.add_reaction("⬇")

                def check(m):
                    return ctx.author == m.author

                try:
                    msg = await client.wait_for('message', check=check, timeout=30)
                except asyncio.TimeoutError:
                    await ctx.author.send("Your request has timed out, please try again.")
                else:
                    chosen_index = int(msg.content) - 1
                    question_text = "To change the particulars of your selected manga, type in the field " \
                                    "(title, chapter, source, link) that you would like to edit, followed by the new " \
                                    "information in this format `[field] \"[new value]\"`"
                    await ctx.author.send(f"You have chosen manga number **{msg.content}**.\n{question_text}")
                    try:
                        msg = await client.wait_for('message', check=check, timeout=30)
                    except asyncio.TimeoutError:
                        await ctx.author.send("Your request has timed out, please try again.")
                    else:
                        edit_field = msg.content.split(" ")[0]
                        if edit_field == "chapter":  # converts the value to its proper field key name
                            edit_field = "chapter_read"
                        new_val = msg.content.split('"')[1]
                        if new_val != "NaN":
                            mangalist[chosen_index][edit_field] = new_val
                            collection.update_one({"_id": ctx.author.id}, {"$set": {"mangalist": mangalist}})

                            await ctx.author.send("Manga List entry has been updated. Here is the new one:\n" +
                                                  f"{mangalist[chosen_index]['title']} | "
                                                  f"{mangalist[chosen_index]['chapter_read']} | "
                                                  f"{mangalist[chosen_index]['source']} | "
                                                  f"{mangalist[chosen_index]['link']}")
                        else:
                            await ctx.author.send("Something went wrong please try again. "
                                                  "If you need help, try: `$h editlist`")
        elif ctx.content.startswith('$delmanga'):
            user = collection.find(myquery)
            for result in user:
                mangalist = result["mangalist"]
                mangalist.sort(key=lambda x: x['title'])
                count = 0
                output = await ctx.author.send("Enter the index number of the manga you would like to delete from the "
                                               "list\n" + display_mangas_in_list(mangalist, count, 10))
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
                    await ctx.author.send(display_mangas_in_list(mangalist, 0, len(mangalist)))
        elif ctx.content.startswith('$gdtest'):  # todo fix this piece of shit and test out the jscript selenium thing
            session = aiohttp.ClientSession
            await GDModule.aio_chapter_search(session, "Isekai Mokushiroku Mynoghra", "Chapter 9,2",
                                              "https://gdegenscans.xyz/manga/isekai-mokushiroku-mynoghra-hametsu-no-bunmei-de-hajimeru-sekai-seifuku/")
            # expected results: 2 updates informing me of Chapters 10.1 and 10.2's addition and links to them

    if "$addmanga" in str(ctx.content.lower()):
        await ctx.author.send("Please type in the title, website source, chapter and link to the manga you "
                              "would like to add to your mangalist, separated by commas.\nFormat: <manga title>, "
                              "<source>, <chapter>, <link>\nIf you are unsure how to proceed, type `$h addmanga`")

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
                            "mangalist": {{"title": title, "source": source, "chapter_read": chapter,
                                          "link": link}}}
                    collection.insert_one(post)
                else:
                    user = collection.find(myquery)
                    for result in user:
                        mangalist = result["mangalist"]
                    mangalist.append({"title": title, "source": source, "chapter_read": chapter, "link": link})
                    collection.update_one({"_id": ctx.author.id}, {"$set": {"mangalist": mangalist}})
                await ctx.author.send("Added the new manga to the list.")


@client.event
async def on_reaction_add(reaction, user):
    if user == client.user:
        return

    if str(reaction.emoji) == "✅":
        message = reaction.message.content  # checks if the reaction is to the correct thing
        number_of_chapters = message.count('\n')
        # number_of_chapters isn't actually counting the number of chapters but instead tries to find the latest chapter
        # mentioned in the update message to be stored in latest_chapter, because I have no idea what else to call it,
        # its stuck with that name for now
        print("There are " + str(number_of_chapters))
        title = message.split("**")[1]
        latest_chapter = message.split("\n")
        latest_chapter = latest_chapter[number_of_chapters].split(":")
        latest_chapter = latest_chapter[0]
        # print(str(user.id) + title + latest_chapter)  # a debugger line that is not in use atm
        manga_object = collection.find({"_id": user.id})
        for results in manga_object:
            mangalist = results["mangalist"]
            for manga in mangalist:
                if manga['title'] == title:
                    manga['chapter_read'] = latest_chapter
            collection.update_one({"_id": user.id}, {"$set": {"mangalist": mangalist}})
        # todo if it's possible, try to find a more direct way to
        #  change the specific value instead of iterating through the whole list
        await user.send(f"{title} has been updated to {latest_chapter}")

        # mangalist[]["chapter_read"] = latest_chapter[0]

    if reaction.emoji == "😘":
        print("Reaction")


client.run(token["discord"])  # discord bot credentials
