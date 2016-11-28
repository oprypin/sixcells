#!/usr/bin/env python

# Copyright (C) 2014-2016 Oleh Prypin <blaxpirit@gmail.com>
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
import contextlib
try:
    import sqlite3
except ImportError:
    pass

import common
from common import *
try:
    from solver import *
except ImportError:
    solve = None

from qt import Signal
from qt.core import QMargins, QRectF, QTimer
from qt.gui import QBrush, QIcon, QKeySequence, QPainter, QPen, QPolygonF, QTransform
from qt.widgets import QHBoxLayout, QLabel, QShortcut, QTabBar, QVBoxLayout, QWidget


@contextlib.contextmanager
def db_connection(file_name):
    try:
        con = sqlite3.connect(here(file_name))
    except sqlite3.OperationalError:
        loc = user_config_location('sixcells', file_name)
        makedirs(loc)
        con = sqlite3.connect(loc)
    yield con
    con.close()


class Cell(common.Cell):
    def __init__(self):
        common.Cell.__init__(self)
        
        self.flower = False
        self.hidden = False
        self.guess = None
        self._display = Cell.unknown

    def upd(self, first=False):
        common.Cell.upd(self, first)
        if self.guess:
            self.setBrush(Color.blue_border if self.guess == Cell.full else Color.black_border)
    
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
        if e.modifiers() & qt.ShiftModifier:
            self.guess = None if self.guess == want else want
            self.upd()
            return
        if self.display is Cell.unknown:
            if self.kind == want:
                self.display = self.kind
                self.scene().undo_history.append([self])
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
        self.guess = None
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
        
        self.undo_history = []

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
        pen = QPen(Color.flower_border, 1.5)
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
                poly = QPolygonF(QRectF(-0.045, 0.525, 0.09, 1e6))
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
        
        self.confirm_guesses()
        self.solving += 1
        app.processEvents()
        progress = False
        undo_step = []
        for cell, value in solve(self):
            assert cell.kind is value
            cell.guess = value
            cell.upd()
            progress = True
            undo_step.append(cell)
        self.undo_history.append(undo_step)
        self.solving -= 1
        
        return progress
    
    def solve_complete(self):
        """Continue solving until stuck.
        Return whether the entire level could be uncovered."""
        self.solving = 1
        while self.solving:
            self.confirm_guesses()
            
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

    def clear_guesses(self):
        for cell in self.all(Cell):
            if cell.guess:
                cell.guess = None
                cell.upd()
    def confirm_guesses(self, opposite=False):
        correct = []
        for cell in self.all(Cell):
            if cell.guess and cell.display is Cell.unknown:
                if (cell.kind == cell.guess) ^ opposite:
                    cell.display = cell.kind
                    cell.upd()
                    correct.append(cell)
                else:
                    self.mistakes += 1
        self.undo_history.append(correct)
    def confirm_opposite_guesses(self):
        self.confirm_guesses(opposite=True)
    
    def undo(self):
        if not self.undo_history:
            return
        last = self.undo_history.pop()
        found = False
        for cell in last:
            if cell.display == Cell.unknown and not cell.guess:
                continue
            cell.display = Cell.unknown
            cell.upd()
            found = True
        if not found:
            self.undo()
    
    def highlight_all_columns(self):
        for col in self.all(Column):
            if not col.hidden:
                col.beam = True
    def highlight_all_flowers(self):
        for cell in self.all(Cell):
            if not cell.hidden and cell.display is Cell.full and cell.value is not None:
                cell.flower = True


