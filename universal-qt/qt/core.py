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
            from PySide.QtCore import *
            from PySide import __version__ as module_version_str
        except Exception as e:
            if exception is None:
                exception = e
        else:
            exception = None
            break
    elif module=='pyqt4':
        try:
            def update_apis(apis='QDate QDateTime QString QTextStream QTime QUrl QVariant'.split()):
                import sys
                if sys.version_info.major==2:
                    import sip
                    for api in apis:
                        try:
                            sip.setapi(api, 2)
                        except:
                            pass
            update_apis()
            del update_apis
            from PyQt4.QtCore import *
            from PyQt4.QtCore import pyqtSignal as Signal
            from PyQt4.QtCore import pyqtSlot as Slot
            from PyQt4.QtCore import PYQT_VERSION_STR as module_version_str
        except Exception as e:
            if exception is None:
                exception = e
        else:
            exception = None
            break
    elif module=='pyqt5':
        try:
            from PyQt5.QtCore import *
            from PyQt5.QtCore import pyqtSignal as Signal
            from PyQt5.QtCore import pyqtSlot as Slot
            from PyQt5.QtCore import PYQT_VERSION_STR as module_version_str
        except Exception as e:
            if exception is None:
                exception = e
        else:
            exception = None
            break

if exception is not None:
    raise exception
del exception