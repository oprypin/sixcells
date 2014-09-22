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


from __future__ import division, print_function

__version__ = '1.0'

import sys
import os.path
import math
import collections
import json
import io
import gzip

try:
    script_path = os.path.dirname(os.path.abspath(__FILE__))
except NameError:
    script_path = os.path.dirname(os.path.abspath(sys.argv[0]))

def here(*args):
    return os.path.join(script_path, *args)

sys.path.insert(0, here('universal-qt'))
import qt
qt.init('pyqt5')
from qt.core import QPointF, QUrl
from qt.gui import QPolygonF, QPen, QColor, QDesktopServices
from qt.widgets import QGraphicsPolygonItem, QGraphicsSimpleTextItem, QMessageBox, QGraphicsScene, QAction, QActionGroup

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
    proven = QColor(0, 160, 0)


no_pen = QPen(qt.transparent, 1e-10, qt.NoPen)


def fit_inside(parent, item, k):
    "Fit one QGraphicsItem inside another, scale by height and center it"
    sb = parent.boundingRect()
    tb = item.boundingRect()
    item.setScale(sb.height()/tb.height()*k)
    tb = item.mapRectToItem(parent, item.boundingRect())
    item.setPos(sb.center()-QPointF(tb.size().width()/2, tb.size().height()/2))


def multiply_font_size(font, k):
    if font.pointSizeF()>0:
        font.setPointSizeF(font.pointSizeF()*k)
    else:
        font.setPixelSize(int(round(font.pixelSize()*k)))


def make_check_action(text, obj, *args):
    action = QAction(text, obj)
    action.setCheckable(True)
    if args:
        if len(args)==1:
            args = (obj,)+args
        def set_attribute(value):
            setattr(*(args+(value,)))
        action.toggled.connect(set_attribute)
    return action

def make_action_group(parent, menu, obj, attribute, items):
    group = QActionGroup(parent)
    group.setExclusive(True)
    result = collections.OrderedDict()
    for text, value in items:
        action = make_check_action(text, parent)
        group.addAction(action)
        menu.addAction(action)
        def set_attribute(truth, value=value):
            if truth:
                setattr(obj, attribute, value)
        action.toggled.connect(set_attribute)
        result[value] = action
    return result


class Cell(QGraphicsPolygonItem):
    "Hexagonal cell"
    unknown = None
    empty = False
    full = True
    
    def __init__(self):
        # This item is a hexagon. Define its points.
        # It will be 0.49*2+0.03 = 1.01 units high, so neighbors will slightly collide.
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

        self._inner = QGraphicsPolygonItem(inner_poly)
        self._inner.setPen(no_pen)

        pen = QPen(Color.border, 0.03)
        pen.setJoinStyle(qt.MiterJoin)
        self.setPen(pen)

        self._text = QGraphicsSimpleTextItem('{?}')
        self._text.setBrush(Color.light_text)
        
        self._kind = Cell.unknown
    
    @event_property
    def kind(self):
        self.upd()
    
    @property
    def text(self):
        return self._text.text()
    @text.setter
    def text(self, value):
        self._text.setText(value)
        if value:
            fit_inside(self, self._text, 0.5)
        self.update()
    
    def is_neighbor(self, other):
        return other in self.neighbors
    
    def upd(self, first=True):
        if self.kind is Cell.unknown:
            self.setBrush(Color.yellow_border)
            self._inner.setBrush(Color.yellow)
            self.text = ''
        elif self.kind is Cell.empty:
            self.setBrush(Color.black_border)
            self._inner.setBrush(Color.black)
        elif self.kind is Cell.full:
            self.setBrush(Color.blue_border)
            self._inner.setBrush(Color.blue)
        
        if self.kind is not Cell.unknown and self.value is not None:
            txt = str(self.value)
            together = self.together
            if together is not None:
                txt = ('{{{}}}' if together else '-{}-').format(txt)
        else:
            txt = '?' if self.kind is Cell.empty else ''
        
        self.text = txt
        
        self.update()
    
    def paint(self, g, option, widget):
        QGraphicsPolygonItem.paint(self, g, option, widget)
        self._inner.paint(g, option, widget)
        g.setTransform(self._text.sceneTransform(), True)
        g.setOpacity(self._text.opacity())
        self._text.paint(g, option, widget)



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
        
        self._text = QGraphicsSimpleTextItem('v')
        self._text.setBrush(Color.dark_text)
        fit_inside(self, self._text, 0.8)
        #self._text.setY(self.text._y()+0.2)

    @property
    def text(self):
        return self._text.text()
    @text.setter
    def text(self, value):
        self._text.setText(value)
        if value:
            self._text.setX(-self._text.boundingRect().width()*self._text.scale()/2)

    def upd(self):
        txt = str(self.value)
        together = self.together
        if together is not None:
            txt = ('{{{}}}' if together else '-{}-').format(txt)
        self.text = txt
        self.update()

    def paint(self, g, option, widget):
        QGraphicsPolygonItem.paint(self, g, option, widget)
        g.setTransform(self._text.sceneTransform(), True)
        self._text.paint(g, option, widget)


