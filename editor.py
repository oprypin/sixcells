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

from qt.core import QPointF, QRectF, QSizeF, QTimer
from qt.gui import QPolygonF, QPen, QPainter, QMouseEvent, QTransform, QPainterPath, QKeySequence
from qt.widgets import QApplication, QGraphicsView, QMainWindow, QMessageBox, QFileDialog, QGraphicsItem, QGraphicsPathItem



class Cell(common.Cell):
    def __init__(self):
        self._revealed = False
        self._show_info = 0
        self.preview = None
        self.columns = weakref.WeakSet()

        common.Cell.__init__(self)

    @event_property
    def show_info(self):
        self.upd()

    @event_property
    def revealed(self):
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
            except KeyError: pass
            self.setOpacity(1)

    @property
    def neighbors(self):
        if not self.scene():
            return
        for it in self.scene().collidingItems(self):
            if isinstance(it, Cell):
                yield it
    
    @property
    def flower_neighbors(self):
        if not self.scene():
            return
        poly = QPolygonF()
        l = 1.7
        for i in range(6):
            a = i*tau/6
            poly.append(QPointF(self.x()+l*math.sin(a), self.y()+l*math.cos(a)))
        for it in self.scene().items(poly):
            if isinstance(it, Cell) and it is not self:
                yield it
    
    @property
    def members(self):
        return (self.flower_neighbors if self.kind is Cell.full else self.neighbors)

    @property
    def together(self):
        if self.show_info==2:
            full_items = {it for it in self.members if it.kind is Cell.full}
            return all_grouped(full_items, key=Cell.is_neighbor)
    @together.setter
    def together(self, value):
        if value is not None:
            self.show_info = 2
        else:
            self.show_info = min(self.show_info, 1)

    @property
    def value(self):
        if self.show_info:
            return sum(1 for it in self.members if it.kind is Cell.full)
    @value.setter
    def value(self, value):
        if value is not None:
            self.show_info = max(self.show_info, 1)
        else:
            self.show_info = 0

    def is_neighbor(self, other):
        return self.collidesWithItem(other)
    
    def overlaps(self, other, allow_horz=False):
        if self.collidesWithItem(other):
            dist = distance(self, other)
            if allow_horz and dist>0.85 and abs(self.y()-other.y())<1e-3:
                return False
            if dist<0.98:
                return True
        return False

    def upd(self, first=True):
        if not self.scene():
            return
        
        common.Cell.upd(self)
        
        if self.revealed:
            self.setBrush(Color.revealed_border)
        #pen = QPen(Color.revealed_border if self.revealed else Color.border, 0.03)
        #pen.setJoinStyle(qt.MiterJoin)
        #self.setPen(pen)

        if first:
            with self.upd_neighbors():
                pass

    @contextlib.contextmanager
    def upd_neighbors(self):
        neighbors = list(self.flower_neighbors)
        scene = self.scene()
        yield
        for it in neighbors:
            it.upd(False)
        for it in scene.all(Column):
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
                if not self.last_tried or not (distance((x, y), self.last_tried)<1e-3):
                    self.last_tried = x, y
                    for it in self.scene().selection:
                        it.original_pos = it.pos()
                        it.setX(it.x()+dx)
                        it.setY(it.y()+dy)
                        for col in it.columns:
                            col.original_pos = col.pos()
                            col.setX(col.x()+dx)
                            col.setY(col.y()+dy)
                    for it in self.scene().selection:
                        bad = False
                        for x in it.collidingItems():
                            if x.overlaps(it) and isinstance(x, (Cell, Column)) and x is not it:
                                bad = True
                                break
                        for c in it.columns:
                            for x in c.collidingItems():
                                if isinstance(x, (Cell, Column)):
                                    bad = True
                                    break
                        if bad:
                            for it in self.scene().selection:
                                it.setPos(it.original_pos)
                                for col in it.columns:
                                    col.setPos(col.original_pos)
                
        elif not self.contains(e.pos()): # mouse was dragged outside
            if not self.preview:
                self.preview = Column()
                self.scene().addItem(self.preview)

            angle = math.atan2(e.pos().x(), -e.pos().y())*360/tau
            if -30<angle<30:
                self.preview.setX(self.x())
                self.preview.setY(self.y()-1)
                self.preview.setRotation(1e-3) # not zero so font doesn't look different from rotated variants
            elif -90<angle<-30:
                self.preview.setX(self.x()-cos30)
                self.preview.setY(self.y()-0.5)
                self.preview.setRotation(-60)
            elif 30<angle<90:
                self.preview.setX(self.x()+cos30)
                self.preview.setY(self.y()-0.5)
                self.preview.setRotation(60)
            elif -120<angle<-90:
                self.preview.setX(self.x()-cos30*1.3)
                self.preview.setY(self.y())
                self.preview.setRotation(-90+1e-3)
            elif 90<angle<120:
                self.preview.setX(self.x()+cos30*1.3)
                self.preview.setY(self.y())
                self.preview.setRotation(90-1e-3)
            else:
                self.scene().removeItem(self.preview)
                self.preview = None
    
    def mouseReleaseEvent(self, e):
        if self.scene().supress:
            return
        if self.scene().selection:
            self.scene().full_upd()

        if e.modifiers()&(qt.ShiftModifier|qt.AltModifier) or self.scene().selection:
            e.ignore()
            return
        if not self.preview:
            if self.contains(e.pos()): # mouse was not dragged outside
                if e.button()==qt.LeftButton:
                    try:
                        self.show_info = (self.show_info+1)%3
                        if self.show_info==2 and self.value<=1:
                            self.show_info = (self.show_info+1)%3
                    except TypeError:
                        pass
                elif e.button()==qt.RightButton:
                    for col in self.columns:
                        self.scene().removeItem(col)
                    with self.upd_neighbors():
                        self.scene().removeItem(self)
        else:
            for it in self.preview.collidingItems():
                self.scene().removeItem(self.preview)
                self.preview = None
                break
            else:
                self.preview.upd()
                self.preview.cell = self
            self.preview = None


