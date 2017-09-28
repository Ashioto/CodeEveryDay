# -*-coding:utf-8-*-
"""
ayou
"""
from bs4 import BeautifulSoup as bs
import asyncio
import aiohttp
import time

#async，协程对象
async def getPage(url,res_list,callback=None):
    print(url)
    headers = {'User-Agent':'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'}
    #asyncio.Semaphore(),限制同时运行协程数量
    sem = asyncio.Semaphore(5)
    with (await sem):
        async with aiohttp.ClientSession() as session:
            async with session.get(url,headers=headers) as resp:
                #断言，判断网站状态
                assert resp.status==200
                #判断不同回调函数做处理
                if callback==grabPage:
                    body = await resp.text()
                    callback(res_list,body)
                elif callback==grabPage1:
                    body = await resp.text()
                    callback(body)
                else:
                    return await resp.text()
                #关闭请求
                session.close()

#解析页面拿到博客url
def grabPage(res_list,body):
    page = bs(body,"lxml")
    articles = page.find_all('div', attrs={'class': 'article_title'})
    for a in articles:
        x = a.find('a')['href']
        # print('http://blog.csdn.net' + x)
        res_list.add('http://blog.csdn.net' + x)

#拿到博客页面的标题
def grabPage1(body):
    page = bs(body,"lxml")
    articles = page.find("title")
    print(articles.text)

start = time.time()

#博客列表页面总页数
page_num = 4
#起始页面
page_url_base = 'http://blog.csdn.net/u013055678/article/list/'
#列表页面的列表
page_urls = [page_url_base + str(i+1) for i in range(page_num)]
#asyncio.get_event_loop()，创建事件循环
loop = asyncio.get_event_loop()
#用来储存所有博客详细页URL
ret_list = set()
#协程任务，获得所有博客详细页面并存到set中
tasks = [getPage(host,ret_list, callback=grabPage) for host in page_urls]
#在事件循环中执行协程程序
loop.run_until_complete(asyncio.gather(*tasks))

#协程任务，获得博客详细页面的标题
tasks = [getPage(url, ret_list, callback=grabPage1) for url in ret_list]
#在事件循环中执行协程程序
loop.run_until_complete(asyncio.gather(*tasks))

#关闭事件循环
loop.close()

print("Elapsed Time: %s" % (time.time() - start))
