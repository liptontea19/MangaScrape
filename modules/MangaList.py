import asyncio
import logging

import aiohttp
import discord
import pymongo
import selenium.common.exceptions

from modules import CatMangaModule, GDModule, KireiCakeModule, MangaDexModule, MangaPlusModule
from pymongo.errors import PyMongoError
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

OK_emoji = "\U0001F197"

ff_options = Options()  # Options for the Firefox Webdriver Engine used by Selenium
ff_options.headless = True  # Turns off the GUI for the webdriver to save resources


def embed_mangalist_display(mangalist: list, start_index: int, footer_text, max_items: int = 10, sort_by="title"):
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


async def list_details(ctx, mangalist, client, session, driver):
    await ctx.author.send("Enter the list number of the manga to view its details.")

    def message_check(msg):
        return ctx.author == msg.author

    try:
        input = await client.wait_for('message', check=message_check, timeout=15)
        index_num = int(input.content) - 1
    except asyncio.TimeoutError:
        logging.info("Manga details search timed out.")
    except ValueError:
        logging.debug("ValueError: User entered a non number as index number input in "
                      "$mangalist command.")
        output = await ctx.author.send("ValueError: Are you sure that's a number?"
                                       "Press ❌ to try again.")
        output.add_reaction("❌")
    else:
        link = mangalist[index_num]['link']
        manga = await manga_search_2(ctx, link, session, driver)
        if manga['request_status'] == "Success":
            embed = discord.Embed(title=manga['title'], url=link, description=manga['description'])
            if 'cover' in manga:
                embed.set_thumbnail(url=manga['cover'])
            embed.set_author(name=manga['source'])
            embed.add_field(name="Chapters Read",
                            value=f"{mangalist[index_num]['chapter_read']}/{manga['chapters']}",
                            inline=True)
            if 'status' in manga:
                embed.add_field(name="Status", value=manga['status'], inline=True)
            if 'author' in manga:
                embed.add_field(name="Manga Author", value=manga['author'], inline=True)
            if 'tag' in manga:
                embed.add_field(name="Tag(s)", value=manga['tag'], inline=True)
            embed.set_footer(text="Press ❌ to return to the mangalist.")
            output = await ctx.author.send(embed=embed)
            await output.add_reaction("❌")
        else:
            logging.info("Website was supported but data retrieval failed. Link: " + link)
            await ctx.author.send(
                f"Status: {manga['request_status']}. The bot was unable to find any information "
                f"at the link you provided.")


async def del_option(ctx, mangalist, collection, client):
    await ctx.author.send("Enter the list number of the manga to view its details.")

    def check(msg):
        return ctx.author == msg.author

    try:
        msg = await client.wait_for('message', check=check, timeout=15)
        index_num = int(msg.content) - 1
        title = mangalist[index_num]['title']
        collection.update_one({"_id": ctx.author.id},
                              {"$pull": {"mangalist": {'title': title,
                                                       'source': mangalist[index_num]['source'],
                                                       'link': mangalist[index_num]['link']}}})
    except asyncio.TimeoutError:  # intended for msg
        output = await ctx.author.send("Your request has timed out")
        logging.debug("Timeouterror has occurred.")
        await output.add_reaction("❌")
    except IndexError:  # if the index_num is out of bounds and the mangalist[index_num] fails
        output = await ctx.author.send("The number you have entered is not on the list. Press ❌ to try again.")
        logging.debug("IndexError has occurred.")
        await output.add_reaction("❌")
    except ValueError:
        output = await ctx.author.send("Are you sure thats a number? Press ❌ to try again.")
        logging.debug("User entered a non-number for index number, command ended.")
        await output.add_reaction("❌")
    except pymongo.errors.PyMongoError:
        output = await ctx.author.send("Failed to delete manga from list. Press ❌ to try again.")
        logging.warning("Deletion of element in mangalist failure.")
        await output.add_reaction("❌")
    else:
        output = await ctx.author.send("Deleted " + title + " from the mangalist. "
                                                            "If you would to delete another manga, press ❌.")
        await output.add_reaction("❌")


