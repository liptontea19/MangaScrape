import logging
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from itertools import groupby
from operator import itemgetter

# list search function is now deprecated


async def chapter_updates(driver: webdriver, series_title, chapter_str, url):
    """
        Checks the given Manga+ Shueisha webpage for any new chapters that come after chapter_str. Dict type object is
        returned containing the chapter number and link to the new chapters.

        :param driver: Selenium webdriver
        :param series_title: name of manga
        :param chapter_str: latest read chapter number of manga
        :param url: link to the Manga found on the Manga+ Shueisha platform
        :return manga (dict): an object with multiple fields that varies based on whether new chapters were found
         on the page
        """
    try:
        driver.get(url)
    except TimeoutException:
        print("Loading timed out.")
        logging.info("Loading timed out.")
        return {'request_status': "Failure"}
    else:
        time.sleep(1)
        description = ""
        chapter_title = []
        field_value = []
        ele_count = 1
        elem_list = driver.find_elements_by_css_selector('div.ChapterListItem-module_chapterListItem_ykICp')
        chapter_list = [elem.find_element_by_css_selector('p.ChapterListItem-module_name_3h9dj').text
                        for elem in elem_list]  # list of chapter numbers
        chapter_exist = False
        index_list = []
        if "-" in chapter_str:
            return {'status': "Failure",
                    'description': f"The chapter listed on your mangalist, {chapter_str}, cannot be found on the "
                                   f"website because it is out of bounds."}
        try:  # 5 possible outcomes depending on position of chapter_str in
            # list and whether chapter_str is even a proper value
            index = chapter_list.index(chapter_str)  # checks if curr_chap's value is in chap_list
        except ValueError:  # if not, convert the list and chapter value into integers and then try finding it again
            logging.debug(f"{chapter_str} is not in chapter_list.")
            try:
                curr_chap = float(chapter_str.strip("#"))  # "#186" -> 186
            except ValueError:
                logging.debug(f"Value {chapter_str.strip('#')} cannot be converted into an integer.")
                count = 0  # Situation 4
            else:
                float_chap_list = []
                for elem in range(0, len(chapter_list)):
                    if chapter_list[elem] == "ex" and elem > 0:
                        float_chap_list.append(float_chap_list[elem - 1] + 0.1)
                    elif (chapter_list[elem] == "ex" and elem == 0) or chapter_list[elem] == "Oneshot":
                        float_chap_list.append(0.1)
                    elif "," in chapter_list[elem]:
                        float_chap_list.append(float(chapter_list[elem].split(",")[-1]))
                    else:
                        float_chap_list.append(float(chapter_list[elem].replace("#", "")))
                count = float_chap_list[-1] - curr_chap
                if curr_chap + 1 in float_chap_list:
                    # checks if value is just one chapter behind any of the available chapters, Situation 2
                    chapter_exist = True
                    index = float_chap_list.index(curr_chap + 1)
                    for index_val in range(index, len(chapter_list)):
                        index_list.append(index_val)
                else:  # Situation 3/5
                    grouped_list = []
                    for k, g in groupby(enumerate(float_chap_list), lambda x: x[0] - x[1]):
                        grouped_list.append(list(map(itemgetter(1), g)))
                    description = f"The chapter listed on your mangalist, {chapter_str}, cannot be found on the " \
                                  f"website.\nChapters available: {grouped_list[0][0]}-{grouped_list[0][-1]} and " \
                                  f"{grouped_list[1][0]}-{grouped_list[1][-1]}\nYou are " \
                                  f"{int(grouped_list[-1][0] - curr_chap)} chapters behind the closest available chapter."
        else:  # chapter_str was found in the list
            count = len(chapter_list) - 1 - index  # how many chapters are between curr_chap and the latest one
            for index_val in range(index + 1,
                                   len(chapter_list)):  # add all chapters index's that come after curr_chap
                index_list.append(index_val)
            chapter_exist = True  # Situation 1 or 2

        for val in index_list:
            if ele_count <= 3 or ele_count >= len(index_list) - 2:
                chapter_title.append(chapter_list[val])
                comment_link = elem_list[val] \
                    .find_element_by_css_selector("a.ChapterListItem-module_commentContainer_1P6qt") \
                    .get_attribute("href")
                link = comment_link.replace("/comments", "/viewer")
                logging.debug(f"{chapter_list[val]} {link}")
                field_value.append(
                    f'[{elem_list[val].find_element_by_css_selector("p.ChapterListItem-module_title_3Id89").text}]'
                    f'({link}) | '
                    f'{elem_list[val].find_element_by_css_selector("p.ChapterListItem-module_date_xe1XF").text}')
                # field_value's value format: "[{subtitle name}]({link to chapter}) | {release date}"
            ele_count = ele_count + 1
        chapter_title.reverse()  # from Release Order ascending to descending (Top:Newest,Bottom:Oldest)
        field_value.reverse()
        if chapter_exist is True:  # Sit 1 or 2
            if count > 0:
                manga = {'chapters': chapter_title,
                         'value': field_value,
                         'thumbnail': driver.find_element_by_css_selector(
                             'img.TitleDetailHeader-module_coverImage_3rvaT').get_attribute("src"),
                         'status': "Update found",
                         'update_count': count}
            else:
                logging.debug("User is up to date with the latest released chapter of " + series_title + ", "
                              + chapter_str + " returned status: Up to date")
                manga = {'status': "Up to date",
                         'update_count': count}
        else:
            logging.info("Manga cannot be found on site.")
            if count < 0:  # occurs when given chapter is higher than the latest chapter found
                logging.debug("User's search chapter is not within the manga list.")
                description = f"The chapter listed on your mangalist, {chapter_str}, cannot be found on the website " \
                              f"because it is out of bounds. Latest chapter: {chapter_list[-1]}"
            elif count == 0:
                logging.debug(f"chapter_str (value: {chapter_str}) is not a number")
                description = f"The chapter listed on your mangalist, {chapter_str}, is not a normal value."
            manga = {'thumbnail': driver
                     .find_element_by_css_selector('img.TitleDetailHeader-module_coverImage_3rvaT')
                     .get_attribute("src"),
                     'status': "Failure",
                     'update_count': count}
            if description != "":
                manga['description'] = description

        return manga


