# ---------------------------------------------------------------------------------
# This program scrapes Kireicake (a manga translation site) for new chapter updates
# main.py contains the discord bot and database interaction codes while the *Modules
# contain the respective website's scraping code
# ---------------------------------------------------------------------------------
import asyncio
from collections import Counter

import aiohttp
import discord
import pymongo.errors
from discord.ext import tasks
import json
import logging
from pymongo import MongoClient

import CatMangaModule
import GDModule
import KireiCakeModule

# import MangaPlusModule
# todo remove all unnecessary print() statements and replace them with logging commands

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
subscriber_collection = db["UserServices"]

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


def embed_mangalist_display(mangalist: list, start_index: int, max_items: int = 10, sort_by="title",
                            footer_text="Use the arrow buttons to view different pages of the mangalist. "
                                        "To view extra information on a manga in the list, press OK and "
                                        "enter the number of the manga."):
    # max_items refers to maximum number of items that can appear in the list at one time
    # footer_text is the string of text to be appended to the bottom of the embed object, usually a description or info
    if sort_by == "chapter":
        sort_by = "chapter_read"
    mangalist.sort(key=lambda x: x[sort_by])
    embed = discord.Embed(description="Sorting by: " + sort_by.capitalize())
    embed.set_author(name="Mangalist")
    embed.clear_fields()
    for x in range(start_index, start_index + max_items):
        embed.add_field(name=f"{x + 1}. {mangalist[x]['title']}",
                        value=f"[Link]({mangalist[x]['link']}) | {mangalist[x]['chapter_read']} |"
                              f" {mangalist[x]['source']}",
                        inline=False)
        if x + 1 == len(mangalist):
            break
    embed.set_footer(text=footer_text)
    return embed


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
        logging.info(f"User {ctx.author.name} ran $search command.")
        session = aiohttp.ClientSession()
        link = ctx.content.replace("$search ", "")
        manga_found = False
        manga_in_db = False
        if "catmanga.org" in link:
            source = "Cat Manga"
            manga = await CatMangaModule.aio_manga_details(session, link)
        elif "kireicake.com/series" in link:
            source = "Kirei Cake"
            manga = await KireiCakeModule.aio_manga_details(session, link)
        else:
            logging.info("Link received was not from a supported website or incomplete, command ended.")
            await ctx.author.send("Hmmm, looks like your command is missing a link or is from an unsupported website. "
                                  "This function only supports the Cat Manga and Kirei Cake websites at the moment, "
                                  "if you would like your website to be added, message Daniel the dev about it.")
            await session.close()
            return

        if manga['request_status'] == "Success":
            manga_found = True
            embed = discord.Embed(title=manga['title'], url=link, description=manga['description'])
            if 'cover' in manga:
                embed.set_thumbnail(url=manga['cover'])
            embed.set_author(name=source)
            embed.add_field(name="Total Chapters", value=manga['chapters'], inline=True)
            if 'status' in manga:
                embed.add_field(name="Status", value=manga['status'], inline=True)
            if 'author' in manga:
                embed.add_field(name="Manga Author", value=manga['author'], inline=True)
            if 'tag' in manga:
                embed.add_field(name="Tag(s)", value=manga['tag'], inline=True)
            if collection.count_documents({'_id': ctx.author.id, 'mangalist': {
                '$elemMatch': {'title': manga['title'], 'source': source}}}) == 1:
                # checks if the queried manga's details match with an existing manga in the database
                embed.set_footer(text="This manga is in your list.")
                manga_in_db = True
                await ctx.author.send(embed=embed)
            else:
                embed.set_footer(text="Would you like to add this manga to your list? (Y/N)")
                output = await ctx.author.send(embed=embed)
                output.add_reaction("\U0001F197")
        else:
            logging.info("Website was supported but data retrieval failed. Link: " + link)
            await ctx.author.send(f"Status: {manga['request_status']}. The bot was unable to find any information "
                                  f"at the link you provided.")
        await session.close()

        if manga_found and manga_in_db is False:
            def check(msg):
                return ctx.author == msg.author

            def reaction_check(reaction, user):
                return user == ctx.author and str(reaction.emoji) == "\U0001F197"

            try:
                reaction, user = await client.wait_for('message', check=reaction_check, timeout=15)
            except asyncio.TimeoutError:
                print("$search command has timed out.")
                logging.info("$search command has timed out 15 seconds after waiting for user to "
                             "confirm adding the manga to mangalist.")
            else:
                if str(reaction.emoji) == "\U0001F197":
                    await ctx.author.send(
                        "Type in the latest chapter you have read, leave blank if you're starting a new series.")
                    try:
                        chapter = await client.wait_for('message', check=check, timeout=15)
                        chapter = chapter.content
                    except asyncio.TimeoutError:
                        chapter = "Chapter 1"
                    logging.info("Adding manga to collection. " + chapter)
                    if collection.count_documents({"_id": ctx.author.id}) == 0:  # first manga being added to list
                        post = {"_id": ctx.author.id,
                                "mangalist": [{"title": manga['title'], "source": source,
                                               "chapter_read": chapter, "link": link}],
                                'dailyupdates': False}
                        collection.insert_one(post)
                    else:
                        try:
                            collection.update_one({'_id': ctx.author.id},
                                                  {"$push": {'mangalist': {"title": manga['title'], "source": source,
                                                                           "chapter_read": chapter, "link": link}}})
                        except:
                            await ctx.author.send("Something went wrong while trying to add the manga to the list :(")
                            return
                    await ctx.author.send(f"Added {manga['title']} to the list. Currently at {chapter}.")
    elif ctx.content.startswith('$addmanga'):
        myquery = {'_id': ctx.author.id}
        if ctx.content.replace("$addmanga ", "") == "":
            await ctx.author.send("Please type in the title, website source, chapter and link to the manga you "
                                  "would like to add to your mangalist, separated by commas.\nFormat: <manga title>, "
                                  "<source>, <chapter>, <link>\nIf you are unsure how to proceed, enter `$h addmanga`")

            def check(msg):
                return ctx.author == msg.author

            try:
                msg = await client.wait_for('message', check=check, timeout=60)
            except asyncio.TimeoutError:
                print("addmanga input timed out, command has been cancelled.")
                await ctx.author.send("Your request has timed out, please try again.")
                return

            try:
                title, source, chapter, link = msg.content.split(", ")
            except ValueError:
                logging.info("User entered an incomplete set of values for $addmanga")
                await ctx.author.send(
                    "There seems to be something wrong with the information that you added, did you miss "
                    "a comma or field of information?")
                return
        else:
            values = ctx.content.replace("$addmanga ", "")
            try:
                title, source, chapter, link = values.split(", ")
            except ValueError:
                logging.info("User entered an incomplete set of values for $addmanga")
                await ctx.author.send(
                    "There seems to be something wrong with the information that you added, did you miss "
                    "a comma or field of information?")
                return

        print(f"Adding manga Title: {title}, Source: {source}, Chapter: {chapter}, Link: {link}")
        if collection.count_documents(myquery) == 0:  # checks if the user has an existing doc in the cluster
            post = {'_id': ctx.author.id,
                    'mangalist': [{"title": title, "source": source, "chapter_read": chapter,
                                   "link": link}],
                    'dailyupdates': False}
            collection.insert_one(post)  # creates a new document with the values in post
        else:
            if collection.count_documents({'_id': ctx.author.id, 'mangalist': {
                '$elemMatch': {'title': title, 'source': source}}}) == 0:
                collection.update_one({'_id': ctx.author.id},
                                      {"$push": {'mangalist': {"title": title, "source": source,
                                                               "chapter_read": chapter, "link": link}}})
        await ctx.author.send("Added the new manga to the list.")

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
            embed = discord.Embed()
            for result in user:
                mangalist = result["mangalist"]
                mangalist.sort(key=lambda x: x['title'])  # alphabetically sorts the mangas by title for displaying
                output_text = display_mangas_in_list(mangalist, curr_count, 10)
                embed.set_author(name="Mangalist")
                for x in range(curr_count, curr_count + 10):
                    embed.add_field(name=f"{x + 1}. {mangalist[x]['title']}",
                                    value=f"[Link]({mangalist[x]['link']}) | {mangalist[x]['chapter_read']} |"
                                          f" {mangalist[x]['source']}",
                                    inline=False)
                    if x + 1 == len(mangalist):
                        break
                embed.set_footer(text="Use the arrow buttons to view different pages of the mangalist.")
                print(output_text)
                output = await ctx.author.send(embed=embed)
                if len(mangalist) >= 10:
                    await output.add_reaction("\U000027A1")  # rightward pointing arrow
                await output.add_reaction("\U0001F197")  # OK emoji

                def check(reaction, user):
                    return user == ctx.author and str(reaction.emoji) in ["\U00002B05", "\U000027A1", "\U0001F197"]

                while True:
                    try:
                        reaction, user = await client.wait_for("reaction_add", check=check, timeout=15.0)
                    except asyncio.TimeoutError:
                        print("Mangalist command listener ends here.")
                        break
                    else:
                        if str(reaction.emoji) in ["\U00002B05", "\U000027A1"]:
                            await output.delete()
                            if str(reaction.emoji) == "\U00002B05":  # if user presses left arrow
                                curr_count = curr_count - 10  # go backwards by 10
                            else:
                                curr_count = curr_count + 10  # go forwards by 10
                            # embed.clear_fields()
                            for x in range(curr_count, curr_count + 10):
                                embed.add_field(name=f"{x + 1}. {mangalist[x]['title']}",
                                                value=f"[Link]({mangalist[x]['link']}) | {mangalist[x]['chapter_read']}"
                                                      f" | {mangalist[x]['source']}",
                                                inline=False)
                                if x + 1 == len(mangalist):
                                    break
                            output = await ctx.author.send(embed=embed)
                            if curr_count >= 10:
                                await output.add_reaction("\U00002B05")  # leftward pointing arrow
                            if (len(mangalist) - curr_count) >= 10:
                                await output.add_reaction("\U000027A1")  # rightward pointing arrow
                            await output.add_reaction("\U0001F197")
                        elif str(reaction.emoji) == "\U0001F197":  # do some shit here
                            await ctx.author.send("Enter the list number of the manga to view its details.")

                            def check(msg):
                                return ctx.author == msg.author

                            try:
                                input = await client.wait_for('message', check=check, timeout=15)
                                index_num = int(input.content) - 1
                            except asyncio.TimeoutError:
                                logging.info("Manga details look up timed out.")
                                return
                            session = aiohttp.ClientSession()
                            search_link = mangalist[index_num]['link']
                            print(search_link)
                            if mangalist[index_num]['source'] == "Cat Manga":
                                manga = await CatMangaModule.aio_manga_details(session, search_link)
                            elif mangalist[index_num]['source'] == "Kirei Cake":
                                manga = await KireiCakeModule.aio_manga_details(session, search_link)
                            else:
                                return

                            if manga['request_status'] == "Success":
                                detail_embed = discord.Embed(title=manga['title'], url=search_link,
                                                             description=manga['description'])
                                if 'cover' in manga:
                                    detail_embed.set_thumbnail(url=manga['cover'])
                                detail_embed.set_author(name=mangalist[index_num]['source'])
                                detail_embed.add_field(name="Chapters Read",
                                                       value=f"{mangalist[index_num]['chapter_read']} out of "
                                                             f"{manga['chapters']}", inline=True)
                                if 'status' in manga:
                                    detail_embed.add_field(name="Status", value=manga['status'], inline=True)
                                if 'author' in manga:
                                    detail_embed.add_field(name="Manga Author", value=manga['author'], inline=True)
                                if 'tag' in manga:
                                    detail_embed.add_field(name="Tag(s)", value=manga['tag'], inline=True)
                                output = await ctx.author.send(embed=detail_embed)
                            else:
                                logging.info("Website was supported but data retrieval failed. Link: " + search_link)
                                await ctx.author.send(
                                    f"Status: {manga['request_status']}. The bot was unable to find any information "
                                    f"at the link you provided.")
                            await session.close()

        elif ctx.content.startswith('$editlist'):
            user = collection.find(myquery)
            for result in user:
                mangalist = result["mangalist"]
                curr_count = 0
                footer_text = "Use the arrow buttons to view different pages of the "
                "mangalist. To edit information of a manga in the list, "
                "press OK and enter the number of the manga."
                output = await ctx.author.send(embed=embed_mangalist_display(mangalist, curr_count, sort_by='title',
                                                                             footer_text=footer_text))
                if (len(mangalist) - curr_count) >= 10:
                    await output.add_reaction("\U000027A1")  # rightward pointing arrow
                await output.add_reaction("\U0001F197")

                def check(m):
                    return ctx.author == m.author

                def react_check(reaction, user):
                    return user == ctx.author and str(reaction.emoji) in ["\U00002B05", "\U000027A1", "\U0001F197"]

                while True:
                    try:
                        reaction, user = await client.wait_for('reaction_add', check=react_check, timeout=15)
                    except asyncio.TimeoutError:
                        await ctx.author.send("Your request has timed out, please try again.")
                        break
                    else:
                        if str(reaction.emoji) in ["\U00002B05", "\U000027A1"]:
                            await output.delete()
                            if str(reaction.emoji) == "\U00002B05":  # if user presses left arrow
                                curr_count = curr_count - 10  # go backwards by 10
                            else:
                                curr_count = curr_count + 10  # go forwards by 10
                            embed = embed_mangalist_display(mangalist, curr_count, footer_text=footer_text)
                            output = await ctx.author.send(embed=embed)
                            if curr_count >= 10:
                                await output.add_reaction("\U00002B05")  # leftward pointing arrow
                            if (len(mangalist) - curr_count) >= 10:
                                await output.add_reaction("\U000027A1")  # rightward pointing arrow
                            await output.add_reaction("\U0001F197")
                        elif str(reaction.emoji) == "\U0001F197":
                            await ctx.author.send("List index number: ")
                            try:
                                msg = await client.wait_for('message', check=check, timeout=15)
                            except asyncio.TimeoutError:
                                await ctx.author.send("The command has timed out.")
                                break
                            else:
                                chosen_index = int(msg.content) - 1
                                question_text = f"You have chosen to edit **{mangalist[chosen_index]['title']}** "\
                                                "To change the particulars of your selected manga, type in the field " \
                                                "(title, chapter, source, link) that you would like to edit, followed" \
                                                " by its new value encased in quote marks in this format: " \
                                                "`[field] \"[new value]\"`"
                                await ctx.author.send(question_text)
                                try:
                                    msg = await client.wait_for('message', check=check, timeout=30)
                                except asyncio.TimeoutError:
                                    await ctx.author.send("Your request has timed out, please try again.")
                                    break
                                else:
                                    edit_field = msg.content.split(" ")[0]
                                    if edit_field in ["title", "chapter", "source", "link"]:
                                        if edit_field == "chapter":  # converts the value to its proper field key name
                                            edit_field = "chapter_read"
                                        try:
                                            new_val = msg.content.split('"')[1]
                                        except IndexError:
                                            await ctx.author.send("Your input was missing quotation marks around the "
                                                                  "value you are trying to update with.")
                                        else:
                                            if new_val != "":
                                                mangalist[chosen_index][edit_field] = new_val
                                                collection.update_one({'_id': user.id},
                                                                      {'$set': {
                                                                          f'mangalist.{chosen_index}.{edit_field}': new_val}})
                                                """
                                                await ctx.author.send(
                                                    "Manga List entry has been updated. Updated data:\n" +
                                                    f"{mangalist[chosen_index]['title']} | "
                                                    f"{mangalist[chosen_index]['chapter_read']} | "
                                                    f"{mangalist[chosen_index]['source']} | "
                                                    f"{mangalist[chosen_index]['link']}")
                                                """
                                                embed = discord.Embed()
                                                embed.set_author(name="Updated Manga Listing")
                                                embed.add_field(name="Title", value=mangalist[chosen_index]['title'])
                                                embed.add_field(name="Current Chapter",
                                                                value=mangalist[chosen_index]['chapter_read'],
                                                                inline=True)
                                                embed.add_field(name="Source", value=mangalist[chosen_index]['source'],
                                                                inline=True)
                                                embed.add_field(name="Link", value=mangalist[chosen_index]['link'],
                                                                inline=False)
                                                await ctx.author.send(embed=embed)
                                                break
                                            else:
                                                await ctx.author.send("You are missing a quotation mark in front of the"
                                                                      " value you are updating with, please try again. "
                                                                      "If you need help, type in: `$h editlist`")
                                                break
                                    else:
                                        await ctx.author.send("The field you are trying to edit is not one of the four "
                                                              "expected values: title, chapter, source or link. Please "
                                                              "try again.")
                                        break
        elif ctx.content.startswith('$delmanga'):
            user = collection.find(myquery)
            footer_text = "Use the arrow buttons to view different pages of the mangalist. To delete " \
                          "a manga in the list, press OK and enter the list number of the manga."
            for result in user:
                mangalist = result["mangalist"]

                mangalist.sort(key=lambda x: x['title'])
                curr_count = 0
                output = await ctx.author.send(embed=embed_mangalist_display(mangalist, curr_count,
                                                                             footer_text=footer_text))
                if len(mangalist) >= 10:
                    await output.add_reaction("\U000027A1")
                await output.add_reaction("\U0001F197")

                def check(m):
                    return ctx.author == m.author

                def react_check(reaction, user):
                    return user == ctx.author and str(reaction.emoji) in ["\U00002B05", "\U000027A1", "\U0001F197"]

                while True:
                    try:
                        reaction, user = await client.wait_for('reaction_add', check=react_check, timeout=15)
                    except asyncio.TimeoutError:
                        await ctx.author.send("Your request has timed out, please try again.")
                        break
                    else:
                        if str(reaction.emoji) in ["\U00002B05", "\U000027A1"]:
                            await output.delete()
                            if str(reaction.emoji) == "\U00002B05":  # if user presses left arrow
                                curr_count = curr_count - 10  # go backwards by 10
                            else:
                                curr_count = curr_count + 10  # go forwards by 10
                            output = await ctx.author.send(embed=embed_mangalist_display(mangalist, curr_count,
                                                                                         footer_text=footer_text))
                            if curr_count >= 10:
                                await output.add_reaction("\U00002B05")  # leftward pointing arrow
                            if (len(mangalist) - curr_count) >= 10:
                                await output.add_reaction("\U000027A1")  # rightward pointing arrow
                            await output.add_reaction("\U0001F197")
                        elif str(reaction.emoji) == "\U0001F197":
                            await ctx.author.send("List index number: ")
                            try:
                                msg = await client.wait_for('message', check=check, timeout=15)
                            except asyncio.TimeoutError:
                                await ctx.author.send("Your request has timed out")
                                break
                            index_num = int(msg.content) - 1
                            title = mangalist[index_num]['title']
                            try:
                                collection.update_one({"_id": ctx.author.id},
                                                      {"$pull": {"mangalist": {'title': title,
                                                                               'source': mangalist[index_num]['source'],
                                                                               'link': mangalist[index_num]['link']}}})
                            except pymongo.errors.PyMongoError:
                                await ctx.author.send("Failed to delete manga from list.")
                                logging.warning("Deletion of element in mangalist failure.")
                                break
                            else:
                                await ctx.author.send("Deleted " + title + " from the mangalist.")
                                break
        elif ctx.content.startswith('$profile'):
            user_doc = collection.find({'_id': ctx.author.id})
            embed = discord.Embed()
            embed.set_author(name=f"{ctx.author.name}'s MangaScrape Profile")
            for result in user_doc:
                mangalist = result['mangalist']
                embed.add_field(name="No. of Manga in List", value=str(len(mangalist)), inline=False)
                if result['dailyupdates']:
                    is_subscriber = "Yes"
                else:
                    is_subscriber = "No"
                embed.add_field(name="Receiving Daily Updates?", value=is_subscriber, inline=False)
                # find the value of the source that appears most in ['source']
                source_list = []
                for mangas in mangalist:
                    source_list.append(mangas['source'])
                most_common_source, source_count = Counter(source_list).most_common(1)[0]
                embed.add_field(name="Favourite Source", value=f"{most_common_source}, {source_count} manga")
                await ctx.author.send(embed=embed)

        elif ctx.content.startswith('$gdtest'):  # todo fix this piece of shit and test out the jscript selenium thing
            session = aiohttp.ClientSession
            await GDModule.aio_chapter_search(session, "Isekai Mokushiroku Mynoghra", "Chapter 9,2",
                                              "https://gdegenscans.xyz/manga/isekai-mokushiroku-mynoghra-hametsu-no-bunmei-de-hajimeru-sekai-seifuku/")
            # expected results: 2 updates informing me of Chapters 10.1 and 10.2's addition and links to them
        elif ctx.content.startswith('$updates'):
            find_list = []
            session = aiohttp.ClientSession()
            user = collection.find(myquery)
            for result in user:
                mangalist = result["mangalist"]
                mangalist.sort(key=lambda x: x['title'])
                for manga in mangalist:
                    title = manga['title']
                    source = manga['source']
                    link = manga['link']
                    chapter = manga['chapter_read']
                    print(f"Looking up {title} on {source}, {chapter}")
                    if source == "Kirei Cake":
                        find_list.append(await KireiCakeModule.aio_chapter_search2(session, title, chapter, link))
                    elif source == "Cat Manga":
                        find_list.append(await CatMangaModule.aio_chapter_search2(session, title, chapter, link))
            await session.close()
            for manga in find_list:
                if manga['status'] != "Up to date":
                    total_chapters = len(manga['chapters'])
                    embed = discord.Embed(title=manga['title'], url=manga["source_link"],
                                          description=manga["description"])
                    embed.set_author(name=manga['source_name'])
                    if 'thumbnail' in manga:
                        embed.set_thumbnail(url=manga['thumbnail'])
                    if 'release_date' in manga:
                        for x in range(total_chapters, 0, -1):
                            embed.add_field(name=manga['chapters'][x - 1],
                                            value=f"[Read here]({manga['chp_links'][x - 1]}) | {manga['release_date'][x - 1]}",
                                            inline=False)
                    else:
                        for x in range(total_chapters, 0, -1):
                            embed.add_field(name=manga['chapters'][x - 1],
                                            value=f"[Read here]({manga['chp_links'][x - 1]})",
                                            inline=True)  # Pack it together

                    if manga['status'] == "Update found":
                        embed.set_footer(text="Press the check button when you are done reading the chapters.")
                    output = await ctx.author.send(embed=embed)
                    if manga['status'] == "Update found":
                        await output.add_reaction("✅")
        elif ctx.content.startswith('$dailyupdates'):
            role = discord.utils.get(ctx.author.guild.roles, name="Daily Updates")
            await ctx.author.add_roles(role)
            collection.update_one({'_id': ctx.author.id}, {'$set': {'dailyupdates': True}})
            await ctx.author.send("You now have the Daily Updates role. To remove it, type `$rm dailyupdates`")
        elif ctx.content.startswith('$rm dailyupdates'):
            role = discord.utils.get(ctx.author.guild.roles, name="Daily Updates")
            await ctx.author.remove_roles(role)
            collection.update_one({'_id': ctx.author.id}, {'$set': {'dailyupdates': False}})
            await ctx.author.send("You have removed the Daily Updates role.")
        elif ctx.content.startswith('$roletest'):
            await daily_updates()


