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


__version__ = '0.4'

import sys
import math
import collections
import json
import io
import gzip

sys.path.insert(0, 'universal-qt')
import qt
qt.init()
from qt.core import QPointF
from qt.gui import QPolygonF, QPen, QColor, QDesktopServices
from qt.widgets import QGraphicsPolygonItem, QGraphicsSimpleTextItem, QMessageBox, QGraphicsScene

from util import *


tau = 2*math.pi # 360 degrees is better than 180 degrees
cos30 = math.cos(tau/12)

class Color(object):
    yellow = QColor(255, 175, 41)
    yellow_border = QColor(255, 159, 0)
    blue = QColor(5, 164, 235)
    blue_border = QColor(20, 156, 216)
    black = QColor(62, 62, 62)
    black_border = QColor(44, 47, 49)
    light_text = QColor(255, 255, 255)
    dark_text = QColor(73, 73, 73)
    border = qt.white
    beam = QColor(220, 220, 220, 140)
    flower = QColor(220, 220, 220, 128)
    flower_border = QColor(128, 128, 128, 192)
    revealed_border = QColor(0, 255, 128)
    selection = qt.black
    proven = qt.darkGreen


#no_pen = QPen(qt.NoPen)
no_pen = QPen(qt.transparent, 1e-10)


def fit_inside(parent, item, k):
    "Fit one QGraphicsItem inside another, scale by height and center it"
    sb = parent.boundingRect()
    tb = item.boundingRect()
    item.setScale(sb.height()/tb.height()*k)
    tb = item.mapRectToItem(parent, item.boundingRect())
    item.setPos(sb.center()-QPointF(tb.size().width()/2, tb.size().height()/2))

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
    return math.sqrt((ax-bx)**2+(ay-by)**2)


class Cell(QGraphicsPolygonItem):
    "Hexagonal cell"
    unknown = None
    empty = False
    full = True
    
    def __init__(self):
        # This item is a hexagon. Define its points.
        # It will be slightly larger than 0.49*2+0.03 = 1.01 units high, so neighbors will slightly collide.
        poly = QPolygonF()
        l = 0.49/cos30
        # There is also a smaller inner part, for looks.
        inner_poly = QPolygonF()
        il = 0.77*l
        for i in range(6):
            a = i*tau/6-tau/12
            poly.append(QPointF(l*math.sin(a), -l*math.cos(a)))
            inner_poly.append(QPointF(il*math.sin(a), -il*math.cos(a)))
        
        QGraphicsPolygonItem.__init__(self, poly)

        self.inner = QGraphicsPolygonItem(inner_poly)
        self.inner.setPen(QPen(qt.transparent, 1e-10))

        pen = QPen(Color.border, 0.03)
        pen.setJoinStyle(qt.MiterJoin)
        self.setPen(pen)

        self.text = QGraphicsSimpleTextItem('z')
        self.text.setBrush(Color.light_text)
        
        self._kind = Cell.unknown
    
    @event_property
    def kind(self):
        self.upd()
    
    def upd(self, first=True):
        try:
            self.proven
        except AttributeError:
            kind = self.kind
            highlight = False
        else:
            kind = self.actual
            highlight = self.proven

        
        if kind is Cell.unknown:
            self.setBrush(Color.yellow_border)
            self.inner.setBrush(Color.yellow)
            self.text.setText("")
        elif kind is Cell.empty:
            self.setBrush(Color.black_border)
            self.inner.setBrush(Color.black)
        elif kind is Cell.full:
            self.setBrush(Color.blue_border)
            self.inner.setBrush(Color.blue)
        
        if kind is not Cell.unknown and self.value is not None:
            txt = str(self.value)
            together = self.together
            if together is not None:
                txt = ('{{{}}}' if together else '-{}-').format(txt)
        else:
            txt = '?' if kind is Cell.empty else ''
        
        self.text.setText('+' if highlight else txt)
        if self.text.text():
            fit_inside(self, self.text, 0.5)
        
        if highlight:
            self.setBrush(Color.yellow_border)
        
        self.update()
    
    def is_neighbor(self, other):
        return other in self.neighbors
    
    def paint(self, g, option, widget):
        QGraphicsPolygonItem.paint(self, g, option, widget)
        self.inner.paint(g, option, widget)
        g.setTransform(self.text.sceneTransform(), True)
        self.text.paint(g, option, widget)

        


