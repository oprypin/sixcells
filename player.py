#!/usr/bin/env python

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


from __future__ import division, print_function

import sys
import os.path

import common
from common import *
try:
    from solver import *
except ImportError:
    solve = None

from qt import Signal
from qt.core import QMargins, QRectF, QTimer
from qt.gui import QBrush, QIcon, QKeySequence, QPainter, QPen, QPolygonF, QTransform
from qt.widgets import QHBoxLayout, QLabel, QShortcut, QVBoxLayout, QWidget


class Cell(common.Cell):
    def __init__(self):
        common.Cell.__init__(self)
        
        self.flower = False
        self.hidden = False
        self.proven = False
        self._display = Cell.unknown

    def upd(self, first=False):
        if self.proven:
            old_display = self.display
            self._display = self.kind
        common.Cell.upd(self, first)
        if self.proven:
            self._display = old_display
            self.setBrush(Color.proven)

    def mousePressEvent(self, e):
        if e.button() == qt.RightButton and self.scene().playtest and self.display is not Cell.unknown:
            self.display = Cell.unknown
            self.upd()
            return
        if self.display is Cell.full and self.value is not None:
            if e.button() == qt.LeftButton:
                self.flower = not self.flower
                return
            if e.button() == qt.RightButton:
                self.hidden = not self.hidden
                self.flower = False
                return
        buttons = [qt.LeftButton, qt.RightButton]
        if self.scene().swap_buttons:
            buttons.reverse()
        if e.button() == buttons[0]:
            want = Cell.full
        elif e.button() == buttons[1]:
            want = Cell.empty
        else:
            return
        if self.display is Cell.unknown:
            if self.kind == want:
                self.display = self.kind
                self.upd()
            else:
                self.scene().mistakes += 1
    
    
    @setter_property
    def display(self, value):
        rem = 0
        try:
            if self.display is not Cell.full and value is Cell.full:
                rem = -1
            if self.display is Cell.full and value is not Cell.full:
                rem = 1
        except AttributeError:
            pass
        yield value
        if rem and self.placed:
            self.scene().remaining += rem
        self.proven = False
        self.flower = False
        self.extra_text = ''
    
    @event_property
    def flower(self):
        if self.scene():
            self.scene().update()
    
    @property
    def hidden(self):
        return self._text.opacity() < 1
    @hidden.setter
    def hidden(self, value):
        self._text.setOpacity(0.2 if value else 1)
        self.update()
        
    def reset_cache(self):
        pass




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
        return self.opacity() < 1
    @hidden.setter
    def hidden(self, value):
        self.setOpacity(0.2 if value else 1)
    
    def mousePressEvent(self, e):
        if e.button() == qt.LeftButton:
            self.beam = not self.beam
        elif e.button() == qt.RightButton:
            self.hidden = not self.hidden
            self.beam = False

    def reset_cache(self):
        pass
    


def _flower_poly():
    result = QPolygonF()
    for i1 in range(6):
        a1 = i1*tau/6
        for i2 in range(6):
            a2 = i2*tau/6
            result = result.united(hex1.translated(math.sin(a1) + math.sin(a2), -math.cos(a1) - math.cos(a2)))
    return result
_flower_poly = _flower_poly()

