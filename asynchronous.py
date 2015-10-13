from threading import Thread as _THREAD
from multiprocessing import Process as _PROCESS
from multiprocessing import Queue
from functools import update_wrapper
from functools import partial


class _Decorator(object):

    def __init__(self, function):
        self.function = function
        update_wrapper(self, function)

    def __call__(self, *args, **kwargs):
        raise NotImplementedError("Cannot call abtract class.")

    def __get__(self, obj, klass):
        return partial(self.__call__, obj)


class _AsyncBase(_Decorator):

    def __call__(self, *args, **kwargs):
        thread = self._THREADING_INTERFACE(
            target=self.function,
            args=args,
            kwargs=kwargs
        )
        thread.daemon = True
        thread.start()
        return thread


class _QueuedResultBase(_AsyncBase):

    def __init__(self, function):
        super(_QueuedResultBase, self).__init__(function)
        self.QUEUE_INSERTION_INDEX = 0

    def __call__(self, *args, **kwargs):
        queue = Queue()
        args = list(args)
        args.insert(self.QUEUE_INSERTION_INDEX, queue)
        return super(_QueuedResultBase, self).__call__(*args, **kwargs), queue

    def __get__(self, obj, klass=None):
        self.QUEUE_INSERTION_INDEX = 1
        return super(_QueuedResultBase, self).__get__(obj, klass)


class _BlockingBase(_QueuedResultBase):

    def __call__(self, *args, **kwargs):
        _, queue = super(_BlockingBase, self).__call__(*args, **kwargs)
        return queue.get()


class Thread(_AsyncBase):
    _THREADING_INTERFACE = _THREAD

    class QueuedResult(_QueuedResultBase):
        _THREADING_INTERFACE = _THREAD

    class Blocking(_BlockingBase):
        _THREADING_INTERFACE = _THREAD


class Process(_AsyncBase):
    _THREADING_INTERFACE = _PROCESS

    class QueuedResult(_QueuedResultBase):
        _THREADING_INTERFACE = _PROCESS

    class Blocking(_BlockingBase):
        _THREADING_INTERFACE = _PROCESS
