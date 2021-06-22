from bs4 import BeautifulSoup


async def aio_chapter_search(session, series_title, chapter_str, url):
    async with session.get(url) as resp:
        print(resp.status)
        page_soup = BeautifulSoup(await resp.read(), 'html.parser').find('div', class_="css-1bgihxk ea6kzkd0")
        print(page_soup.prettify())
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
            body_text = body_text + f"\n{chapter_element_title.text}: {chapter_element_link}"
            chapter = chapter.next_sibling
            earliest_chapter = chapter_element_title.text
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
                   f"list.\nNewest chapter found: {page_soup.find('p', class_='css-1lrrmqm e1ba5g7u2').text}. " \
                   f"Oldest chapter found: {earliest_chapter}. Total chapters: {str(total_chapters)}\nLink: {url}"


async def aio_manga_details(session, url):
    # return an object that contains: Manga Description, Author Name, Number of Chapters, Latest Chapter, Status:ongoing
    async with session.get(url) as resp:
        print(resp.status)
        page_soup = BeautifulSoup(await resp.read(), 'html.parser')