"""
list_search planned outputs

Because of stupid licensing issues, I'm stuck having to write an algorithm that accounts for missing chapters on the 
webpage.
Variable Assignment:
Chapter #048 - newest_chapter, chap_list(-1)
Chapter #047
Chapter #046 - closest_available_chapter
Chapters #004 to #045 - missing_chapters
Chapter #003 - 
Chapter #002
Chapter #001 - oldest_chapter, chap_list(0)

Test 1: curr_chap is the latest chapter in the list
test_list = ["#001", "#002", "#003", "#046", "#047", "#048"]
Condition: if curr_chap = list(index)
curr_chap = "#048"
return chap_found = True and no index values

Test 2: curr_chap is one of the values in list 
test_list = ["#001", "#002", "#003", "#046", "#047", "#048"]
Condition: if curr_chap = list(index)
curr_chap = "#046"
return chap_found = True and list index values to the chapters that come after 46 ( 4, 5 )

Test 3: curr_chap is higher than any of the integer converted values in the list 
curr_chap = "#049"
newest_chap = chap_list(-1)
Condition: if int(curr_chap) > int(newest_chap)
return chap_found = False and no index values

Test 4: curr_chap is none of the values in list but is within the range of missing chapters 
curr_chap = "#024"
Condition: 

Test 5: curr_chap is not a number because the User is fucking stupid
curr_chap = "#06A"

Test 6: curr_chap is 1 chapter behind the highest
Condition: if int(curr_chap) + 1 = int(list(index)

flow:
Can value be found in List?
Yes: Diff in values of latest_chapter and curr_chap?
    Yes: return chapter_found = True and list = [index numbers] 
    No: return chapter_found = True and list = []
No: Where is Chapter relative to list?
    Chapter is higher than list[-1]: 
        return chapter_found = False and list = []
    Chapter is part of missing chapters:
        Is it next to closest_available_chapter(cap)?:
            return chapter_found = False and list = [cap_index]
        else:
            return chapter_found = False, list = [], 

To determine the final output, I need:
The number of chapters in between curr_chap and new_chap
The values or at least the indexes to the chapter title, subtitle and links

"""


