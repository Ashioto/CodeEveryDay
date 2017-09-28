#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys

default_encoding = 'utf-8'
if sys.getdefaultencoding() != default_encoding:
    reload(sys)
    sys.setdefaultencoding(default_encoding)
import asyncio

# limited task
sema_task = asyncio.Semaphore(1)
# limited connection
sema_connection = asyncio.Semaphore(11)
import aiohttp
import os

try:
    import urllib3.contrib.pyopenssl

    urllib3.contrib.pyopenssl.inject_into_urllib3()
except ImportError:
    pass
import requests

requests.adapters.DEFAULT_RETRIES = 5
import random
import re
from bs4 import BeautifulSoup


# 前段时间好蠢的，居然用随机UA，但是不换IP现在干脆试试Baiduspider
def header_making():
    header = {'User-Agent': 'Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)',
              'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
              'Accept-Encoding': 'gzip, deflate, sdch',
              'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3'}
    return header


##
# list all filename in path
##
def Get_filelist(path):
    for home, dirs, files in os.walk(path):
        for filename in files:
            yield os.path.join(home, filename)


##
# to find the biggest name
##
def File_naming(path='D:\\spiderdown3'):
    return max([int(i.split("\\")[-1].split('.')[0]) for i in Get_filelist(path)] or [1])


##
# fetch HTML
##
async def fetch_content(url):
    header = header_making()
    header['Referer'] = url
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=header, timeout=60) as response:
            return await response.text(encoding='utf-8')


##
# download picture
##
async def pic_download(path, url, targetDir='D:\\spiderdown3'):
    with(await sema_connection):
        if not os.path.isdir(targetDir):
            os.mkdir(targetDir)
        pic_dir = os.path.join(targetDir, path)
        header = header_making()
        header['Referer'] = url
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=header, timeout=60) as response:
                    with open(pic_dir, 'wb') as img:
                        while True:
                            chunk = await response.content.read(1024)
                            if not chunk:
                                break
                            img.write(chunk)
                        img.close()
                        return
        except:
            print("requests download...")
            header = header_making()
            header['Referer'] = url
            r = requests.Session()
            r.keep_alive = False
            image = r.get(url, stream=True, headers=header, timeout=60)
            if image.status_code == 200:
                image = image.content
                with open(pic_dir, 'wb') as img:
                    img.write(image)
                    img.close()
                    return
            else:
                print('download failed')
                return


##
# parse HTML
##
async def parse(url):
    with (await sema_task):
        print("start")
        soup = BeautifulSoup(await fetch_content(url), "html.parser")
        fetch_list = []
        result = []

        fetch_list = ["http://cl.gv8.xyz/" + i.get("href") for i in
                      soup.find_all("a", href=re.compile("htm_data.*?html"), id="")]
        fetch_list = sorted(set(fetch_list), key=fetch_list.index)

        tasks = [fetch_content(url) for url in fetch_list]
        pages = await asyncio.gather(*tasks)
        for page in pages:
            soupChild = BeautifulSoup(page, "html.parser")
            [result.append(linkchild.get("src")) for linkchild in
             soupChild.findAll("input", type="image", src=re.compile("https://.*?\.jpg"))]
        # de-duplicated for fetch_list
        result = sorted(set(result), key=result.index)
        tasks = [pic_download(path=str(index + File_naming()) + '.jpg', url=url) for index, url in enumerate(result)]
        print(tasks)
        await asyncio.gather(*tasks)

        return


if __name__ == '__main__':
    from time import time

    loop = asyncio.get_event_loop()
    start = time()
    tasks = [asyncio.ensure_future(parse("http://cl.gv8.xyz/thread0806.php?fid=16&search=&page=" + str(i))) for i in
             range(1, 9)]
    loop.run_until_complete(asyncio.gather(*tasks))
    end = time()
    print(end - start)
    loop.close()