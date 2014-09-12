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


import sys
import math
import itertools
import collections
import contextlib
import weakref
import json

sys.path.insert(0, 'universal-qt')
import qt
qt.init()
from qt.core import QPointF, QRectF, QSizeF
from qt.gui import QPolygonF, QPen, QBrush, QPainter, QColor, QMouseEvent, QTransform
from qt.widgets import QApplication, QGraphicsScene, QGraphicsView, QGraphicsPolygonItem, QGraphicsSimpleTextItem, QMainWindow, QMessageBox, QFileDialog, QAction

from qt.util import add_to


app = QApplication(sys.argv)


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
    revealed_border = qt.red



def fit_inside(parent, it, k):
    sb = parent.boundingRect()
    it.setBrush(Color.light_text)
    tb = it.boundingRect()
    it.setScale(sb.height()/tb.height()*k)
    tb = it.mapRectToParent(it.boundingRect())
    it.setPos(sb.center()-QPointF(tb.size().width()/2, tb.size().height()/2))

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
            poly.append(QPointF(l*math.sin(a), l*math.cos(a)))
            inner_poly.append(QPointF(il*math.sin(a), il*math.cos(a)))
        
        QGraphicsPolygonItem.__init__(self, poly)

        self.inner = QGraphicsPolygonItem(inner_poly, self)
        pen = QPen(qt.transparent, 0)
        pen.setJoinStyle(qt.MiterJoin)
        self.inner.setPen(pen)

        self.text = QGraphicsSimpleTextItem('', self)
        
        self.prev_show_info = self.next_show_info = 0
        
        self._kind = Hex.unknown
        self._show_info = 0
        self._revealed = False
        self.upd()
        
        self.pre = None
        self.cols = weakref.WeakSet()
    
    @contextlib.contextmanager
    def upd_neighbors(self):
        neighbors = list(self.circle_neighbors())
        scene = self.scene()
        yield
        for it in neighbors:
            it.upd()
        if scene:
            for it in scene.items():
                if isinstance(it, Col):
                    it.upd()

    
    @property
    def kind(self):
        return self._kind
    @kind.setter
    def kind(self, value):
        self._kind = value
        self.upd()
        with self.upd_neighbors():
            pass
    
    @property
    def show_info(self):
        return self._show_info
    @show_info.setter
    def show_info(self, value):
        self._show_info = value
        self.upd()
    
    @property
    def revealed(self):
        return self._revealed
    @revealed.setter
    def revealed(self, value):
        self._revealed = value
        self.upd()
    
    def upd(self):
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
        txt = ''
        if self.show_info:
            items = list(self.circle_neighbors() if self.kind==Hex.full else self.neighbors())
            txt = str(sum(1 for it in items if it.kind==Hex.full))
            if self.show_info==2:
                full_items = {it for it in items if it.kind==Hex.full}
                txt = ('{{{}}}' if all_connected(full_items) else '-{}-').format(txt)
        elif self.kind==Hex.empty:
            txt = '?'
        
        self.text.setText(txt)
        if txt:
            fit_inside(self, self.text, 0.5)
        
        pen = QPen(Color.revealed_border if self.revealed else Color.border, 0.03)
        pen.setJoinStyle(qt.MiterJoin)
        self.setPen(pen)




    def neighbors(self):
        try:
            for it in self.scene().collidingItems(self):
                if isinstance(it, Hex) and it is not self:
                    yield it
        except AttributeError:
            pass
    
    def circle_neighbors(self):
        poly = QPolygonF()
        l = 1.7
        for i in range(6):
            a = i*math.tau/6
            poly.append(QPointF(self.x()+l*math.sin(a), self.y()+l*math.cos(a)))
        try:
            for it in self.scene().items(poly):
                if isinstance(it, Hex) and it is not self:
                    yield it
        except AttributeError:
            pass
    
    def mousePressEvent(self, e):
        if e.button()==qt.LeftButton and e.modifiers()&qt.AltModifier:
            self.revealed = not self.revealed
            e.ignore()
    
    def mouseMoveEvent(self, e):
        if not self.contains(e.pos()): # mouse was dragged outside
            if not self.pre:
                self.pre = Col()
                self.scene().addItem(self.pre)

            angle = math.atan2(e.pos().x(), -e.pos().y())
            if -math.tau/12<angle<math.tau/12:
                self.pre.setX(self.x())
                self.pre.setY(self.y()-1)
                self.pre.setRotation(1e-3) # not zero so font doesn't look different from rotated variants
            elif -3*math.tau/12<angle<-math.tau/12:
                self.pre.setX(self.x()-cos30)
                self.pre.setY(self.y()-0.5)
                self.pre.setRotation(-60)
            elif math.tau/12<angle<3*math.tau/12:
                self.pre.setX(self.x()+cos30)
                self.pre.setY(self.y()-0.5)
                self.pre.setRotation(60)
            else:
                self.scene().removeItem(self.pre)
                self.pre = None
            

    
    def mouseReleaseEvent(self, e):
        if self.scene().supress:
            return
        if not self.pre:
            if self.contains(e.pos()): # mouse was not dragged outside
                if e.button()==qt.LeftButton:
                    self.kind = Hex.empty if self.kind==Hex.full else Hex.full
                    self.prev_show_info = self.show_info
                    if self.next_show_info is not None:
                        self.show_info = self.next_show_info
                        self.next_show_info = None
                    else:
                        self.show_info = self.kind==Hex.empty
                elif e.button()==qt.RightButton:
                    for col in self.cols:
                        self.scene().removeItem(col)
                    with self.upd_neighbors():
                        self.scene().removeItem(self)
        else:
            for it in self.scene().collidingItems(self.pre):
                if it is self.pre.text:
                    continue
                self.scene().removeItem(self.pre)
                break
            else:
                self.pre.upd()
                self.cols.add(self.pre)
            self.pre = None
    
    def mouseDoubleClickEvent(self, e):
        try:
            self.next_show_info = (self.prev_show_info+1)%3
        except TypeError:
            pass

