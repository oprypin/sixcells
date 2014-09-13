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
import contextlib
import weakref
import io

import common
from common import *
from qt.util import add_to



class Hex(common.Hex):
    def __init__(self):
        self._revealed = False
        self._show_info = 0
        self.prev_show_info = self.next_show_info = None
        self.pre = None
        self.cols = weakref.WeakSet()

        common.Hex.__init__(self)

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

    @property
    def selected(self):
        return self in self.scene().selection
    @selected.setter
    def selected(self, value):
        if value:
            self.scene().selection.add(self)
            self.setOpacity(0.5)
        else:
            try:
                self.scene().selection.remove(self)
            except KeyError:
                pass
            self.setOpacity(1)
        self.update()

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
    
    @property
    def members(self):
        return (self.circle_neighbors() if self.kind==Hex.full else self.neighbors())

    @property
    def together(self):
        if self.show_info==2:
            full_items = {it for it in self.members if it.kind==Hex.full}
            return all_connected(full_items)
    @together.setter
    def together(self, value):
        if value is not None:
            self.show_info = 2
        else:
            self.show_info = min(self.show_info, 1)

    @property
    def value(self):
        if self.show_info:
            return sum(1 for it in self.members if it.kind==Hex.full)
    @value.setter
    def value(self, value):
        if value is not None:
            self.show_info = max(self.show_info, 1)
        else:
            self.show_info = 0


    def upd(self, first=True):
        if not self.scene():
            return
        
        common.Hex.upd(self)
        
        pen = QPen(Color.revealed_border if self.revealed else Color.border, 0.03)
        pen.setJoinStyle(qt.MiterJoin)
        self.setPen(pen)

        if first:
            with self.upd_neighbors():
                pass

    @contextlib.contextmanager
    def upd_neighbors(self):
        neighbors = list(self.circle_neighbors())
        scene = self.scene()
        yield
        for it in neighbors:
            it.upd(False)
        for it in scene.items():
            if isinstance(it, Col):
                it.upd()

    def mousePressEvent(self, e):
        if e.button()==qt.LeftButton and e.modifiers()&qt.ShiftModifier:
            self.selected = not self.selected
            e.ignore()
        if self.scene().selection:
            self.last_tried = None
            return
        if e.button()==qt.LeftButton and e.modifiers()&qt.AltModifier:
            self.revealed = not self.revealed
            e.ignore()
        
        
    
    def mouseMoveEvent(self, e):
        if self.scene().selection:
            if self.selected:
                x, y = convert_pos(e.scenePos().x(), e.scenePos().y())
                dx = x-self.x()
                dy = y-self.y()
                if not self.last_tried or not (abs(x-self.last_tried[0])<1e-3 and abs(y-self.last_tried[1])<1e-3):
                    self.last_tried = x, y
                    for it in self.scene().selection:
                        it.original_pos = it.pos()
                        it.setX(it.x()+dx)
                        it.setY(it.y()+dy)
                        for col in it.cols:
                            col.original_pos = col.pos()
                            col.setX(col.x()+dx)
                            col.setY(col.y()+dy)
                    for it in self.scene().selection:
                        bad = False
                        for x in it.inner.collidingItems():
                            if isinstance(x, (Hex, Col)) and x is not it:
                                bad = True
                                break
                        for c in it.cols:
                            for x in c.collidingItems():
                                if isinstance(x, (Hex, Col)):
                                    bad = True
                                    break
                        if bad:
                            for it in self.scene().selection:
                                it.setPos(it.original_pos)
                                for col in it.cols:
                                    col.setPos(col.original_pos)
                
        elif not self.contains(e.pos()): # mouse was dragged outside
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
        if self.scene().selection:
            self.scene().full_upd()

        if e.modifiers()&(qt.ShiftModifier|qt.AltModifier) or self.scene().selection:
            e.ignore()
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


class Col(common.Col):
    def __init__(self):
        common.Col.__init__(self)
        
        self._show_info = False

    @property
    def members(self):
        try:
            sr = self.scene().sceneRect()
        except AttributeError:
            return
        poly = QPolygonF(QRectF(-0.001, 0.05, 0.002, 2*max(sr.width(), sr.height())))
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
    
    @property
    def value(self):
        return sum(1 for it in self.members if it.kind==Hex.full)
    
    @property
    def together(self):
        if self.show_info:
            items = sorted(self.members, key=lambda it: (it.y(), it.x()))
            groups = itertools.groupby(items, key=lambda it: it.kind==Hex.full)
            return sum(1 for kind, _ in groups if kind==Hex.full)<=1
    @together.setter
    def together(self, value):
        self.show_info = value is not None

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



def convert_pos(x, y):
    x = round(x/cos30)
    y = round(y*2)/2
    #if x%2==0:
        #y = round(y)
    #else:
        #y = round(y+0.5)-0.5
    x *= cos30
    return x, y


