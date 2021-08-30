import logging
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException


async def manga_details(driver: webdriver, url):
    try:
        driver.get(url)
    except TimeoutException:
        logging.info("Failed to get url: " + url)
    else:
        time.sleep(1)
        manga = {
            'request_status': "Success",
            'title': driver.find_element_by_xpath("//div[@class='post-title']/h1").text,
            'cover': driver.find_element_by_xpath("//div[@class='summary_image']/a/img").get_attribute("src"),
            'description': driver.find_element_by_css_selector("div.summary__content.show-more").text,
            'status': driver.find_element_by_xpath("//div[@class='post-status']/div[2]/div[@class='summary-content']").text,
            'chapters': driver.find_element_by_css_selector("li.wp-manga-chapter").find_element_by_xpath("a").text
        }
        try:
            manga['author'] = driver.find_element_by_css_selector("div.author-content").text
        except NoSuchElementException:
            print("Could not locate author name.")
        try:
            manga['artist'] = driver.find_element_by_css_selector("div.artist-content").text
        except NoSuchElementException:
            print("Could not locate artist name.")
        try:
            manga['tag'] = driver.find_element_by_css_selector("div.tags-content").text
        except NoSuchElementException:
            logging.debug("No tags were found.")
        return manga


async def manga_search(driver: webdriver, url):
    pass
