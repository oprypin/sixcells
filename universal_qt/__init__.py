# Copyright (C) 2014-2016 Oleh Prypin <blaxpirit@gmail.com>
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


import sys as _sys


defaults = ['PyQt5', 'PySide', 'PyQt4']
qt = None


class QtSelector(object):
    """Implements import hooks for `universal_qt.*`.
    Selects a Qt implementation to be used in the `qt` module.
    For example, `import universal_qt.PyQt5` will select PyQt5"""

    @staticmethod
    def find_module(fullname, path=None):
        if fullname.split('.', 1)[0] == 'universal_qt':
            return QtSelector

    @staticmethod
    def load_module(fullname):
        if fullname in _sys.modules:
            return _sys.modules[fullname]

        _, name = fullname.split('.')

        global qt

        if qt:
            # If a Qt implementation was already selected previously
            # and the selected module is the same as the one being imported,
            # then return it, otherwise False.
            if qt.__name__ == name:
                _sys.modules[fullname] = qt; return qt
            else:
                _sys.modules[fullname] = False; return False

        if name == 'PyQt4' and _sys.version_info[0] == 2:
            # Select API version 2, this is needed only for PyQt4 on Python 2.x
            try:
                import sip
                for api in ['QDate', 'QDateTime', 'QString', 'QTextStream',
                            'QTime', 'QUrl', 'QVariant']:
                    try:
                        sip.setapi(api, 2)
                    except Exception:
                        pass
            except Exception:
                pass

        # The selection of Qt implementation is successful only if its QtCore
        # module can be imported.
        try:
            qt = __import__(name + '.QtCore')
        except ImportError:
            _sys.modules[fullname] = False; return False

        core = qt.QtCore

        # Turn `QtCore.Qt` object into a package,
        # because `import qt` will actually give this object.
        core.Qt.__path__ = []
        core.Qt.__package__ = 'qt'

        # Put some additional attributes into `qt`.
        core.Qt.module = name
        core.Qt.version_str = core.qVersion()
        core.Qt.major = int(core.Qt.version_str.split('.', 1)[0])
        if name.startswith('PyQt'):
            core.Qt.module_version_str = core.PYQT_VERSION_STR
            core.Signal = core.pyqtSignal
            core.Slot = core.pyqtSlot
        else:
            core.Qt.module_version_str = qt.__version__
        core.Qt.Signal = core.Signal
        core.Qt.Slot = core.Slot

        _sys.modules[fullname] = qt; return qt


class QtImporter(object):
    """Implements import hooks for `qt`, `qt.*`.
    For `import qt` returns the `Qt` object of some Qt implementation, e.g.
    `PySide.QtCore.Qt`, but that object is pre-populated to act like a package.
    For `import qt.*` returns the corresponding module, with capitalized parts.
    In Qt 5 some modules were split, e.g. QtGui -> QtGui+QtWidgets, so for Qt 4
    `Qt*Widgets` imports are turned into their combined module,
    e.g. `import qt.web_kit_widgets` gives `PyQt5.QtWebKitWidgets` if PyQt5 was
    selected or `PySide.QtWebKit` if PySide was selected."""

    @staticmethod
    def find_module(fullname, path=None):
        if fullname.split('.', 1)[0] == 'qt':
            return QtImporter

    @staticmethod
    def load_module(fullname):
        if fullname in _sys.modules:
            return _sys.modules[fullname]

        if not qt:
            # If Qt hasn't been selected yet (or none of the attempts were
            # successful), try to select any from the list of defaults.
            for d in defaults:
                QtSelector.load_module('universal_qt.' + d)
            if not qt:
                raise ImportError("Couldn't import any Qt implementation")

        if fullname == 'qt':
            # `import qt` will try to import QtCore (but return QtCore.Qt)
            module = 'core'
        else:
            # `import qt.*`: we're getting the `*` part.
            _, module = fullname.split('.')
        # Split by underscore and capitalize each part.
        # 'web_kit_widgets' -> 'WebKitWidgets'
        to_load = renamed = ''.join(
            part[0].upper() + part[1:]
            for part in module.split('_')
        )

        try:
            top = __import__(qt.__name__ + '.Qt' + to_load, level=0)
            # e.g. 'PyQt5.QtWidgets', but it returns the `PyQt5` package,
            # hence the name `top`.
        except ImportError as e:
            if to_load.endswith('Widgets'):
                # If failed to import, try to import the non-'Widgets'
                # counterpart, e.g. `PySide.QtWidgets` -> `PySide.QtGui`.
                to_load = to_load[:-7] or 'Gui'
                try:
                    top = __import__(qt.__name__ + '.Qt' + to_load, level=0)
                except ImportError:
                    raise e
            else:
                raise e
        # Get the actual module from the top-level package
        result = getattr(top, 'Qt' + to_load)

        if renamed == 'Widgets':
            if qt.__name__.startswith('PyQt'):
                __import__(qt.__name__ + '.uic', level=0)
                result.load_ui = qt.uic.loadUi
            elif qt.__name__.startswith('PySide'):
                def load_ui(filename):
                    __import__(qt.__name__ + '.QtUiTools', level=0)
                    loader = qt.QtUiTools.QUiLoader()
                    uifile = qt.QtCore.QFile(filename)
                    uifile.open(qt.QtCore.QFile.ReadOnly)
                    ui = loader.load(uifile)
                    uifile.close()
                    return ui
                result.load_ui = load_ui

        # As mentioned before, `import qt` returns `QtCore.Qt`.
        if fullname == 'qt':
            result = result.Qt

        _sys.modules[fullname] = result; return result


# Add/activate the import hooks
_sys.meta_path.insert(0, QtSelector)
_sys.meta_path.insert(0, QtImporter)
