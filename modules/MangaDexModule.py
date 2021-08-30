import time
import logging


async def chapter_updates(session, chapter, url):
    """
    1) Get manga ID from URL
    2) Send HTTP request using api_url and parameters for the specified language and the 10 latest chapters available
    3) Receive results and convert into json format
    4) Convert all chapter values into a separate array and check if url chapter param is found in array
    5) If array does not contain chapter param value, send another http request 0.5 seconds later fetching
     the next 10 chapters
    6) Loop from step 3 until no more chapters are found.
    7a) If the chapter was present in the array, get all chapter information for chapters that are lower than the
    param chapter's index. ex. Chapter 74 is 5th element in array, index = 4, get info of array elements 0 to 3.
    7b) If no more chapters are found, send a message to user that their chapter was not in the database

    Count < 6:
        Item 1
        Item 2
        Item 3
    Count > 6 and < 10: (All item values are taken from the same set)
        Item 1  Item 8
        Item 2  Item 9
        Item 3  Item 10
    Count > 10: (Count = 12)
        Item 1  Item 10 (Taken from previous http call)
        Item 2  Item 11 (1st item from set 2)
        Item 3  Item 12 (2nd item from set 2)
    :param session:
    :param chapter:
    :param url:
    :return:
    """
    chapter = float(chapter.split()[-1])
    language = "en"
    offset = 0  # whoo whoo whoo
    found_stat = False
    manga_id = url.split("/")[-1]
    params = f"?manga={manga_id}&order[chapter]=desc&translatedLanguage[]={language}"
    api_url = f"https://api.mangadex.org/chapter{params}"
    chapters = []
    value_field = []
    while found_stat is False:
        async with session.get(api_url) as resp:
            chapter_list_json = await resp.json()
            chapter_num_list = [float(chapters['data']['attributes']['chapter']) for chapters in chapter_list_json['results']]
            if chapter in chapter_num_list:  # or chapter == chapter_num_list[-1] - 1:
                index = chapter_num_list.index(chapter)
                count = index + offset
                """
                if count < 6:  # add all found values in if there are <=6 chapters found
                    for i in range(0, index):
                        chapters.append("Chapter " + chapter_list_json['results'][i]['data']['attributes']['chapter'])
                        link = "https://mangadex.org/chapter/" + chapter_list_json['results'][i]['data']['id']
                        value_field.append(f"[Read Here]({link})")
                else:
                    pass
                """
                return count
                # found_stat = True
                # break
            elif chapter == chapter_num_list[-1] - 1:
                return offset
            else:
                offset = offset + 10  # next http request will call the next 10 elements in the list
                api_url = f"https://api.mangadex.org/chapter{params}&offset={offset}"

"""
async def manga_details0(driver: webdriver.Firefox, url):  
    # Regular web-page scraper that is slower than manga_details due to using a webdriver instead of HTTP requests to
    # fetch information
    try:
        driver.get(url)
    except TimeoutException:
        return {'request_status': "Failure"}
    else:
        time.sleep(1)
        manga = {'title': WebDriverWait(driver, 10).until(EC.presence_of_element_located((
                    # By.CSS_SELECTOR, 'div.mt-4.mb-sm-2.text-h6'
                    By.CSS_SELECTOR, 'div.mt-4.mb-sm-2.title__desktop'
                    # Firefox web engine receives this element name for title
                    ))).text,
                 'request_status': "Success",
                 'status': driver.find_element_by_css_selector('span.simple-tag').text,
                 'description': WebDriverWait(driver, 10)
                     .until(EC.presence_of_element_located((By.CSS_SELECTOR, 'p.ma-0'))).text
                 }

        try:
            time.sleep(1)
            cover_url = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((
                By.CSS_SELECTOR, 'div.v-image__image.v-image__image--contain'))) \
                .value_of_css_property('background-image')
            manga['cover'] = cover_url.split('"')[1]
        except NoSuchElementException:
            logging.info("Unable to locate manga's cover page url.")
        except IndexError:
            logging.info("URL located, but unable to be retrieved.")

        # tag script
        container_names = driver.find_elements_by_css_selector('h4.mb-3')
        tag_output = []
        tag_string = ""
        for name in container_names:
            if name.text in ["Author", "Artist"]:
                creator_name = name.find_element_by_xpath('..//a/span').text
                manga[name.text.lower()] = creator_name
            elif name.text in ["Genres", "Themes"]:
                try:
                    logging.debug(f"Searching for {name.text} container")
                    tag_list = name.find_elements_by_xpath('../div/span[@class="simple-tag"]')
                    tag_output.extend(tag_list)
                except NoSuchElementException:
                    print(f"Could not locate {name.text}'s container.")
            elif name.text == "Demographic":
                try:
                    logging.debug("Searching for Demographic tags.")
                    tag_list = name.find_elements_by_xpath("..//span[@class='simple-tag']")
                    tag_output.extend(tag_list)
                except NoSuchElementException:
                    print("Could not locate Demographic tags.")
        for index in range(0, len(tag_output)):
            if index == 0:
                tag_string = tag_output[0].text
                continue
            tag_string = tag_string + ", " + tag_output[index].text
        if tag_string != "":
            manga['tag'] = tag_string
        else:
            logging.debug("No tags were found.")

        driver.find_element_by_xpath("//div[@class='selector']/following-sibling::div[2]").click()
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((
            By.CSS_SELECTOR, 'div.v-input__icon.v-input__icon--append'))).click()
        driver.find_element_by_css_selector("div.v-input--selection-controls__input").click()
        chapter = WebDriverWait(driver, 10).until(EC.presence_of_element_located((
            By.CSS_SELECTOR, 'div.d-flex.align-center.align-self-start.col-lg-2.col-12'))).text
        manga['chapters'] = chapter

        return manga
"""


async def MDAPIDetails(session, url):
    """
    Retrieves manga ID from url and feeds it into the MangaDex API to get information.
    Information is then placed in a manga Dict object. Always returns a 'request_status' field in object.

    :param session: aiohttp session instance
    :param url: url to manga page
    :return dict: Object that contains multiple key/value pairs with information on manga.
    """
    manga_id = url.split("/")[4]  # grabs Manga's ID from the back of the given URL
    api_url = "https://api.mangadex.org/manga/" + manga_id + '?includes[]=author&includes[]=artist&includes[]=cover_art'
    async with session.get(api_url) as resp:
        det_json: dict
        det_json = await resp.json()
        if det_json['result'] == "ok":
            manga = {
                'description': det_json['data']['attributes']['description']['en'],
                'request_status': "Success",
                'tags': [tags['attributes']['name']['en'] for tags in det_json['data']['attributes']['tags']],
                'author': det_json['relationships'][0]['attributes']['name'],
                'artist': det_json['relationships'][1]['attributes']['name'],
                'chapter': det_json['data']['attributes']['lastChapter'],
                'status': det_json['data']['attributes']['status'].capitalize(),
                'id': manga_id
            }
            if 'en' in det_json['data']['attributes']['title']:
                manga['title'] = det_json['data']['attributes']['title']['en']
            elif 'jp' in det_json['data']['attributes']['title']:
                manga['title'] = det_json['data']['attributes']['title']['jp']
            else:
                return {'request_status': "Failed to retrieve title."}
            cover_filename = det_json['relationships'][2]['attributes']['fileName']
            manga['cover'] = f"https://uploads.mangadex.org/covers/{manga_id}/{cover_filename}.256.jpg"
            return manga
        else:
            return {'request_status': "Failure"}
