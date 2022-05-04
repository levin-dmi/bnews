import requests
import bs4
import pickle
import telebot
import logging
import os
import yaml


def load_page(options: dict) -> str:
    """Load page from site"""
    user_agent = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko)'
                 'Chrome/50.0.2661.102 Safari/537.36')
    headers = {'User-Agent': user_agent}
    page = requests.get(options['url'], headers=headers)
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


script_dir = os.path.dirname(os.path.abspath(__file__))
script_data_file = os.path.join(script_dir, 'bnews.dat')
script_log_file = os.path.join(script_dir, 'bnews.log')
script_config_file = os.path.join(script_dir, 'config.yaml')

# Load configuration file
with open(script_config_file, encoding='utf-8') as fh:
    loaded_config = yaml.load(fh, Loader=yaml.FullLoader)

# Set log level and start logging
DEBUG_LEVEL = logging.DEBUG
if 'log_level' in loaded_config:
    if loaded_config['log_level'] == 'info':
        DEBUG_LEVEL = logging.INFO
    elif loaded_config['log_level'] == 'error':
        DEBUG_LEVEL = logging.ERROR
logging.basicConfig(format='%(asctime)s.%(msecs)d %(levelname)s in \'%(module)s\' at line %(lineno)d: %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S',
                    level=DEBUG_LEVEL,
                    filename=script_log_file)
logging.info('Bot started')

#  Set telegram parameters
try:
    CHANNEL_NAME = loaded_config['telegram']['channel_name']
    TELEGRAM_BOT_ID = loaded_config['telegram']['telegram_bot_id']
    TELEGRAM_ON = True
except KeyError:
    TELEGRAM_ON = False

#  Load page list
try:
    PAGE_LIST = loaded_config['pages']
except KeyError:
    logging.error("Can't loading pages list from config file")
    raise SystemExit(1)

if TELEGRAM_ON:
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
                  'sign': current_page,
                  'link': li, }
        current_news.append(new_el)

    # Compare news and old_news
    if current_page in news_records:
        for li in current_news:
            if not any(nr['news'] == li['news'] for nr in news_records[current_page]):  # if new news not in records
                l_with_sign = li['news'] + '\n' + '[' + li['sign'] + '](' + li['link'] + ')'
                if not TELEGRAM_ON:
                    logging.info('Debug channel message: {}'.format(l_with_sign))
                else:
                    try:
                        bot.send_message(CHANNEL_NAME, l_with_sign, parse_mode='Markdown',
                                         disable_web_page_preview=True)
                    except Exception as err:
                        logging.error('Error to send message to channel: {}'.format(str(err)))

    else:
        for li in current_news:
            l_with_sign = li['news'] + '\n' + '[' + li['sign'] + '](' + li['link'] + ')'
            logging.info('New chanel added with message: {}'.format(l_with_sign))
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

# TODO Обновить requirements
# TODO Разобраться с git clone на удаленном сервере, проверить тесты, улучшить читаемость переменные и добавить функций
# TODO Сделать чтобы не править в продакшене руками уровень логгирования и бот айди
# TODO Сделать закрепленное сообщение в канале чтобы было видно что бот работает и что он делает
# TODO Более длительное храниение новостей, чтобы исключить сбои
