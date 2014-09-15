def count(it, condition=None):
    "Count the number of elements in an iterable (that satisfy the condition, if the function is provided)"
    if condition is None:
        try:
            return len(it)
        except:
            return sum(1 for _ in it)
    else:
        return sum(1 for i in it if condition(i))

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


class lazy_property(object):
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
        return obj.__dict__[self.attr]
    
    def __set__(self, obj, value):
        for value in self.fset(obj, value):
            obj.__dict__[self.attr] = value

class event_property(setter_property):
    """An ordinary attribute that can you can get and set,
    but a function without arguments is called when setting it."""
    def __set__(self, obj, value):
        obj.__dict__[self.attr] = value
        self.fset(obj)