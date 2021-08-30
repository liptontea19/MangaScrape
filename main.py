# ---------------------------------------------------------------------------------
# This program scrapes Kireicake (a manga translation site) for new chapter updates
# main.py contains the discord bot and database interaction codes while the *Modules
# contain the respective website's scraping code
# ---------------------------------------------------------------------------------
import asyncio
import json
import logging
from collections import Counter

import aiohttp
import discord
from discord.ext import tasks
from pymongo import MongoClient
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

from modules import CatMangaModule, KireiCakeModule, GDModule, MangaPlusModule, MangaList

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

ff_options = Options()  # Options for the Firefox Webdriver Engine used by Selenium
ff_options.headless = True  # Turns off the GUI for the webdriver to save resources
# driver = webdriver.Firefox(options=ff_options, executable_path='geckodriver-v0.29.1-win64/geckodriver.exe',
# service_log_path='logs/geckodriver.log')
# print("Webdriver up and running.")

# force program to wait for driver to be started before doing anything else

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
                     "Do note that the bot's search capabilities are limited to the Cat Manga, Kirei Cake and Manga+ "
                     "websites currently.")

client = discord.Client(intents=intents)

# list of commonly used emoji's and their unicode references
OK_emoji = "\U0001F197"
LEFT_ARROW_emoji = "\U00002B05"
RIGHT_ARROW_emoji = "\U000027A1"


def display_mangas_in_list(mangalist, curr_index: int, size: int):
    # size refers to the number of items in the list to display in text form
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


def updates_desc_maker(manga, title, chapter):
    """
    Function writes update descriptions for $updates response messages based on whether the program managed to find new
    releases for the manga being searched.  3 Statuses are produced from the update functions: Update found, Up to date
    & Failure
    :param manga: the object always has a status value and optional values such as update_count if the search function
    managed to find chapter updates. For error messages a default error message is present if the search function does
    not attach one
    :param title:
    :param chapter:
    :return desc: description that informs user of number of updates or whether there was an error
    """
    update_count = manga['update_count']
    if manga['status'] != "Failure":
        if update_count > 0:  # status: Update found
            if update_count == 1:
                desc = f"1 update since your last read chapter, {chapter}."
            elif update_count <= 6:
                logging.debug(f"{update_count} updates found.")
                desc = f"{update_count} updates since your last read chapter, {chapter}."
            else:
                desc = f"{update_count} updates since your last read chapter, {chapter}.\nDisplaying the 3 " \
                                     "chapters closest to your last read chapter and the 3 newest chapters found."
        else:  # status: Up to date
            logging.debug("User is up to date with the latest released chapter of " + title + ", "
                          + chapter + " returned status: Up to date")
            desc = ""  # needed as desc is always returned at the end
    else:  # status: Failure
        logging.debug("Manga cannot be found on site. Reason: Input Chapter Value is out of bounds")
        # logging.debug("User's search chapter is not within the manga list.")

        desc = f"{title} chapter: {chapter}, stored on your mangalist cannot be found on the website."
    return desc


"""
async def message_wait(ctx, check_con, time_window):
    try:
        msg = await client.wait_for('message', check=check_con, timeout=time_window)
        message = msg.content
        timed_out = False
    except asyncio.TimeoutError:
        message = ""
        timed_out = True
        await ctx.author.send("Your request has timed out, please try again.")
    return message, timed_out
"""


