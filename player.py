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
import collections
import time
import os.path

import common
from common import *
try:
    from solver import *
except ImportError:
    solve = None

from qt import Signal
from qt.core import QRectF, QTimer, QMargins, QByteArray
from qt.gui import QPolygonF, QPen, QPainter, QTransform, QKeySequence, QBrush
from qt.widgets import QApplication, QGraphicsView, QMainWindow, QFileDialog, QShortcut, QAction, QVBoxLayout, QLabel, QWidget


class Cell(common.Cell):
    def __init__(self):
        common.Cell.__init__(self)
        
        self.value = None
        self.flower = False

    def upd(self, first=True):
        try:
            self.proven
        except AttributeError:
            common.Cell.upd(self)
        else:
            old_kind = self._kind
            self._kind = self.actual
            common.Cell.upd(self)
            self._kind = old_kind
            self.setBrush(Color.proven)


    def mousePressEvent(self, e):
        if e.button()==qt.LeftButton and self.kind is Cell.full and self.value is not None:
            self.flower = not self.flower
            return
        if e.button()==qt.RightButton and self.scene().playtest and self.kind is not Cell.unknown:
            self.kind = Cell.unknown
            return
        buttons = [qt.LeftButton, qt.RightButton]
        if self.scene().swap_buttons:
            buttons.reverse()
        if e.button()==buttons[0]:
            want = Cell.full
        elif e.button()==buttons[1]:
            want = Cell.empty
        else:
            return
        if self.kind is Cell.unknown:
            if self.actual==want:
                self.kind = self.actual
            else:
                self.scene().mistakes += 1
    


    @setter_property
    def kind(self, value):
        rem = 0
        if self.kind is Cell.unknown and value is Cell.full:
            rem = -1
        if self.kind is Cell.full and value is Cell.unknown:
            rem = 1
        yield value
        if rem and self.scene():
            self.scene().remaining += rem
        try:
            del self.proven
        except AttributeError:
            pass
        self.flower = False
        self.upd()
    
    @event_property
    def flower(self):
        if self.scene():
            self.scene().update()


class Column(common.Column):
    def __init__(self):
        common.Column.__init__(self)
        self.beam = False
    
    @event_property
    def beam(self):
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


class Scene(common.Scene):
    text_changed = Signal()

    def __init__(self):
        common.Scene.__init__(self)
        
        self.swap_buttons = False
        
        self.remaining = 0
        self.mistakes = 0
        
        self.solving = False

    @event_property
    def remaining(self):
        self.text_changed.emit()

    @event_property
    def mistakes(self):
        self.text_changed.emit()
    
    @cached_property
    def _flower_poly(self):
        result = QPolygonF()
        hex1 = QPolygonF()
        l = 0.501/cos30
        for i in range(6):
            a = i*tau/6-tau/12
            hex1.append(QPointF(l*math.sin(a), -l*math.cos(a)))
        for i1 in range(6):
            a1 = i1*tau/6
            for i2 in range(6):
                a2 = i2*tau/6
                result = result.united(hex1.translated(math.sin(a1)+math.sin(a2), -math.cos(a1)-math.cos(a2)))
        return result

    def set_swap_buttons(self, value):
        self.swap_buttons = value
    
    def drawForeground(self, g, rect):
        g.setBrush(Color.flower)
        g.setPen(no_pen)
        for it in self.all(Cell):
            if it.flower:
                poly = self._flower_poly.translated(it.scenePos())
                g.drawPolygon(poly)

        g.setBrush(QBrush(qt.NoBrush))
        pen = QPen(Color.flower_border, 2)
        pen.setCosmetic(True)
        g.setPen(pen)
        for it in self.all(Cell):
            if it.flower:
                poly = self._flower_poly.translated(it.scenePos())
                g.drawPolygon(poly)
        
        g.setPen(no_pen)
        g.setBrush(Color.beam)
        for it in self.all(Column):
            if it.beam:
                poly = QPolygonF(QRectF(-0.03, 0.525, 0.06, 1e6))
                poly = QTransform().translate(it.scenePos().x(), it.scenePos().y()).rotate(it.rotation()).map(poly)
                poly = poly.intersected(QPolygonF(rect))
                g.drawConvexPolygon(poly)

    
    @cached_property
    def all_cells(self):
        return list(self.all(Cell))

    @cached_property
    def all_columns(self):
        return list(self.all(Column))

    
    def solve_step(self):
        """Derive everything that can be concluded from the current state.
        Return whether progress has been made."""
        if self.solving:
            return
        self.confirm_proven()
        self.solving = True
        app.processEvents()
        progress = False
        for cell, value in solve(self):
            try:
                assert cell.actual==value
            except AssertionError:
                cell.setPen(QPen(qt.red, 0.2))
                raise
            cell.proven = True
            cell.upd()
            progress = True
        
        self.solving = False
        
        return progress
    
    def solve_complete(self):
        """Continue solving until stuck.
        Return whether the entire level could be uncovered."""
        while True:
            self.confirm_proven()
            app.processEvents()
            
            progress = True
            while progress:
                progress = False
                for cell, value in solve_simple(self):
                    progress = True
                    try:
                        assert cell.actual==value
                    except AssertionError:
                        cell.setPen(QPen(qt.red, 0.2))
                        raise
                    cell.kind = cell.actual
                    cell.upd()
            if not self.solve_step():
                break

        
        # If it identified all blue cells, it'll have the rest uncovered as well
        return self.remaining == 0

    def confirm_proven(self):
        if self.solving:
            return
        for cell in self.all(Cell):
            try:
                del cell.proven
                cell.kind = cell.actual
                cell.upd()
            except AttributeError:
                pass
    def clear_proven(self):
        if self.solving:
            return
        for cell in self.all(Cell):
            try:
                del cell.proven
                cell.upd()
            except AttributeError:
                pass

