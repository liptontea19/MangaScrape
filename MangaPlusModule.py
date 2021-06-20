import requests
from bs4 import BeautifulSoup


def chapter_search(series_title, chapter_str, link):
    series_page = requests.get(link)
    # response_code_check(series_page.status_code)  # checks for any http request failure and informs the user if there is
    chapter_read = int(chapter_str.replace("#", ""))  # removes the '#' sign from chapter_read string to convert to int
    page_soup = BeautifulSoup(series_page.content, 'html.parser')
    chapter = page_soup.find_all('div', class_='ChapterListItem-module_chapterListItem_ykICp')
    #print(page_soup.prettify())
    print(len(chapter))