@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))


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
        # session = aiohttp.ClientSession()
        link = ctx.content.replace("$search ", "")
        # driver = webdriver.Firefox(options=ff_options, executable_path='geckodriver-v0.29.1-win64/geckodriver.exe',
                                   # service_log_path='logs/geckodriver.log')
        print("Driver has loaded")
        await MangaList.manga_search(ctx, link, collection, client, add_option=True)
        # driver.quit()
        """
        manga_found = False
        manga_in_db = False
        try:
            if "catmanga.org" in link:
                source = "Cat Manga"
                manga = await CatMangaModule.aio_manga_details(session, link)
            elif "kireicake.com/series" in link:
                source = "Kirei Cake"
                manga = await KireiCakeModule.aio_manga_details(session, link)
            elif "mangaplus.shueisha.co.jp/" in link:
                options = Options()
                options.headless = True
                driver = webdriver.Firefox(options=options, executable_path='geckodriver-v0.29.1-win64/geckodriver.exe',
                                           service_log_path='logs/geckodriver.log')
                source = "MANGA Plus by SHUEISHA"
                manga = await MangaPlusModule.manga_details(driver, link)
            else:
                logging.info("Link received was not from a supported website or incomplete, $search command ended.")
                await ctx.author.send("Hmmm, looks like your command is missing a link or is from an unsupported "
                                      "website. This function only supports the Cat Manga and Kirei Cake websites at "
                                      "the moment, if you would like your website to be added, message Daniel "
                                      "about it.")
                return
        except aiohttp.InvalidURL:
            await ctx.author.send("The link you were trying to access does not exist on the website.")
            logging.debug("User tried to access a link not existent on website.")
        except aiohttp.ClientConnectorError as e:
            logging.info("Connection Error: " + str(e))
            await ctx.author.send(f"Error: {str(e)} There seems to be a problem connecting to the server.")
        except selenium.common.exceptions.TimeoutException:
            await ctx.author.send("Web driver search timed out.")
        else:
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
                    await output.add_reaction(OK_emoji)
            else:
                logging.info("Website was supported but data retrieval failed. Link: " + link)
                await ctx.author.send(f"Status: {manga['request_status']}. The bot was unable to find any information "
                                      f"at the link you provided.")
        finally:
            await session.close()

        if manga_found is True and manga_in_db is False:
            def check(msg):
                return ctx.author == msg.author

            def reaction_check(reaction, user):
                return user == ctx.author and str(reaction.emoji) == OK_emoji

            try:
                reaction, user = await client.wait_for('reaction_add', check=reaction_check, timeout=15)
            except asyncio.TimeoutError:
                print("$search command has timed out.")
                logging.info("$search command has timed out 15 seconds after waiting for user to "
                             "confirm adding the manga to mangalist.")
            else:
                if str(reaction.emoji) == OK_emoji:
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
                        except pymongo.errors.PyMongoError:
                            await ctx.author.send("Something went wrong while trying to add the manga to the list :(")
                            return
                    await ctx.author.send(f"Added {manga['title']} to the list. Currently at {chapter}.")
        """
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
        elif ctx.content.startswith("$mangalist"):
            user_doc = collection.find_one(myquery)
            mangalist = user_doc["mangalist"]
            curr_count = 0
            session = aiohttp.ClientSession()
            driver = webdriver.Chrome(executable_path='chromedriver_win32/chromedriver.exe')
            """
            driver = webdriver.Firefox(options=ff_options,
                                       executable_path='geckodriver-v0.29.1-win64/geckodriver.exe',
                                       service_log_path='logs/geckodriver.log')
            print("Firefox Driver has started.")
            """
            footer_text = "Use the arrow buttons to view different pages of the mangalist. " \
                          "To view extra information on a manga in the list, press OK and " \
                          "enter the number of the manga."

            def react_check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["\U00002B05", "\U000027A1", OK_emoji]

            def cancel_check(reaction, user):
                return user == ctx.author and str(
                    reaction.emoji) == "\U0000274C"  # checks if user still wants to continue

            while True:
                output = await ctx.author.send(
                    embed=embed_mangalist_display(mangalist, curr_count, footer_text=footer_text))
                if curr_count >= 10:
                    await output.add_reaction("\U00002B05")  # leftward pointing arrow
                if (len(mangalist) - curr_count) >= 10:
                    await output.add_reaction("\U000027A1")  # rightward pointing arrow
                await output.add_reaction(OK_emoji)

                # OK reaction actions that can be taken
                try:
                    reaction, user = await client.wait_for("reaction_add", check=react_check, timeout=15.0)
                except asyncio.TimeoutError:
                    print("Mangalist command listener ends here.")
                    logging.info("User's command timed out.")
                    break
                else:
                    if str(reaction.emoji) in ["\U00002B05", "\U000027A1"]:
                        await output.delete()
                        if str(reaction.emoji) == "\U00002B05":  # if user presses left arrow
                            curr_count = curr_count - 10  # go backwards by 10
                        else:
                            curr_count = curr_count + 10  # go forwards by 10
                    elif str(reaction.emoji) == OK_emoji:  # do some shit here
                        await MangaList.list_details(ctx, mangalist, client, session, driver)
                        try:
                            await client.wait_for("reaction_add", check=cancel_check, timeout=15.0)
                        except asyncio.TimeoutError:
                            print("Mangalist command listener ends here.")
                            break

            await session.close()
        elif ctx.content.startswith('$editlist'):
            user_doc = collection.find_one(myquery)
            mangalist = user_doc["mangalist"]
            curr_count = 0
            footer_text = "Use the arrow buttons to view different pages of the mangalist. To edit information of a " \
                          "manga in the list, press OK and enter the number of the manga."

            def react_check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["\U00002B05", "\U000027A1", OK_emoji]

            def cancel_check(reaction, user):
                return user == ctx.author and str(
                    reaction.emoji) == "\U0000274C"  # checks if user still wants to continue

            while True:
                # displays mangalist
                output = await ctx.author.send(
                    embed=embed_mangalist_display(mangalist, curr_count, footer_text=footer_text))
                if curr_count >= 10:
                    await output.add_reaction("\U00002B05")  # leftward pointing arrow
                if (len(mangalist) - curr_count) >= 10:
                    await output.add_reaction("\U000027A1")  # rightward pointing arrow
                await output.add_reaction(OK_emoji)

                # OK reaction actions that can be taken
                try:
                    reaction, user = await client.wait_for("reaction_add", check=react_check, timeout=15.0)
                except asyncio.TimeoutError:
                    print("Mangalist command listener ends here.")
                    logging.info("User's command timed out.")
                    break
                else:
                    if str(reaction.emoji) in ["\U00002B05", "\U000027A1"]:
                        await output.delete()
                        if str(reaction.emoji) == "\U00002B05":  # if user presses left arrow
                            curr_count = curr_count - 10  # go backwards by 10
                        else:
                            curr_count = curr_count + 10  # go forwards by 10
                    elif str(reaction.emoji) == OK_emoji:  # do some shit here
                        await MangaList.edit_option(ctx, mangalist, collection, client)

                        try:
                            await client.wait_for("reaction_add", check=cancel_check, timeout=15.0)
                        except asyncio.TimeoutError:
                            print("Mangalist command listener ends here.")
                            break
        elif ctx.content.startswith('$delmanga'):
            user_doc = collection.find_one(myquery)
            mangalist = user_doc["mangalist"]
            curr_count = 0
            session = aiohttp.ClientSession()
            footer_text = "Use the arrow buttons to view different pages of the mangalist. To delete " \
                          "a manga in the list, press OK and enter the list number of the manga."

            def react_check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["\U00002B05", "\U000027A1", OK_emoji]

            def cancel_check(reaction, user):
                return user == ctx.author and str(
                    reaction.emoji) == "\U0000274C"  # checks if user still wants to continue

            while True:
                # displays mangalist
                output = await ctx.author.send(embed=embed_mangalist_display(mangalist, curr_count,
                                                                             footer_text=footer_text))
                if curr_count >= 10:
                    await output.add_reaction("\U00002B05")  # leftward pointing arrow
                if (len(mangalist) - curr_count) >= 10:
                    await output.add_reaction("\U000027A1")  # rightward pointing arrow
                await output.add_reaction(OK_emoji)

                # OK reaction actions that can be taken
                try:
                    reaction, user = await client.wait_for("reaction_add", check=react_check, timeout=15.0)
                except asyncio.TimeoutError:
                    print("Mangalist command listener ends here.")
                    logging.info("User's command timed out.")
                    break
                else:
                    if str(reaction.emoji) in ["\U00002B05", "\U000027A1"]:
                        await output.delete()
                        if str(reaction.emoji) == "\U00002B05":  # if user presses left arrow
                            curr_count = curr_count - 10  # go backwards by 10
                        else:
                            curr_count = curr_count + 10  # go forwards by 10
                    elif str(reaction.emoji) == OK_emoji:  # do some shit here
                        await MangaList.del_option(ctx, mangalist, collection, client)
                        try:
                            await client.wait_for("reaction_add", check=cancel_check, timeout=15.0)
                        except asyncio.TimeoutError:
                            print("Mangalist command listener ends here.")
                            break
            await session.close()
        elif ctx.content.startswith('$profile'):
            user_doc = collection.find({'_id': ctx.author.id})
            embed = discord.Embed()
            embed.set_author(name=f"{ctx.author.name}'s MangaScrape Profile")
            embed.set_thumbnail(url=ctx.author.avatar_url)
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
                embed.add_field(name="Favourite Manga Source",
                                value=f"{most_common_source}, {source_count} manga in list")
                await ctx.channel.send(embed=embed)
        elif ctx.content.startswith('$updates'):
            find_list = []
            session = aiohttp.ClientSession()
            driver = webdriver.Firefox(options=ff_options, executable_path='geckodriver-v0.29.1-win64/geckodriver.exe',
                                       service_log_path='logs/geckodriver.log')
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
                    logging.debug(f"Looking up {title} on {source}, {chapter}")
                    try:
                        if source == "Cat Manga":
                            find_list.append(await CatMangaModule.aio_chapter_search2(session, title, chapter, link))
                        elif source == "Kirei Cake":
                            find_list.append(await KireiCakeModule.aio_chapter_search2(session, title, chapter, link))
                            """
                            elif source == "MangaDex":
                                manga = await MangaDexModule.chapter_updates(session, title, chapter, link)
                                if 'description' not in manga:
                                    manga['description'] = updates_desc_maker(manga, title, chapter)
                                manga['title'] = title
                                manga['source_name'] = source
                                manga['source_link'] = link
                                find_list.append(manga)
                            """
                        elif source == "MANGA Plus by SHUEISHA":
                            manga = await MangaPlusModule.chapter_updates(driver, title, chapter, link)
                            if 'description' not in manga:
                                manga['description'] = updates_desc_maker(manga, title, chapter)
                            manga['title'] = title
                            manga['source_name'] = source
                            manga['source_link'] = link
                            find_list.append(manga)
                    except aiohttp.InvalidURL:
                        await ctx.author.send(f"Error: The link to {title} stored in the database does not exist!\n"
                                              f"Link: {link}")
            await session.close()
            driver.quit()
            if not find_list:
                logging.debug("User is up to date with all their manga chapters.")
            for manga in find_list:
                if manga['status'] != "Up to date":
                    total_chapters = len(manga['chapters'])
                    embed = discord.Embed(title=manga['title'],
                                          url=manga["source_link"],
                                          description=manga["description"])
                    embed.set_author(name=manga['source_name'])
                    if 'thumbnail' in manga:
                        embed.set_thumbnail(url=manga['thumbnail'])
                    if manga['status'] == "Update found":
                        for x in range(total_chapters, 0, -1):
                            embed.add_field(name=manga['chapters'][x - 1],
                                            value=manga['value'][x - 1],
                                            inline=False)
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
            await ctx.author.send("You will not receive daily updates.")

        # test commands for different things
        """elif ctx.content.startswith('$gdtest'):  # todo fix this piece of shit and test out the jscript selenium thing
            session = aiohttp.ClientSession
            # await GDModule.manga_search(session, "Isekai Mokushiroku Mynoghra", "Chapter 9,2",
            #                                  "https://gdegenscans.xyz/manga/isekai-mokushiroku-mynoghra-hametsu-no-bunmei-de-hajimeru-sekai-seifuku/")
            # expected results: 2 updates informing me of Chapters 10.1 and 10.2's addition and links to them
        
        elif ctx.content.startswith('$roletest'):
            await daily_updates()"""


