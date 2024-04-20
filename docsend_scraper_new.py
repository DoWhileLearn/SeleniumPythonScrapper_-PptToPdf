import os
import time
import random
from PIL import Image
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
import hashlib as hash
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class DisabledDocsendLinkException(Exception):

    def __init__(self, url, msg):
        super(DisabledDocsendLinkException, self).__init__(msg)
        self.url = url

    def getUrl(self):
        return self.url

opts = webdriver.ChromeOptions()
#opts.add_argument('--headless')
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-dev-shm-usage')
# opts.add_argument('headless')
# opts.add_argument("--window-size=1920x1080")
# assert opts.headless  # Operating in headless mode
WAIT_TIME = 3

def preprocessFirstPage(browser, email, passcode):
    emailRequired = None
    passcodeRequired = None

    try:
        emailRequired = browser.find_element("id",'link_auth_form_email')
    except NoSuchElementException:
        print("Page is not requesting email")

    try:
        passcodeRequired = browser.find_element("id",'link_auth_form_passcode')
    except NoSuchElementException:
        print("Page is not requesting passcode")

    if emailRequired and emailRequired.is_displayed():
        emailRequired.send_keys(email)
    if passcodeRequired and passcodeRequired.is_displayed():
        passcodeRequired.send_keys(passcode)

    if emailRequired or passcodeRequired:
        if emailRequired and passcodeRequired:
            submitButton = browser.find_element("xpath",'//*[@id="new_link_auth_form"]/div[2]/div[3]/input')
        else:
            submitButton = browser.find_element("xpath",'//form[@id="new_link_auth_form"]//button')
        submitButton.click()
        _wait_for_page_load_v2(browser)

def _wait_for_page_load(browser):
    loadingGif = browser.find_element("class_name",'loading-gif')
    while loadingGif.is_displayed():
        time.sleep(WAIT_TIME)

def _wait_for_page_load_v2(browser, duration = WAIT_TIME):
    sleep_time = duration + random.uniform(1.0, 3.0)
    time.sleep(sleep_time)

def process_scrolling_long_screen(browser, scroll_height):
    print("process_scrolling_long_screen invoked with scroll_height:{}".format(scroll_height))
    browser.execute_script("$('#toolbar').hide();")
    slices = []
    offset = 0
    while offset < scroll_height:
        print("offset: {}".format(offset))
        browser.execute_script("window.scrollTo(0, {});".format(offset))
        file_name = "/data/screen_{}.png".format(offset)
        browser.get_screenshot_as_file(file_name)
        img = Image.open(file_name)
        slices.append(img)
        img.close
        # if os.path.exists(file_name):
            # os.remove(file_name)
        page_size = browser.execute_script("return window.innerHeight;")
        print("page size for offset:{} is {}".format(offset, page_size))
        if (offset + page_size) < scroll_height:
            offset += page_size
        else:
            delta = offset + page_size - scroll_height
            offset += delta + page_size
        _wait_for_page_load_v2(browser, 0.1)
    return slices

def process(url, passcode = None, email = None):
    resultPDFName = []
    imagelist = []
    service = Service(executable_path='D:\\chromedriver-win64\\chromedriver.exe')

    browser = webdriver.Chrome(options=opts, service=service)  # Update this line

    # Add Try Catch finally block to close the browser
    try:
        

        
        # browser = webdriver.Chrome("D:\\chromedriver.exe")  # Path to where I installed the web driver


        urlLength = len(url)
        while urlLength > 0 and url[urlLength-1] != '/':
            resultPDFName.insert(0, url[urlLength-1])
            urlLength = urlLength - 1
        pdfFile = ''.join(resultPDFName).join("11")

        browser.get(url)
        _wait_for_page_load_v2(browser)
        
        wait = WebDriverWait(browser, 10)

        emailRequired = wait.until(EC.element_to_be_clickable((By.ID, "link_auth_form_email")))
        preprocessFirstPage(browser, email, passcode)
        js = 'return Math.max( document.body.scrollHeight, document.body.offsetHeight,  document.documentElement.clientHeight,  document.documentElement.scrollHeight,  document.documentElement.offsetHeight);'
        scroll_height = browser.execute_script(js)
        print("scroll height for url: {} is {}".format(url, scroll_height))
        slices = []
        ss_document = False
        if scroll_height > 864:
            # Indicates a scrolling long file and not a presentation
            slices = process_scrolling_long_screen(browser, scroll_height)
            ss_document = True
        else:
            currentPageNum = 1
            hasNextPage = True
            while hasNextPage:
                _wait_for_page_load_v2(browser)
                file_name = "/data/screen_{}.png".format(currentPageNum)
                browser.get_screenshot_as_file(file_name)
                img = Image.open(file_name)
                slices.append(img)
                img.close
                #if os.path.exists(file_name):
                 #   os.remove(file_name)
                page_controls = browser.find_element("xpath","//*[@class='presentation-toolbar_buttons pull-right']/div").text
                print("page control"+page_controls)
                print("page controls: {}".format(page_controls))
                pg_ctrl_parts = [p.strip() for p in page_controls.split("/")]
                if pg_ctrl_parts[0] == pg_ctrl_parts[1]:
                    hasNextPage = False

                if hasNextPage:
                    nextPage = None
                    try:
                        nextPage = browser.find_element("id",'nextPageIcon')
                    except:
                        print("Reached last page")
                        hasNextPage = False
                    if nextPage:
                        nextPage.click()
                        _wait_for_page_load_v2(browser)
                        print("Moving to next screen ...")
                        currentPageNum += 1
                    else:
                        hasNextPage = False

        browser.quit()

        filePath = '/data/{}.pdf'.format(pdfFile)
        print("Capture complete, pdf creation started")
        if ss_document == True:
            screenshot = Image.new('RGB', (slices[0].size[0], scroll_height))
            offset = 0
            for img in slices:
                screenshot.paste(img, (0, offset))
                offset += img.size[1]
            file_name = '/data/{}.png'.format(pdfFile)
            screenshot.save(file_name)
            img = Image.open(file_name)
            img.save(filePath, "PDF" ,resolution=100.0, save_all=True)
            if os.path.exists(file_name):
                os.remove(file_name)
        else:
            images = []
            for img in slices:
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                images.append(img)
            images[0].save(filePath, "PDF" ,resolution=100.0, save_all=True, append_images=images[1:])

        print("Capture complete, pdf created")
        return filePath
    except Exception as e:
        print("Error:{}".format(e))
        browser.quit()
        raise e
    finally:
        browser.quit()
        

def hashstr(str):
    sha = hash.sha256()
    sha.update(bytes(str, 'utf-8'))
    return sha.hexdigest()

if __name__ == '__main__':
    urls = [
       # 'https://docsend.com/view/3w76385g7b8g5qzc',
        'https://docsend.com/view/kmbm7tseanguj4sz',
    ]

    for url in urls:
        print("hash:{}".format(hashstr(url)))
        filePath = process(url, passcode='12345678', email='arman@baerstudios.xyz')
        print(filePath)