class Col(QGraphicsPolygonItem):
    def __init__(self):
        poly = QPolygonF()
        l = 0.48/cos30
        for i in range(6):
            a = i*math.tau/6-math.tau/12
            poly.append(QPointF(l*math.sin(a), l*math.cos(a)))
        
        QGraphicsPolygonItem.__init__(self, poly)

        self.setBrush(QColor(255, 255, 255, 0))
        pen = QPen(qt.transparent, 0) #TODO
        self.setPen(pen)
        
        self.text = QGraphicsSimpleTextItem('v', self)
        fit_inside(self, self.text, 0.5)
        self.text.setY(self.text.y()+0.2)
        self.text.setBrush(Color.dark_text)
        
        self._show_info = False
    
    def mousePressEvent(self, e):
        pass
    
    def mouseReleaseEvent(self, e):
        if self.scene().supress:
            return
        if self.contains(e.pos()): # mouse was not dragged outside
            if e.button()==qt.LeftButton:
                self.show_info = not self.show_info
            elif e.button()==qt.RightButton:
                self.scene().removeItem(self)
    
    def members(self):
        sr = self.scene().sceneRect()
        poly = QPolygonF(QRectF(-0.001, 0, 0.002, 2*max(sr.width(), sr.height())))
        if abs(self.rotation())>1e-2:
            poly = QTransform().rotate(self.rotation()).map(poly)
        poly.translate(self.scenePos())
        items = self.scene().items(poly)
        for it in items:
            if isinstance(it, Hex):
                if not poly.containsPoint(it.pos(), qt.OddEvenFill):
                    raise ValueError()
                yield it
        
    @property
    def show_info(self):
        return self._show_info
    @show_info.setter
    def show_info(self, value):
        self._show_info = value
        self.upd()

    def upd(self):
        try:
            members = list(self.members())
        except ValueError:
            txt = '!?'
        else:
            txt = str(sum(1 for it in members if it.kind==Hex.full))
            if self.show_info:
                items = sorted(members, key=lambda it: (it.y(), it.x()))
                groups = itertools.groupby(items, key=lambda it: it.kind==Hex.full)
                all_connected = sum(1 for kind, _ in groups if kind==Hex.full)<=1
                txt = ('{{{}}}' if all_connected else '-{}-').format(txt)
        self.text.setText(txt)
        self.text.setX(-self.text.boundingRect().width()*self.text.scale()/2)


        

