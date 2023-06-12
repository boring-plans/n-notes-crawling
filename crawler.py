import os
import datetime
import json
import re
import time
from pathlib import Path
from typing import List
import traceback

import schedule
import PyRSS2Gen
import requests
import tqdm
from bs4 import BeautifulSoup

BASE_URL = 'https://n-notes.tkzt.cn'
ARCHIVES = ['/notes', '/boring-plans', '/cheap-talks']
MAX_ABSTRACT = 150
DIST_DIR = 'dist'
RSS_FILENAME = 'feed.xml'
BLOGS_JSON_FILENAME = 'blogs.json'


class proxy:
    
    def __enter__(self):
        os.system('/etc/clash/start.sh start')
    
    
    def __exit__(self, *args):
        os.system('/etc/clash/start.sh stop')


def exec_with_retrying(fn, retry_times=3, retry_interval=3.7, message_when_error=''):
    retrying = 0
    result = None
    while retrying<=retry_times:
        try:
            result = fn()
            break
        except:
            print(message_when_error)
            traceback.print_exc()
            time.sleep(retry_interval)
            retrying += 1
    return result


def crawl() -> List[dict]:
    articles = []
    proxies = {
        'http': 'http://127.0.0.1:7890',
        'https': 'http://127.0.0.1:7890',
    }
    for archive in ARCHIVES:
        print(f'\nCrawling {archive}..')

        response = exec_with_retrying(
            lambda :requests.get(BASE_URL + archive, proxies=proxies),
            message_when_error=f'Failed to fetch {archive}'
        )

        if response:
            soup = BeautifulSoup(response.text, "html.parser")

            for link in tqdm.tqdm(soup.find_all('a')):
                href = link['href']
                if href.startswith('/') and href.endswith('html'):
                    full_url = BASE_URL + href

                    _response = exec_with_retrying(
                        lambda :requests.get(full_url, proxies=proxies),
                        message_when_error=f'Failed to fetch {link}'
                    )

                    if _response:
                        _soup = BeautifulSoup(_response.text, 'html.parser')

                        title = _soup.select_one('.vp-doc > h1')
                        content = _soup.select_one('main')
                        date = _soup.select_one('.info .info-text')

                        if title and content and date:
                            title_text = re.sub(r'\s#$', '', title.text)
                            if not any(map(lambda a: a['title']==title_text, articles)):
                                articles.append({
                                    'title': title_text,
                                    'link': full_url,
                                    'description': content.prettify(),
                                    'pubDate': datetime.datetime(
                                        *map(lambda x: int(x), date.text.split('-'))
                                    ) if '-' in date.text else None,
                                    'guid': PyRSS2Gen.Guid(full_url)
                                })
                time.sleep(1.2)
    return articles


def gen_rss(articles: List[dict]) -> None:
    rss = PyRSS2Gen.RSS2(
        title='N Notes',
        description='以有涯隨無涯，殆已！已而為知者，殆而已矣！是的，这是一个博客网站。',
        link=BASE_URL,
        lastBuildDate=datetime.datetime.now(),
        items=map(lambda a: PyRSS2Gen.RSSItem(**a), articles),
    )

    directory = Path(DIST_DIR)
    directory.mkdir(exist_ok=True)
    with open(directory / RSS_FILENAME, 'w', encoding='utf-8') as f:
        rss.write_xml(f, encoding='utf-8')


def gen_json(articles: List[dict]) -> None:
    directory = Path(DIST_DIR)
    directory.mkdir(exist_ok=True)
    with open(directory / BLOGS_JSON_FILENAME, 'w', encoding='utf-8') as f:
        f.write(json.dumps(list(map(
            lambda a: {
                'title': a['title'],
                'date': a['pubDate'].strftime('%Y-%m-%d') if a['pubDate'] else '旧时',
                'link': a['link']
            }, articles)), ensure_ascii=False))


def update_repo():
    time.sleep(3.7)
    os.system('./update_repo.sh')


def crawling_job():
    with proxy():
        articles = crawl()
        if articles:
            gen_rss(articles)
            gen_json(articles)
            update_repo()
        else:
            print("Failed to crawl articles.")

def schedule_job():
    schedule.every().day.at("14:23").do(crawling_job)
    print('Job initialized.')
    
    while True:
        schedule.run_pending()
        time.sleep(3.7)


if __name__ == '__main__':
    schedule_job()
