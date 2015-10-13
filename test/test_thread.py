from __future__ import absolute_import
from unittest import TestCase
from time import sleep
from time import time
from math import floor
import threading
import multiprocessing

from .. import *

TOLERANCE = 0.5
SLEEP_TIME = 1

class TestUnbound(TestCase):

    def _fireAndTime(self, func, runtime, *args, **kwargs):
        start = time()
        t = func(*args, **kwargs)
        self.assertTrue(isinstance(t, threading.Thread))
        while t.is_alive():
            pass
        total = time() - start
        withinTolerance = total >= runtime - TOLERANCE and total <= runtime + TOLERANCE
        self.assertTrue(withinTolerance)

    def testNoArgs(self):
        @Thread
        def f():
            sleep(SLEEP_TIME)
        self.assertTrue(isinstance(f, Thread), type(f))
        self.assertEqual(f.__name__, "f")
        self._fireAndTime(f, SLEEP_TIME)

    def testArgs(self):
        @Thread
        def f(a):
            self.assertEqual(a, 1)
            sleep(SLEEP_TIME)
        self.assertTrue(isinstance(f, Thread), type(f))
        self.assertEqual(f.__name__, "f")
        self._fireAndTime(f, SLEEP_TIME, 1)

    def testKwargs(self):
        @Thread
        def f(a=None):
            self.assertEqual(a, 1)
            sleep(SLEEP_TIME)
        self.assertTrue(isinstance(f, Thread), type(f))
        self.assertEqual(f.__name__, "f")
        self._fireAndTime(f, SLEEP_TIME, a=1)

    def testOptionalParams(self):
        @Thread
        def f(a=None):
            self.assertEqual(a, None)
            sleep(SLEEP_TIME)
        self.assertTrue(isinstance(f, Thread), type(f))
        self.assertEqual(f.__name__, "f")
        self._fireAndTime(f, SLEEP_TIME)

    def testBadKwargs(self):
        @Thread
        def f(a=None):
            self.assertEqual(a, 1)
            sleep(SLEEP_TIME)
        self.assertTrue(isinstance(f, Thread), type(f))
        self.assertEqual(f.__name__, "f")
        try:
            f(b=1)
        except TypeError as error:
            pass

    def testTooManyArgs(self):
        @Thread
        def f():
            pass
        self.assertTrue(isinstance(f, Thread), type(f))
        self.assertEqual(f.__name__, "f")
        try:
            f(1)
        except TypeError as error:
            pass

    def testTooFewArgs(self):
        @Thread
        def f(a):
            pass
        self.assertTrue(isinstance(f, Thread), type(f))
        self.assertEqual(f.__name__, "f")
        try:
            f()
        except TypeError as error:
            pass