import asyncio
import sys
import logging
import time
import aiohttp

import crawling

def main():
    logging.basicConfig(level=logging.INFO)

    loop = asyncio.get_event_loop()
    roots = ['http://www.sohu.com:80']
    crawler = crawling.Crawler(roots, max_workers=10, max_tries=2, loop=loop)
    try:
        loop.run_until_complete(crawler.crawl())
    except KeyboardInterrupt:
        sys.stderr.flush()
        print('\nInterrupted\n')
    finally:
        crawler.close()
        for task in asyncio.Task.all_tasks():
            print(task.cancel())
        loop.stop()
        loop.run_forever()

        loop.close()

if __name__ == '__main__':
    main()