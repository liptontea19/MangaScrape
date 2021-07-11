from bs4 import BeautifulSoup

# another page that suffers from I LIKE JAVASCRIPT SYNDROME
async def aio_chapter_search(session, series_title, chapter_str, url):
    async with session.get(url) as resp:
        print(resp.status)
        page_soup = BeautifulSoup(await resp.read(), 'html.parser')
        print(page_soup.prettify())
        chapter = page_soup.find('li', class_="wp-manga-chapter ")
        total_chapters = len(page_soup.find_all('a', class_="wp-manga-chapter "))
        chapter_exists: bool = False
        body_text = ""
        for count in range(0, total_chapters):
            chapter_element_link = chapter.find('a')['href']
            chapter_element_title = chapter.find('a')
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
                   f"list.\nNewest chapter found: {page_soup.find('li', class_='wp-manga-chapter ').text}. " \
                   f"Oldest chapter found: {earliest_chapter}. Total chapters: {str(total_chapters)}\nLink: {url}\n"