class Scene(QGraphicsScene):
    def __init__(self):
        QGraphicsScene.__init__(self)
        self.pre = None
    
    def place(self, p):
        if not self.pre:
            self.pre = Hex()
            self.pre.kind = Hex.unknown
            self.pre.setOpacity(0.4)
            self.addItem(self.pre)
        x, y = p.x(), p.y()
        x = round(x/cos30)
        y = round(y*2)/2
        #if x%2==0:
            #y = round(y)
        #else:
            #y = round(y+0.5)-0.5
        x *= cos30
        self.pre.setPos(x, y)

    
    def mousePressEvent(self, e):
        if self.supress:
            return
        if e.button()==qt.LeftButton:
            if not self.itemAt(e.scenePos(), QTransform()):
                self.place(e.scenePos())
                return
        QGraphicsScene.mousePressEvent(self, e)

    def mouseMoveEvent(self, e):
        if self.supress:
            return
        if self.pre:
            self.place(e.scenePos())
        else:
            QGraphicsScene.mouseMoveEvent(self, e)

    
    def mouseReleaseEvent(self, e):
        if self.supress:
            return
        if self.pre:
            for it in self.collidingItems(self.pre):
                if it is self.pre.inner:
                    continue
                if not isinstance(it, Hex):
                    # it's an inner part
                    self.removeItem(self.pre)
                    break
            else:
                self.pre.setOpacity(1)
                self.pre.kind = Hex.empty
                self.pre.show_info = True
            self.pre = None
        else:
            QGraphicsScene.mouseReleaseEvent(self, e)
        

class View(QGraphicsView):
    def __init__(self, scene):
        QGraphicsView.__init__(self, scene)
        self.scene = scene
        self.scene.supress = False
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setRenderHints(self.renderHints()|QPainter.Antialiasing)
        inf = -1e10
        self.setHorizontalScrollBarPolicy(qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(qt.ScrollBarAlwaysOff)
        self.setSceneRect(QRectF(QPointF(-inf, -inf), QPointF(inf, inf)))

    def mousePressEvent(self, e):
        if e.button()==qt.MidButton:
            fake = QMouseEvent(e.type(), e.pos(), qt.LeftButton, qt.LeftButton, e.modifiers())
            self.scene.supress = True
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            QGraphicsView.mousePressEvent(self, fake)
        else:
            QGraphicsView.mousePressEvent(self, e)
    
    def _ensure_visible(self):
        self.ensureVisible(QRectF(self.scene.itemsBoundingRect().center(), QSizeF(1e-10, 1e-10)))
    
    def resizeEvent(self, e):
        QGraphicsView.resizeEvent(self, e)
        self._ensure_visible()
    
    def mouseReleaseEvent(self, e):
        if e.button()==qt.MidButton:
            fake = QMouseEvent(e.type(), e.pos(), qt.LeftButton, qt.LeftButton, e.modifiers())
            QGraphicsView.mouseReleaseEvent(self, fake)
            self.setDragMode(QGraphicsView.NoDrag)
            self._ensure_visible()
            self.scene.supress = False
        else:
            QGraphicsView.mouseReleaseEvent(self, e)

    def wheelEvent(self, e):
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        d = 1.0015**e.delta()
        self.scale(d, d)
        self._ensure_visible()


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.scene = Scene()

        self.view = View(self.scene)
        self.setCentralWidget(self.view)
        
        
        add_to(self.menuBar().addMenu("File"),
            QAction("Save...", self, triggered=self.save_file),
            None,
            QAction("Quit", self, triggered=self.close),
        )
        add_to(self.menuBar().addMenu("Help"),
            QAction("About", self, triggered=self.about),
        )
        
        self.setWindowTitle("SixCells Editor")
    
    @staticmethod
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
    
    def save_file(self):
        fn, _ = QFileDialog.getSaveFileName(self, "Save")
        if not fn:
            return
        
        hexs, cols = [], []
        for it in self.scene.items():
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
            self._save_common(j, it)
            hexs_j.append(j)
        
        for it in cols:
            j = collections.OrderedDict()
            j['members'] = [hexs.index(n) for n in it.members()]
            self._save_common(j, it)
            cols_j.append(j)
        
        result = collections.OrderedDict([('hexs', hexs_j), ('cols', cols_j)])
        
        with open(fn, 'w') as f:
            json.dump(result, f, indent=2)
    
    def about(self):
        QMessageBox.information(None, "About", """
            <h1>SixCells Editor</h1>
            <h3>Version 0.1</h3>

            <p>(C) 2014 Oleh Prypin &lt;<a href="mailto:blaxpirit@gmail.com">blaxpirit@gmail.com</a>&gt;</p>

            <p>License: <a href="http://www.gnu.org/licenses/gpl.txt">GNU General Public License Version 3</a></p>

            Using:
            <ul>
            <li>Python {}
            <li>Qt {}
            <li>{} {}
            </ul>
        """.format(
            sys.version.split(' ', 1)[0],
            qt.version_str,
            qt.module, qt.module_version_str,
        ))

    

def main():
    w = MainWindow()
    w.showMaximized()
    app.processEvents()
    w.view.scale(50, 50)
    #w.view.fitInView(w.scene.sceneRect().adjusted(-1, -1, 1, 1), qt.KeepAspectRatio)

    app.exec_()

if __name__=='__main__':
    main(*sys.argv[1:])