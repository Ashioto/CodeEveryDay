import asyncio
import time

# link: http://www.jianshu.com/p/b5e347b3a17c
now = lambda : time.time()

async def coroutine(x):
    print('coroutine say: x', x)
    return x

start = now()

cor = coroutine(10)
loop = asyncio.get_event_loop()
task = loop.create_task(cor)
print(task)
loop.run_until_complete(task)
print(task)
print(now()-start)