import logging


async def chapter_updates(session, title, chapter, url, language="en", translator_grp="None"):
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
    :param title:
    :param language:
    :param translator_grp:
    :param session:
    :param chapter:
    :param url:
    :return:
    """
    try:
        chapter = float(chapter.split()[-1])
    except ValueError:
        logging.debug(f"{chapter} is not an acceptable value.")
        return {'status': "Failure",
                'description': f"{title}'s chapter value: {chapter} is not a numerical value."}
    else:
        offset = 0  # whoo whoo whoo
        found_stat = False
        manga_id = url.split("/")[4]
        params = f"?manga={manga_id}&order[chapter]=desc&translatedLanguage[]={language}&includes[]=scanlation_group"
        if translator_grp != "None":
            params = params + "&groups[]=" + translator_grp
        api_url = f"https://api.mangadex.org/chapter{params}"
        chapters = []
        value_field = []
        while found_stat is False:
            async with session.get(api_url) as resp:
                chapter_list_json = await resp.json()
                if not chapter_list_json['results']:
                    break
                chapter_num_list = [float(chapters['data']['attributes']['chapter']) for chapters in
                                    chapter_list_json['results']]
                if chapter in chapter_num_list:  # or chapter == chapter_num_list[-1] - 1:
                    index = chapter_num_list.index(chapter)
                    count = index + offset
                    if count < 10:
                        for elem_count in range(0, index):
                            if elem_count <= 2 or elem_count >= index - 3:
                                chapters.append(
                                    "Chapter " + chapter_list_json['results'][elem_count]['data']['attributes'][
                                        'chapter'])
                                value_field.append(
                                    f"Group: {chapter_list_json['results'][elem_count]['relationships'][0]['attributes']['name']} [Read Here]({'https://mangadex.org/chapter/' + chapter_list_json['results'][elem_count]['data']['id']}) "
                                    f"{chapter_list_json['results'][elem_count]['data']['attributes']['publishAt'].split('T')[0]}")
                    else:
                        """
                        chapters value structure: "Chapter {chapter number}"
                        value_field value structure: "Group: {scanlation group's name} [Read Here]({chapter link}) {date}"
                        for grabbing values on pages that come after the first, only the last 3 values of
                        chapters and value_field will be replaced as the first 3 are always the latest 3 updates                        
                        in the case of the next page only containing 1 or 2 older updates, the last 3 values will
                        be shifted, 5th element value in list-> 4th element's value, to accommodate the last
                        value being the oldest update                          
                        Step 1: Shift Last two values of both lists one position up, 5 -> 4, 6 -> 5
                        Step 2: Last elements of the lists will then have the "oldest" update data be added in
                        Step 3: Repeat until stop point (index) has been reached 
                        """
                        if index <= 2:
                            for elem_count in range(0, index):  # loop stops after either 1 or 2 cycles
                                chapters[3] = chapters[4]
                                chapters[4] = chapters[5]
                                value_field[3] = value_field[4]
                                value_field[4] = value_field[5]
                                chapters[5] = "Chapter " + \
                                              chapter_list_json['results'][elem_count]['data']['attributes']['chapter']
                                value_field[
                                    5] = f"Group: {chapter_list_json['results'][elem_count]['relationships'][0]['attributes']['name']} " \
                                         f"[Read Here]({'https://mangadex.org/chapter/' + chapter_list_json['results'][elem_count]['data']['id']}) " + \
                                         f"{chapter_list_json['results'][elem_count]['data']['attributes']['publishAt'].split('T')[0]}"
                        else:
                            i = 3
                            for elem_count in range(index - 3, index):
                                chapters[i] = "Chapter " + \
                                              chapter_list_json['results'][elem_count]['data']['attributes']['chapter']
                                value_field[
                                    i] = f"Group: {chapter_list_json['results'][elem_count]['relationships'][0]['attributes']['name']} " \
                                         f"[Read Here]({'https://mangadex.org/chapter/' + chapter_list_json['results'][elem_count]['data']['id']}) " + \
                                         f"{chapter_list_json['results'][elem_count]['data']['attributes']['publishAt'].split('T')[0]}"
                                i = i + 1
                    found_stat = True
                else:
                    if offset == 0:
                        for elem_count in range(0, 10):
                            if elem_count <= 2 or elem_count >= 7:
                                chapters.append(
                                    "Chapter " + chapter_list_json['results'][elem_count]['data']['attributes'][
                                        'chapter'])
                                value_field.append(
                                    f"Group: {chapter_list_json['results'][elem_count]['relationships'][0]['attributes']['name']} "
                                    f"[Read Here]({'https://mangadex.org/chapter/' + chapter_list_json['results'][elem_count]['data']['id']}) "
                                    f"{chapter_list_json['results'][elem_count]['data']['attributes']['publishAt'].split('T')[0]}")
                    else:
                        """
                        if the last read chapter is not on the current page, grab the last 3 values on current
                        page and move on. If there are less than 3 values on the current page, push the last 2 values in
                        the list up one position while adding the information into the last position, repeat until
                        completion. Make one final check to see if there are less than 10 chapters on the current page.
                        If there are < 10, break the loop. On the off-chance that the last value in the list happens to 
                        be the first chapter in the manga while also being the 10th value in the list, a 'result' check
                        at the start of the loop will immediately break the loop and skip the rest of the code. 
                        """
                        chap_count = len(chapter_list_json['results'])
                        if chap_count >= 3:
                            i = 3
                            for elem_count in range(chap_count - 3, chap_count):
                                chapters[i] = "Chapter " + \
                                              chapter_list_json['results'][elem_count]['data']['attributes'][
                                                  'chapter']
                                value_field[
                                    i] = f"Group: {chapter_list_json['results'][elem_count]['relationships'][0]['attributes']['name']} " \
                                         f"[Read Here]({'https://mangadex.org/chapter/' + chapter_list_json['results'][elem_count]['data']['id']}) " + \
                                         f"{chapter_list_json['results'][elem_count]['data']['attributes']['publishAt'].split('T')[0]}"
                                i = i + 1
                        else:
                            for elem_count in range(0, chap_count):
                                chapters[3] = chapters[4]
                                chapters[4] = chapters[5]
                                value_field[3] = value_field[4]
                                value_field[4] = value_field[5]
                                chapters[5] = "Chapter " + \
                                              chapter_list_json['results'][elem_count]['data']['attributes']['chapter']
                                value_field[
                                    5] = f"Group: {chapter_list_json['results'][elem_count]['relationships'][0]['attributes']['name']} " \
                                         f"[Read Here]({'https://mangadex.org/chapter/' + chapter_list_json['results'][elem_count]['data']['id']}) " + \
                                         f"{chapter_list_json['results'][elem_count]['data']['attributes']['publishAt'].split('T')[0]}"
                        if chap_count < 10:
                            break  # breaks loop as there will be no more values to retrieve on the next call
                    offset = offset + 10  # next http request will call the next 10 elements in the list
                    api_url = f"https://api.mangadex.org/chapter{params}&offset={offset}"
        if found_stat:
            if count > 0:
                manga = {'chapters': chapters,
                         'value': value_field,
                         'status': "Update found",
                         'update_count': count}
            else:
                manga = {'status': "Up to date"}
        else:
            manga = {'status': "Failure",
                     'description': f"{title} chapter, {chapter}, stored on your mangalist cannot be found on the "
                                    f"website. Chapters found: {chapters[-1]} - {chapters[0]}. Please verify that your "
                                    f"stored chapter value is present on the page."
                     }
        return manga


async def manga_details(session, url):
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
                'chapters': det_json['data']['attributes']['lastChapter'],
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
