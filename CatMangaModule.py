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
            return f"**{series_title}**\n`{chapter_str}` cannot be found on the website. You might want to check your " \
                   f"list.\nNewest chapter found: {page_soup.find('p', class_='css-1lrrmqm e1ba5g7u2').text}. " \
                   f"Oldest chapter found: {earliest_chapter}. Total chapters: {str(total_chapters)}\nLink: {url}\n"


async def aio_manga_details(session, url):
    # return an object that contains: Manga Description, Author Name, Number of Chapters, Latest Chapter, Status:ongoing
    async with session.get(url) as resp:
        print(resp.status)
        if resp.status != 200:
            return {"status": "Request failed"}
        page_soup = BeautifulSoup(await resp.read(), 'html.parser')
        try:
            title = page_soup.find('p', class_='css-1xo73o4 e1jf7yel5').text
        except:
            return {"status": "Unable to gather information from link."}
        else:
            author_name = page_soup.find('p', class_='css-1g7ibvt e1dq2ku10').text
            description = page_soup.find('p', class_='css-fo0pm6 e1jf7yel3').text
            manga_status = page_soup.find('span', class_='css-15575wy e1jf7yel0').text
            chapter_count = len(page_soup.find_all('a', class_='css-1pfv033 e1ba5g7u0'))
            return {
                "title": title, "author": author_name, "description": description,
                "status": manga_status, "chapters": chapter_count
            }

