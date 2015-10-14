from threading import Thread as _THREAD
from multiprocessing import Process as _PROCESS
from multiprocessing import Queue
from functools import update_wrapper
from functools import partial
from inspect import getargspec

SELF = "self"
CLS = "cls"


class _Decorator(object):

    def __init__(self, function=None, **kwargs):
        self.function = function
        for k, v in kwargs.items():
            self.__setattr__(k, v)
        if function:
            # If function was not defined then updating the wrapper
            # is deferred until __call__ is executed.
            self.__wrap__(function)

    def __decorator__(self, *args, **kwargs):
        '''
        __decorator__ must be defined by inheriting classes as a surrogate
        to __call__. That is, behavior that you would typically place under
        __call__ should be placed under __decorator__ instread.
        '''
        raise NotImplementedError("Call behavior is not defined in this abstract class")

    def __call__(self, *args, **kwargs):
        '''
        __call__ behaves like a dispatcher. If a function was received
        during instantation then __decorator__ will be called immediately.
        Otherwise __call_wrapper__ will be called
        '''
        if self.function:
            # If we have a function already then that means the method
            # signature looked like:
            #
            #   @my_decorator
            #   def something():
            #       ...
            #
            # ...thus we can directly call the work defined by the
            # __decorator__. Otherwise the signature received some arguments
            # instead of a function, a la:
            #
            #   @my_decorator(config=True)
            #   def something():
            #       ...
            #
            # ...in which case we need to wrap __decorator__ first via
            # __call_wrapper__ before returning the wrapper proper.
            return self.__decorator__(*args, **kwargs)
        return self.__wrap__(args[0])

    def __get__(self, obj, klass=None):
        '''
        Non-data descriptor for inserting an instance as the first parameter
        to __call__ if this object is being accessed as a member.
        '''
        if obj is None:
            raise TypeError('''\
unbound method {NAME}() must be called with instance as first argument\
(got nothing instead)'''.format(
                    NAME=self.function.__name__)
            )
        return partial(self.__call__, obj)

    def __wrap__(self, function):
        '''
        Updates self to wrap function.

        Returns __decorator__ which defines executed behavior.
        '''
        self.function = function
        update_wrapper(self, function)
        return self


class _AsyncBase(_Decorator):

    def __init__(self, function=None, daemon=True, **kwargs):
        super(_AsyncBase, self).__init__(function)
        self.daemon = daemon
        self.kwargs = kwargs

    def __decorator__(self, *args, **kwargs):
        '''
        Create, start, and return a thread-like object.
        '''
        thread = self._THREADING_INTERFACE(
            target=self.function,
            args=args,
            kwargs=kwargs,
            **self.kwargs
        )
        thread.daemon = self.daemon
        thread.start()
        return thread


class _QueuedResultBase(_AsyncBase):

    def __init__(self, function=None, daemon=True, **kwargs):
        super(_QueuedResultBase, self).__init__(function, daemon, **kwargs)
        if self.function:
            self._get_insertion_index()
        else:
            self.QUEUE_INSERTION_INDEX = -1

    def __decorator__(self, *args, **kwargs):
        if self.QUEUE_INSERTION_INDEX is -1:
            # Definition of self.function was deferred until now.
            self._get_insertion_index()
        queue = Queue()
        args = list(args)
        args.insert(self.QUEUE_INSERTION_INDEX, queue)
        return super(_QueuedResultBase, self).__decorator__(*args, **kwargs), queue

    def _get_insertion_index(self):
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
        argspec = getargspec(self.function)[0]
        isMethodOrClassmethod = (
            argspec and
            (argspec[0] == SELF or argspec[0] == CLS)
        )
        self.QUEUE_INSERTION_INDEX = 1 if isMethodOrClassmethod else 0


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
