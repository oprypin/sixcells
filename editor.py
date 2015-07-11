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
import math
import os.path

import common
from common import *

from qt.core import QPoint, QPointF, QRectF, QTimer
from qt.gui import QIcon, QKeySequence, QMouseEvent, QPainterPath, QPen, QTransform, QPolygonF
from qt.widgets import QDialog, QDialogButtonBox, QFileDialog, QGraphicsPathItem, QGraphicsView, QLabel, QLineEdit, QMessageBox, QShortcut, QVBoxLayout



class Cell(common.Cell):
    def __init__(self):
        common.Cell.__init__(self)

        self.revealed = False
        self.preview = None

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

    def upd(self, first=False):
        common.Cell.upd(self, first)

        if self.revealed:
            self.setBrush(Color.revealed_border)

    def mousePressEvent(self, e):
        if e.button() == qt.LeftButton and e.modifiers() & qt.ShiftModifier:
            self.selected = not self.selected
            e.ignore()
        if self.scene().selection:
            return
        if e.button() == qt.LeftButton and e.modifiers() & (qt.AltModifier | qt.ControlModifier):
            self.revealed = not self.revealed
            self.upd()
            e.ignore()
        
    def mouseMoveEvent(self, e):
        if self.scene().selection:
            if self.selected:
                x, y = convert_pos(e.scenePos().x(), e.scenePos().y())
                x, y = round(x), round(y)
                dx = x-self.coord.x
                dy = y-self.coord.y
                if dx or dy:
                    full_selection = set(self.scene().selection)
                    for cell in self.scene().selection:
                        full_selection |= set(cell.columns)
                    for it in full_selection:
                        new = Cell()
                        self.scene().addItem(new)
                        new.coord = (it.coord.x+dx, it.coord.y+dy)
                        overlapping = set(new.overlapping)-full_selection
                        new.remove()
                        if overlapping:
                            break
                    else:
                        for cell in self.scene().selection:
                            for it in [cell] + cell.columns:
                                it.place((it.coord.x+dx, it.coord.y+dy))
                
        elif not self.contains(e.pos()): # mouse was dragged outside
            if not self.preview:
                self.preview = Column()
                self.scene().addItem(self.preview)

            a = angle(e.pos())*360/tau
            x, y = self.coord
            if -30 < a < 30:
                self.preview.coord = x, y-2
                self.preview.angle = 0
            elif -90 < a < -30:
                self.preview.coord = x-1, y-1
                self.preview.angle = -60
            elif 30 < a < 90:
                self.preview.coord = x+1, y-1
                self.preview.angle = 60
            else:
                self.preview.remove()
                self.preview = None
            if self.preview:
                self.preview.upd()
    
    def mouseReleaseEvent(self, e):
        if self.scene().ignore_release:
            self.scene().ignore_release = False
            return
        if self.scene().supress:
            return
        if self.scene().selection:
            self.scene().full_upd()
            self.scene().undo_step()

        if e.modifiers() & (qt.ShiftModifier | qt.AltModifier | qt.ControlModifier) or self.scene().selection:
            e.ignore()
            return
        if not self.preview:
            if self.contains(e.pos()): # mouse was not dragged outside
                if e.button() == qt.LeftButton:
                    self.show_info = (self.show_info+1)%(3 if self.kind is Cell.empty else 2)
                    self.upd()
                    self.scene().undo_step(self)
                elif e.button() == qt.RightButton:
                    for col in self.columns:
                        col.remove()
                    scene = self.scene()
                    with self.upd_neighbors():
                        self.remove()
                    scene.undo_step()
        else:
            for it in self.preview.overlapping:
                self.preview.remove()
                self.preview = None
                break
            else:
                self.preview.place()
                self.preview.upd()
            self.preview = None

    def copyattrs(self, new):
        new.kind = self.kind
        new.show_info = self.show_info
        new.revealed = self.revealed


class Column(common.Column):
    def __init__(self):
        common.Column.__init__(self)
        
    def mousePressEvent(self, e):
        pass
    
    def mouseReleaseEvent(self, e):
        if self.scene().supress:
            return
        if self.contains(e.pos()): # mouse was not dragged outside
            if e.button() == qt.LeftButton:
                self.show_info = not self.show_info
                self.upd()
                self.scene().undo_step(self)
            elif e.button() == qt.RightButton:
                scene = self.scene()
                self.remove()
                scene.undo_step(self)

    def copyattrs(self, new):
        new.angle = self.angle
        new.show_info = self.show_info