class Scene(QGraphicsScene):
    def __init__(self):
        QGraphicsScene.__init__(self)
        self.pre = None
        self.selection = set()
        self.selection_path = None
    
    def place(self, p):
        if not self.pre:
            self.pre = Hex()
            self.pre.kind = Hex.unknown
            self.pre.setOpacity(0.4)
            self.addItem(self.pre)
        x, y = convert_pos(p.x(), p.y())
        self.pre.setPos(x, y)
        self.pre.upd()

    
    def mousePressEvent(self, e):
        if self.supress:
            return
        #if self.itemAt(e.scenePos(), QTransform()):
            #return
        
        if self.selection:
            if (e.button()==qt.LeftButton and not self.itemAt(e.scenePos(), QTransform())) or e.button()==qt.RightButton:
                old_selection = self.selection
                self.selection = set()
                for it in old_selection:
                    try:
                        it.selected = False
                    except AttributeError:
                        pass
        if e.button()==qt.LeftButton:
            if not self.itemAt(e.scenePos(), QTransform()):
                if e.modifiers()&qt.ShiftModifier:
                    self.selection_path = QGraphicsPathItem()
                    self.selection_ppath = p = QPainterPath()
                    self.selection_path.setPen(QPen(qt.black, 0, qt.DashLine))
                    p.moveTo(e.scenePos())
                    self.selection_path.setPath(p)
                    self.addItem(self.selection_path)
                else:
                    self.place(e.scenePos())
                return
        
        QGraphicsScene.mousePressEvent(self, e)

    def mouseMoveEvent(self, e):
        if self.supress:
            return
        if self.selection_path:
            p = self.selection_ppath
            p.lineTo(e.scenePos())
            p2 = QPainterPath(p)
            p2.lineTo(p.pointAtPercent(0))
            self.selection_path.setPath(p2)
        elif self.pre:
            self.place(e.scenePos())
        else:
            QGraphicsScene.mouseMoveEvent(self, e)

    
    def mouseReleaseEvent(self, e):
        if self.supress:
            return
        if self.selection_path:
            p = self.selection_ppath
            p.lineTo(p.pointAtPercent(0))
            for it in self.items(p, qt.IntersectsItemShape):
                if isinstance(it, Hex):
                    it.selected = True
            self.removeItem(self.selection_path)
            self.selection_path = None

        elif self.pre:
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
    
    def full_upd(self):
        for it in self.items():
            if isinstance(it, Hex):
                it.upd(False)
        for it in self.items():
            if isinstance(it, Col):
                it.upd()

        

class View(QGraphicsView):
    def __init__(self, scene):
        QGraphicsView.__init__(self, scene)
        self.scene = scene
        self.scene.supress = False
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setRenderHints(self.renderHints()|QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(qt.ScrollBarAlwaysOff)
        inf = -1e10
        self.setSceneRect(QRectF(QPointF(-inf, -inf), QPointF(inf, inf)))
        self.scale(50, 50)


    def mousePressEvent(self, e):
        if e.button()==qt.MidButton or (e.button()==qt.RightButton and not self.scene.itemAt(self.mapToScene(e.pos()), QTransform())):
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
        if e.button()==qt.MidButton or (e.button()==qt.RightButton and self.scene.supress):
            fake = QMouseEvent(e.type(), e.pos(), qt.LeftButton, qt.LeftButton, e.modifiers())
            QGraphicsView.mouseReleaseEvent(self, fake)
            self.setDragMode(QGraphicsView.NoDrag)
            self._ensure_visible()
            self.scene.supress = False
        else:
            QGraphicsView.mouseReleaseEvent(self, e)

    def wheelEvent(self, e):
        d = 1.0015**e.delta()
        self.scale(d, d)
        self._ensure_visible()


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        self.resize(1280, 720)
            
        self.scene = Scene()

        self.view = View(self.scene)
        self.setCentralWidget(self.view)
        
        self.setWindowTitle("SixCells Editor")

        add_to(self.menuBar().addMenu("File"),
            QAction("Save...", self, triggered=self.save_file),
            QAction("Open...", self, triggered=self.open_file),
            None,
            QAction("Quit", self, triggered=self.close),
        )
        add_to(self.menuBar(),
            QAction("Play", self, triggered=self.play),
        )
        add_to(self.menuBar().addMenu("Help"),
            QAction("Instructions", self, triggered=help),
            QAction("About", self, triggered=lambda: about(self.windowTitle())),
        )
        
    
    def save_file(self, fn=None):
        if not fn:
            fn, _ = QFileDialog.getSaveFileName(self, "Save")
        if not fn:
            return
        save(fn, self.scene)
    
    def open_file(self, fn=None):
        if not fn:
            fn, _ = QFileDialog.getOpenFileName(self, "Open")
        if not fn:
            return
        self.scene.clear()
        load(fn, self.scene, Hex=Hex, Col=Col)
        for it in self.scene.items():
            if isinstance(it, Col):
                min(it.members, key=lambda m: (m.pos()-it.pos()).manhattanLength()).cols.add(it)
        self.view.fitInView(self.scene.itemsBoundingRect().adjusted(-0.5, -0.5, 0.5, 0.5), qt.KeepAspectRatio)
    
    def play(self):
        import player

        try:
            f = io.StringIO()
            self.save_file(f)
        except TypeError:
            f = io.BytesIO()
            self.save_file(f)
        f.seek(0)
        
        w = player.MainWindow()
        w.showMaximized()
        QTimer.singleShot(100, lambda: w.open_file(f))
        

    
def main(f=None):
    w = MainWindow()
    w.showMaximized()

    if not f and len(sys.argv[1:])==1:
        f = sys.argv[1]
    if f:
        QTimer.singleShot(100, lambda: w.open_file(f))
    
    app.exec_()

if __name__=='__main__':
    main()