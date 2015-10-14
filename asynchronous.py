from threading import Thread as _THREAD
from multiprocessing import Process as _PROCESS
from multiprocessing import Queue
from functools import update_wrapper
from functools import partial
from inspect import getargspec

SELF = "self"
CLS = "cls"


class _Decorator(object):

    def __init__(self, function):
        self.function = function
        update_wrapper(self, function)

    def __call__(self, *args, **kwargs):
        raise NotImplementedError("Cannot call abtract class.")

    def __get__(self, obj, klass=None):
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
        # If we are decorating an unbound method then our expectation is
        # that our queueing object will be inserted as the first argument.
        #
        # However, if we are decorating a bound method or a classmethod, then
        # our queue must come SECOND, after the self/cls parameter.
        #
        # The use of "self" and "cls" is such a strong convention that I
        # believe it reasonable to expect these to be used. As such, when
        # we instantiate a _QueuedResult we take a glance at the argument spec
        # and if the first positional argument is either "self" or "cls" then
        # we set the queue insertion index to that of the second argument, else
        # the first.
        #
        # I've struggled to think of a more desterministic way to do this, but
        # they have all involved making assumptions about the programmer's
        # intent (e.g. I can check to see if the first argument given has the
        # target function as a member, but what if we are decorating something
        # like a copy constructor...?).
        argspec = getargspec(function)[0]
        isMethodOrClassmethod = (
            argspec and
            (argspec[0] == SELF or argspec[0] == CLS)
        )
        self.QUEUE_INSERTION_INDEX = 1 if isMethodOrClassmethod else 0

    def __call__(self, *args, **kwargs):
        queue = Queue()
        args = list(args)
        args.insert(self.QUEUE_INSERTION_INDEX, queue)
        return super(_QueuedResultBase, self).__call__(*args, **kwargs), queue


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
