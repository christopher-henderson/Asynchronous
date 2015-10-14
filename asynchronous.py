from threading import Thread as _THREAD
from multiprocessing import Process as _PROCESS
from multiprocessing import Queue
from functools import update_wrapper
from functools import partial
from inspect import getargspec

__author__ = "Christopher Henderson"
__copyright__ = "Copyright 2015, Christopher Henderson"
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Christopher Henderson"
__email__ = "chris@chenderson.org"

SELF = "self"
CLS = "cls"


class _Decorator(object):

    '''
    Defines an interface for class based decorators.
    When inheriting from this class the typical protocol for writting a
    decorator class changes slightly.

    __decorator__:
        Must be overriden.
        This is where the decorating behavior should be written, as opposed
        to __call__.

    __wrap__:
        Optionally overriden.
        Defines how this class wraps a target function.
    '''

    def __init__(self, function=None):
        self.function = function
        if function:
            # If function was not defined then updating the wrapper
            # is deferred until __call__ is executed.
            self.__wrap__(function)

    def __decorator__(self, *args, **kwargs):
        '''
        __decorator__ must be defined by inheriting classes as a surrogate
        to __call__. That is, behavior that would be typically placed under
        __call__ should be placed under __decorator__ instead.
        '''
        raise NotImplementedError("Call behavior is not defined in this abstract class")

    def __call__(self, *args, **kwargs):
        '''
        Depending on how this decorator was defined, __call__ will either
        execute the target function or it will wrap the target function.

        If a function was received during instantation then __decorator__ will
        be called immediately as we have already succesfully wrapped the
        target function.

        Otherwise this decorator was given keyword arguments,
        which means function wrapping was deferred until now.
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
            # __wrap__ before returning the wrapper proper.
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
        __wrap__ is called at the time when the decorating class is
        given its function to wrap.
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
        '''Create, start, and return a thread-like object.'''

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

    def __decorator__(self, *args, **kwargs):
        '''Insert multiprocessing.Queue object into parameter list.'''

        queue = Queue()
        args = list(args)
        args.insert(self.QUEUE_INSERTION_INDEX, queue)
        return super(_QueuedResultBase, self).__decorator__(*args, **kwargs), queue

    def __wrap__(self, function):
        '''Called when class first wraps a function.'''

        self.QUEUE_INSERTION_INDEX = self._get_insertion_index(function)
        return super(_QueuedResultBase, self).__wrap__(function)

    def _get_insertion_index(self, function):
        '''
        Retrieve the index of the parameter list where this class shoud
        insert a multiprocessing.Queue object
        '''

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
        return 1 if isMethodOrClassmethod else 0


class _BlockingBase(_QueuedResultBase):

    def __decorator__(self, *args, **kwargs):
        _, queue = super(_BlockingBase, self).__decorator__(*args, **kwargs)
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