def convert_pos(x, y):
    return x/cos30, y*2


class Scene(common.Scene):
    def __init__(self):
        common.Scene.__init__(self)
        self.reset()
        self.swap_buttons = False
        self.use_rightclick = False
        self.ignore_release = False
        self.undo_history_length = 16
        self.undo_step()
    
    def reset(self):
        self.clear()
        self.preview = None
        self.selection = set()
        self.selection_path_item = None
        self.supress = False
        self.title = self.author = self.information = ''
        self.undo_history = []
        self.undo_pos = -1
    
    def _place(self, p, kind=Cell.unknown):
        if not self.preview:
            self.preview = Cell()
            self.preview.kind = kind
            self.preview.setOpacity(0.4)
            self.addItem(self.preview)
        x, y = convert_pos(p.x(), p.y())
        x = round(x)
        for yy in [round(y), int(math.floor(y - 1e-4)), int(math.ceil(y + 1e-4))]:
            self.preview.coord = (x, yy)
            if not any(isinstance(it, Cell) for it in self.preview.overlapping):
                break
        else:
            self.preview.coord = (round(x), round(y))
        self.preview.upd()
        self.preview._text.setText('')
    
    def mousePressEvent(self, e):
        if self.supress:
            return

        self.last_press = self.itemAt(e.scenePos(), QTransform())

        if self.selection:
            if (e.button() == qt.LeftButton and not self.itemAt(e.scenePos(), QTransform())) or e.button() == qt.RightButton:
                old_selection = self.selection
                self.selection = set()
                for it in old_selection:
                    try:
                        it.selected = False
                    except AttributeError: pass
        if not self.itemAt(e.scenePos(), QTransform()):
            if e.button() == qt.LeftButton:
                if e.modifiers() & qt.ShiftModifier:
                    self.selection_path_item = QGraphicsPathItem()
                    self.selection_path = path = QPainterPath()
                    self.selection_path_item.setPen(QPen(Color.selection, 0, qt.DashLine))
                    path.moveTo(e.scenePos())
                    self.selection_path_item.setPath(path)
                    self.addItem(self.selection_path_item)
            if e.button() == qt.LeftButton or (self.use_rightclick and e.button() == qt.RightButton):
                if not e.modifiers() & qt.ShiftModifier:
                    self._place(e.scenePos(), Cell.full if (e.button() == qt.LeftButton) ^ self.swap_buttons else Cell.empty)
        else:
            common.Scene.mousePressEvent(self, e)

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
            self._place(e.scenePos())
        else:
            common.Scene.mouseMoveEvent(self, e)

    
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
            for it in self.preview.overlapping:
                if isinstance(it, Column):
                    if it.coord == self.preview.coord:
                        col = it
                        continue
                if isinstance(it, Cell) or abs(it.coord.y - self.preview.coord.y) == 1:
                    self.preview.remove()
                    break
            else:
                if col:
                    old_cell = col.cell
                    p = (col.coord.x - old_cell.coord.x + self.preview.coord.x, col.coord.y - old_cell.coord.y + self.preview.coord.y)
                    if not self.grid.get(p):
                        old_cell = col.cell
                        col.place((col.coord.x - old_cell.coord.x + self.preview.coord.x, col.coord.y - old_cell.coord.y + self.preview.coord.y))
                        col.upd()
                        col = None
                if not col:
                    self.preview.setOpacity(1)
                    self.preview.place()
                    self.undo_step()
                    self.preview.show_info = self.black_show_info if self.preview.kind is Cell.empty else self.blue_show_info
                    self.preview.upd(True)
                else:
                    self.preview.remove()

            self.preview = None
        else:
            common.Scene.mouseReleaseEvent(self, e)
    
    def mouseDoubleClickEvent(self, e):
        it = self.itemAt(e.scenePos(), QTransform())
        if not it:
            self.mousePressEvent(e)
            return
        if not isinstance(it, Cell):
            return
        if self.last_press is None and not self.use_rightclick:
            if it.kind is Cell.full:
                it.kind = Cell.empty
                it.show_info = self.black_show_info
            else:
                it.kind = Cell.full
                it.show_info = self.blue_show_info
            it.upd()
            self.ignore_release = True
        common.Scene.mouseDoubleClickEvent(self, e)

    def undo_step(self, it=None):
        step = dict(self.grid)
        if it is not None:
            new = type(it)()
            it.copyattrs(new)
            step[tuple(it.coord)] = new
        self.undo_history[self.undo_pos+1:] = [step]
        self.undo_pos = len(self.undo_history) - 1
        if self.undo_history_length and len(self.undo_history) > self.undo_history_length:
            del self.undo_history[0]
            self.undo_pos -= 1
            
    def undo(self, step=-1):
        self.undo_pos += step
        try:
            if self.undo_pos < 0:
                raise IndexError()
            grid = self.undo_history[self.undo_pos]
        except IndexError:
            self.undo_pos -= step
            return
        for it in self.items():
            self.removeItem(it)
        self.grid = {}
        for (x, y), it in grid.items():
            self.addItem(it)
            it.place((x, y))
        self.full_upd()
        return True
    
    def redo(self):
        self.undo(1)
    