async def edit_option(ctx, mangalist, collection, client):
    await ctx.author.send("List index number: ")

    def check(msg):
        return ctx.author == msg.author

    try:
        msg = await client.wait_for('message', check=check, timeout=15)
        chosen_index = int(msg.content) - 1
    except asyncio.TimeoutError:
        await ctx.author.send("The command has timed out.")
        logging.info("TimeoutError: $editlist command timed out.")
        return
    except ValueError:
        logging.debug("ValueError: User entered in a non number as index input in $editlist.")
        await ctx.author.send("ValueError: Are you sure that's a number?")
        return
    else:
        try:
            question_text = f"You are currently editing **{mangalist[chosen_index]['title']}" \
                            f"**.\n**Title**: {mangalist[chosen_index]['title']}\n" \
                            f"Chapter: {mangalist[chosen_index]['chapter_read']}\n" \
                            f"Source: {mangalist[chosen_index]['source']}\n" \
                            f"Link: {mangalist[chosen_index]['link']}\n" \
                            f"To change the particulars of your selected manga:\n1) Type in the" \
                            " **field** (title, chapter, source, link) that you would like to edit\n" \
                            "2)Add a **space** followed by the new value encased in quote marks in " \
                            "the format: `[field] \"[new value]\"`"
        except IndexError:
            await ctx.author.send("The number you have entered is not on the list. $editlist "
                                  "command ended.")
            return
        await ctx.author.send(question_text)
        try:
            msg = await client.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError:
            logging.debug("User timed out when changing value.")
            await ctx.author.send("Your request has timed out, please try again.")
        else:
            edit_field = msg.content.split(" ")[0]
            if edit_field in ["title", "chapter", "source", "link"]:
                if edit_field == "chapter":  # converts the value to its proper field key name
                    edit_field = "chapter_read"
                try:
                    new_val = msg.content.split('"')[1]
                except IndexError:
                    output = await ctx.author.send("Your input was missing quotation marks around the "
                                                   "value you are trying to update with. Press ❌ to try again.")
                    await output.add_reaction("❌")

                else:
                    if new_val != "":
                        mangalist[chosen_index][edit_field] = new_val
                        collection.update_one({'_id': ctx.author.id}, {'$set': {f'mangalist.{chosen_index}.{edit_field}': new_val}})
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
                        output = await ctx.author.send(embed=embed)
                        await output.add_reaction("❌")
                    else:
                        output = await ctx.author.send("You are missing a quotation mark in front of the"
                                                       " value you are updating with, please try again. "
                                                       "If you need help, type in: `$h editlist`")
                        logging.info('User input missing quote ("") marks '
                                     'encasement for value.')
                        await output.add_reaction("❌")
            else:
                output = await ctx.author.send("The field you are trying to edit is not one of the four "
                                               "expected values: title, chapter, source or link. Press ❌ "
                                               "to try again.")
                await output.add_reaction("❌")


async def mangalist(ctx, collection: pymongo.collection, client, opt_action="default"):
    myquery = {'_id': ctx.author.id}
    user_doc = collection.find_one(myquery)
    mangalist = user_doc["mangalist"]
    curr_count = 0
    session = ""
    driver = ""
    """
    driver = webdriver.Firefox(options=ff_options,
                               executable_path='geckodriver-v0.29.1-win64/geckodriver.exe',
                               service_log_path='logs/geckodriver.log')
    print("Firefox Driver has started.")
    
    output = await ctx.author.send(embed=embed_mangalist_display(mangalist, curr_count, footer_text, 10))
    if len(mangalist) >= 10:
        await output.add_reaction("\U000027A1")  # rightward pointing arrow
    await output.add_reaction(OK_emoji)
    """
    if opt_action == "delete":
        footer_text = "Use the arrow buttons to view different pages of the mangalist. To delete " \
                      "a manga in the list, press OK and enter the list number of the manga."
    elif opt_action == "edit":
        footer_text = "Use the arrow buttons to view different pages of the mangalist. To edit information of a " \
                      "manga in the list, press OK and enter the number of the manga."
    else:  # the default mangalist footer text if there no opt_action was specified
        footer_text = "Use the arrow buttons to view different pages of the mangalist. " \
                      "To view extra information on a manga in the list, press OK and " \
                      "enter the number of the manga."

    def react_check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["\U00002B05", "\U000027A1", OK_emoji]

    def cancel_check(reaction, user):
        return user == ctx.author and str(reaction.emoji) == "\U0000274C"  # checks if user still wants to continue

    if opt_action == "default":
        session = aiohttp.ClientSession()
        driver = webdriver.Chrome(executable_path='chromedriver_win32/chromedriver.exe')

    while True:
        # displays mangalist
        output = await ctx.author.send(embed=embed_mangalist_display(mangalist, curr_count, footer_text))
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
                if opt_action == "default":
                    await list_details(ctx, mangalist, client, session, driver)
                elif opt_action == "delete":
                    await del_option(ctx, mangalist, collection, client)
                elif opt_action == "edit":
                    await edit_option(ctx, mangalist, collection, client)

                try:
                    await client.wait_for("reaction_add", check=cancel_check, timeout=15.0)
                except asyncio.TimeoutError:
                    print("Mangalist command listener ends here.")
                    break

    if opt_action == "default":
        await session.close()


