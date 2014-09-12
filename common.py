#!/usr/bin/env python

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


__version__ = '0.2'

import sys
import math
import collections
import json

sys.path.insert(0, 'universal-qt')
import qt
qt.init()
from qt import Signal
from qt.core import QPointF, QRectF, QSizeF, QTimer
from qt.gui import QPolygonF, QPen, QBrush, QPainter, QColor, QMouseEvent, QTransform
from qt.widgets import QApplication, QGraphicsScene, QGraphicsView, QGraphicsPolygonItem, QGraphicsSimpleTextItem, QMainWindow, QMessageBox, QFileDialog, QAction, QGraphicsRectItem

math.tau = 2*math.pi
cos30 = math.cos(math.tau/12)



class Color:
    yellow = QColor(255, 175, 41)
    yellow_border = QColor(255, 159, 0)
    blue = QColor(5, 164, 235)
    blue_border = QColor(20, 156, 216)
    black = QColor(62, 62, 62)
    black_border = QColor(44, 47, 49)
    light_text = QColor(255, 255, 255)
    dark_text = QColor(73, 73, 73)
    border = qt.white
    beam = QColor(220, 220, 220, 128)
    revealed_border = qt.red


def all_connected(items):
    try:
        connected = {next(iter(items))}
    except StopIteration:
        return True
    anything_to_add = True
    while anything_to_add:
        anything_to_add = False
        for it in items-connected:
            if any(x.collidesWithItem(it) for x in connected):
                anything_to_add = True
                connected.add(it)
    return not (items-connected)


def fit_inside(parent, it, k):
    sb = parent.boundingRect()
    it.setBrush(Color.light_text)
    tb = it.boundingRect()
    it.setScale(sb.height()/tb.height()*k)
    tb = it.mapRectToParent(it.boundingRect())
    it.setPos(sb.center()-QPointF(tb.size().width()/2, tb.size().height()/2))


class Hex(QGraphicsPolygonItem):
    unknown = None
    empty = False
    full = True
    
    def __init__(self):
        poly = QPolygonF()
        l = 0.49/cos30
        inner_poly = QPolygonF()
        il = 0.77*l
        for i in range(6):
            a = i*math.tau/6-math.tau/12
            poly.append(QPointF(l*math.sin(a), -l*math.cos(a)))
            inner_poly.append(QPointF(il*math.sin(a), -il*math.cos(a)))
        
        QGraphicsPolygonItem.__init__(self, poly)

        self.inner = QGraphicsPolygonItem(inner_poly, self)
        self.inner.setPen(qt.NoPen)

        self.text = QGraphicsSimpleTextItem('', self)
        
        pen = QPen(Color.border, 0.03)
        pen.setJoinStyle(qt.MiterJoin)
        self.setPen(pen)
        
        self._kind = Hex.unknown
    
    @property
    def kind(self):
        return self._kind
    @kind.setter
    def kind(self, value):
        self._kind = value
        self.upd()
    
    def upd(self, first=True):
        if self.kind==Hex.unknown:
            self.setBrush(Color.yellow_border)
            self.inner.setBrush(Color.yellow)
            self.text.setText("")
        elif self.kind==Hex.empty:
            self.setBrush(Color.black_border)
            self.inner.setBrush(Color.black)
        elif self.kind==Hex.full:
            self.setBrush(Color.blue_border)
            self.inner.setBrush(Color.blue)
        if self.kind is not Hex.unknown and self.value is not None:
            txt = str(self.value)
            together = self.together
            if together is not None:
                txt = ('{{{}}}' if together else '-{}-').format(txt)
        else:
            txt = '?' if self.kind==Hex.empty else ''
        
        self.text.setText(txt)
        if txt:
            fit_inside(self, self.text, 0.5)

    