class Scene(common.Scene):
    text_changed = Signal()

    def __init__(self):
        common.Scene.__init__(self)
        
        self.swap_buttons = False
        
        self.remaining = 0
        self.mistakes = 0
        
        self.solving = 0

    @event_property
    def remaining(self):
        self.text_changed.emit()

    @event_property
    def mistakes(self):
        self.text_changed.emit()
    
    def set_swap_buttons(self, value):
        self.swap_buttons = value
    
    def drawForeground(self, g, rect):
        g.setBrush(Color.flower)
        g.setPen(no_pen)
        for it in self.all(Cell):
            if it.flower:
                poly = _flower_poly.translated(it.scenePos())
                g.drawPolygon(poly)

        g.setBrush(QBrush(qt.NoBrush))
        pen = QPen(Color.flower_border, 2)
        pen.setCosmetic(True)
        g.setPen(pen)
        for it in self.all(Cell):
            if it.flower:
                poly = _flower_poly.translated(it.scenePos())
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

    def reset_cache(self):
        for attr in ['all_cells', 'all_columns']:
            try:
                delattr(self, attr)
            except AttributeError: pass
    
    def solve_step(self):
        """Derive everything that can be concluded from the current state.
        Return whether progress has been made."""
        if self.solving:
            return
        
        self.confirm_proven()
        self.solving += 1
        app.processEvents()
        progress = False
        for cell, value in solve(self):
            assert cell.kind is value
            cell.proven = True
            cell.upd()
            progress = True
        self.solving -= 1
        
        return progress
    
    def solve_complete(self):
        """Continue solving until stuck.
        Return whether the entire level could be uncovered."""
        self.solving = 1
        while self.solving:
            self.confirm_proven()
            
            progress = True
            while progress:
                progress = False
                for cell, value in solve_simple(self):
                    progress = True
                    assert cell.kind is value
                    cell.display = cell.kind
                    cell.upd()
            self.solving -= 1
            if not self.solve_step():
                break
            self.solving += 1
        
        self.solving = 0
        # If it identified all blue cells, it'll have the rest uncovered as well
        return self.remaining == 0

    def clear_proven(self, confirm=False):
        for cell in self.all(Cell):
            if cell.proven:
                cell.proven = False
                if confirm:
                    cell.display = cell.kind
                cell.upd()
    def confirm_proven(self):
        self.clear_proven(True)


class View(common.View):
    def __init__(self, scene):
        common.View.__init__(self, scene)
        self.scene.text_changed.connect(self.viewport().update) # ensure a full redraw
        self.setMouseTracking(True) # fix for not updating position for simulated events
        
    def resizeEvent(self, e):
        common.View.resizeEvent(self, e)
        if not self.scene.playtest:
            self.fit()

    def fit(self):
        rect = self.scene.itemsBoundingRect().adjusted(-0.3, -0.3, 0.3, 0.3)
        self.setSceneRect(rect)
        self.fitInView(rect, qt.KeepAspectRatio)
        zoom = self.transform().mapRect(QRectF(0, 0, 1, 1)).width()
        if zoom > 100:
            self.resetTransform()
            self.scale(100, 100)
    
    def paintEvent(self, e):
        common.View.paintEvent(self, e)
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
            g.drawText(self.viewport().rect().adjusted(5, 2, -5, -2), qt.AlignTop | qt.AlignRight, txt)
        except AttributeError: pass

    def wheelEvent(self, e):
        pass


