import requests
import bs4
import pickle
import telebot
import logging
import os

CHANNEL_NAME = '@RuBridgeNews'
PAGE_LIST = {'Bridgesport': {'url': 'http://bridgesport.ru',
                             'encoding': 'utf-8',
                             'soup string':
                                 'section[class *= "CardSlider"] span[class = "CardSlider__ItemTitle"]',
                             'link soup string': 'section[class *= "CardSlider"] a[class="CardSlider__ItemContent"]',
                             'sign': 'bridgesport.ru', },
             'Dzen-zbb': {'url': 'https://zen.yandex.ru/id/5bfe862c042fd800aa67035b',
                          'encoding': 'utf-8',
                          'soup string': 'div[class *= "card-title"] > div[class="clamp__text-expand"]',
                          'link soup string': 'a[class="card-image-view__clickable"]',
                          'max records': 3,
                          'cat link after': '?',
                          'sign': 'Записки бриджевой блондинки', },
             'ebl': {'url': 'http://www.eurobridge.org',
                     'encoding': 'utf-8',
                     'soup string': 'div[class = "item-details"] h3',
                     'link soup string': 'div[class = "item-details"] h3 > a',
                     'sign': 'eurobridge.org', },
             'wbf': {'url': 'http://www.worldbridge.org',
                     'encoding': 'utf-8',
                     'soup string': 'div[class *= "WBF-News"] h2',
                     'link soup string': 'div[class *= "WBF-News"] h2 > a',
                     'sign': 'worldbridge.org', },
             'AKeluin': {'url': 'http://akelyin.ru',
                         'encoding': 'utf-8',
                         'soup string': 'h2',
                         'sign': 'akelyin.ru', },
             'Bridgeclub-forum': {'url': 'http://www.bridgeclub.ru/forums/index.php?showforum=16',
                                  'encoding': 'cp1251',
                                  'soup string': 'span[id^="tid-span-"]',
                                  'link soup string': 'span[id^="tid-span-"] > a',
                                  'sign': 'bridgeclub.ru: форум', },
             'Bridgeclub': {'url': 'http://www.bridgeclub.ru',
                            'encoding': 'cp1251',
                            'soup string':
                                'table[width != "100%"] > tr > td[valign != "bottom"]',
                            'link soup string': 'table[width != "100%"] > tr > td[valign != "bottom"] > a',
                            'sign': 'bridgeclub.ru', },
             'Gambler-main': {'url': 'https://www.gambler.ru/forum/index.php?showforum=4',
                              'encoding': 'cp1251',
                              'soup string':
                                  'td > a[href*="showtopic"], td > b > a[href*="showtopic"]',
                              'link soup string':
                                  'td > a[href*="showtopic"], td > b > a[href*="showtopic"]',
                              'sign': 'gambler.ru: бридж', },
             'Gambler-contest': {'url': 'https://www.gambler.ru/forum/index.php?showforum=24',
                                 'encoding': 'cp1251',
                                 'soup string':
                                     'td > a[href*="showtopic"], td > b > a[href*="showtopic"]',
                                 'link soup string':
                                     'td > a[href*="showtopic"], td > b > a[href*="showtopic"]',
                                 'sign': 'gambler.ru: турниры', },
             'Gambler-referee': {'url': 'https://www.gambler.ru/forum/index.php?showforum=26',
                                 'encoding': 'cp1251',
                                 'soup string':
                                     'td > a[href*="showtopic"], td > b > a[href*="showtopic"]',
                                 'link soup string':
                                     'td > a[href*="showtopic"], td > b > a[href*="showtopic"]',
                                 'sign': 'gambler.ru: судейство', },
             'Gambler-hupp': {'url': 'https://www.gambler.ru/forum/index.php?showforum=82',
                              'encoding': 'cp1251',
                              'soup string':
                                  'td > a[href*="showtopic"], td > b > a[href*="showtopic"]',
                              'link soup string':
                                  'td > a[href*="showtopic"], td > b > a[href*="showtopic"]',
                              'sign': 'gambler.ru: хюпп', },
             }

DEBUG_LEVEL = logging.DEBUG
DATA_FILE_NAME = 'bnews.dat'
LOG_FILE_NAME = 'bnews.log'
TELEGRAM_BOT_ID = ''

try:
    from dev_settings import *
except ImportError:
    pass


def load_page(options: dict) -> str:
    """Load page from site"""

    page = requests.get(options['url'])
    page.raise_for_status()  # Do exception if code not 400 OK
    page.encoding = options['encoding'] if 'encoding' in options else None
    return page.text


