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
    PURPOSE:
    The normal protocol of a decorator dictates that an __init__
    and a __call__ should be defined. If __init__ accepts only one
    argument, then it will be given the function to be decorated and can be
    used without parenthesis. E.G.:
        @my_decorator
        def some_func():
            pass
    If __init__ takes in arguments related to the decorator itself, then
    __call__ must accept the decorated function and return the desired wrapper.
    The result being that a decorator that takens in optional arguments can
    end up looking like this:
        @my_decorator(verbose=True)
        def some_func():
            pass
        @my_decorator()
        def some_other_func():
            pass
    This is cumbersome and leads to confusion on whether or not a particuler
    no-argument decorator requires parenthesis or not.
    In addition, many programmers newer to Python are at a loss on how to pass
    self to a decorated instance method.
    As such, the purpose of the Decorator class is to abstract away the
    nuances of function wrapping, __call__ behavior, and non-data descriptors.
    PROTOCAL:
    When inheriting from this class the typical protocol for writing a
    decorator class changes slightly.
    __decorator__:
        Must be overriden.
        This is where the decorating behavior should be written, as opposed
        to __call__.
    __wrap__:
        Optionally overriden.
        Defines how this class wraps a target function.
    The wrapped function can be found at self.function.
    SIMPLE EXAMPLE:
    ############################################################################
    class Logged(Decorator):
        def __decorator__(self, *args, **kwargs):
            print ("Now calling {FUNC}".format(FUNC=self.function.__name__))
            function_result = self.function(*args, **kwargs)
            print ("Finished {FUNC}".format(FUNC=self.function.__name__))
            return function_result
    @Logged
    def add(a, b):
        return a + b
    result = add(1, 2)
    print (result)
    ############################################################################
    OUTPUTS:
        Now calling add
        Finished add
        3
    COMPLEX EXAMPLE:
    ############################################################################
    class Logged(Decorator):
        def __init__(self, function=None, verbose=False):
            self.verbose = verbose
            super(Logged, self).__init__(function)
        def __decorator__(self, *args, **kwargs):
            if self.verbose:
                print ("Now calling {FUNC}".format(
                    FUNC=self.function.__name__)
                )
            function_result = self.function(*args, **kwargs)
            if self.verbose:
                print ("Finished {FUNC}".format(
                    FUNC=self.function.__name__)
                )
            return function_result
    class Math(object):
        @staticmethod
        @Logged
        def add(a, b):
            return a + b
        @staticmethod
        @Logged(verbose=True)
        def subract(a, b):
            return a - b
    print (Math.add(1, 2))
    print (Math.subract(2, 1))
    ############################################################################
    OUTPUTS:
        3
        Now calling subract
        Finished subract
        1
    '''

    def __init__(self, function=None):
        '''
        If function is left undefined, then function wrapping is deferred
        until the first time __call__ is executed.
        '''
        self.function = function
        if function:
            self.__wrap__(function)

    def __decorator__(self, *args, **kwargs):
        '''
        __decorator__ must be defined by the inheriting classes as a surrogate
        to __call__. That is, behavior that you would be typically placed under
        __call__ should be placed under __decorator__ instead.
        '''
        raise NotImplementedError("Call behavior is not defined in this abstract class")

    def __wrap__(self, function):
        '''
        Called at the time when the decorating class is
        given its function to wrap.
        '''
        self.function = function
        update_wrapper(self, function)
        return self

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
            return self.__decorator__(*args, **kwargs)
        return self.__wrap__(args[0])

    def __get__(self, instance, klass=None):
        '''
        Non-data descriptor for inserting an instance as the first parameter
        to __call__ if this object is being accessed as a member.
        '''
        if instance is None:
            return self
        return partial(self, instance)


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
