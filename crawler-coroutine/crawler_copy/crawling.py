"""A simple web crawler -- class implementing crawling logic"""

import asyncio
import logging
import re
import time
import urllib.parse
import aiohttp
import cgi
import async_timeout

from asyncio import Queue
from collections import namedtuple

LOGGER = logging.getLogger(__name__)


def is_redirect(response):
    return response.status in (300, 301, 302, 303, 307)


FetchStatistic = namedtuple('FetchStatistics', [
    'url',
    'next_url',
    'status',
    'exception',
    'size',
    'content_type',
    'encoding',
    'num_urls',
    'num_new_urls'
])


class Crawler:
    """Crawl a set of URLs

    This manages two sets of URLs: 'urls' and 'done'. 'urls' is a set of
    URLs seen. 'done' is a list of 'FetchStatistics'.
    """
    def __init__(self, roots, max_tries=4, max_workers=10, loop=None):
        self.roots = roots
        self.loop = loop or asyncio.get_event_loop()
        self.max_tries = max_tries
        self.max_workers = max_workers
        self.q = Queue(loop=self.loop)
        self.seen_urls = set()
        self.done = []
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.root_domains = set()
        for root in roots:
            parts = urllib.parse.urlparse(root)
            host, port = urllib.parse.splitport(parts.netloc)
            if not host:
                continue
            if re.match(r'\A[\d\.]*\Z', host):
                self.root_domains.add(host)
            else:
                host = host.lower()
                self.root_domains.add(host)
        for root in roots:
            self.add_url(root)
        self.t0 = time.time()
        self.t1 = None

        assert self.q.qsize() > 0
        LOGGER.info("root urls are: %r", self.q)

    def close(self):
        """Close resources"""
        self.session.close()

    def add_url(self, url):
        LOGGER.debug('adding {}'.format(url))
        self.seen_urls.add(url)
        self.q.put_nowait(url)

    def record_statistic(self, fetch_statistic):
        """Record the FetchStatistic for completed/failed fetch URL"""
        self.done.append(fetch_statistic)

    async def parse_links(self, response):
        links = set()
        content_type = None
        encoding = None
        body = await response.read()

        if response.status == 200:
            content_type = response.headers.get('content-type')
            pdict = {}

            if content_type:
                content_type, pdict = cgi.parse_header(content_type)

            encoding = pdict.get('charset', 'utf-8')
            if content_type in ('text/html', 'application/xml'):
                text = body.decode(encoding)

                # Replace href with (?:href|src) to follow image links
                urls = re.findall(r'''(?i)href=["']([^\s"'<>]+)["']''', text)
                urls = set(urls)

                if urls:
                    LOGGER.info('got %r distinct urls from %r', len(urls), response.url)
                for url in urls:
                    # normalized = urllib.parse.urljoin(response.url, url)
                    # print(response.url.host, url, normalized)
                    if 'http://' in url:
                        links.add(url)

            stat = FetchStatistic(
                url=response.url,
                next_url=None,
                status=response.status,
                exception=None,
                size=len(body),
                content_type=content_type,
                encoding=encoding,
                num_urls=len(links),
                num_new_urls=len(links-self.seen_urls)
            )

            return stat, links

    async def fetch(self, url):
        """Fetch one URL"""
        tries = 0
        exception = None
        while tries < self.max_tries:
            try:
                response = await self.session.get(url, timeout=5)

                if tries > 1:
                    LOGGER.info('try %r for %r success', tries, url)
                break
            except aiohttp.ClientError as client_error:
                LOGGER.info('try %r for %r raised %r', tries, url, client_error)
                exception = client_error
            except asyncio.TimeoutError as timeout_error:
                LOGGER.info('try %r for %r raised %r', tries, url, timeout_error)
                exception = timeout_error

            tries += 1
        else:
            LOGGER.error('%r falild after %r tries', url, tries)
            self.record_statistic(FetchStatistic(
                url=url,
                next_url=None,
                status=None,
                exception=exception,
                size=0,
                content_type=None,
                encoding=None,
                num_urls=0,
                num_new_urls=0
            ))
            return

        try:
            stat, links = await self.parse_links(response)
            self.record_statistic(stat)
            for link in links.difference(self.seen_urls):
                self.q.put_nowait(link)
            self.seen_urls.update(links)
        except Exception as e:
            LOGGER.error('parse link error')
        finally:
            await response.release()

    async def work(self):
        """Process queue items forever"""
        LOGGER.info("worker start")
        while True:
            try:
                url = await self.q.get()
                assert url in self.seen_urls
                await self.fetch(url)
                self.q.task_done()
                LOGGER.info("there are %r urls in queue. %r urls have been seen.", self.q.qsize(), len(self.seen_urls))
            except asyncio.CancelledError as e:
                LOGGER.error('worker error: %r', e)
            except AssertionError as e:
                LOGGER.error('worker error: %r, %r', e, url)
            except Exception as e:
                LOGGER.error('worker another: %r', e)

    async def crawl(self):
        """Run the crawler untill all finished"""
        workers = [asyncio.ensure_future(self.work(), loop=self.loop)
                   for _ in range(self.max_workers)]
        self.t0 = time.time()
        await self.q.join()
        self.t1 = time.time()
        for w in workers:
            w.cancle()