class MainWindow(common.MainWindow):
    title = "SixCells Player"
    Cell = Cell
    Column = Column
    
    def __init__(self, playtest=False):
        common.MainWindow.__init__(self)
        
        if not playtest:
            self.resize(1280, 720)
        self.setWindowIcon(QIcon(here('resources', 'player.ico')))

        self.scene = Scene()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout()
        layout.setContentsMargins(QMargins())
        layout.setSpacing(0)
        self.central_widget.setLayout(layout)
        
        top_layout = QHBoxLayout()
        layout.addLayout(top_layout)
        
        self.author_align_label = QLabel()
        self.author_align_label.setStyleSheet('color: rgba(0,0,0,0%)')
        top_layout.addWidget(self.author_align_label, 0)
        
        self.title_label = QLabel()
        self.title_label.setAlignment(qt.AlignHCenter)
        font = self.title_label.font()
        multiply_font_size(font, 1.8)
        self.title_label.setFont(font)
        top_layout.addWidget(self.title_label, 1)

        self.author_label = QLabel()
        self.author_label.setAlignment(qt.AlignRight)
        top_layout.addWidget(self.author_label, 0)
        
        
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
        
        
        menu = self.menuBar().addMenu("&File")
        
        if not playtest:
            action = menu.addAction("&Open...", self.load_file, QKeySequence.Open)
            menu.addSeparator()
        self.copy_action = action = menu.addAction("&Copy State to Clipboard", lambda: self.copy(display=True), QKeySequence('Ctrl+C'))
        action.setStatusTip("Copy the current state of the level into clipboard, in a text-based .hexcells format, padded with Tab characters.")
        if not playtest:
            action = menu.addAction("&Paste from Clipboard", self.paste, QKeySequence('Ctrl+V'))
            action.setStatusTip("Load a level in text-based .hexcells format that is currently in the clipboard.")
        menu.addSeparator()

        
        action = menu.addAction("&Quit", self.close, QKeySequence('Tab') if playtest else QKeySequence.Quit)
        if playtest:
            QShortcut(QKeySequence.Quit, self, action.trigger)
        else:
            QShortcut(QKeySequence.Close, self, action.trigger)
        
        
        menu = self.menuBar().addMenu("&Solve")
        menu.setEnabled(solve is not None)
        
        menu.addAction("&One Step", self.scene.solve_step, QKeySequence("S"))
        
        menu.addAction("Confirm &Revealed", self.scene.confirm_proven, QKeySequence("C"))
        
        menu.addAction("&Clear Revealed", self.scene.clear_proven, QKeySequence("X"))
        
        menu.addSeparator()
        
        menu.addAction("&Solve Completely", self.scene.solve_complete, QKeySequence("Shift+S"))

        
        menu = self.menuBar().addMenu("&Preferences")
        
        self.swap_buttons_action = action = make_check_action("&Swap Buttons", self, self.scene, 'swap_buttons')
        menu.addAction(action)

        
        menu = self.menuBar().addMenu("&Help")
        
        action = menu.addAction("&Instructions", self.help, QKeySequence.HelpContents)
        
        action = menu.addAction("&About", self.about)
        
        
        self.last_used_folder = None
        
        self.close_file()
        
        load_config_from_file(self, self.config_format, 'sixcells', 'player.cfg')
    
    config_format = '''
        swap_buttons = swap_buttons_action.isChecked(); swap_buttons_action.setChecked(v)
        antialiasing = view.antialiasing; view.antialiasing = v
        last_used_folder
        window_geometry_qt = save_geometry_qt(); restore_geometry_qt(v)
    '''
    
    def close_file(self):
        self.current_file = None
        self.scene.clear()
        self.scene.remaining = 0
        self.scene.mistakes = 0
        self.scene.reset_cache()
        for it in [self.title_label, self.author_align_label, self.author_label, self.information_label]:
            it.hide()
        self.copy_action.setEnabled(False)
        return True
    
    @event_property
    def current_file(self):
        title = self.title
        if self.current_file:
            title = os.path.basename(self.current_file) + ' - ' + title
        self.setWindowTitle(("Playtest" + ' - ' if self.playtest else '') + title)
    
    def prepare(self):
        if not self.playtest:
            self.view.fit()
        remaining = 0
        for i, cell in enumerate(self.scene.all(Cell)):
            cell.id = i
            if cell.kind is Cell.full and not cell.revealed:
                remaining += 1
            cell._display = cell.kind if cell.revealed else Cell.unknown
        for i, col in enumerate(self.scene.all(Column)):
            col.id = i
        self.scene.remaining = remaining
        self.scene.mistakes = 0
        author_text = ("by {}" if self.scene.author else "").format(self.scene.author)
        for txt, it in [
            (self.scene.title, self.title_label),
            (author_text, self.author_label),
            (author_text, self.author_align_label),
            (self.scene.information, self.information_label),
        ]:
            if txt:
                it.setText(txt)
                it.show()
            else:
                it.hide()
        self.scene.full_upd()
        self.copy_action.setEnabled(True)
        

    def closeEvent(self, e):
        self.scene.solving = 0

        save_config_to_file(self, self.config_format, 'sixcells', 'player.cfg')



def main(f=None):
    global window
    
    window = MainWindow()
    window.show()
    
    if not f and len(sys.argv[1:]) == 1:
        f = sys.argv[1]
    if f:
        f = os.path.abspath(f)
        QTimer.singleShot(0, lambda: window.load_file(f))

    app.exec_()

if __name__ == '__main__':
    main()