class View(common.View):
    def __init__(self, scene):
        common.View.__init__(self, scene)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        inf = -1e10
        self.setSceneRect(QRectF(QPointF(-inf, -inf), QPointF(inf, inf)))
        self.scale(50, 50) #*1.00955
        self.hexcells_ui = False


    def mousePressEvent(self, e):
        if e.button() == qt.MidButton or (e.button() == qt.RightButton and not self.scene.use_rightclick and not self.scene.itemAt(self.mapToScene(e.pos()), QTransform())):
            fake = QMouseEvent(e.type(), e.pos(), qt.LeftButton, qt.LeftButton, e.modifiers())
            self.scene.supress = True
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            common.View.mousePressEvent(self, fake)
        else:
            common.View.mousePressEvent(self, e)
        
    
    def mouseReleaseEvent(self, e):
        if e.button() == qt.MidButton or (e.button() == qt.RightButton and self.scene.supress):
            fake = QMouseEvent(e.type(), e.pos(), qt.LeftButton, qt.LeftButton, e.modifiers())
            common.View.mouseReleaseEvent(self, fake)
            self.setDragMode(QGraphicsView.NoDrag)
            self.scene.supress = False
        else:
            common.View.mouseReleaseEvent(self, e)

    def zoom(self, d):
        zoom = self.transform().scale(d, d).mapRect(QRectF(0, 0, 1, 1)).width()
        if zoom < 10 and d < 1:
            return
        elif zoom > 350 and d > 1:
            return

        self.scale(d, d)

    def wheelEvent(self, e):
        try:
            d = e.angleDelta().y()
        except AttributeError:
            d = e.delta()
        self.zoom(1.0015**d) #1.00005

    @event_property
    def hexcells_ui(self):
        self.viewport().update()
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate if self.hexcells_ui else QGraphicsView.MinimalViewportUpdate)
    
    def drawBackground(self, g, rect):
        if self.hexcells_ui:
            pts = [(-13.837, 8.321), (-13.837, -4.232), (-9.843, -8.274), (11.713, -8.274), (11.713, -5.421), (13.837, -5.421), (13.837, 8.321)]
            poly = QPolygonF([rect.center() + QPointF(*p) for p in pts])
            pen = QPen(qt.gray, 1)
            pen.setCosmetic(True)
            g.setPen(pen)
            g.drawPolygon(poly)