class Column(common.Column):
    def __init__(self):
        common.Column.__init__(self)
        
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
            if isinstance(it, Cell):
                if not poly.containsPoint(it.pos(), qt.OddEvenFill):
                    continue
                yield it
    
    @event_property
    def show_info(self):
        self.upd()
    
    @property
    def value(self):
        return sum(1 for it in self.members if it.kind is Cell.full)
    
    @setter_property
    def cell(self, value):
        try:
            self.cell.columns.remove(self)
        except (AttributeError, KeyError):
            pass
        yield value
        value.columns.add(self)
    
    @property
    def together(self):
        if self.show_info:
            items = sorted(self.members, key=lambda it: (it.y(), it.x()))
            groups = itertools.groupby(items, key=lambda it: it.kind is Cell.full)
            return sum(1 for kind, _ in groups if kind is Cell.full)<=1
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


class Scene(common.Scene):
    def __init__(self):
        common.Scene.__init__(self)
        self.preview = None
        self.selection = set()
        self.selection_path_item = None
    
    def place(self, p):
        if not self.preview:
            self.preview = Cell()
            self.preview.kind = Cell.unknown
            self.preview.setOpacity(0.4)
            self.addItem(self.preview)
        x, y = convert_pos(p.x(), p.y())
        self.preview.setPos(x, y)
        self.preview.upd()

    
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
                    self.selection_path_item = QGraphicsPathItem()
                    self.selection_path = path = QPainterPath()
                    self.selection_path_item.setPen(QPen(Color.selection, 0, qt.DashLine))
                    path.moveTo(e.scenePos())
                    self.selection_path_item.setPath(path)
                    self.addItem(self.selection_path_item)
                else:
                    self.place(e.scenePos())
                return
        
        QGraphicsScene.mousePressEvent(self, e)

    def mouseMoveEvent(self, e):
        if self.supress:
            return
        if self.selection_path_item:
            p = self.selection_path
            p.lineTo(e.scenePos())
            p2 = QPainterPath(p)
            p2.lineTo(p.pointAtPercent(0))
            self.selection_path_item.setPath(p2)
        elif self.preview:
            self.place(e.scenePos())
        else:
            QGraphicsScene.mouseMoveEvent(self, e)

    
    def mouseReleaseEvent(self, e):
        if self.supress:
            return
        if self.selection_path_item:
            p = self.selection_path
            p.lineTo(p.pointAtPercent(0))
            for it in self.items(p, qt.IntersectsItemShape):
                if isinstance(it, Cell):
                    it.selected = True
            self.removeItem(self.selection_path_item)
            self.selection_path_item = None

        elif self.preview:
            col = None
            for it in self.collidingItems(self.preview):
                pass
                if isinstance(it, Column) and distance(it, self.preview)<1e-3:
                    col = it
                    continue
                if isinstance(it, Cell) and self.preview.overlaps(it, allow_horz=e.modifiers()&qt.AltModifier):
                    with self.preview.upd_neighbors():
                        self.removeItem(self.preview)
                    self.preview = None
                    break
            else:
                self.preview.setOpacity(1)
                self.preview.kind = Cell.empty
                self.preview.show_info = 1
                if col:
                    old_cell = col.cell
                    col.cell = self.preview
                    col.setPos(col.pos()-old_cell.pos()+self.preview.pos())
            self.preview = None
        else:
            QGraphicsScene.mouseReleaseEvent(self, e)
    
    def mouseDoubleClickEvent(self, e):
        it = self.itemAt(e.scenePos(), QTransform())
        if not it:
            return
        if isinstance(it, Cell):
            pass
        elif isinstance(it.parentItem(), Cell):
            it = it.parentItem()
        else:
            return
        if it.kind is Cell.full:
            it.kind = Cell.empty
            it.show_info = 1
        else:
            it.kind = Cell.full
            it.show_info = 0



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
        try:
            d = e.angleDelta().y()
        except AttributeError:
            d = e.delta()
        d = 1.0015**d
        
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

        menu = self.menuBar().addMenu("File")
        menu.addAction("Save...", self.save_file, QKeySequence.Save)
        menu.addAction("Open...", self.open_file, QKeySequence.Open)
        menu.addSeparator()
        menu.addAction("Quit", self.close, QKeySequence.Quit)

        menu = self.menuBar().addMenu("Play")
        menu.addAction("From Start", self.play, QKeySequence('`'))
        menu.addAction("Resume", lambda: self.play(resume=True), QKeySequence('Tab'))
        
        menu = self.menuBar().addMenu("Help")
        menu.addAction("Instructions", help, QKeySequence.HelpContents)
        menu.addAction("About", lambda: about(self.windowTitle()))
        
        
    
    def save_file(self, fn=None, resume=False):
        filt = ''
        if not fn:
            try:
                dialog = QFileDialog.getSaveFileNameAndFilter
            except AttributeError:
                dialog = QFileDialog.getSaveFileName
            fn, filt = dialog(self, "Save", filter="SixCells level (JSON, gzipped) (*.sixcells.gz);;SixCells level (JSON) (*.sixcells)")#;;HexCells level (EXPORT ONLY) (*.hexcells)
        if not fn:
            return
        if 'hexcells' in filt:
            try:
                return save_hexcells(fn, self.scene)
            except ValueError as e:
                QMessageBox.warning(None, "Error", str(e))
        try:
            gz = fn.endswith('.gz')
        except AttributeError:
            gz = False
        return save(fn, self.scene, resume=resume, pretty=True, gz=gz)
    
    def open_file(self, fn=None):
        if not fn:
            try:
                dialog = QFileDialog.getOpenFileNameAndFilter
            except AttributeError:
                dialog = QFileDialog.getOpenFileName
            fn, _ = dialog(self, "Open", filter="SixCells level (JSON) (*.sixcells *.sixcells.gz)")
        if not fn:
            return
        self.scene.clear()
        load(fn, self.scene, gz=fn.endswith('.gz'), Cell=Cell, Column=Column)
        for it in self.scene.all(Column):
            it.cell = min(it.members, key=lambda m: (m.pos()-it.pos()).manhattanLength())
        self.view.fitInView(self.scene.itemsBoundingRect().adjusted(-0.5, -0.5, 0.5, 0.5), qt.KeepAspectRatio)
    
    def play(self, resume=False):
        import player
        
        player.app = app
        try:
            f = io.StringIO()
            self.save_file(f)
            self.player_by_id = self.save_file(f, resume=resume)
        except TypeError:
            f = io.BytesIO()
            self.player_by_id = self.save_file(f, resume=resume)
        f.seek(0)
        
        window = player.MainWindow(playtest=True)
        window.setWindowModality(qt.ApplicationModal)
        window.setGeometry(self.geometry())

        windowcloseevent = window.closeEvent
        def closeevent(e):
            windowcloseevent(e)
            for it in window.scene.all(player.Cell):
                self.player_by_id[it.id].revealed_resume = it.kind is not Cell.unknown
        window.closeEvent = closeevent

        window.show()
        def delayed():
            window.open_file(f)
            #player.View.fit(self.view)
            window.view.setSceneRect(self.view.sceneRect())
            window.view.setTransform(self.view.transform())
            window.view.horizontalScrollBar().setValue(self.view.horizontalScrollBar().value())
            window.view.verticalScrollBar().setValue(self.view.verticalScrollBar().value())
        QTimer.singleShot(0, delayed)
            

        

    
def main(f=None):
    global app, window

    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.showMaximized()

    if not f and len(sys.argv[1:])==1:
        f = sys.argv[1]
    if f:
        QTimer.singleShot(50, lambda: window.open_file(f))
    
    app.exec_()

if __name__=='__main__':
    main()