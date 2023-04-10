from selenium import webdriver
import time
from selenium.webdriver.common.by import By
import re
import random
import json
from selenium.webdriver.chrome.service import Service
import requests
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.expected_conditions import invisibility_of_element
from selenium.common.exceptions import StaleElementReferenceException


# software, machine learning, technology, data, engineer
def getUrl(key_word, page):
    return f"https://www.usajobs.gov/Search/Results?k={key_word}&p={page}"

# def nextPage(wd):
#     # Wait for the blocking element to become invisible
#     wait_for_invisibility_of_element(wd, ".acsAbandonButton.acsModalBackdrop")
    
#     # Click the Next Page button
#     wd.find_element(By.CSS_SELECTOR, "#paginator > ul > li.usajobs-search-pagination__next-page-container > a").click()


def eachJobOnPage(wd):
    return wd.find_elements(By.CSS_SELECTOR, ".usajobs-search-result--core")

def jobName(job):
    return job.find_element(By.CSS_SELECTOR, "[href]").text

def jobUrl(job, wd, max_retries=5):
    retries = 0
    while retries < max_retries:
        try:
            WebDriverWait(wd, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[href]"))
            )
            return job.find_element(By.CSS_SELECTOR, "[href]").get_attribute("href")
        except StaleElementReferenceException:
            retries += 1
            time.sleep(1)  # Wait for 1 second before retrying
    raise StaleElementReferenceException("Failed to find element after maximum retries")


def saveFile(data, name):
    with open(name, 'w') as f:
        json.dump(data, f)

def wait_for_invisibility_of_element(wd, css_selector, timeout=10):
    try:
        WebDriverWait(wd, timeout).until(
            invisibility_of_element((By.CSS_SELECTOR, css_selector))
        )
    except:
        pass

def main(page, keyword):
    """
    Scrapes job listings from USAJobs.gov for a given keyword and number of pages.

    Args:
    - page (int): The number of pages to scrape.
    - keyword (str): The search term for the job listings.

    Returns:
    - None

    The function saves the scraped job listings as JSON files in the current directory. Each file contains up to 20 job listings,
    and the file names follow the format 'USJobs_<count>.json', where <count> is the number of files saved.
    """
    p = 1
    count = 0
    arr = []

    # BeautifulSoup init
    session = requests.Session()
    headers = {
            'User-Agent' : 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:46.0) Gecko/20100101 Firefox/46.0',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Connection' : 'Keep-Alive',
            'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }

    while count < page:
        service = Service(r'/Users/tingkangzhao/SeleniumDriver/chromedriver')
        wd = webdriver.Chrome(service=service)
        wd.implicitly_wait(10)
        url = getUrl(keyword, p)
        wd.get(url)
        for job in eachJobOnPage(wd):
            dic = {}
            # Selenium work
            try:
                link = jobUrl(job, wd)
            except:
                continue
            try:
                jobTitle = jobName(job)
            except:
                pass
            # BS work
            url_obj = session.get(link, headers = headers)
            bs = BeautifulSoup(url_obj.text, "html.parser")
            if not jobTitle:
                jobTitle = bs.find('h1', {'class': 'usajobs-joa-banner__title'}).text
            for i in bs.find_all('li', "usajobs-joa-summary__item usajobs-joa-summary--pilot__item margin-bottom-20"):
                children = [i for i in i.children]
                if children[1].text == "Control number":
                    job_id = [i.text for i in children[1].next_siblings][1]
            posted = bs.find("p", {"class": "usajobs-joa-summary__value usajobs-joa-summary--pilot__value"}).text[2:12]
            jobLocation = ''.join([i for i in bs.find("span", {"class": "usajobs-joa-locations__city"}).text if i != '\r' and i != '\n' and i != ' '])
            companyName = ''.join([i for i in bs.find('a', {"class": "usajobs-joa-banner__agency usajobs-joa-banner--v1-3__agency"}).text if i != '\r' and i != '\n' and i != ' '])
            jobType = bs.find('p', {"class": "usajobs-joa-summary__value usajobs-joa-summary--pilot__value", "itemprop":"employmentType"}).text
            salary = []
            for i in bs.find('p', {'class':'usajobs-joa-summary__salary salary-text-normal'}).text.split('-'):
                salary.append(''.join([j for j in i if j.isdigit()]))
            jobDescription = bs.find('div', {'id': "duties"}).text
            requirements = bs.find('div', {'id': "requirements"}).text
            fullTime, partTime = False, False
            if jobType.endswith("Full Time and Part Time"):
                fullTime, partTime = True, True
            if jobType.endswith("Full-time -"):
                fullTime, partTime = True, False
            # Feed data into dic
            dic["jobID"] = job_id
            dic["origin_search"] = "https://www.usajobs.gov/"
            dic["posted"] = posted
            dic["jobTitle"] = jobTitle
            dic["companyName"] = companyName
            dic["link"] = link
            dic["jobLocation"] = {
                "remote": "not specified",
                "city": jobLocation.split(',')[0],
                "state": jobLocation.split(',')[1] if len(jobLocation.split(',')) > 1 else None,
                "country": "US"
            }
            dic["educationRequirement"] = {
                "education": None,
                "major": None
            }
            dic["jobType"] = {
                "internship": False,
                "partTime": partTime,
                "fullTime": fullTime,
                "coop": False,
                "contract": False,
                "independent_contractor": False,
                "temporary": False,
                "oncall": False,
                "volunteer": False
            }
            dic["visaSponsorship"] = {
                "none": True,
                "cpt_opt": False,
                "h1b": False,
                "eb": False
            }
            dic["salary"] = {
                "min": int(salary[0]),
                "max": int(salary[1])
            }
            dic["benefits"] = None
            dic["requirements"] = requirements
            dic["jobDescription"] = jobDescription
            # put each job dic into arr
            arr.append(dic)
            time.sleep(random.uniform(1, 3))
        p += 1
        count += 1
        wd.quit()
        if len(arr) >= 20:
            saveFile(arr, f"USJobs_{count}.json")
            arr = []
    
main(10,  "software")