async def manga_search(ctx, link, collection, client, add_option=False):
    # session = aiohttp.ClientSession()
    manga_found = False
    manga_in_db = False
    source = ""
    manga = {}
    try:
        if "catmanga.org" in link or "kireicake.com/series" in link or "mangadex.org/title/" in link:
            session = aiohttp.ClientSession()
            if "catmanga.org" in link:
                source = "Cat Manga"
                manga = await CatMangaModule.aio_manga_details(session, link)
            elif "kireicake.com/series" in link:
                source = "Kirei Cake"
                manga = await KireiCakeModule.manga_details(session, link)
            elif "mangadex.org/title/" in link:
                source = "MangaDex"
                manga = await MangaDexModule.manga_details(session, link)
            await session.close()
        elif "gdegenscans.xyz/manga/" in link or "mangaplus.shueisha.co.jp/" in link:
            options = Options()
            options.headless = True
            driver = webdriver.Firefox(options=options, executable_path='geckodriver-v0.29.1-win64/geckodriver.exe',
                                       service_log_path='logs/geckodriver.log')
            if "gdegenscans.xyz/manga/" in link:
                source = "Galaxy Degen Scans"
                manga = await GDModule.manga_details(driver, link)
            elif "mangaplus.shueisha.co.jp/" in link:
                source = "MANGA Plus by SHUEISHA"
                manga = await MangaPlusModule.manga_details(driver, link)
            driver.quit()
        else:
            logging.info("Link received was not from a supported website or incomplete, $search command ended.")
            await ctx.author.send("Hmmm, looks like your command is missing a link or is from an unsupported "
                                  "website. This function only supports the Cat Manga, Galaxy Degen, Kirei Cake and "
                                  "Shueisha's Manga+ websites at "
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
            embed.set_author(name=source)
            embed.add_field(name="Latest Chapter", value=manga['chapters'], inline=True)
            if 'cover' in manga:
                embed.set_thumbnail(url=manga['cover'])
            if 'status' in manga:
                embed.add_field(name="Status", value=manga['status'], inline=True)
            if 'artist' in manga:
                embed.add_field(name="Manga Artist", value=manga['artist'], inline=True)
            if 'author' in manga:
                embed.add_field(name="Manga Author", value=manga['author'], inline=True)
            if 'tag' in manga:
                embed.add_field(name="Tag(s)", value=manga['tag'], inline=True)
            if add_option is True:
                if collection.count_documents({'_id': ctx.author.id, 'mangalist': {'$elemMatch': {'title': manga['title'], 'source': source}}}) == 1:
                    # checks if the queried manga's details match with an existing manga in the database
                    embed.set_footer(text="This manga is in your list.")
                    manga_in_db = True
                    await ctx.author.send(embed=embed)
                else:
                    embed.set_footer(text="Press OK to add this manga to your list.")
                    output = await ctx.author.send(embed=embed)
                    await output.add_reaction(OK_emoji)
            else:
                await ctx.author.send(embed=embed)
        else:
            logging.info("Website was supported but data retrieval failed. Link: " + link)
            await ctx.author.send(f"Status: {manga['request_status']}. The bot was unable to find any information "
                                  f"at the link you provided.")

    if add_option is True and manga_found is True and manga_in_db is False:
        def check(msg):
            return ctx.author == msg.author

        def reaction_check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == OK_emoji

        try:
            reaction, user = await client.wait_for('reaction_add', check=reaction_check, timeout=15)
        except asyncio.TimeoutError:
            print("$search adding manga function has timed out.")
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


async def manga_search_2(ctx, link, session, driver):
    # function that only returns all the values needed and allows other things to be done
    # such as display, i should write manga_search_1 to be an override function lmao
    manga = {'request_status': "Failure"}
    try:
        if "catmanga.org" in link:
            manga = await CatMangaModule.aio_manga_details(session, link)
            manga['source'] = "Cat Manga"

        elif "kireicake.com/series" in link:
            manga = await KireiCakeModule.manga_details(session, link)
            manga['source'] = "Kirei Cake"
        elif "mangaplus.shueisha.co.jp/" in link:
            manga = await MangaPlusModule.manga_details(driver, link)
            manga['source'] = "MANGA Plus by SHUEISHA"
        else:
            logging.info("Link received was not from a supported website or incomplete, $search command ended.")
            await ctx.author.send("Hmmm, looks like your command is missing a link or is from an unsupported "
                                  "website. This function only supports the Cat Manga and Kirei Cake websites at "
                                  "the moment, if you would like your website to be added, message Daniel "
                                  "about it.")
    except aiohttp.InvalidURL:
        await ctx.author.send("The link you were trying to access does not exist on the website.")
        logging.debug("User tried to access a link not existent on website.")
    except aiohttp.ClientConnectorError as e:
        logging.info("Connection Error: " + str(e))
        await ctx.author.send(f"Error: {str(e)} There seems to be a problem connecting to the server.")
    except selenium.common.exceptions.TimeoutException:
        await ctx.author.send("Web driver search timed out.")
    finally:
        return manga