class MainWindow(common.MainWindow):
    title = "SixCells Editor"
    Cell = Cell
    Column = Column
    
    def __init__(self):
        common.MainWindow.__init__(self)

        self.resize(1280, 720)
        self.setWindowIcon(QIcon(here('resources', 'editor.ico')))
        
        self.scene = Scene()

        self.view = View(self.scene)
        self.setCentralWidget(self.view)
        
        self.statusBar()
        
        menu = self.menuBar().addMenu("&File")
        action = menu.addAction("&New", self.close_file, QKeySequence.New)
        action.setStatusTip("Close the current level and start with an empty one.")
        action = menu.addAction("&Open...", self.load_file, QKeySequence.Open)
        action.setStatusTip("Close the current level and load one from a file.")
        action = menu.addAction("&Save", lambda: self.save_file(self.current_file), QKeySequence.Save)
        action.setStatusTip("Save the level, overwriting the current file.")
        action = menu.addAction("Save &As...", self.save_file, QKeySequence('Ctrl+Shift+S'))
        action.setStatusTip("Save the level into a different file.")
        
        menu.addSeparator()
        
        action = menu.addAction("&Copy to Clipboard", self.copy, QKeySequence('Ctrl+C'))
        action.setStatusTip("Copy the current level into clipboard, in a text-based .hexcells format, padded with Tab characters.")
        action = menu.addAction("&Paste from Clipboard", self.paste, QKeySequence('Ctrl+V'))
        action.setStatusTip("Load a level in text-based .hexcells format that is currently in the clipboard.")
        
        menu.addSeparator()
        
        action = menu.addAction("&Quit", self.close, QKeySequence.Quit)
        action.setStatusTip("Close SixCells Editor.")


        menu = self.menuBar().addMenu("&Edit")
        action = menu.addAction("&Undo", self.scene.undo, QKeySequence.Undo)
        action.setStatusTip("Cancel the last action.")
        action = menu.addAction("&Redo", self.scene.redo, QKeySequence.Redo)
        action.setStatusTip("Repeat the last cancelled action.")
        
        menu.addSeparator()
        
        action = menu.addAction("Level &Information", self.set_information, QKeySequence('Ctrl+D'))
        action.setStatusTip("Add or change the level's title, author's name and custom text hints.")


        menu = self.menuBar().addMenu("&Play")
        action = menu.addAction("From &Start", self.play, QKeySequence('Shift+Tab'))
        QShortcut(QKeySequence('Ctrl+Tab'), self, action.trigger)
        action.setStatusTip("Playtest this level from the beginning (discarding all progress).")
        action = menu.addAction("&Resume", lambda: self.play(resume=True), QKeySequence('Tab'))
        action.setStatusTip("Continue playtesting this level from where you left off.")
        
        
        menu = self.menuBar().addMenu("Preference&s")
        
        self.swap_buttons_group = make_action_group(self, menu, self.scene, 'swap_buttons', [
            ("&Left Click Places Blue", False, "A blue cell will be placed when left mouse button is clicked. Black will then be the secondary color."),
            ("&Left Click Places Black", True, "A black cell will be placed when left mouse button is clicked. Blue will then be the secondary color."),
        ])
        self.swap_buttons_group[False].setChecked(True)
        
        menu.addSeparator()
        
        self.secondary_action_group = make_action_group(self, menu, self.scene, 'use_rightclick', [
            ("&Right Click Places Secondary", True, "A cell with color opposite to the above choice will be placed when right mouse button is clicked."),
            ("&Double Click Places Secondary", False, "A cell with color opposite to the above choice will be placed when left mouse button is double-clicked."),
        ])
        self.secondary_action_group[True].setChecked(True)
        
        menu.addSeparator()
        
        states = [
            ("&Blank", 0, "When placed, these cells will not contain a number."),
            ("With &Number", 1, "When placed, these cells will contain a number, for example, \"2\"."),
            ("With &Connection Info", 2, "When placed, these cells will contain a number and connection information, for example, \"{2}\" or \"-3-\"."),
        ]
        submenu = menu.addMenu("Place Blac&ks")
        submenu.setStatusTip("Black cells, when placed, will be...")
        self.black_show_info_group = make_action_group(self, submenu, self.scene, 'black_show_info', states)
        self.black_show_info_group[1].setChecked(True)
        submenu = menu.addMenu("Place &Blues")
        submenu.setStatusTip("Blue cells, when placed, will be...")
        self.blue_show_info_group = make_action_group(self, submenu, self.scene, 'blue_show_info', states[:-1])
        self.blue_show_info_group[0].setChecked(True)
        self.blue_show_info_group[2] = self.blue_show_info_group[0] # for config backwards compatibility

        menu.addSeparator()
        
        self.enable_hexcells_ui_action = action = make_check_action("Show Hexcells &UI", self, 'hexcells_ui')
        action.setChecked(False)
        action.setStatusTip("Show the borders of Hexcells UI to see the limit of level size.")
        menu.addAction(action)
        self.enable_statusbar_action = action = make_check_action("Show &Status Bar", self, 'statusbar_visible')
        action.setChecked(True)
        menu.addAction(action)


        menu = self.menuBar().addMenu("&Help")
        action = menu.addAction("&Instructions", self.help, QKeySequence.HelpContents)
        action.setStatusTip("View README on the project's webpage.")
        action = menu.addAction("&About", self.about)
        action.setStatusTip("About SixCells Editor.")
        
        
        action = QAction("Zoom In", self)
        action.setShortcut(QKeySequence.ZoomIn)
        QShortcut(QKeySequence('+'), self, action.trigger)
        QShortcut(QKeySequence('='), self, action.trigger)
        action.triggered.connect(lambda: self.view.zoom(1.2))
        self.addAction(action)
        action = QAction("Zoom Out", self)
        action.setShortcut(QKeySequence.ZoomOut)
        QShortcut(QKeySequence('-'), self, action.trigger)
        action.triggered.connect(lambda: self.view.zoom(0.85))
        self.addAction(action)


        self.current_file = None
        self.any_changes = False
        self.scene.changed.connect(self.changed)

        self.last_used_folder = None
        self.swap_buttons = False
        self.default_author = None
        
        load_config_from_file(self, self.config_format, 'sixcells', 'editor.cfg')
    
    config_format = '''
        swap_buttons = next(v for v, a in swap_buttons_group.items() if a.isChecked()); swap_buttons_group[v].setChecked(True)
        secondary_cell_action = 'double' if next(v for v, a in secondary_action_group.items() if a.isChecked()) else 'right'; secondary_action_group[v=='double'].setChecked(True)
        default_black = next(v for v, a in black_show_info_group.items() if a.isChecked()); black_show_info_group[v].setChecked(True)
        default_blue = next(v for v, a in blue_show_info_group.items() if a.isChecked()); blue_show_info_group[v].setChecked(True)
        hexcells_ui = enable_hexcells_ui_action.isChecked(); enable_hexcells_ui_action.setChecked(v)
        status_bar = enable_statusbar_action.isChecked(); enable_statusbar_action.setChecked(v)
        undo_history_length = scene.undo_history_length; scene.undo_history_length = v
        antialiasing = view.antialiasing; view.antialiasing = v
        default_author
        last_used_folder
        window_geometry_qt = save_geometry_qt(); restore_geometry_qt(v)
    '''
    
    
    def changed(self, rects=None):
        if rects is None or any((rect.width() or rect.height()) for rect in rects):
            self.any_changes = True
    def no_changes(self):
        self.any_changes = False
        def no_changes():
            self.any_changes = False
        QTimer.singleShot(0, no_changes)
    
    @property
    def status(self):
        return self.statusBar().currentMessage()
    @status.setter
    def status(self, value):
        if not value:
            self.statusBar().clearMessage()
        elif isinstance(value, tuple):
            self.statusBar().showMessage(value[0], int(value[1]*1000))
        else:
            self.statusBar().showMessage(value)
        app.processEvents()
    
    @property
    def hexcells_ui(self):
        self.view.hexcells_ui
    @hexcells_ui.setter
    def hexcells_ui(self, value):
        self.view.hexcells_ui = value
    
    @property
    def statusbar_visible(self):
        return self.statusBar().isVisible()
    @statusbar_visible.setter
    def statusbar_visible(self, value):
        self.statusBar().setVisible(value)
    
    @event_property
    def current_file(self):
        title = self.title
        if self.current_file:
            title = os.path.basename(self.current_file) + ' - ' + title
        self.setWindowTitle(title)
    
    def close_file(self):
        result = False
        if not self.any_changes:
            result = True
        else:
            if self.current_file:
                msg = "The level \"{}\" has been modified. Do you want to save it?".format(self.current_file)
            else:
                msg = "Do you want to save this level?"
            btn = QMessageBox.warning(self, "Unsaved changes", msg, QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
            if btn == QMessageBox.Save:
                if self.save_file(self.current_file):
                    result = True
            elif btn == QMessageBox.Discard:
                result = True
        if result:
            self.current_file = None
            self.scene.reset()
            self.no_changes()
            self.scene.undo_step()
        return result

    
    def set_information(self, desc=None):
        dialog = QDialog()
        dialog.setWindowTitle("Level Information")
        layout = QVBoxLayout()
        dialog.setLayout(layout)
        
        layout.addWidget(QLabel("Title:"))
        title_field = QLineEdit(self.scene.title)
        title_field.setMaxLength(50)
        layout.addWidget(title_field)
        
        layout.addWidget(QLabel("Author name:"))
        author_field = QLineEdit(self.scene.author or self.default_author)
        author_field.setMaxLength(20)
        layout.addWidget(author_field)
        old_author = author_field.text()
        
        information = (self.scene.information).splitlines()
        layout.addWidget(QLabel("Custom text hints:"))
        information1_field = QLineEdit(information[0] if information else '')
        information1_field.setMaxLength(120)
        layout.addWidget(information1_field)
        information2_field = QLineEdit(information[1] if len(information) > 1 else '')
        information2_field.setMaxLength(120)
        layout.addWidget(information2_field)

        layout.addWidget(QLabel("This text will be displayed within the level"))
        
        def accepted():
            self.scene.title = title_field.text().strip()
            self.scene.author = author_field.text().strip()
            if self.scene.author and self.scene.author!=old_author:
                self.default_author = self.scene.author
            self.scene.information = '\n'.join(line for line in [information1_field.text().strip(), information2_field.text().strip()] if line)
            self.changed()
            dialog.close()
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.rejected.connect(dialog.close)
        button_box.accepted.connect(accepted)
        layout.addWidget(button_box)
        
        dialog.exec_()
        
    def center_on(self, x, y):
        self.view.centerOn(x*cos30, y/2 + 0.3)
    
    def copy(self):
        common.MainWindow.copy(self)
        self.center_on(*common.level_center)
    
    def save_file(self, fn=None):
        if not fn:
            try:
                dialog = QFileDialog.getSaveFileNameAndFilter
            except AttributeError:
                dialog = QFileDialog.getSaveFileName
            fn, _ = dialog(self, "Save", self.last_used_folder, "Hexcells level (*.hexcells)")
        if not fn:
            return
        self.status = "Saving..."
        try:
            status = save_file(fn, self.scene)
            if isinstance(status, basestring):
                QMessageBox.warning(None, "Warning", status + '\n' + "Saved anyway.")
            self.no_changes()
            self.current_file = fn
            self.last_used_folder = os.path.dirname(fn)
            self.status = "Done", 1
            self.center_on(*common.level_center)
            return True
        except ValueError as e:
            QMessageBox.critical(None, "Error", str(e))
            self.status = "Failed", 1
    
    
    def prepare(self):
        self.view.fitInView(self.scene.itemsBoundingRect().adjusted(-0.5, -0.5, 0.5, 0.5), qt.KeepAspectRatio)
        self.center_on(16, 16)
        self.no_changes()
        self.scene.undo_step()
    

    def play(self, resume=False):
        self.status = "Switching to Player..."
        
        import player
        
        player.app = app
        
        window = player.MainWindow(playtest=True)
        window.setWindowModality(qt.ApplicationModal)
        window.setWindowState(self.windowState())
        window.setGeometry(self.geometry())

        window.scene.author = self.scene.author
        window.scene.title = self.scene.title
        window.scene.information = self.scene.information
        
        corresponding_cells = []

        for cell in self.scene.all(Cell):
            new = player.Cell()
            window.scene.addItem(new)
            new.place(cell.coord)
            cell.copyattrs(new)
            if resume:
                try:
                    new.revealed = new.revealed or cell.revealed_resume
                except AttributeError: pass
            corresponding_cells.append((cell, new))
            
        for col in self.scene.all(Column):
            new = player.Column()
            window.scene.addItem(new)
            new.place(col.coord)
            col.copyattrs(new)
            
        window.prepare()
    
        windowcloseevent = window.closeEvent
        def closeevent(e):
            windowcloseevent(e)
            for edcell, plcell in corresponding_cells:
                edcell.revealed_resume = plcell.display is not Cell.unknown
        window.closeEvent = closeevent

        window.show()
        app.processEvents()
        window.view.setSceneRect(self.view.sceneRect())
        window.view.setTransform(self.view.transform())
        window.view.horizontalScrollBar().setValue(self.view.horizontalScrollBar().value())
        delta = window.view.mapTo(window.central_widget, QPoint(0, 0))
        window.view.verticalScrollBar().setValue(self.view.verticalScrollBar().value() + delta.y())

        self.status = "Done", 1
    
    def closeEvent(self, e):
        if not self.close_file():
            e.ignore()
            return
        
        save_config_to_file(self, self.config_format, 'sixcells', 'editor.cfg')



def main(f=None):
    global window

    window = MainWindow()
    window.show()

    if not f and len(sys.argv[1:]) == 1:
        f = sys.argv[1]
    if f:
        f = os.path.abspath(f)
        QTimer.singleShot(50, lambda: window.load_file(f))
    
    app.exec_()

if __name__ == '__main__':
    main()