class View(QGraphicsView):
    def __init__(self, scene):
        QGraphicsView.__init__(self, scene)
        self.scene = scene
        self.scene.text_changed.connect(self.viewport().update) # ensure a full redraw
        self.setRenderHints(self.renderHints()|QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(qt.ScrollBarAlwaysOff)

    def resizeEvent(self, e):
        QGraphicsView.resizeEvent(self, e)
        if not self.scene.playtest:
            self.fit()

    def fit(self):
        self.fitInView(self.scene.itemsBoundingRect().adjusted(-0.5, -0.5, 0.5, 0.5), qt.KeepAspectRatio)
    
    def paintEvent(self, e):
        QGraphicsView.paintEvent(self, e)
        g = QPainter(self.viewport())
        g.setRenderHints(self.renderHints())
        try:
            self._info_font
        except AttributeError:
            self._info_font = g.font()
            multiply_font_size(self._info_font, 3)
        
        try:
            txt = ('{r} ({m})' if self.scene.mistakes else '{r}').format(r=self.scene.remaining, m=self.scene.mistakes)
            g.setFont(self._info_font)
            g.drawText(self.viewport().rect().adjusted(5, 2, -5, -2), qt.AlignTop|qt.AlignRight, txt)
        except AttributeError:
            pass

    def wheelEvent(self, e):
        pass


class MainWindow(QMainWindow):
    title = "SixCells Player"
    
    def __init__(self, playtest=False):
        QMainWindow.__init__(self)
        
        if not playtest:
            self.resize(1280, 720)

        self.scene = Scene()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout()
        layout.setContentsMargins(QMargins())
        layout.setSpacing(0)
        self.central_widget.setLayout(layout)
        
        self.view = View(self.scene)
        layout.addWidget(self.view, 1)

        self.information_label = QLabel()
        self.information_label.setAlignment(qt.AlignHCenter)
        self.information_label.setWordWrap(True)
        self.information_label.setContentsMargins(5, 5, 5, 5)
        font = self.information_label.font()
        multiply_font_size(font, 1.5)
        self.information_label.setFont(font)
        layout.addWidget(self.information_label)

        self.scene.playtest = self.playtest = playtest
        
        
        menu = self.menuBar().addMenu("File")
        
        if not playtest:
            action = menu.addAction("Open...", self.load_file, QKeySequence.Open)
            
            menu.addSeparator()
        
        action = menu.addAction("Quit", self.close, QKeySequence('Tab') if playtest else QKeySequence.Quit)
        if playtest:
            QShortcut(QKeySequence.Quit, self, action.trigger)
        else:
            QShortcut(QKeySequence.Close, self, action.trigger)
        
        
        menu = self.menuBar().addMenu("Preferences")
        
        self.swap_buttons_action = action = QAction("Swap Buttons", self)
        action.setCheckable(True)
        def set_swap_buttons(v): self.scene.swap_buttons = v
        action.toggled.connect(set_swap_buttons)
        menu.addAction(action)

        
        menu = self.menuBar().addMenu("Solve")
        menu.setEnabled(solve is not None)
        
        menu.addAction("One Step", self.scene.solve_step, QKeySequence("S"))
        
        menu.addAction("Confirm Revealed", self.scene.confirm_proven, QKeySequence("C"))
        
        menu.addAction("Clear Revealed", self.scene.clear_proven, QKeySequence("X"))
        
        menu.addSeparator()
        
        menu.addAction("Solve Completely", self.scene.solve_complete)

        
        menu = self.menuBar().addMenu("Help")
        
        action = menu.addAction("Instructions", help, QKeySequence.HelpContents)
        
        action = menu.addAction("About", lambda: about(self.title))
        
        
        self.current_file = None
        
        self.last_used_folder = None
        
        try:
            with open('player.cfg') as cfg_file:
                cfg = cfg_file.read()
        except OSError:
            pass
        else:
            load_config(self, self.config_format, cfg)
    
    config_format = '''
        swap_buttons = swap_buttons_action.isChecked(); swap_buttons_action.setChecked(v)
        last_used_folder = last_used_folder; last_used_folder = v
        window_geometry_qt = save_geometry_qt(); restore_geometry_qt(v)
    '''
    def save_geometry_qt(self):
        return self.saveGeometry().toBase64().data().decode('ascii')
    def restore_geometry_qt(self, value):
        self.restoreGeometry(QByteArray.fromBase64(value.encode('ascii')))
    
    @event_property
    def current_file(self):
        title = self.title
        if self.current_file:
            title = os.path.splitext(os.path.basename(self.current_file))[0]+' - '+title
        self.setWindowTitle(title)
    
    def load(self, struct):
        load(struct, self.scene, Cell=Cell, Column=Column)
        self._prepare()
    
    def load_file(self, fn=None):
        if not fn:
            try:
                dialog = QFileDialog.getOpenFileNameAndFilter
            except AttributeError:
                dialog = QFileDialog.getOpenFileName
            fn, _ = dialog(self, "Open", filter="SixCells level (*sixcells *.sixcellz)")
        if not fn:
            return
        self.scene.clear()
        try:
            gz = fn.endswith('.sixcellz')
        except AttributeError:
            gz = False
        load_file(fn, self.scene, gz=gz, Cell=Cell, Column=Column)
        self._prepare()
        self.current_file = fn
        self.last_used_folder = os.path.dirname(fn)
    
    def _prepare(self):
        if not self.playtest:
            self.view.fit()
        remaining = 0
        for it in self.scene.all(Cell):
            it.actual = it.kind
            if not it.revealed:
                if it.kind == Cell.full:
                    remaining += 1
                it.kind = Cell.unknown
        self.scene.remaining = remaining
        self.scene.mistakes = 0
        if self.scene.information:
            self.information_label.setText(self.scene.information)
            self.information_label.show()
        else:
            self.information_label.hide()

    def closeEvent(self, e):
        self.scene.solving = False

        cfg = save_config(self, self.config_format)
        with open('player.cfg', 'w') as cfg_file:
            cfg_file.write(cfg)
    


def main(f=None):
    global app, window
    
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    
    if not f and len(sys.argv[1:])==1:
        f = sys.argv[1]
    if f:
        QTimer.singleShot(0, lambda: window.load_file(f))

    app.exec_()

if __name__=='__main__':
    main()