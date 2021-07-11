import logging

from bs4 import BeautifulSoup


async def aio_chapter_search(session, series_title, chapter_str, url):
    async with session.get(url) as resp:
        print(resp.status)
        page_soup = BeautifulSoup(await resp.read(), 'html.parser').find('div', class_="css-1bgihxk ea6kzkd0")
        chapter = page_soup.find('a', class_="css-1pfv033 e1ba5g7u0")
        total_chapters = len(page_soup.find_all('a', class_="css-1pfv033 e1ba5g7u0"))
        chapter_exists: bool = False
        body_text = ""
        for count in range(0, total_chapters):
            chapter_element_link = "https://catmanga.org" + chapter['href']
            chapter_element_title = chapter.find('p', class_="css-1lrrmqm e1ba5g7u2")
            if chapter_element_title.text == chapter_str:
                chapter_exists = True
                break
            # chapter_element_subtitle = chapter_element_title.next_sibling
            print(f"{chapter_element_title.text}: {chapter_element_link}")
            body_text = f"\n{chapter_element_title.text}: {chapter_element_link}" + body_text
            chapter = chapter.next_sibling
            earliest_chapter = chapter_element_title.text
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
            return f"**{series_title}**\n`{chapter_str}` cannot be found on the website. You might want to check your "\
                   f"list.\nNewest chapter found: {page_soup.find('p', class_='css-1lrrmqm e1ba5g7u2').text}. " \
                   f"Oldest chapter found: {earliest_chapter}. Total chapters: {str(total_chapters)}\nLink: {url}\n"


async def aio_chapter_search2(session, series_title, chapter_str, url):
    async with session.get(url) as resp:
        print(resp.status)
        page_soup = BeautifulSoup(await resp.read(), 'html.parser')
        chapter = page_soup.find('a', class_="css-1pfv033 e1ba5g7u0")
        total_chapters = len(page_soup.find_all('a', class_="css-1pfv033 e1ba5g7u0"))
        chapter_exists: bool = False
        chapters = []
        value_field = []
        for count in range(0, total_chapters):
            chapter_title = chapter.find('p', class_="css-1lrrmqm e1ba5g7u2").text
            if chapter_title == chapter_str:
                chapter_exists = True
                if count > 6:
                    for cnt in range(5, 2, -1):
                        chapter = chapter.previous_sibling
                        chapters[cnt] = chapter.find('p', class_="css-1lrrmqm e1ba5g7u2").text
                        # chp_links[cnt] = "https://catmanga.org" + chapter['href']
                        value_field[cnt] = "https://catmanga.org" + chapter['href']
                    print(chapters)
                break
            if count < 6:  # stop appending after the 6th element
                chapters.append(chapter_title)
                # chp_links.append("https://catmanga.org" + chapter['href'])
                link = "https://catmanga.org" + chapter['href']
                value_field.append(f"[Read here]({link})")
            earliest_chapter = chapter_title
            chapter = chapter.next_sibling
        if chapter_exists:
            print("Chapter exists")
            if count > 0:
                if count == 1:
                    description = f"1 update since your last read chapter, {chapter_str}."
                elif count <= 6:
                    description = f"{count} updates since your last read chapter, {chapter_str}."
                else:
                    description = f"{count} updates since your last read chapter, {chapter_str}.\nDisplaying the 3 " \
                                  "chapters closest to your last read chapter and the 3 newest chapters found."
                print(description + " returned status: Update Found")
                manga = {'title': series_title, 'source_name': "Cat Manga", 'source_link': url, 'chapters': chapters,
                         'value': value_field, 'description': description,
                         'thumbnail': page_soup.find('img', class_='e1jf7yel7 css-1jarxog e1je4q6n0')['src'],
                         'status': "Update found"}
            else:
                print("User is up to date with the latest released chapter of " + series_title + ", "
                      + chapter_str + " returned status: Up to date")
                manga = {'status': "Up to date"}
        else:
            print(f"{series_title} {chapter_str} cannot be found on the website, returned status: Failure.")
            manga = {'title': series_title, 'source_name': "Cat Manga", 'source_link': url,
                     'thumbnail': page_soup.find('img', class_='e1jf7yel7 css-1jarxog e1je4q6n0')['src'],
                     'chapters': [], 'value': [], 'status': "Failure",
                     'description': f"The chapter listed on your mangalist, {chapter_str}, cannot be found on the "
                                    f"website.\nChapters found: {earliest_chapter} - "
                                    f"{page_soup.find('p', class_='css-1lrrmqm e1ba5g7u2').text}. "
                                    f"\nTotal chapters: {str(total_chapters)}"}
        return manga
    # todo find a way to get the break in chapters and display it.


async def aio_manga_details(session, url):
    # return an object that contains: Manga Description, Author Name, Number of Chapters, Latest Chapter, Status:ongoing
    async with session.get(url) as resp:
        print(resp.status)
        if resp.status != 200:
            return {'request_status': "Failure"}
        page_soup = BeautifulSoup(await resp.read(), 'html.parser')
        try:
            title = page_soup.find('p', class_='css-1xo73o4 e1jf7yel5').text
        except AttributeError:
            return {'request_status': "Unable to gather information from link"}
        else:
            manga = {'title': title, 'request_status': "Success",
                     'author': page_soup.find('p', class_='css-1g7ibvt e1dq2ku10').text,
                     'description': page_soup.find('p', class_='css-fo0pm6 e1jf7yel3').text,
                     'chapters': len(page_soup.find_all('a', class_='css-1pfv033 e1ba5g7u0')),
                     'cover': page_soup.find('img', class_='e1jf7yel7 css-1jarxog e1je4q6n0')['src']}
            try:
                manga['status'] = page_soup.find('span', class_='css-15575wy e1jf7yel0').text.replace("• ", "")
            except AttributeError:
                logging.info("Unable to get manga's release status.")
            try:
                tag = page_soup.find('div', class_='css-1cls7c6 eibv1gc1')
                tags = tag.text
                max_range = len(page_soup.find_all('div', class_='css-1cls7c6 eibv1gc1'))
                for b in range(1, max_range):
                    tag = tag.next_sibling
                    tags = tags + ", " + tag.text
                manga['tag'] = tags
            except AttributeError:
                print("No tags found")
                logging.info("Unable to get manga's genre tags")
            return manga