class Col(QGraphicsPolygonItem):
    def __init__(self):
        poly = QPolygonF()
        poly.append(QPointF(-0.25, 0.48))
        poly.append(QPointF(-0.25, 0.02))
        poly.append(QPointF(0.25, 0.02))
        poly.append(QPointF(0.25, 0.48))
        
        QGraphicsPolygonItem.__init__(self, poly)

        self.setBrush(QColor(255, 255, 255, 0))
        self.setPen(qt.NoPen)
        
        self.text = QGraphicsSimpleTextItem('v', self)
        fit_inside(self, self.text, 0.9)
        #self.text.setY(self.text.y()+0.2)
        self.text.setBrush(Color.dark_text)

    def upd(self):
        try:
            list(self.members)
        except ValueError:
            txt = '!?'
        else:
            txt = str(self.value)
            together = self.together
            if together is not None:
                txt = ('{{{}}}' if together else '-{}-').format(txt)
        self.text.setText(txt)
        self.text.setX(-self.text.boundingRect().width()*self.text.scale()/2)


def save(fn, scene):
    hexs, cols = [], []
    for it in scene.items():
        if isinstance(it, Hex):
            hexs.append(it)
        elif isinstance(it, Col):
            cols.append(it)
    hexs_j, cols_j = [], []
    
    for i, it in enumerate(hexs):
        j = collections.OrderedDict()
        j['id'] = i
        if it.kind==Hex.empty:
            j['kind'] = 0
            if it.text.text()!='?' and it.show_info:
                j['members'] = [hexs.index(n) for n in it.neighbors()]
        elif it.kind==Hex.full:
            j['kind'] = 1
            if it.show_info:
                j['members'] = [hexs.index(n) for n in it.circle_neighbors()]
        if it.revealed:
            j['revealed'] = True
        _save_common(j, it)
        hexs_j.append(j)
    
    for it in cols:
        j = collections.OrderedDict()
        j['members'] = [hexs.index(n) for n in it.members]
        _save_common(j, it)
        j['angle'] = round(it.rotation())
        
        cols_j.append(j)
    
    result = collections.OrderedDict([('cells', hexs_j), ('columns', cols_j)])
    
    with open(fn, 'w') as f:
        json.dump(result, f, indent=2)

def _save_common(j, it):
    s = it.text.text()
    if s.startswith('{'):
        j['together'] = True
    elif s.startswith('-'):
        j['together'] = False
    j['x'] = it.x()
    j['y'] = it.y()
    if s and s!='?':
        j['value'] = int(s.strip('{-}'))


def load(fn, scene, Hex=Hex, Col=Col):
    with open(fn) as f:
        try:
            jj = json.load(f)
        except Exception as e:
            QMessageBox.warning(None, "Error", "Error while parsing JSON:\n{}".format(e))
            return False
        
    by_id = [None]*len(jj['cells'])
    
    for j in jj['cells']:
        it = Hex()
        by_id[j['id']] = it
        it.kind = [Hex.empty, Hex.full, Hex.unknown][j['kind']]
        it._members = j.get('members') or []
        it.revealed = j.get('revealed', False)
        it.together = j.get('together', None)
        it.setX(j['x'])
        it.setY(j['y'])
        it.value = j.get('value')
    for it in by_id:
        try:
            it.members = [by_id[i] for i in it._members]
        except AttributeError:
            pass
        del it._members
        scene.addItem(it)
    
    for j in jj['columns']:
        it = Col()
        try:
            it.members = [by_id[i] for i in j['members']]
        except AttributeError:
            pass
        it.together = j.get('together', None)
        it.setX(j['x'])
        it.setY(j['y'])
        it.setRotation(j.get('angle', 0))
        try:
            it.value = j['value']
        except AttributeError:
            pass
        scene.addItem(it)
    
    for it in scene.items():
        if isinstance(it, (Hex, Col)):
            it.upd()


def about(app):
    QMessageBox.information(None, "About", """
        <h1>{}</h1>
        <h3>Version {}</h3>

        <p>(C) 2014 Oleh Prypin &lt;<a href="mailto:blaxpirit@gmail.com">blaxpirit@gmail.com</a>&gt;</p>

        <p>License: <a href="http://www.gnu.org/licenses/gpl.txt">GNU General Public License Version 3</a></p>

        Using:
        <ul>
        <li>Python {}
        <li>Qt {}
        <li>{} {}
        </ul>
    """.format(
        app, __version__,
        sys.version.split(' ', 1)[0],
        qt.version_str,
        qt.module, qt.module_version_str,
    ))