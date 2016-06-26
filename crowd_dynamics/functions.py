import itertools
import math
import sys
from collections import Iterable
from collections import deque
from functools import wraps
from timeit import default_timer as timer

import numpy as np


def format_time(timespan, precision=3):
    """Jupyter notebook timeit time formatting.
    Formats the timespan in a human readable form"""

    if timespan >= 60.0:
        # we have more than a minute, format that in a human readable form
        # Idea from http://snipplr.com/view/5713/
        parts = [("d", 60 * 60 * 24), ("h", 60 * 60), ("min", 60), ("s", 1)]
        time = []
        leftover = timespan
        for suffix, length in parts:
            value = int(leftover / length)
            if value > 0:
                leftover %= length
                time.append(u'%s%s' % (str(value), suffix))
            if leftover < 1:
                break
        return " ".join(time)

    # Unfortunately the unicode 'micro' symbol can cause problems in
    # certain terminals.
    # See bug: https://bugs.launchpad.net/ipython/+bug/348466
    # Try to prevent crashes by being more secure than it needs to
    # E.g. eclipse is able to print a µ, but has no sys.stdout.encoding set.
    units = [u"s", u"ms", u'us', "ns"]  # the recordable value
    if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding:
        try:
            u'\xb5'.encode(sys.stdout.encoding)
            units = [u"s", u"ms", u'\xb5s', "ns"]
        except:
            pass
    scaling = [1, 1e3, 1e6, 1e9]

    if timespan > 0:
        order = min(-int(math.floor(math.log10(timespan)) // 3), 3)
    else:
        order = 3
    return u"%.*g %s" % (precision, timespan * scaling[order], units[order])


def filter_none(arg):
    """Make iterables and filter None values"""
    if not isinstance(arg, Iterable):
        arg = (arg,)
    return tuple(filter(None, arg))


def timed_execution(func):
    calls = itertools.count()
    prev = deque((0,), maxlen=100)

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = timer()
        ret = func(*args, **kwargs)
        dt = timer() - start
        if dt < 1.0:
            prev.append(dt)
        # TODO: better formatting
        print("Calls:{:6d}".format(next(calls)),
              "Time:", format_time(dt),
              "Avg time:", format_time(np.mean(prev)))
        return ret

    return wrapper