def list_search(curr_chap, chap_list):  # returns index numbers of chapters in the list and chapter_exists = True/False
    """ returns index numbers of chapters in the list that come after curr_chap's value, how many chapters and whether
    curr_chap can be found in chap_list

    :param curr_chap: string value of read chapter number
    :param chap_list: a list of chapter numbers in "#XX" string format ordered by oldest chapter to newest chapter
    :return chapter_exists(bool):
    :return return_list(string list):
    :return diff(int):
    """
    chapter_exists = False
    return_list = []
    diff = 0
    try:
        index = chap_list.index(curr_chap)  # checks if curr_chap is any of the values in chap_list
    except ValueError:
        print(f"{curr_chap} is not in input list.")
    else:
        diff = len(chap_list) - 1 - index  # how many chapters are between curr_chap and the latest one
        """
        for index_val in range(index + 1, len(chap_list)):  # add all chapters that come after curr_chap
            return_list.append(index_val)
        """
        return_list = chap_list[index + 1:]
        chapter_exists = True
    if chapter_exists is True:
        return chapter_exists, return_list, diff
    else:
        curr_chap = int(curr_chap.strip("#"))
        new_chap_list = [ele.replace("#", "") for ele in chap_list]
        int_chap_list = list(map(int, new_chap_list))  # these 3 lines convert the list of title numbers and curr_chap
        # into integers and compare the difference between the curr_chap and the newest chapter
        diff = int_chap_list[-1] - curr_chap
        if curr_chap + 1 in int_chap_list:  # checks if value is just one chapter behind any of the available chapters
            chapter_exists = True
            index = int_chap_list.index(curr_chap + 1)
            for index_val in range(index, len(chap_list)):
                return_list.append(index_val)
        return chapter_exists, return_list, diff


async def manga_details(driver: webdriver, url):
    try:
        driver.get(url)
    except TimeoutException:
        print("Loading timed out.")
        return {'request_status': "Failure"}
    else:
        time.sleep(1)
        manga = {'request_status': "Success"}
        logging.debug("Fetching manga cover art link")
        manga['cover'] = driver.find_element_by_css_selector('img.TitleDetailHeader-module_coverImage_3rvaT')\
            .get_attribute("src")
        logging.debug("Fetching manga title")
        title = driver.find_element_by_css_selector('h1.TitleDetailHeader-module_title_Iy33M').text
        manga['title'] = title
        logging.debug("Fetching manga author's name")
        manga['author'] = driver.find_element_by_css_selector('p.TitleDetailHeader-module_author_3Q2QN').text
        logging.debug("Fetching manga description")
        manga['description'] = driver.find_element_by_class_name('TitleDetailHeader-module_overview_32fOi').text
        logging.debug("Fetching chapter list")
        chapter_list = driver.find_elements_by_css_selector('div.ChapterListItem-module_chapterListItem_ykICp')
        logging.debug("Fetching latest chapter number.")
        manga['chapters'] = chapter_list[-1].find_element_by_xpath(
            ".//div[@class='ChapterListItem-module_chapterWrapper_3CxyE']/p").text
        # manga['chapters'] has the value of the last element on the chapter list, (index: -1), which would be the
        # latest chapter found on the webpage.
        logging.debug(f"Fetching of information for {title} using $search successful")
        return manga
