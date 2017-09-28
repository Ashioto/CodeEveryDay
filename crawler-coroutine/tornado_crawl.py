import tornado.ioloop
from tornado.httpclient import AsyncHTTPClient

urls = ["http://www.baidu.com", "http://www.qq.com", "http://www.taobao.com"] * 100

def handle_response(response):
    if response.error:
        print("Error: {}".format(response.error))
    else:
        url = response.request.url
        data = response.body
        print("{}: {} bytes: {}".format(url, len(data), 1))

http_client = AsyncHTTPClient()
for url in urls:
    http_client.fetch(url, handle_response)

tornado.ioloop.IOLoop.instance().start()