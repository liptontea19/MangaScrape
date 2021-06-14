# This program scrapes Kireicake (a manga translation site) for new chapter updates
# series{
#   title{
#       series title's text and hyperlink to series page
#   }
#   element{
#       title div{
#           Chapter text and Chapter's Hyperlink
#       }
#       meta_r{
#           Translator's Info, Release Date
#       }
#   }
# }
import requests
from bs4 import BeautifulSoup

URL = 'https://reader.kireicake.com/reader/'
page = requests.get(URL)

soup = BeautifulSoup(page.content, 'html.parser')
chapter_updates = soup.find(id='content')
titles = ["Dai Dark", "Yakuza Reincarnation", "Little Girl x Scoop x Evil Eye", "Frieren at the Funeral"]


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
    release_date = meta_r.text.replace("by", "")  # I can't believe I wrote 5 lines of text to remove words
    release_date = release_date.replace("Kirei", "")
    release_date = release_date.replace("Cake", "")
    release_date = release_date.replace(",", "")
    release_date = release_date.replace(" ", "", 4)

    print(f"The latest release from Kirei Cake was: {title.text}\n"
          f"{chapter_number.text} on {release_date}\nLink: {latest_link}")


#find_new_chapters(titles)
latest_release()
