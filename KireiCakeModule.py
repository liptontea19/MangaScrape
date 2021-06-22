import requests
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
    page_soup = BeautifulSoup(series_page.content, 'html.parser').find(id='content')
    count = 0
    chapter = page_soup.find('div', class_='element')
    total_chapters = len(page_soup.find_all('div', class_='element'))
    while 1:  # loop should not continue more than the total number of chapters
        chapter_element_link = chapter.find('a')['href']
        chapter_element_name = chapter.find('div', class_='title')
        if chapter_element_name.text == chapter_str:
            break
        count = count + 1
        print(f"{chapter_element_name.text}: {chapter_element_link}")
        chapter = chapter.next_sibling
    if count > 0:
        if count == 1:
            print(f"Found {count} update for {series_title} since your last read chapter, {chapter_str}")
        else:
            print(f"Found {count} updates for {series_title} since your last read chapter, {chapter_str}")
    else:
        print("You are up to date with the latest released chapter, " + chapter_str)


async def aiochapter_search(session, series_title, chapter_str, url):
    async with session.get(url) as resp:
        print(resp.status)
        page_soup = BeautifulSoup(await resp.read(), 'html.parser').find(id='content')
        chapter = page_soup.find('div', class_='element')
        total_chapters = len(page_soup.find_all('div', class_='element'))
        print("Total Chapters: " + str(total_chapters))
        chapter_exists: bool = False
        body_text = ""
        for count in range(0, total_chapters):  # loop should not continue more than the total number of chapters
            chapter_element_link = chapter.find('a')['href']
            chapter_element_name = chapter.find('div', class_='title')
            if chapter_element_name.text == chapter_str:
                chapter_exists = True
                break
            print(f"{chapter_element_name.text}: {chapter_element_link}")
            body_text = body_text + f"\n{chapter_element_name.text}: {chapter_element_link}"
            chapter = chapter.next_sibling
            earliest_chapter = chapter_element_name
        if chapter_exists:
            print("Chapter exists")
            if count > 0:
                if count == 1:
                    print(f"Found {count} update for {series_title} since your last read chapter, {chapter_str}.")
                    return f"Found {count} update for {series_title} since your last read chapter, " \
                           f"{chapter_str}." + body_text
                else:
                    print(f"Found {count} updates for {series_title} since your last read chapter, {chapter_str}.")
                    return f"Found {count} updates for {series_title} since your last read chapter, " \
                           f"{chapter_str}." + body_text
            else:
                print("You are up to date with the latest released chapter, " + chapter_str)
        else:
            print("Your manga chapter cannot be found on the website. You might want to check your list.")
            return f"{series_title} {chapter_str} cannot be found on the website. You might want to check your " \
                   f"list.\nNewest chapter found: {page_soup.find('div', class_='element')}. " \
                   f"Oldest chapter found: {earliest_chapter} Total chapters: {str(total_chapters)}\nLink: {url}"
            # inform the user in the event that the manga could not be found
