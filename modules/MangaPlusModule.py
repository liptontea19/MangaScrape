import logging
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException


async def aio_chapter_search(driver: webdriver, series_title, chapter_str, url):
    try:
        driver.get(url)
    except TimeoutException:
        print("Loading timed out.")
        logging.info("Loading timed out.")
        return {'request_status': "Failure"}
    else:
        time.sleep(1)
        chapter_title = []
        chapter_list = []
        field_value = []
        ele_count = 1
        elem_list = driver.find_elements_by_css_selector('div.ChapterListItem-module_chapterListItem_ykICp')
        for elem in elem_list:
            chapter_list.append(elem.find_element_by_css_selector('p.ChapterListItem-module_name_3h9dj').text)

        chapter_exist, index_list, count = list_search(chapter_str, chapter_list)
        for val in index_list:
            if ele_count <= 3 or ele_count >= len(index_list) - 2:
                # only appends the first 3 and last 3 elements, if theres only 6,
                # it'll append all 6 values since they pass the condition
                chapter_title.append(chapter_list[val])
                comment_link = elem_list[val] \
                    .find_element_by_css_selector("a.ChapterListItem-module_commentContainer_1P6qt") \
                    .get_attribute("href")
                link = comment_link.replace("/comments", "/titles")
                logging.debug("{chapter_list[val]} {link}")
                field_value.append(
                    f'[{elem_list[val].find_element_by_css_selector("p.ChapterListItem-module_title_3Id89").text}]'
                    f'({link}) | '
                    f'{elem_list[val].find_element_by_css_selector("p.ChapterListItem-module_date_xe1XF").text}')
            ele_count = ele_count + 1
        chapter_title.reverse()
        field_value.reverse()
        if chapter_exist is True:
            if count > 0:
                if count == 1:
                    description = f"1 update since your last read chapter, {chapter_str}."
                elif count <= 6:
                    print(f"{count} updates found.")
                    description = f"{count} updates since your last read chapter, {chapter_str}."
                else:
                    description = f"{count} updates since your last read chapter, {chapter_str}.\nDisplaying the 3 " \
                                  "chapters closest to your last read chapter and the 3 newest chapters found."
                manga = {'title': series_title, 'source_name': "MANGAPlus by SHUEISHA", 'source_link': url,
                         'chapters': chapter_title, 'value': field_value, 'description': description,
                         'thumbnail': driver.find_element_by_css_selector(
                             'img.TitleDetailHeader-module_coverImage_3rvaT').get_attribute("src"),
                         'status': "Update found"}
            else:
                print("User is up to date with the latest released chapter of " + series_title + ", "
                      + chapter_str + " returned status: Up to date")
                manga = {'status': "Up to date"}

        else:
            print("Manga cannot be found on site.")
            if count < 0:  # inform user that their chapter shouldn't exist yet.
                print("Value is out of bounds.")
                logging.debug("User's search chapter is not within the manga list.")
                description = f"The chapter listed on your mangalist, {chapter_str}, cannot be found on the website " \
                              f"because it is out of bounds. Latest chapter: {chapter_list[-1]}"
            else:
                description = f"The chapter listed on your mangalist, {chapter_str}, cannot be found on the " \
                              f"website.\nChapters available: [start_val]-[break_val_1] and [break_val_2]-[end_val]\n" \
                              f"You are [diff] behind the closest available chapter []"
            manga = {'title': series_title, 'source_name': "MANGAPlus by SHUEISHA", 'source_link': url,
                     'thumbnail': driver
                         .find_element_by_css_selector('img.TitleDetailHeader-module_coverImage_3rvaT')
                         .get_attribute("src"),
                     'chapters': [], 'value': [], 'status': "Failure",
                     'description': description}
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


def list_search(curr_chap, chap_list):  # returns index numbers of chapters in the list and chapter_found = True/False
    chapter_exists = False
    return_list = []
    diff = 0
    try:
        index = chap_list.index(curr_chap)  # checks if curr_chap is any of the values in chap_list
    except ValueError:
        print(f"{curr_chap} is not in input list.")
    else:
        diff = len(chap_list) - 1 - index
        for index_val in range(index + 1, len(chap_list)):
            return_list.append(index_val)
        chapter_exists = True
    if chapter_exists is True:
        return chapter_exists, return_list, diff
    else:
        curr_chap = int(curr_chap.strip("#"))
        new_chap_list = [ele.replace("#", "") for ele in chap_list]
        int_chap_list = list(map(int, new_chap_list))
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
        logging.debug("Fetching manga cover art link")
        cover = driver.find_element_by_css_selector('img.TitleDetailHeader-module_coverImage_3rvaT').get_attribute(
            "src")
        logging.debug("Fetching manga title")
        title = driver.find_element_by_css_selector('h1.TitleDetailHeader-module_title_Iy33M').text
        logging.debug("Fetching manga author's name")
        author_name = driver.find_element_by_css_selector('p.TitleDetailHeader-module_author_3Q2QN').text
        logging.debug("Fetching manga description")
        description = driver.find_element_by_class_name('TitleDetailHeader-module_overview_32fOi').text
        logging.debug("Fetching chapter list")
        chapter_list = driver.find_elements_by_css_selector('div.ChapterListItem-module_chapterListItem_ykICp')
        total_chapters_on_page = len(chapter_list)
        logging.debug("Fetching latest chapter number.")
        latest_chapter_num = chapter_list[total_chapters_on_page - 1].find_element_by_xpath(
            ".//div[@class='ChapterListItem-module_chapterWrapper_3CxyE']/p").text
        manga = {'title': title,
                 'author': author_name,
                 'request_status': "Success",
                 'description': description,
                 'chapters': latest_chapter_num.replace("#", ""),
                 'cover': cover}
        logging.info(f"Fetching of information for {title} using $search successful")
        return manga
