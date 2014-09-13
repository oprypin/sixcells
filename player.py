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
import itertools

import common
from common import *
from qt.util import add_to


class Hex(common.Hex):
    def __init__(self):
        common.Hex.__init__(self)
        
        self.value = None

    def mousePressEvent(self, e):
        if e.button()==qt.LeftButton:
            want = Hex.empty
        elif e.button()==qt.RightButton:
            want = Hex.full
        else:
            return
        if self.kind==Hex.unknown:
            if self.actual==want:
                self.kind = self.actual
                if self.kind==Hex.full:
                    self.scene().remaining -= 1
            else:
                self.scene().mistakes += 1


class Col(common.Col):
    def __init__(self):
        common.Col.__init__(self)
        self.beam = False
    
    @property
    def beam(self):
        return self._beam
    @beam.setter
    def beam(self, value):
        self._beam = value
        if self.scene():
            self.scene().update()
    
    @property
    def hidden(self):
        return self.opacity()<1
    @hidden.setter
    def hidden(self, value):
        self.setOpacity(0.2 if value else 1)
    
    def mousePressEvent(self, e):
        if e.button()==qt.LeftButton:
            self.beam = not self.beam
        elif e.button()==qt.RightButton:
            self.hidden = not self.hidden
            self.beam = False


class Scene(QGraphicsScene):
    text_changed = Signal()

    def __init__(self):
        QGraphicsScene.__init__(self)

    @property
    def remaining(self):
        return self._remaining
    @remaining.setter
    def remaining(self, value):
        self._remaining = value
        self.text_changed.emit()

    @property
    def mistakes(self):
        return self._mistakes
    @mistakes.setter
    def mistakes(self, value):
        self._mistakes = value
        self.text_changed.emit()
    
    def drawForeground(self, g, rect):
        g.setBrush(Color.beam)
        g.setPen(qt.NoPen)
        for it in self.items():
            if isinstance(it, Col) and it.beam:
                t = g.transform()
                poly = QPolygonF(QRectF(-0.03, 0.525, 0.06, 1000))
                poly = QTransform().translate(it.scenePos().x(), it.scenePos().y()).rotate(it.rotation()).map(poly)
                poly = poly.intersected(QPolygonF(rect))
                g.drawConvexPolygon(poly)
                g.setTransform(t)
    
    def full_upd(self):
        for it in self.items():
            if isinstance(it, Hex):
                it.upd(False)
        for it in self.items():
            if isinstance(it, Col):
                it.upd()
    
    def solve(self):
        hexs = [it for it in self.items() if isinstance(it, Hex)]
        cols = [it for it in self.items() if isinstance(it, Col)]
        
        known = [it for it in hexs if it.kind is not Hex.unknown]
        for cur in itertools.chain(known, cols):
            if not any(x.kind is Hex.unknown for x in cur.members):
                continue
            if cur.value is not None:
                # Fill up remaining fulls
                if cur.value==sum(1 for x in cur.members if x.kind is not Hex.empty):
                    for x in cur.members:
                        if x.kind is Hex.unknown:
                            assert x.actual==Hex.full
                            x.kind = x.actual
                    if isinstance(cur, Col):
                        cur.hidden = True
                    yield
                # Fill up remaining empties
                if len(cur.members)-cur.value==sum(1 for x in cur.members if x.kind is not Hex.full):
                    for x in cur.members:
                        if x.kind is Hex.unknown:
                            assert x.actual==Hex.empty
                            x.kind = x.actual
                    if isinstance(cur, Col):
                        cur.hidden = True
                    yield
            
    
    def do_solve(self):
        try:
            next(self.solve())
        except StopIteration:
            pass


class View(QGraphicsView):
    def __init__(self, scene):
        QGraphicsView.__init__(self, scene)
        self.scene = scene
        self.scene.text_changed.connect(lambda: self.resizeEvent(None))
        self.setRenderHints(self.renderHints()|QPainter.Antialiasing)
        self._fit()

    def resizeEvent(self, e):
        QGraphicsView.resizeEvent(self, e)
        self._fit()

    def _fit(self):
        self.fitInView(self.scene.itemsBoundingRect().adjusted(-0.5, -0.5, 0.5, 0.5), qt.KeepAspectRatio)
    
    def paintEvent(self, e):
        QGraphicsView.paintEvent(self, e)
        g = QPainter(self.viewport())
        g.setRenderHints(self.renderHints())
        try:
            font = self._text_font
        except AttributeError:
            self._text_font = font = g.font()
            font.setPointSize(30 if font.pointSize()==-1 else font.pointSize()*3)
        g.setFont(font)
        try:
            txt = ('{r} ({m})' if self.scene.mistakes else '{r}').format(r=self.scene.remaining, m=self.scene.mistakes)
            g.drawText(self.viewport().rect().adjusted(5, 2, -5, -2), qt.AlignTop|qt.AlignRight, txt)
        except AttributeError:
            pass
    

    


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.resize(1280, 720)

        self.scene = Scene()

        self.view = View(self.scene)
        self.setCentralWidget(self.view)
        
        self.setWindowTitle("SixCells Player")
        
        add_to(self.menuBar().addMenu("File"),
            QAction("Open...", self, triggered=self.open_file),
            None,
            QAction("Quit", self, triggered=self.close),
        )
        add_to(self.menuBar(),
            QAction("Solve", self, triggered=self.scene.do_solve),
        )
        add_to(self.menuBar().addMenu("Help"),
            QAction("Instructions", self, triggered=help),
            QAction("About", self, triggered=lambda: about(self.windowTitle())),
        )
        
    
    def open_file(self, fn=None):
        if not fn:
            fn, _ = QFileDialog.getOpenFileName(self, "Open")
        if not fn:
            return
        self.scene.clear()
        load(fn, self.scene, Hex=Hex, Col=Col)
        self.view._fit()
        remaining = 0
        for it in self.scene.items():
            if isinstance(it, Hex):
                it.actual = it.kind
                if not it.revealed:
                    if it.kind == Hex.full:
                        remaining += 1
                    it.kind = Hex.unknown
        self.scene.remaining = remaining
        self.scene.mistakes = 0


def main(f=None):
    global app, window
    
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.showMaximized()
    
    if not f and len(sys.argv[1:])==1:
        f = sys.argv[1]
    if f:
        QTimer.singleShot(100, lambda: window.open_file(f))

    app.exec_()

if __name__=='__main__':
    main()