class Scene(QGraphicsScene):
    def __init__(self):
        QGraphicsScene.__init__(self)
        self.information = None
    
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

def save(scene, resume=False):
    cells = list(scene.all(Cell))[::-1]
    columns = list(scene.all(Column))[::-1]

    cells_j, columns_j = [], []
    
    for i, it in enumerate(cells):
        j = collections.OrderedDict()
        j['id'] = i
        j['kind'] = 0 if it.kind is Cell.empty else 1 if it.kind is Cell.full else -1
        neighbors = sorted(it.neighbors, key=lambda n: (angle(it, n)+0.01)%tau)
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
        j['angle'] = int(round(it.rotation()))
        
        columns_j.append(j)
    
    struct = collections.OrderedDict([('version', 1)])
    if scene.title:
        struct['title'] = scene.title
    if scene.information:
        struct['author'] = scene.author
    if scene.information:
        struct['information'] = scene.information
    struct['cells'] = cells_j
    struct['columns'] = columns_j

    return (struct, cells, columns)

def save_file(file, scene, resume=False, pretty=False, gz=False):
    result, _, _ = save(scene, resume)

    if isinstance(file, basestring):
        file = (gzip.open if gz else io.open)(file, 'w')
    if pretty:
        result = json.dumps(result, indent=1, separators=(',', ': '), ensure_ascii=False)
        # Edit the resulting JSON string to join together the numbers that are alone in a line
        lines = result.splitlines(True)
        for i, line in enumerate(lines):
            if line.strip().rstrip(',').isdigit():
                lines[i-1] = lines[i-1].rstrip()+('' if '[' in lines[i-1] else ' ')
                lines[i] = line.strip()
                lines[i+1] = lines[i+1].lstrip()
        result = ''.join(lines)
    else:
        result = json.dumps(result, separators=(',', ':'), ensure_ascii=False)
    file.write(result)


def load(struct, scene, Cell=Cell, Column=Column):
    by_id = [None]*len(struct['cells'])
    
    for j in struct['cells']:
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
    
    for j in struct['columns']:
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
    
    scene.title = struct.get('title') or ''
    scene.author = struct.get('author') or ''
    scene.information = struct.get('information') or ''
    
    scene.full_upd()
    return True

def load_file(file, scene, Cell=Cell, Column=Column, gz=False):
    if isinstance(file, basestring):
        file = (gzip.open if gz else io.open)(file, 'rb')
    jj = file.read()
    if not isinstance(jj, unicode):
        jj = jj.decode('utf-8')
    try:
        jj = json.loads(jj)
    except Exception as e:
        QMessageBox.warning(None, "Error", "Error while parsing JSON:\n{}".format(e))
        return False
    load(jj, scene, Cell=Cell, Column=Column)
    return True


