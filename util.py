# Copyright (C) 2014 Oleh Prypin <blaxpirit@gmail.com>
# 
# This file is part of SixCells.
# 
# SixCells is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# SixCells is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with SixCells.  If not, see <http://www.gnu.org/licenses/>.


import sys as _sys
import os.path as _path
import math as _math
import collections as _collections


def minmax(*args, **kwargs):
    return min(*args, **kwargs), max(*args, **kwargs)


def all_grouped(items, key):
    """Are all the items in one group or not?
    `key` should be a function that says whether 2 items are connected."""
    try:
        grouped = {next(iter(items))}
    except StopIteration:
        return True
    anything_to_add = True
    while anything_to_add:
        anything_to_add = False
        for a in items-grouped:
            if any(key(a, b) for b in grouped):
                anything_to_add = True
                grouped.add(a)
    return len(grouped)==len(items)


def distance(a, b, squared=False):
    "Distance between two items"
    try:
        ax, ay = a
    except TypeError:
        ax, ay = a.x(), a.y()
    try:
        bx, by = b
    except TypeError:
        bx, by = b.x(), b.y()
    r = (ax-bx)**2+(ay-by)**2
    if not squared:
        r = _math.sqrt(r)
    return r

def angle(a, b=None):
    """Angle between two items: 0 if b is above a, tau/4 if b is to the right of a...
    If b is not supplied, this becomes the angle between (0, 0) and a."""
    try:
        ax, ay = a
    except TypeError:
        ax, ay = a.x(), a.y()
    if b is None:
        return _math.atan2(ax, -ay)
    try:
        bx, by = b
    except TypeError:
        bx, by = b.x(), b.y()
    return _math.atan2(bx-ax, ay-by)


Point = _collections.namedtuple('Point', 'x, y')


class Entity(object):
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return self.name



try:
    _script_name = __FILE__
except NameError:
    _script_name = _sys.argv[0]
_script_path = _path.dirname(_path.abspath(_script_name))

def here(*args):
    return _path.join(_script_path, *args)



class cached_property(object):
    "Attribute that is calculated and stored upon first access."
    def __init__(self, fget):
        self.__doc__ = fget.__doc__
        self.fget = fget
        self.attr = fget.__name__
    
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        value = self.fget(obj)
        obj.__dict__[self.attr] = value
        return value


class setter_property(object):
    "Attribute that is based only on a setter function; the getter just returns the value"
    def __init__(self, fset):
        self.__doc__ = fset.__doc__
        self.fset = fset
        self.attr = '_'+fset.__name__
    
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.attr)
    
    def __set__(self, obj, value):
        it = self.fset(obj, value)
        try:
            it = iter(it)
        except TypeError: pass
        else:
            for value in it:
                setattr(obj, self.attr, value)

class event_property(setter_property):
    """An ordinary attribute that can you can get and set,
    but a function without arguments is called when setting it."""
    def __set__(self, obj, value):
        setattr(obj, self.attr, value)
        self.fset(obj)





# Python 2.7 + 3.x compatibility

try:
    unicode
except NameError:
    unicode = str

try:
    basestring
except NameError:
    basestring = (str, bytes)

if isinstance(round(0), float):
    _round = round
    def round(number, ndigits=None):
        if ndigits is None:
            return int(_round(number))
        else:
            return _round(number, ndigits)

def exec_(expression, globals=None, locals=None):
    eval(compile(expression, '<string>', 'exec'), globals, locals)