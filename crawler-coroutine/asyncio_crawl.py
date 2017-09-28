import asyncio
import aiohttp

urls = ['http://www.baidu.com', 'http://www.taobao.com', 'http://www.qq.com']

@asyncio.coroutine
def call_url(url):
    response = yield from aiohttp.get(url)
    data = yield from response.text()
    print("{} : {} bytes".format(url, len(data)))
    return data

futures = [call_url(url) for url in urls]

loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.wait(futures))

print(futures)