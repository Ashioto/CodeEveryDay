import asyncio
import time

now = lambda : time.time()

async def do_something(x):
    print("it says: {}".format(x))
    return x

def callback(future):
    print("callback says {}".format(future.result()))

start = now()
loop = asyncio.get_event_loop()
task = asyncio.ensure_future(do_something(10))
task.add_done_callback(callback)

loop.run_until_complete(task)
print(now()-start)