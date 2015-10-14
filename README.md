# Asynchronous

Asynchronous is a collection of decorators for quickly writing asynchronous code in Python. Any decorated method or function will be ran concurrently/in parallel (depending on which annotation is used).


```python
from time import sleep
from Asynchronous import Thread

@Thread(daemon=False, name="hello_world")
def hello():
  for _ in range(10):
    print ("Hello, from another thread!")
    sleep(2)

thread = hello()
while thread.is_alive():
  print ("It's still going!")
  sleep(3)
```



The *Thread* and *Process* classes are themselves wrappers for *threading.Thread* and *multiprocessing.Process*, respectively, and as such behave like those modules. This is especially important to note if you are trying to escape the Global Interpreter Lock as you must use *Process*.

For all decorators you may specify whether or not the underlying thread is daemonized (default, True) as well as any keyword arguments that would normally go into *threading.Thread* or *multiprocessing.Process* (except for *target*, *args*, and *kwargs*). Otherwise, a no-arg decorator will daemonize the thread and provide no extra arguments.

## Thread
- **Thread** -- Basic threading decorator wrapping the *threading.Thread* class. Returns a *threading.Thread* object.
```python
@Thread
def hello():
  ...

thread = hello()
print (thread.is_alive())
```
- **Thread.QueuedResult** -- Decorated methods/functions are given a *multiprocessing.Queue* object as its first non-self parameter. Returns a tuple of a *threading.Thread* object and a *multiprocessing.Queue* object.
```python
@Threading.QueuedResult
def calculate_result(self, queue, a, b):
  queue.put(a + b)

...
thread, queue = some_obj.calculate_result(a, b)
while thread.is_alive():
  pass
print (queue.get())
```
- **Thread.Blocking** -- Decorated methods/functions are given a *multiprocessing.Queue* object as its first non-self parameter. The call is blocking until a value is placed into this queue, thus putting a value into this queue should be treated as the surrogate *return* statement. This is only really useful if you are wanting to isolate a function, but still want serial behavior.
```python
@Thread.Blocking
def calculate_result(self, queue, a, b):
  queue.put(a + b)

...
print (some_obj.calculate_result(a, b))
```

## Process
- **Process** -- Basic threading decorator wrapping the *multiprocessing.Process* class. Returns a *multiprocessing.Process* object.
```python
@Process
def hello():
  ...

process = hello()
print (process.is_alive())
```
- **Process.QueuedResult** -- Decorated methods/functions are given a *multiprocessing.Queue* object as its first non-self parameter. Returns a tuple of a *multiprocessing.Process* object and a *multiprocessing.Queue* object.
```python
@Process.QueuedResult
def calculate_result(self, queue, a, b):
  queue.put(a + b)

...
process, queue = some_obj.calculate_result(a, b)
while process.is_alive():
  pass
print (queue.get())
```
- **Process.Blocking** -- Decorated methods/functions are given a *multiprocessing.Queue* object as its first non-self parameter. The call is blocking until a value is placed into this queue, thus putting a value into this queue should be treated as the surrogate *return* statement. This is only really useful if you are wanting to isolate a function, but still want serial behavior.
```python
@Process.Blocking
def calculate_result(self, queue, a, b):
  queue.put(a + b)

...
print (some_obj.calculate_result(a, b))
```
