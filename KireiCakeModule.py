import requests
import string
from bs4 import BeautifulSoup

URL = 'https://reader.kireicake.com/reader/'
page = requests.get(URL)

soup = BeautifulSoup(page.content, 'html.parser')
chapter_updates = soup.find(id='content')
titles = ["Dai Dark", "Yakuza Reincarnation", "Little Girl x Scoop x Evil Eye", "Frieren at the Funeral"]


def response_code_check(code):  # identifies if the response code is a Request redirect or error and displays it
    if 300 < code < 399:
        print("Request was redirected. Error code: " + code)
    if 400 < code < 599:
        print("Request had an error. Error code: " + code)


def find_new_chapters(manga_list):  # scours the chapter updates page for manga titles that much the manga_list of names
    chapter_found = False
    for manga_titles in manga_list:
        title_listing = chapter_updates.find_all('div', string=manga_titles)
        # looks through the soup for listings of the specific title
        num_of_listings = len(title_listing)
        if num_of_listings > 0:
            # if the scraper finds listings of the title in the soup, begin to fetch info about it to display
            # taking into account that the page may have multiple listings of the same title on different dates
            chapter_found = True
            if num_of_listings == 1:
                print(f"A listing of {manga_titles} has been found")
            else:
                print(f"{num_of_listings} listings of {manga_titles} have been found")
            for chapters in title_listing:
                chapter_links = chapters.a.parent.parent.find_all('div', class_='element')
                # the element contains the chapter's info such as chapter number, link and release date
                for links in chapter_links:
                    # this checks for multiple chapter links in each single listing
                    link = links.find('a')['href']
                    chapter_number = links.find('div', class_='title')
                    print(f"Read {chapter_number.text} at: {link}")
        else:
            print("There are no new chapters for " + manga_titles)

    if not chapter_found:
        print("There were no new chapters found")


def latest_release():
    release = chapter_updates.find('div', class_='group')
    element = release.find('div', class_='element')
    meta_r = release.find('div', class_='meta_r')

    title = release.find('div', class_='title')
    latest_link = element.find('a')['href']
    chapter_number = element.find('div', class_='title')
    release_date = meta_r.text.replace("by", "")
    # todo write an if else statement to check if the release date is a word or a date and filter the data accordingly
    release_date = release_date.replace("Kirei", "")
    release_date = release_date.replace("Cake", "")
    release_date = release_date.replace(",", "")
    release_date = release_date.replace(" ", "", 4)

    print(f"The latest release from Kirei Cake was: {title.text}\n"
          f"{chapter_number.text} on {release_date}\nLink: {latest_link}")


def chapter_search(series_title, chapter_str, link):  # it should take the JSON object, grab the link from it and search
    series_page = requests.get(link)
    response_code_check(series_page.status_code)  # checks for any http request failure and informs the user if there is
    chapter_read = int(chapter_str.strip(string.ascii_letters).replace(" ", ""))
    page_soup = BeautifulSoup(series_page.content, 'html.parser').find(id='content')
    latest_chapter = page_soup.find('div', class_='element')
    chapter_number = int(latest_chapter.find('div', class_='title').text.strip(string.ascii_letters).replace(" ", ""))
    diff = chapter_number - chapter_read
    if chapter_number > chapter_read:
        if diff == 1:
            print(f"Found {diff} update for {series_title} since your last read chapter, {chapter_str}")
        else:
            print(f"Found {diff} updates for {series_title} since your last read chapter, {chapter_str}")
        chapter = page_soup.find('div', class_='element')
        for chapters in range(chapter_read, chapter_number):  # for loop to fetch each chapter
            chapter_element_link = chapter.find('a')['href']
            chapter_element_name = chapter.find('div', class_='title')
            print(f"{chapter_element_name.text}: {chapter_element_link}")
            chapter = chapter.next_sibling
            # when the discord implementation is in place, allow the user to react to the message with a tick
            # or cross emoji confirming whether the user has read the latest chapter, thereby updating the JSON
            # file with the latest number
    else:
        print("You are up to date with the latest released chapter, " + chapter_str)