class Column(QGraphicsPolygonItem):
    "Column number marker"
    def __init__(self):
        # The collision box is rectangular
        poly = QPolygonF()
        poly.append(QPointF(-0.25, 0.48))
        poly.append(QPointF(-0.25, 0.02))
        poly.append(QPointF(0.25, 0.02))
        poly.append(QPointF(0.25, 0.48))
        #l = 0.49/cos30
        #for i in range(6):
            #a = i*tau/6-tau/12
            #poly.append(QPointF(l*math.sin(a), -l*math.cos(a)))

        
        QGraphicsPolygonItem.__init__(self, poly)

        self.setBrush(QColor(255, 255, 255, 0))
        #self.setPen(QPen(qt.red, 0))
        self.setPen(no_pen)
        
        self.text = QGraphicsSimpleTextItem('v')
        self.text.setBrush(Color.dark_text)
        fit_inside(self, self.text, 0.8)
        #self.text.setY(self.text.y()+0.2)

    def upd(self):
        #try:
            #list(self.members)
        #except ValueError:
            #txt = '!?'
        #else:
        txt = str(self.value)
        together = self.together
        if together is not None:
            txt = ('{{{}}}' if together else '-{}-').format(txt)
        self.text.setText(txt)
        self.text.setX(-self.text.boundingRect().width()*self.text.scale()/2)
        
        self.update()

    def paint(self, g, option, widget):
        QGraphicsPolygonItem.paint(self, g, option, widget)
        g.setTransform(self.text.sceneTransform(), True)
        self.text.paint(g, option, widget)


class Scene(QGraphicsScene):
    def all(self, types=(Cell, Column)):
        return (it for it in self.items() if isinstance(it, types))

    def full_upd(self):
        for it in self.all(Cell):
            it.upd(False)
        for it in self.all(Column):
            it.upd()


def _save_common(j, it):
    if it.value is not None:
        j['value'] = it.value
    if it.together is not None:
        j['together'] = it.together
    j['x'] = it.x()
    j['y'] = it.y()

def save(file, scene, resume=False, pretty=False, gz=False):
    cells = list(scene.all(Cell))
    columns = list(scene.all(Column))

    cells_j, columns_j = [], []
    
    for i, it in enumerate(cells):
        j = collections.OrderedDict()
        j['id'] = i
        j['kind'] = 0 if it.kind is Cell.empty else 1
        neighbors = sorted(it.neighbors, key=lambda n: (math.atan2(n.x()-it.x(), it.y()-n.y())+0.01)%tau)
        j['neighbors'] = [cells.index(x) for x in neighbors]
        if it.show_info and it.value is not None:
            if it.kind is Cell.empty:
                j['members'] = j['neighbors']
            else:
                j['members'] = [cells.index(x) for x in it.members]
        if it.revealed or (resume and getattr(it, 'revealed_resume', False)):
            j['revealed'] = True
        _save_common(j, it)
        cells_j.append(j)
    
    for it in columns:
        j = collections.OrderedDict()
        if it.rotation()<-45: key = lambda it: it.x()
        elif it.rotation()>45: key = lambda it: -it.x()
        else: key = lambda it: it.y()
        j['members'] = [cells.index(n) for n in sorted(it.members, key=key)]
        _save_common(j, it)
        j['angle'] = round(it.rotation())
        
        columns_j.append(j)
    
    result = collections.OrderedDict([('cells', cells_j), ('columns', columns_j)])
    
    if isinstance(file, str):
        file = (gzip.open if gz else io.open)(file, 'wb')
    if pretty:
        result = json.dumps(result, indent=1, separators=(',', ': '))
        # Edit the resulting JSON string to join together the numbers that are alone in a line
        lines = result.splitlines(True)
        for i, line in enumerate(lines):
            if line.strip().rstrip(',').isdigit():
                lines[i-1] = lines[i-1].rstrip()+('' if '[' in lines[i-1] else ' ')
                lines[i] = line.strip()
                lines[i+1] = lines[i+1].lstrip()
        result = ''.join(lines)
    else:
        result = json.dumps(result, separators=(',', ':'))
    file.write(result.encode('ascii'))
    
    return cells




