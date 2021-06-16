import requests
import string
from bs4 import BeautifulSoup

def chapter_search(series_title, chapter_str, link):
    series_page = requests.get(link)
    # response_code_check(series_page.status_code)  # checks for any http request failure and informs the user if there is
    chapter_read = int(chapter_str.strip(string.ascii_letters).replace(" ", ""))

