# ---------------------------------------------------------------------------------
# This program scrapes Kireicake (a manga translation site) for new chapter updates
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

    else:
        if ctx.content.startswith('$hello'):
            await ctx.channel.send(f'Welcome back {ctx.author.name}!')
        elif "$mangalist" in str(ctx.content.lower()):
            user = collection.find(myquery)
            for result in user:
                mangalist = result["mangalist"]
                mangalist.sort(key=lambda x: x['title'])  # alphabetically sorts the mangas by title for displaying
                output_text = '\n'.join(('Title: ' + manga['title'] + ' on ' + manga['source']) for manga in mangalist)
                print(output_text)
                await ctx.author.send(output_text)
        elif "$updates" in str(ctx.content.lower()):
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

    if "$addmanga" in str(ctx.content.lower()):
        await ctx.author.send("Please type in the title, website source, chapter and link to the manga you "
                              "would like to add to your mangalist, separated by commas.\nFormat: <manga title>, "
                              "<source>, <chapter>, <link>\nIf you are unsure how to proceed, type `$h addmanga`.")

        def check(msg):
            return ctx.author == msg.author

        try:
            msg = await client.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError:
            print("addmanga input timed out, command has been cancelled.")
            await ctx.author.send("Your request has timed out.")
        else:
            try:
                title, source, chapter, link = msg.content.split(", ")
            except:
                await ctx.author.send(
                    "There seems to be something wrong with the information that you added, did you miss"
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


client.run("ODU1MDMwMzk5MTA4MzgyNzUx.YMsjHA.zKWpJFJ4l_ZA8lR96OZdnoFNiyY")  # discord bot credentials
