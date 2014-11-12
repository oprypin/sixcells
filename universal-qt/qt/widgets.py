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


from . import _prefer

exception = None

for module in _prefer:
    if module=='pyside':
        try:
            from PySide.QtWidgets import *
        except Exception as e:
            if exception is None:
                exception = e
        else:
            exception = None
            break
        try:
            from PySide.QtGui import *
        except Exception as e:
            if exception is None:
                exception = e
        else:
            exception = None
            break
    elif module=='pyqt4':
        try:
            from PyQt4.QtGui import *
        except Exception as e:
            if exception is None:
                exception = e
        else:
            exception = None
            break
    elif module=='pyqt5':
        try:
            from PyQt5.QtWidgets import *
        except Exception as e:
            if exception is None:
                exception = e
        else:
            exception = None
            break

if exception is not None:
    raise exception
del exception