import requests
import logging
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
    release_date = meta_r.text.split(",")[1].replace(" ", "")

    print(f"The latest release from Kirei Cake was: {title.text}\n"
          f"{chapter_number.text} on {release_date}\nLink: {latest_link}")


async def aio_chapter_search(session, series_title, chapter_str, url):
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
            body_text = f"\n{chapter_element_name.text}: {chapter_element_link}" + body_text
            chapter = chapter.next_sibling
            earliest_chapter = chapter_element_name
        if chapter_exists:
            print("Chapter exists")
            if count > 0:
                if count == 1:
                    head_text = f"**{series_title}**\n1 update since your last read chapter, {chapter_str}."
                    print(head_text)
                else:
                    head_text = f"**{series_title}**\n{count} updates since your last read chapter, {chapter_str}."
                    print(head_text)
                return head_text + body_text + "\n"
            else:
                print("You are up to date with the latest released chapter, " + chapter_str)
                return ""
        else:
            print("Your manga chapter cannot be found on the website. You might want to check your list.")
            return f"**{series_title}**\n`{chapter_str}` cannot be found on the website. You might want to check " \
                   f"your list.\nNewest chapter found: {page_soup.find('div', class_='element')}. " \
                   f"Oldest chapter found: {earliest_chapter} Total chapters: {str(total_chapters)}\nLink: {url}\n"
            # inform the user in the event that the manga could not be found


async def aio_chapter_search2(session, series_title, chapter_str, url):
    async with session.get(url) as resp:
        print(resp.status)
        page_soup = BeautifulSoup(await resp.read(), 'html.parser')
        chapter = page_soup.find('div', class_='element')
        total_chapters = len(page_soup.find_all('div', class_='element'))
        print("Total Chapters: " + str(total_chapters))
        chapter_exists: bool = False
        chapters = []
        chp_links = []
        field_values = []
        for count in range(0, total_chapters):
            if chapter.find('div', class_='title').text == chapter_str:
                chapter_exists = True
                if count > 6:
                    for cnt in range(5, 2, -1):
                        chapter = chapter.previous_sibling
                        chapters[cnt] = chapter.find('div', class_='title').text
                        field_values[cnt] = f"[Read here]({chapter.find('a')['href']}) | " \
                                            f"{chapter.find('div', class_='meta_r').text.split(',')[1].replace(' ', '')}"
                    print(chapters)
                break
            if count < 6:  # stop appending after the 6th element
                chapters.append(chapter.find('div', class_='title').text)
                field_values.append(f"[Read here]({chapter.find('a')['href']}) | "
                                    f"{chapter.find('div', class_='meta_r').text.split(',')[1].replace(' ', '')}")
            earliest_chapter = chapter.find('div', class_='title').text
            chapter = chapter.next_sibling
            """
            1. Iterate down list until item is found, when found and count < 6, break loop
            2. There should be no more than 6 elements in the array, after the 6th element is added, stop appending 
                values into the array until the chapter is found but keep iterating through elements and tracking the 
                earliest_chapter value
            3. If found and count >= 6, roll back the chapter to the previous 3 before the current one and put those 
                values into the array
            Example: Count of 14 items, array elements 1 to 3: 1st 2nd & 3rd, array elements 4 to 6: 12th, 13th & 14th 
            """
        if chapter_exists:
            print("Chapter exists")
            if count > 0:
                if count == 1:
                    description = f"1 update since your last read chapter, {chapter_str}."
                elif count <= 6:
                    description = f"{count} updates since your last read chapter, {chapter_str}."
                else:
                    description = f"{count} updates since your last read chapter, {chapter_str}.\nDisplaying the 3 " \
                                  f"chapters closest to your last read chapter and the 3 newest chapters found."
                print(description + " returned status: Update Found")
                manga = {'title': series_title, 'source_name': "Kirei Cake", 'source_link': url, 'chapters': chapters,
                         'value': field_values, 'description': description,
                         'status': "Update found"}
                try:
                    manga['thumbnail'] = page_soup.find('div', class_='thumbnail').find('img')['src']
                except AttributeError:
                    print("Manga thumbnail cannot be found.")
            else:
                print("User is up to date with the latest released chapter of " + series_title + ", "
                      + chapter_str + " returned status: Up to date")
                manga = {'status': "Up to date"}
        else:
            print(f"{series_title} {chapter_str} cannot be found on the website, returned status: Failure.")
            manga = {'title': series_title, 'source_name': "Kirei Cake", 'source_link': url,
                     'chapters': [], 'value': [], 'status': "Failure",
                     'description': f"The chapter listed on your mangalist, {chapter_str}, cannot be found on the "
                                    f"website.\nChapters found: {earliest_chapter} - "
                                    f"{page_soup.find('div', class_='element').find('div', class_='title').text}. "
                                    f"\nTotal chapters: {str(total_chapters)}"}
            try:
                manga['thumbnail'] = page_soup.find('div', class_='thumbnail').find('img')['src']
            except AttributeError:
                print("Manga thumbnail cannot be found.")
        return manga
        # All conditions result in a return of the manga dict with a status variable:
        # "Update found", "Up to date" or "Failure"


async def aio_manga_details(session, url):
    # return an object that contains: Manga Description, Author Name, Number of Chapters, Latest Chapter, Status:ongoing
    async with session.get(url) as resp:
        print(resp.status)
        if resp.status != 200:
            return {'request_status': "Failure"}
        page_soup = BeautifulSoup(await resp.read(), 'html.parser')
        try:
            title = page_soup.find('div', class_='info').find('li').text.replace("Title: ", "")
        except AttributeError:
            return {"request_status": "Unable to gather information from link"}
        else:
            description = page_soup.find('div', class_='info').find('li').find_next_sibling('li').text
            print(description)
            if description == "":
                description = "Not found."
            manga = {
                'title': title, 'description': description,
                'chapters': len(page_soup.find_all('div', class_='element')),
                'request_status': "Success"
            }
            try:
                manga['cover'] = page_soup.find('div', class_='thumbnail').find('img')['src']
            except AttributeError:
                logging.info("Manga thumbnail cannot be found.")
            return manga