@tasks.loop(hours=24)
async def daily_updates():
    session = aiohttp.ClientSession()
    user = collection.find({'dailyupdates': True})  # only return the documents of users who subscribed to dailyUpdates
    driver = webdriver.Firefox(options=ff_options, executable_path='geckodriver-v0.29.1-win64/geckodriver.exe',
                               service_log_path='logs/geckodriver.log')
    for result in user:
        # checks through mangalist and calling the web-scraping functions based on source, functions return a Dict
        # type object which is added to an array to be handled by the next for loop
        find_list = []
        member_id = result["_id"]
        mangalist = result["mangalist"]
        mangalist.sort(key=lambda x: x['title'])
        user_obj = await client.fetch_user(member_id)
        for manga in mangalist:
            title = manga['title']
            source = manga['source']
            link = manga['link']
            chapter = manga['chapter_read']
            print(f"Looking up {title} on {source}, {chapter}")
            try:
                if source == "Kirei Cake":
                    find_list.append(
                        await KireiCakeModule.aio_chapter_search2(session, title, chapter, link))
                elif source == "Cat Manga":
                    find_list.append(
                        await CatMangaModule.aio_chapter_search2(session, title, chapter, link))
                elif source == "MANGA Plus by SHUEISHA":
                    find_list.append(await MangaPlusModule.chapter_updates(driver, title, chapter, link))
            except aiohttp.InvalidURL:
                await user_obj.send(f"Error: The link to {title} stored on your database does not exist.\nLink: {link}")
            except aiohttp.ClientConnectorError as e:
                logging.info("Connection Error: " + str(e))
                await user_obj.send(f"Error: {str(e)} There seems to be a problem connecting to the server.")
        for manga in find_list:  # manga['status'] value is used to decide the type of output to give to the user
            if manga['status'] != "Up to date":
                total_chapters = len(manga['chapters'])
                embed = discord.Embed(title=manga['title'], url=manga["source_link"],
                                      description=manga["description"])
                embed.set_author(name=manga['source_name'])
                if 'thumbnail' in manga:
                    embed.set_thumbnail(url=manga['thumbnail'])
                for x in range(total_chapters, 0, -1):
                    embed.add_field(name=manga['chapters'][x - 1],
                                    value=manga['values'][x - 1],
                                    inline=False)

                if manga['status'] == "Update found":
                    embed.set_footer(text="Press the check button when you are done reading the chapters.")
                output = await user_obj.send(embed=embed)
                if manga['status'] == "Update found":
                    await output.add_reaction("✅")
    await session.close()
    driver.quit()


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
                try:
                    update_val = message.embeds[0].fields[index_num].name
                except IndexError:
                    await user.send("The number you have entered is not on the list. Please try again.")
                    logging.debug("Error: Input number for index was out of bounds.")
                    return

        print(f"Updating {message.embeds[0].title}'s chapter progress to {update_val}")
        collection.update_one({
            '_id': user.id,
            'mangalist': {'$elemMatch': {'title': message.embeds[0].title}}
        }, {'$set': {'mangalist.$.chapter_read': update_val}})
        await user.send(f"{message.embeds[0].title} has been updated on the mangalist to {update_val}")


client.run(token["discord"])  # discord bot credentials
# await daily_updates.start() only put this function into action once the bot gets transferred to a 24/7 host
