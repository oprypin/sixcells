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


def distance(a, b):
    "Distance between two items"
    try:
        ax, ay = a
    except TypeError:
        ax, ay = a.x(), a.y()
    try:
        bx, by = b
    except TypeError:
        bx, by = b.x(), b.y()
    return _math.sqrt((ax-bx)**2+(ay-by)**2)


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




class cached_property(object):
    "Attribute that is calculated upon first access and then stored"
    def __init__(self, fget):
        self.__doc__ = fget.__doc__
        self.fget = fget
    
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        obj.__dict__[self.fget.__name__] = value = self.fget(obj)
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
        try:
            return obj.__dict__[self.attr]
        except KeyError as e:
            raise AttributeError()
    
    def __set__(self, obj, value):
        it = self.fset(obj, value)
        try:
            it = iter(it)
        except TypeError:
            pass
        else:
            for value in it:
                obj.__dict__[self.attr] = value

class event_property(setter_property):
    """An ordinary attribute that can you can get and set,
    but a function without arguments is called when setting it."""
    def __set__(self, obj, value):
        obj.__dict__[self.attr] = value
        self.fset(obj)


try:
    unicode
except NameError:
    unicode = str
try:
    basestring
except NameError:
    basestring = (str, bytes)