def hexcells_pos(x, y):
    return int(round(x/cos30)), int(round(y*2))

def save_hexcells(file, scene):
    grid = {}
    for it in scene.all():
        if isinstance(it, (Cell, Column)):
            grid[hexcells_pos(it.x(), it.y())] = it
    min_x, max_x = minmax([x for x, y in grid] or [0])
    min_y, max_y = minmax([y for x, y in grid] or [0])
    mid_x, mid_y = (min_x+max_x)//2, (min_y+max_y)//2
    min_t, max_t = 0, 32
    mid_t = (min_t+max_t)//2
    grid = {(x-mid_x+mid_t, y-mid_y+mid_t): it for (x, y), it in grid.items()}
    min_x, max_x = minmax([x for x, y in grid] or [0])
    min_y, max_y = minmax([y for x, y in grid] or [0])
    if min_x<min_t or max_x>max_t:
        raise ValueError("This level is too wide to fit into Hexcells format")
    if min_y<min_t or min_y>max_t:
        raise ValueError("This level is too high to fit into Hexcells format")
    result = [[['.', '.'] for x in range(0, max_t+1)] for y in range(0, max_t+1)]
    for (x, y), it in grid.items():
        r = result[y][x]
        if isinstance(it, Column):
            r[0] = {-90: '>', -60: '\\', 0: '|', 60: '/', 90: '<'}[int(round(it.rotation()))]
        else:
            r[0] = 'x' if it.kind is Cell.full else 'o'
        if it.value is not None:
            if it.together is not None:
                r[1] = 'c' if it.together else 'n'
            else:
                r[1] = '+'
        if isinstance(it, Cell) and it.revealed:
            r[0] = r[0].upper()
    result = '\n'.join(''.join(''.join(part) for part in line) for line in result)
    if isinstance(file, basestring):
        file = io.open(file, 'wb')
    file.write(b'Hexcells level v1'+b'\n')
    file.write(scene.title.encode('utf-8')+b'\n')
    file.write(scene.author.encode('utf-8')+b'\n')
    file.write((b'\n' if '\n' not in scene.information else b'')+scene.information.encode('utf-8')+b'\n')
    file.write(result.encode('utf-8'))
    return True


def load_hexcells(file, scene, Cell=Cell, Column=Column):
    if isinstance(file, basestring):
        file = io.open(file, encoding='utf-8')
    
    level = []

    header = file.readline().strip()
    if header!='Hexcells level v1':
        raise ValueError("Can read only Hexcells level v1")
    
    scene.title = file.readline().strip()
    scene.author = file.readline().strip()
    scene.information = '\n'.join(line for line in [file.readline().strip(), file.readline().strip()] if line)
    
    for y, line in enumerate(file):
        line = line.strip().replace(' ', '')
        
        row = []
        
        for x in range(0, len(line)//2):
            kind, value = line[x*2:x*2+2]
            
            if kind.lower() in 'ox':
                item = Cell()
            elif kind in '\\|/':
                item = Column()
            else:
                continue
            
            item.setX(x*cos30)
            item.setY(y/2)
            
            if isinstance(item, Cell):
                item.kind = Cell.full if kind.lower()=='x' else Cell.empty
                item.revealed = kind.isupper()
                item.show_info = 0 if value=='.' else 1 if value=='+' else 2
            else:
                item.setRotation(-60 if kind=='\\' else 60 if kind=='/' else 1e-3)
                item.show_info = False if value=='+' else True
            
            scene.addItem(item)
        
    scene.full_upd()
    

def about(title):
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
        title, __version__,
        sys.version.split(' ', 1)[0],
        qt.version_str,
        qt.module, qt.module_version_str,
        pulp_version
    ))

def help():
    QDesktopServices.openUrl(QUrl('https://github.com/blaxpirit/sixcells/#readme'))