def parsing_page(page: str, soup_string: str, tag: str = "text") -> list:
    """Parsing html page and return list
        if tag not set then return text
        else return tag
    """

    # Get news
    soup = bs4.BeautifulSoup(page, 'html.parser')
    # Extract <script>
    to_extract = soup.findAll('script')
    for item in to_extract:
        item.extract()

    tag_news = soup.select(soup_string)

    # Convert news (Tag) to list of strings
    str_news = []
    for t in tag_news:
        if tag == "text":
            st = t.get_text()
        else:
            st = t[tag]
        st = st.replace('\r', '').replace('\n\n', '\n').strip()
        str_news.append(st) if st != '' else None
    return str_news


# Set script_data and script_log file name
script_dir = os.path.dirname(os.path.abspath(__file__))
script_data_file = os.path.join(script_dir, DATA_FILE_NAME)
script_log_file = os.path.join(script_dir, LOG_FILE_NAME)

logging.basicConfig(format='%(asctime)s.%(msecs)d %(levelname)s in \'%(module)s\' at line %(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=DEBUG_LEVEL,
                    filename=script_log_file)

logging.info('Bridge News Bot started')

bot = telebot.TeleBot(TELEGRAM_BOT_ID)

# Try to load old news
try:
    with open(script_data_file, 'rb') as f:
        news_records = pickle.load(f)
        logging.info('Data file loaded')
except Exception as err:
    news_records = {}
    logging.warning('Error to read {}: {}'.format(script_data_file, str(err)))

for current_page in PAGE_LIST:
    # Try to get news
    try:
        loaded_page = load_page(PAGE_LIST[current_page])
        logging.info('Read page {}: success'.format(current_page))
    except Exception as err:
        logging.warning('Can not read page {}: {}'.format(current_page, err))
        continue

    current_news = []
    nn = parsing_page(loaded_page, PAGE_LIST[current_page]['soup string'])  # list of news
    if 'max records' in PAGE_LIST[current_page]:
        del nn[PAGE_LIST[current_page]['max records']:]
    if 'link soup string' in PAGE_LIST[current_page]:
        ln = parsing_page(loaded_page, PAGE_LIST[current_page]['link soup string'], "href")  # list of links
        if 'max records' in PAGE_LIST[current_page]:
            del ln[PAGE_LIST[current_page]['max records']:]
        if 'cat link after' in PAGE_LIST[current_page]:
            ln2 = []
            for ln_link in ln:
                symbol_pos = ln_link.find(PAGE_LIST[current_page]['cat link after'])
                ln_link = ln_link[:symbol_pos] if symbol_pos > -1 else None
                ln2.append(ln_link)
            ln = ln2
    else:
        ln = [PAGE_LIST[current_page]['url']] * len(nn)
    for (n, li) in zip(nn, ln):
        if li[0:4] != 'http':  # correct relative link
            if li[0] == '/':
                li = PAGE_LIST[current_page]['url'] + li
            else:
                li = PAGE_LIST[current_page]['url'] + '/' + li
        new_el = {'news': n,
                  'sign': PAGE_LIST[current_page]['sign'],
                  'link': li, }
        current_news.append(new_el)

    # Compare news and old_news
    if current_page in news_records:
        for li in current_news:
            if not any(nr['news'] == li['news'] for nr in news_records[current_page]):  # if new news not in records
                l_with_sign = li['news'] + '\n' + '[' + li['sign'] + '](' + li['link'] + ')'
                if DEBUG_LEVEL == logging.DEBUG:
                    logging.debug('Debug channel message: {}'.format(l_with_sign))
                else:
                    try:
                        bot.send_message(CHANNEL_NAME, l_with_sign, parse_mode='Markdown',
                                         disable_web_page_preview=True)
                    except Exception as err:
                        logging.error('Error to send message to channel: {}'.format(str(err)))

    # Save news
    news_records[current_page] = current_news

# Try to save news in file
try:
    with open(script_data_file, 'wb') as f:
        pickle.dump(news_records, f)
        logging.info('Data file saved')
except Exception as err:
    logging.error('Error to write {}: {}'.format(script_data_file, str(err)))

logging.info('Bridge News Bot work done')


# TODO Разобраться с git clone на удаленном сервере, проверить тесты, улучшить читаемость переменные и добавить функций
# TODO Сделать чтобы не править в продакшене руками уровень логгирования и бот айди
# TODO Сделать закрепленное сообщение в канале чтобы было видно что бот работает и что он делает
# TODO Более длительное храниение новостей, чтобы исключить сбои