@tasks.loop(hours=24)
async def daily_updates():
    session = aiohttp.ClientSession()
    user = collection.find({'dailyupdates': True})  # only return the documents of users who subscribed to dailyUpdates
    for result in user:
        # checks through mangalist and calling the web-scraping functions based on source, functions return a Dict
        # type object which is added to an array to be handled by the next for loop
        find_list = []
        member_id = result["_id"]
        mangalist = result["mangalist"]
        mangalist.sort(key=lambda x: x['title'])
        for manga in mangalist:
            title = manga['title']
            source = manga['source']
            link = manga['link']
            chapter = manga['chapter_read']
            print(f"Looking up {title} on {source}, {chapter}")
            if source == "Kirei Cake":
                find_list.append(
                    await KireiCakeModule.aio_chapter_search2(session, title, chapter, link))
            elif source == "Cat Manga":
                find_list.append(
                    await CatMangaModule.aio_chapter_search2(session, title, chapter, link))
        for manga in find_list:  # manga['status'] value is used to decide the type of output to give to the user
            if manga['status'] != "Up to date":
                total_chapters = len(manga['chapters'])
                embed = discord.Embed(title=manga['title'], url=manga["source_link"],
                                      description=manga["description"])
                embed.set_author(name=manga['source_name'])
                if 'thumbnail' in manga:
                    embed.set_thumbnail(url=manga['thumbnail'])
                if 'release_date' in manga:
                    for x in range(total_chapters, 0, -1):
                        embed.add_field(name=manga['chapters'][x - 1],
                                        value=f"[Read here]({manga['chp_links'][x - 1]}) | {manga['release_date'][x - 1]}",
                                        inline=False)
                else:
                    for x in range(total_chapters, 0, -1):
                        embed.add_field(name=manga['chapters'][x - 1],
                                        value=f"[Read here]({manga['chp_links'][x - 1]})",
                                        inline=True)  # Pack it together

                if manga['status'] == "Update found":
                    embed.set_footer(text="Press the check button when you are done reading the chapters.")
                user_obj = await client.fetch_user(member_id)
                output = await user_obj.send(embed=embed)
                if manga['status'] == "Update found":
                    await output.add_reaction("✅")
    await session.close()


