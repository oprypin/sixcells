# Copyright (C) 2014-2015 Oleh Prypin <blaxpirit@gmail.com>
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


import collections as _collections
import os as _os
import os.path as _path

from util import here, exec_ as _exec


class _ObjLocals(object):
    def __init__(self, obj):
        self.obj = obj
    def __getitem__(self, key):
        try:
            return getattr(self.obj, key)
        except AttributeError:
            raise KeyError()
    def __setitem__(self, key, value):
        try:
            setattr(self.obj, key, value)
        except AttributeError:
            raise KeyError()

def _parse_config_format(config_format):
    lines = ('{0} = {0}; {0} = v'.format(line.strip()) if ' = ' not in line else line for line in config_format.strip().splitlines())
    lines = (line.strip().split(' = ', 1) for line in lines)
    return _collections.OrderedDict((k, v.split('; ')) for k, v in lines)


def save_config(obj, config_format):
    config_format = _parse_config_format(config_format)
    
    result = []
    for name, (getter, setter) in config_format.items():
        value = eval(getter, None, _ObjLocals(obj))
        result.append('{} = {!r}'.format(name, value))
    
    return '\n'.join(result)

def load_config(obj, config_format, config):
    config_format = _parse_config_format(config_format)
    
    class Locals(object):
        def __setitem__(self, key, value):
            try:
                stmt = config_format[key][1]
            except KeyError:
                return
            _exec(stmt, locals=_ObjLocals(obj), globals={'v': value})
        def __getitem__(self, key):
            raise KeyError()
        def __delitem__(self, key):
            raise KeyError()
        
    _exec(config, locals=Locals())


def _user_config_location(folder_name, file_name):
    from qt.core import QSettings
    
    name, ext = _path.splitext(file_name)
    target = QSettings(QSettings.IniFormat, QSettings.UserScope, folder_name, name).fileName()
    target, _ = _path.splitext(target)
    target += ext
    return target


def save_config_to_file(obj, config_format, folder_name, file_name):
    try:
        cfg = save_config(obj, config_format)
        try:
            f = open(here(file_name), 'w')
        except OSError:
            loc = _user_config_location(folder_name, file_name)
            path = _path.dirname(loc)
            if not _path.exists(path):
                _os.makedirs(path)
            f = open(loc, 'w')
        f.write(cfg)
        f.close()
        return True
    except (OSError, IOError):
        return False

def load_config_from_file(obj, config_format, folder_name, file_name):
    try:
        try:
            f = open(here(file_name))
        except OSError:
            loc = _user_config_location(folder_name, file_name)
            f = open(loc)
        cfg = f.read()
        f.close()
        load_config(obj, config_format, cfg)
        return True
    except (OSError, IOError):
        return False