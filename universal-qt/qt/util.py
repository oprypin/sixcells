# Copyright (C) 2014 Oleh Prypin <blaxpirit@gmail.com>
# 
# This file is part of UniversalQt.
# 
# UniversalQt is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# UniversalQt is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with UniversalQt.  If not, see <http://www.gnu.org/licenses/>.


def qu(target, *args, **properties):
    if args or isinstance(target, type):
        target = target(*args)
    for k, v in properties.items():
        try:
            f = getattr(target, 'set'+''.join(w.capitalize() for w in k.split('_')))
            if type(v) is tuple:
                f(*v)
            else:
                f(v)
        except AttributeError:
            f = getattr(target, ''.join(w.capitalize() if i else w.lower() for i, w in enumerate(k.split('_'))))
            from . import Signal
            try:
                f.connect(v)
            except AttributeError:
                if type(v) is tuple:
                    f(*v)
                else:
                    f(v)
    return target


def add_to(target, *items):
    from .widgets import QWidget, QMenu, QLayout, QAction, QTabWidget, QSplitter, QFormLayout
    if len(items)==1:
        try:
            items = list(items[0])
        except TypeError:
            pass
    for item in items:
        if isinstance(item, tuple):
            item, args = item[0], item
        else:
            args = item,
        if isinstance(target, QTabWidget):
            target.addTab(args)
        elif isinstance(target, QSplitter):
            target.addWidget(item)
            if len(args)>1:
                target.setStretchFactor(target.count()-1, *args[1:])
        elif isinstance(target, QFormLayout):
            target.addRow(*args)
        elif item in (None, Ellipsis) and hasattr(target, 'addSeparator'):
            target.addSeparator()
        else:
            for typ in [QLayout, QAction, QMenu, QWidget, type(item)]:
                if isinstance(item, typ):
                    name = typ.__name__
                    if name.startswith('Q') and name[1].isupper():
                        name = name[1:]
                    getattr(target, 'add'+name.capitalize())(*args)
                    break
            else:
                raise TypeError()
    return target


def fit_and_resize(rect, content_size, percent=1):
    if rect.width()/content_size.width()<rect.height()/content_size.height():
        new_width = rect.height()/content_size.height()*content_size.width()
        delta_width = (new_width-rect.width())/2
        return rect.adjusted(-delta_width*percent, 0, delta_width*percent, 0)
    else:
        new_height = rect.width()/content_size.width()*content_size.height()
        delta_height = (new_height-rect.height())/2
        return rect.adjusted(0, -delta_height*percent, 0, delta_height*percent)  