"""
@client.event
async def on_reaction_add(reaction, user):
    if user == client.user:
        return
"""


@client.event
async def on_raw_reaction_add(payload):
    # channel = client.get_channel(payload.channel_id)
    user = client.get_user(payload.user_id)
    if user == client.user:
        return

    message = await user.fetch_message(payload.message_id)
    reaction = payload.emoji.name

    if reaction == "✅":  # a cross mark to avoid mixing up with the check mark during testing, same purpose
        print("received reaction.")
        total_chapters = len(message.embeds[0].fields)
        print(message.embeds[0].fields[total_chapters - 1].name)
        print(message.embeds[0].title)
        # print(message.embeds[0].field.name)

        update_val = message.embeds[0].fields[total_chapters - 1].name

        def check(msg):
            return user == msg.author

        if total_chapters > 1:  # options that allow reader's to pick which chapter they have finished reading
            output_list = "No.| Chapter\n"
            for x in range(0, total_chapters):
                output_list = output_list + f"{x + 1}.  | {message.embeds[0].fields[x].name}\n"
            await user.send("Enter the number of the latest chapter you have finished reading, "
                            "leave blank if you read all new chapters.\n" + output_list)
            try:
                msg = await client.wait_for('message', check=check, timeout=10)
                index_num = int(msg.content) - 1
            except asyncio.TimeoutError:
                print("User did not respond, update_val is assumed to be " + update_val)
            else:
                update_val = message.embeds[0].fields[index_num].name

        print(f"Updating {message.embeds[0].title}'s chapter progress to {update_val}")
        collection.update_one({
            '_id': user.id,
            'mangalist': {'$elemMatch': {'title': message.embeds[0].title}}
        }, {'$set': {'mangalist.$.chapter_read': update_val}})


client.run(token["discord"])  # discord bot credentials
# await daily_updates.start() only put this function into action once the bot gets transferred to a 24/7 host
