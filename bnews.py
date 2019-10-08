import requests
import bs4
import pickle
import telebot
import logging
import os

CHANNEL_NAME = '@RuBridgeNews'
PAGE_LIST = {'Bridgesport': {'url': 'http://bridgesport.ru',
                             'encoding': 'cp1251',
                             'soup string':
                                 'table[class = "contentpaneopen"] td[valign = "top"][class != "createdate"]',
                             'sign': '[bridgesport.ru](http://bridgesport.ru)', },
             'ebl': {'url': 'http://www.eurobridge.org',
                     'encoding': 'utf-8',
                     'soup string': 'div[class = "item-details"] h3',
                     'sign': '[eurobridge.org](http://www.eurobridge.org)', },
             'wbf': {'url': 'http://www.worldbridge.org',
                     'encoding': 'utf-8',
                     'soup string': 'div[class *= "WBF-News"] h2',
                     'sign': '[worldbridge.org](http://www.worldbridge.org)', },
             'AKeluin': {'url': 'http://akelyin.ru',
                                'encoding': 'utf-8',
                                'soup string': 'h2',
                                'sign': '[akelyin.ru](http://akelyin.ru)', },
             'Bridgeclub-forum': {'url': 'http://www.bridgeclub.ru/forums/index.php?showforum=16',
                                  'encoding': 'cp1251',
                                  'soup string': 'span[id^="tid-span-"]',
                                  'sign': '[bridgeclub.ru: Форум] \
                                         (http://www.bridgeclub.ru/forums/index.php?showforum=16)', },
             'Bridgeclub': {'url': 'http://www.bridgeclub.ru',
                            'encoding': 'cp1251',
                            'soup string':
                                'table[width != "100%"] > tr > td[valign != "bottom"]',
                            'sign': '[bridgeclub.ru](http://http://www.bridgeclub.ru)', },
             'Gambler-main': {'url': 'https://www.gambler.ru/forum/index.php?showforum=4',
                              'encoding': 'cp1251',
                              'soup string':
                                  'td > a[href*="showtopic"], td > b > a[href*="showtopic"]',
                              'sign': '[gambler.ru: Бридж](https://www.gambler.ru/forum/index.php?showforum=4)', },
             'Gambler-contest': {'url': 'https://www.gambler.ru/forum/index.php?showforum=24',
                                 'encoding': 'cp1251',
                                 'soup string':
                                     'td > a[href*="showtopic"], td > b > a[href*="showtopic"]',
                                 'sign':
                                     '[gambler.ru: Турниры](https://www.gambler.ru/forum/index.php?showforum=24)', },
             'Gambler-referee': {'url': 'https://www.gambler.ru/forum/index.php?showforum=26',
                                 'encoding': 'cp1251',
                                 'soup string':
                                     'td > a[href*="showtopic"], td > b > a[href*="showtopic"]',
                                 'sign':
                                     '[gambler.ru: Cудейство](https://www.gambler.ru/forum/index.php?showforum=82)', },
             'Gambler-hupp': {'url': 'https://www.gambler.ru/forum/index.php?showforum=82',
                              'encoding': 'cp1251',
                              'soup string':
                                  'td > a[href*="showtopic"], td > b > a[href*="showtopic"]',
                              'sign': '[gambler.ru: Хюпп](https://www.gambler.ru/forum/index.php?showforum=82)', },
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


def parsing_page(page: str, options: dict) -> list:
    """Parsing html page and return list of news"""

    # Get news
    soup = bs4.BeautifulSoup(page, 'html.parser')
    # Extract <script>
    to_extract = soup.findAll('script')
    for item in to_extract:
        item.extract()

    tag_news = soup.select(options['soup string'])

    # Convert news (Tag) to list of strings
    str_news = []
    for t in tag_news:
        st = t.get_text()
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

    current_news = parsing_page(loaded_page, PAGE_LIST[current_page])

    # Compare news and old_news
    if current_page in news_records:
        for l in current_news:
            if l not in news_records[current_page]:
                l_with_sign = l + '\n' + PAGE_LIST[current_page]['sign']
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

# TODO Сделать чтобы не править в продакшене руками уровень логгирования и бот айди
# TODO Сделать закрепленное сообщение в канале чтобы было видно что бот работает и что он делает
# TODO Сделать переход с сообщения Телеграм сразу внутрь новости
# TODO Ьолее длительное храниение новостей, чтобы исключить сбои