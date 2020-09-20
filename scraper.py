from bs4 import BeautifulSoup
import requests

from time import sleep
from datetime import datetime
from random import randint
import os.path

import pandas

import smtplib


# see http://www.networkinghowtos.com/howto/common-user-agent-list/
USER_AGENT_HEADER = ({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
                      'Accept-Language':'en-US, en, it-IT;q=0.5'})

# used file paths
XL_LOG_PATH = 'search_history/search_history.xlsx'
CSV_FILE = 'tracker_products.csv'
PROXY_FILE = 'res/http_proxies.txt'


def delay() -> None:    # set a pseudo random delay
    sleep(randint(15, 30))
    return None


def set_proxy() -> list:    # copy proxies from file to a list
    proxy_list = []

    with open(PROXY_FILE) as proxies_file:
        proxy_list = proxies_file.readlines()

    return proxy_list


def set_client(url) -> requests.Response:   # opens connection
    proxies = set_proxy()

    index = randint(0, len(proxies) - 1)
    proxy = { 'http': f'http://{proxies[index][:-1]}' }

    print(f'>>> Setting proxy {{ {proxies[index][:-1]} }}')

    return requests.get(url, headers=USER_AGENT_HEADER, proxies=proxy)


# create xlsx table if it's not already there
if not os.path.isfile(XL_LOG_PATH):
    wb = openpyxl.Workbook()
    wb.save(XL_LOG_PATH)
    print('>>> Created template table\n\n')
    wb.close()


def scrape():
    tracker = pandas.read_csv(CSV_FILE, sep=',')
    prod_urls = tracker.url
    tracker_log = pandas.DataFrame()

    for x, url in enumerate(prod_urls):
        print(f'>>> Scraping \'{tracker.name[x]}\'')

        page = set_client(url)
        print(f'>>> Status code: {page.status_code}')

        while page.status_code != 200:
            print('>>> Error, page cannot be reached!')
            delay()
            page = set_client()

        soup = BeautifulSoup(page.content, features='lxml')

        # product title
        title = soup.find(id='productTitle').get_text().strip()

        # product price
        try:
            price = soup.find(id='priceblock_ourprice') or soup.find(id='priceblock_saleprice') or soup.find(id='priceblock_dealprice')
            price = float(price.get_text().replace('.', '').replace('€', '').replace(',', '.').strip())
        except:
            price = ''
            print(f'>>> No price was found for {tracker.name[x]}')

        # check if there is 'Out of stock'
        try:
            soup.select('#availability .a-color-state')[0].get_text().strip()
            stock = 'Out of Stock'
        except:
            # check if there is 'Out of stock' at another possible position
            try:
                soup.select('#availability .a-color-price')[0].get_text().strip()
                stock = 'Out of Stock'
            except:
                stock = 'Available'

        log = pandas.DataFrame({
            'date': datetime.now().strftime('%Y-%m-%d %Hh%Mm').replace('h',':').replace('m',''),
            'name': tracker.name[x],
            'url': url,
            'title': title,
            'buy_below': tracker.buy_below[x],
            'price': price,
            'stock': stock
        }, index=[x])

        tracker_log = tracker_log.append(log)
        print(f'>>> Appended to dataframe')

        print('>>> Sleeping...\n')
        delay()


    search_history = pandas.read_excel(XL_LOG_PATH)
    df = search_history.append(tracker_log, sort=False)

    df.to_excel(XL_LOG_PATH, index=False)
    print('>>> Finished scraping')


scrape()