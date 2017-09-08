from queue import Queue
import socket
import select

class Task:
	taskid = 0
	def __init__(self, target):
		Task.taskid += 1
		self.tid = Task.taskid
		self.target = target
		self.sendval = None
	def run(self):
		return self.target.send(self.sendval)

class Scheduler:
	def __init__(self):
		self.ready = Queue()
		self.taskmap = {}
		self.exit_waiting = {}

		self.read_waiting = {}
		self.write_waiting = {}

	def new(self, target):
		newtask = Task(target)
		self.taskmap[newtask.tid] = newtask
		self.schedule(newtask)
		return newtask.tid

	def schedule(self, task):
		self.ready.put(task)

	def exit(self, task):
		del self.taskmap[task.tid]
		print('Task %d terminated.' % task.tid)
		# Notify other tasks waiting for exit
		for task in self.exit_waiting.pop(task.tid, []):
			self.schedule(task)

	def waitforexit(self, task, waittid):
		if waittid in self.taskmap:
			self.exit_waiting.setdefault(waittid, []).append(task)
			return True
		else:
			return False

	def waitforread(self, task, fd):
		self.read_waiting[fd] = task

	def waitforwrite(self, task, fd):
		self.write_waiting[fd] = task

	def iopool(self, timeout):
		if self.read_waiting or self.write_waiting:
			r, w, e = select.select(self.read_waiting, self.write_waiting, [], timeout)
			for fd in r: self.schedule(self.read_waiting.pop(fd))
			for fd in w: self.schedule(self.write_waiting.pop(fd))

	def iotask(self):
		while True:
			if self.ready.empty():
				self.iopool(None)
			else:
				self.iopool(0)
		yield

	def mainloop(self):
		self.new(self.iotask())
		while self.taskmap:
			task = self.ready.get()
			try:
				result = task.run()
				if isinstance(result, SystemCall):
					result.task = task
					result.sched = self
					result.handle()
					continue
			except StopIteration:
				self.exit(task)
				continue
			self.schedule(task)	

class SystemCall:
	def __init__(self):
		pass

	def handle(self):
		pass


class GetTid(SystemCall):
	def handle(self):
		self.task.sendval = self.task.tid
		self.sched.schedule(self.task)

def ex2():
	def foo():
		for _ in range(10):
			print("I'am foo")
			yield

	def bar():
		for _ in range(15):
			print("I'am bar")
			yield

	sche = Scheduler()
	sche.new(foo())
	sche.new(bar())
	sche.mainloop()

def ex3():
	def foo():
		mytid = yield GetTid()
		for _ in range(5):
			print("I'am foo.", mytid)
			yield

	def bar():
		mytid = yield GetTid()
		for _ in range(10):
			print("I'am bar.", mytid)
			yield

	sched = Scheduler()
	sched.new(foo())
	sched.new(bar())
	sched.mainloop()

class NewTask(SystemCall):
	def __init__(self, target):
		self.target = target
	def handle(self):
		tid = self.sched.new(self.target)
		self.task.sendval = tid
		self.sched.schedule(self.task)

class KillTask(SystemCall):
	def __init__(self, tid):
		self.tid = tid
	def handle(self):
		task = self.sched.taskmap.get(self.tid, None)
		if task:
			task.target.close()
			self.task.sendval = True
		else:
			self.task.sendval = False
		self.sched.schedule(self.task)

def ex4():
	def foo():
		mytid = yield GetTid()
		while True:
			print("I'am foo.", mytid)
			yield

	def main():
		child = yield NewTask(foo())
		for _ in range(5):
			yield
		result = yield KillTask(child)
		print("main done.", result)

	sched = Scheduler()
	sched.new(main())
	sched.mainloop()


class WaitTask(SystemCall):
	def __init__(self, tid):
		self.tid = tid
	def handle(self):
		result = self.sched.waitforexit(self.task, self.tid)
		self.task.sendval = result
		if not result:
			self.sched.schedule(self.task)

def ex5():
	def foo():
		for _ in range(5):
			print("I'am foo")
			yield
	def main():
		child = yield NewTask(foo())
		print('Waiting for child')
		yield WaitTask(child)
		print('Child done')

	sched = Scheduler()
	sched.new(main())
	sched.mainloop()


def handle_client(client, addr):
	print('Connection from', addr)
	while True:
		yield ReadWait(client)
		data = client.recv(65536)
		if not data:
			break
		yield WriteWait(client)
		client.send(data)
	client.close()
	print('Client closed')
	yield

def server(port):
	print('Server starting')
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.bind(("", port))
	sock.listen(5)
	while True:
		yield ReadWait(sock)
		client, addr = sock.accept()
		yield NewTask(handle_client(client, addr))

def ex5():
	def alive():
		while True:
			print("I'am alive")
			yield

	sched = Scheduler()
	sched.new(alive())
	sched.new(server(45000))
	sched.mainloop()

class ReadWait(SystemCall):
	def __init__(self, f):
		self.f = f
	def handle(self):
		fd = self.f.fileno()
		self.sched.waitforread(self.task, fd)

class WriteWait(SystemCall):
	def __init__(self, f):
		self.f = f
	def handle(self):
		fd = self.f.fileno()
		self.sched.waitforwrite(self.task, fd)

ex5()