class View(common.View):
    def __init__(self, scene):
        common.View.__init__(self, scene)
        self.setMouseTracking(True) # fix for not updating position for simulated events
        self.scene.text_changed.connect(self.viewport().update) # ensure a full redraw
        self.progress_loaded_timer = QTimer()
        self.progress_loaded_timer.setInterval(1500)
        self.progress_loaded_timer.setSingleShot(True)
        self.progress_loaded_timer.timeout.connect(self.viewport().update)
        
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
        area = self.viewport().rect().adjusted(5, 2, -5, -2)
        
        if self.progress_loaded_timer.isActive():
            g.setPen(QPen(Color.dark_text))
            g.drawText(area, qt.AlignTop | qt.AlignLeft, "Progress loaded")
        
        try:
            self._info_font
        except AttributeError:
            self._info_font = g.font()
            multiply_font_size(self._info_font, 3)
        
        try:
            txt = ('{r} ({m})' if self.scene.mistakes else '{r}').format(r=self.scene.remaining, m=self.scene.mistakes)
            g.setFont(self._info_font)
            g.setPen(QPen(Color.dark_text))
            g.drawText(area, qt.AlignTop | qt.AlignRight, txt)
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
        
        self.levels_bar = QTabBar()
        layout.addWidget(self.levels_bar)
        self.levels_bar.currentChanged.connect(self.level_change)
        
        top_layout = QHBoxLayout()
        layout.addLayout(top_layout)
        
        self.author_align_label = QLabel()
        self.author_align_label.setStyleSheet('color: rgba(0,0,0,0%)')
        top_layout.addWidget(self.author_align_label, 0)
        
        self.title_label = QLabel()
        self.title_label.setAlignment(qt.AlignHCenter)
        update_font(self.title_label, lambda f: multiply_font_size(f, 1.8))
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
        update_font(self.information_label, lambda f: multiply_font_size(f, 1.5))
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
        
        
        menu = self.menuBar().addMenu("&Edit")
        
        action = menu.addAction("&Undo", self.scene.undo, QKeySequence.Undo)
        QShortcut(QKeySequence('Z'), self, action.trigger)
        action.setStatusTip("Cover the last uncovered cell.")
        action = menu.addAction("Clear &Progress", self.clear_progress)
        menu.addSeparator()
        
        menu.addAction("&Clear Annotations", self.scene.clear_guesses, QKeySequence("X"))
        menu.addAction("Con&firm Annotated Guesses", self.scene.confirm_guesses, QKeySequence("C"))
        menu.addAction("&Deny Annotated Guesses", self.scene.confirm_opposite_guesses, QKeySequence("D"))
        menu.addSeparator()
        
        menu.addAction("Highlight All C&olumn Hints", self.scene.highlight_all_columns)
        menu.addAction("Highlight All F&lower Hints", self.scene.highlight_all_flowers)

        
        menu = self.menuBar().addMenu("&Solve")
        menu.setEnabled(solve is not None)
        
        menu.addAction("&One Step", self.scene.solve_step, QKeySequence("S"))
        action = menu.addAction("Con&firm Solved", self.scene.confirm_guesses, QKeySequence("C"))
        action.setShortcutContext(qt.WidgetWithChildrenShortcut) # To prevent "ambiguous shortcut"
        action = menu.addAction("&Clear Solved", self.scene.clear_guesses, QKeySequence("X"))
        action.setShortcutContext(qt.WidgetWithChildrenShortcut)
        
        menu.addSeparator()
        
        menu.addAction("&Solve Completely", self.scene.solve_complete)

        
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
        if not self.playtest:
            total = 0
            revealed = 0
            for cell in self.scene.all(Cell):
                if not cell.revealed:
                    total += 1
                    if cell.display is not Cell.unknown:
                        revealed += 1
            clearing = hasattr(self, 'clearing')
            if 0 < revealed < total or clearing:
                try:
                    saved = save(self.scene, display=True, padding=False)
                    do_save = self.original_level != saved
                    if do_save:
                        if not clearing:
                            msg = "Would you like to save your progress for this level?"
                            btn = QMessageBox.warning(self, "Unsaved progress", msg, QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
                        else:
                            msg = "Are you sure you want to clear progress for this level?"
                            btn = QMessageBox.warning(self, "Clear progress", msg, QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Discard)
                        if btn == QMessageBox.Discard:
                            do_save = False
                        elif btn == QMessageBox.Cancel:
                            return
                    with db_connection('sixcells.sqlite3') as con:
                        with con:
                            con.execute('CREATE TABLE IF NOT EXISTS `saves` (`level` TEXT PRIMARY KEY, `save` TEXT, `mistakes` INT)')
                            con.execute('DELETE FROM `saves` WHERE `level` = ?', (self.original_level,))
                            if do_save:
                                con.execute('INSERT INTO `saves` (`level`, `save`, `mistakes`) VALUES (?, ?, ?)', (self.original_level, saved, self.scene.mistakes))
                except Exception as e:
                    pass
        self.current_file = None
        self.scene.clear()
        self.scene.remaining = 0
        self.scene.mistakes = 0
        self.scene.reset_cache()
        for it in [self.title_label, self.author_align_label, self.author_label, self.information_label]:
            it.hide()
        self.copy_action.setEnabled(False)
        self.undo_history = []
        self.view.progress_loaded_timer.stop()
        self.view.viewport().repaint()
        return True
    
    def clear_progress(self):
        self.clearing = True
        self.load_one(self.original_level)
        delattr(self, 'clearing')
    
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
    
    def load_one(self, level):
        if common.MainWindow.load(self, level):
            self.original_level = save(self.scene, padding=False)
            try:
                with db_connection('sixcells.sqlite3') as con:
                    with con:
                        [(saved, mistakes)] = con.execute('SELECT `save`, `mistakes` FROM `saves` WHERE `level` = ?', (self.original_level,))
                common.MainWindow.load(self, saved)
                self.scene.mistakes = mistakes
                self.view.progress_loaded_timer.start()
                self.view.viewport().update()
            except Exception:
                pass
            self.view.setFocus()
            return True
    
    def load(self, level):
        while self.levels_bar.count():
            self.levels_bar.removeTab(0)
        self.levels_bar.hide()
        levels = []
        lines = level.splitlines()
        start = None
        skip = 0
        for i, line in enumerate(lines + [None]):
            if skip:
                skip -= 1
                continue
            if line is None or line.strip() == 'Hexcells level v1':
                if start is not None:
                    level_lines = lines[start:i]
                    levels.append(('\n'.join(level_lines), level_lines[1]))
                start = i
                skip = 4
        self.current_level = 0
        if len(levels) > 1:
            self.levels_bar.show()
            self.load_one(levels[0][0])
            for level, title in levels:
                self.levels_bar.addTab(title)
                self.levels_bar.setTabData(self.levels_bar.count()-1, level)
        else:
            self.load_one(level)

    def level_change(self, index):
        if index >= 0 and index != self.current_level:
            level = self.levels_bar.tabData(index)
            if level:
                if self.load_one(level):
                    self.current_level = index
                else:
                    self.levels_bar.setCurrentIndex(self.current_level)


    def closeEvent(self, e):
        if not self.close_file():
            e.ignore()
            return
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
