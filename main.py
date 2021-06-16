# ---------------------------------------------------------------------------------
# This program scrapes Kireicake (a manga translation site) for new chapter updates
# ---------------------------------------------------------------------------------
import KireiCakeModule
import MangaPlusModule
import json

user = "000001"  # later implementation will contain a login feature, telling the code which account's list to access
filepath = "storage_files/list.json"  # relative path from the main.py file to the test.json file located in a folder

with open(filepath) as userFile:  # fetches information from the JSON user info file
    jsonObject = json.load(userFile)
    userFile.close()

mangaList = jsonObject["users"][user]["mangalist"]  # puts data containing info for diff. manga into a list
for manga in mangaList:
    title = manga["title"]
    source = manga["source"]
    chapter_read = manga["chapter_read"]
    link = manga["link"]
    print(f"Looking up {title} on {source}")
    if source == "Kirei Cake":
        KireiCakeModule.chapter_search(title, chapter_read, link)
    elif source == "MANGA Plus by SHUEISHA":
        MangaPlusModule.chapter_search(title, chapter_read, link)

# def createNewAccount

# KireiCakeModule.find_new_chapters(["Dai Dark", "Yakuza Reincarnation"])
# KireiCakeModule.latest_release()
# KireiCakeModule.chapter_search("Dai Dark", 20, "https://reader.kireicake.com/series/yakuza_reincarnation/")

# -w KC [Dai Dark] # the search parameter command to call the KireiCake search function