def load(file, scene, gz=False, Cell=Cell, Column=Column):
    if isinstance(file, str):
        file = (gzip.open if gz else io.open)(file, 'rb')
    jj = file.read().decode('ascii')
    try:
        jj = json.loads(jj)
    except Exception as e:
        QMessageBox.warning(None, "Error", "Error while parsing JSON:\n{}".format(e))
        return False
        
    by_id = [None]*len(jj['cells'])
    
    for j in jj['cells']:
        it = Cell()
        it.id = j['id']
        by_id[it.id] = it
        it.kind = [Cell.empty, Cell.full, Cell.unknown][j['kind']]
        it._neighbors = j.get('neighbors')
        it._members = j.get('members') or []
        it.revealed = j.get('revealed', False)
        it.together = j.get('together', j.get('together', None))
        it.setX(j['x'])
        it.setY(j['y'])
        it.value = j.get('value')
    for it in by_id:
        try:
            it.neighbors = [by_id[i] for i in it._neighbors]
        except (TypeError, AttributeError): pass
        del it._neighbors
        try:
            it.members = [by_id[i] for i in it._members]
        except AttributeError: pass
        del it._members
        scene.addItem(it)
    
    for j in jj['columns']:
        it = Column()
        try:
            it.members = [by_id[i] for i in j['members']]
        except AttributeError: pass
        it.together = j.get('together', j.get('together', None))
        it.setX(j['x'])
        it.setY(j['y'])
        it.setRotation(j.get('angle') or 1e-3) # not zero so font doesn't look different from rotated variants
        try:
            it.value = j['value']
        except AttributeError: pass
        scene.addItem(it)
    
    scene.full_upd()


def hexcells_pos(x, y):
    return round(x/cos30), round(y*2)

def save_hexcells(file, scene):
    grid = {}
    for it in scene.all():
        if isinstance(it, (Cell, Column)):
            # Columns that are right above a cell are actually lower in this format than what this editor deals with
            dy = 0.5 if (isinstance(it, Column) and round(it.rotation())==0) else 0
            grid[hexcells_pos(it.x(), it.y()+dy)] = it
    min_x, max_x = minmax([x for x, y in grid])
    min_y, max_y = minmax([y for x, y in grid])
    mid_x, mid_y = (min_x+max_x)//2, (min_y+max_y)//2
    min_t, max_t = 0, 32
    mid_t = (min_t+max_t)//2
    grid = {(x-mid_x+mid_t, y-mid_y+mid_t): it for (x, y), it in grid.items()}
    min_x, max_x = minmax([x for x, y in grid])
    min_y, max_y = minmax([y for x, y in grid])
    if min_x<min_t or max_x>max_t:
        raise ValueError("This level is too wide to fit into Cellcells format")
    if min_y<min_t or min_y>max_t:
        raise ValueError("This level is too high to fit into Cellcells format")
    result = [[['-', '-', '-'] for x in range(0, max_t+1)] for y in range(0, max_t+1)]
    for (x, y), it in grid.items():
        r = result[y][x]
        if isinstance(it, Column):
            r[0] = {-90: '>', -60: '\\', 0: 'v', 60: '/', 90: '<'}[round(it.rotation())]
        else:
            r[0] = '1' if it.kind is Cell.full else '0'
        if it.value is not None:
            if it.together is not None:
                r[1] = 'c' if it.together else 'n'
            else:
                r[1] = 'x'
        if isinstance(it, Cell) and it.revealed:
            r[2] = 'r'
    result = '\n'.join(' '.join(''.join(part) for part in line) for line in result)
    if isinstance(file, str):
        file = io.open(file, 'wb')
    file.write(result.encode('ascii'))

    

def about(app):
    try:
        import pulp
    except ImportError:
        pulp_version = "(missing!)"
    else:
        pulp_version = pulp.VERSION
    
    QMessageBox.information(None, "About", """
        <h1>{}</h1>
        <h3>Version {}</h3>

        <p>&copy; 2014 Oleh Prypin &lt;<a href="mailto:blaxpirit@gmail.com">blaxpirit@gmail.com</a>&gt;<br/>
           &copy; 2014 Stefan Walzer &lt;<a href="mailto:sekti@gmx.net">sekti@gmx.net</a>&gt;</p>

        <p>License: <a href="http://www.gnu.org/licenses/gpl.txt">GNU General Public License Version 3</a></p>

        Using:
        <ul>
        <li>Python {}
        <li>Qt {}
        <li>{} {}
        <li>PuLP {}
        </ul>
    """.format(
        app, __version__,
        sys.version.split(' ', 1)[0],
        qt.version_str,
        qt.module, qt.module_version_str,
        pulp_version
    ))

def help():
    QDesktopServices.openUrl('https://github.com/blaxpirit/sixcells/#readme')