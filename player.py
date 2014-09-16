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

import common
from common import *
from pulp import *

from qt import Signal
from qt.core import QRectF, QTimer
from qt.gui import QPolygonF, QPen, QPainter, QTransform, QShortcut
from qt.widgets import QApplication, QGraphicsView, QMainWindow, QFileDialog, QKeySequence


class Cell(common.Cell):
    def __init__(self):
        common.Cell.__init__(self)
        
        self.value = None

    def mousePressEvent(self, e):
        if e.button()==qt.LeftButton:
            want = Cell.full
        elif e.button()==qt.RightButton:
            want = Cell.empty
        else:
            return
        if self.kind is Cell.unknown:
            if self.actual==want:
                self.kind = self.actual
            else:
                self.scene().mistakes += 1

    def proven(self, value):
        try:
            assert self.actual==value
        except AssertionError:
            self.setPen(QPen(qt.red, 0.2))
            raise
        self.kind = value

    @setter_property
    def kind(self, value):
        rem = self.kind is Cell.unknown and value is Cell.full
        yield value
        if rem and self.scene():
            self.scene().remaining -= 1
        self.upd()

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
        
        self.remaining = 0
        self.mistakes = 0

    @event_property
    def remaining(self):
        self.text_changed.emit()

    @event_property
    def mistakes(self):
        self.text_changed.emit()
    
    def drawForeground(self, g, rect):
        g.setBrush(Color.beam)
        g.setPen(QPen(no_pen))
        for it in self.all(Column):
            if it.beam:
                poly = QPolygonF(QRectF(-0.03, 0.525, 0.06, 1e6))
                poly = QTransform().translate(it.scenePos().x(), it.scenePos().y()).rotate(it.rotation()).map(poly)
                poly = poly.intersected(QPolygonF(rect))
                g.drawConvexPolygon(poly)
    
    def solve_assist(self):
        try:
            self.cells
        except AttributeError:
            self.cells = list(self.all(Cell))
            self.columns = list(self.all(Column))
            
            self.related = collections.defaultdict(set)
            for cur in itertools.chain(self.cells, self.columns):
                for x in cur.members:
                    self.related[x].add(cur)
        
        known = {it: it.kind for it in self.cells if it.kind is not Cell.unknown}
        
        return self.cells, self.columns, known, self.related

    
    def solve_simple(self):
        cells, columns, known, related = self.solve_assist()
    
        for cur in itertools.chain(known, columns):
            if not any(x.kind is Cell.unknown for x in cur.members):
                continue
            if cur.value is not None:
                # Fill up remaining fulls
                if cur.value==sum(1 for x in cur.members if x.kind is not Cell.empty):
                    for x in cur.members:
                        if x.kind is Cell.unknown:
                            x.proven(Cell.full)
                    if isinstance(cur, Column):
                        cur.hidden = True
                    yield
                # Fill up remaining empties
                if len(cur.members)-cur.value==sum(1 for x in cur.members if x.kind is not Cell.full):
                    for x in cur.members:
                        if x.kind is Cell.unknown:
                            x.proven(Cell.empty)
                    if isinstance(cur, Column):
                        cur.hidden = True
                    yield

    #def is_possible(self, assumed, max_depth=None, depth=0):
        #cells, columns, known, related = self.solve_assist()
        
        #def kind(x):
            #try:
                #return assumed[x]
            #except KeyError:
                #return x.kind
        
        #all_related = set(itertools.chain.from_iterable((x for x in related[cur] if isinstance(x, Column) or (x.kind is not Cell.unknown and x.value is not None)) for cur in assumed))
        
        #for cur in all_related:
            #if sum(1 for x in cur.members if kind(x) is Cell.full)>cur.value:
                #return False
            #if sum(1 for x in cur.members if kind(x) is Cell.empty)>len(cur.members)-cur.value:
                #return False
            #if cur.together is not None and cur.value>1:
                #if isinstance(cur, Cell):
                    #together = all_grouped({x for x in cur.members if kind(x) is Cell.full}, key=Cell.is_neighbor)
                #else:
                    #groups = list(itertools.groupby(cur.members, key=lambda x: kind(x) is Cell.full))
                    #together = sum(1 for k, gr in groups if k)<=1
                #if not cur.together and together and cur.value>=#TODO
        #return True


    #def solve_negative_proof(self):
        #cells, columns, known, related = self.solve_assist()
        
        #for cur in self.cells:
            #if cur.kind is Cell.unknown:
                #if not self.is_possible({cur: Cell.full}):
                    #cur.proven(Cell.empty)
                    #yield
                #elif not self.is_possible({cur: Cell.empty}):
                    #cur.proven(Cell.full)
                    #yield
    
    def getSolver(self):
        # Windows: Current path is not in the PATH
        #          We need to tell GLPK where to find the binary
        if (GLPK(os.getcwd() + "\\glpsol.exe").available()):
            return GLPK(os.getcwd() + "\\glpsol.exe", msg=0)
        
        # Other OS: Assume there is a solver installed
        #           Have pulp find and decide on one.
        # Todo: Test if it works fine with some solvers.
        return None
        
    def solve(self):
        # Todo: Determine equivalance classes for greater speed
        def v(c):
            return str(c.id)
        
        cells, columns, known, related = self.solve_assist()
        
        # create problem and varibles
        problem = LpProblem("HexcellsMILP", LpMinimize)
        dic     = LpVariable.dicts("v", [v(cell) for cell in cells], 0, 1, 'Binary')
        
        # create total sum constraint
        total    = sum([1 for c in cells if c.actual == Cell.full])
        problem += lpSum(dic[v(c)] for c in cells) == total
        
        # create column-number constraints
        for col in columns:
            problem += lpSum(dic[v(c)] for c in col.members) == col.value
            
            if col.together is not None and col.value >= 2:
                def m(i): return col.members[i]
                n = len(col.members)
                if col.together:
                    for i in range(n - col.value):
                        problem += lpSum([dic[v(m(i))], dic[v(m(i+col.value))]]) <= 2
                else:
                    for i in range(n - col.value + 1):
                        problem += lpSum(dic[v(m(i+j))] for j in range(col.value)) <= col.value - 1
        
        while(True):
            # create cell-number constraints 
            for cell in known:
                problem += dic[v(cell)] == (1 if cell.kind == Cell.full else 0)
                
                if cell.value is not None:
                    problem += lpSum(dic[v(c)] for c in cell.members) == cell.value
                if cell.together is not None and cell.value >= 2 and cell.value <= 4:
                    # note: Cells are ordered clockwise from m(0) to m(n-1)!
                    n = len(cell.members)
                    def m(i): return cell.members[i % n]
                    if cell.together:
                        # we must avoid the -X- and the X-X pattern
                        for i in range(n):
                            cond = dic[v(m(i))]
                            if (m(i).is_neighbor(m(i-1))):
                                cond -= dic[v(m(i-1))]
                            if (m(i).is_neighbor(m(i+1))):
                                cond -= dic[v(m(i+1))]
                                
                            # no isolated cell
                            problem += cond <= 0
                            # no isolated gap
                            problem += cond >= -1
                    else:
                        # not all together:
                        for i in range(n):
                            if all(m(i+j).is_neighbor(m(i+j+1)) for j in range(cell.value-1)):
                                problem += lpSum(dic[v(m(i+j))] for j in range(cell.value)) <= cell.value-1
            
            uncover = []
            for c in cells:
                if c.kind == Cell.unknown:
                    problem.setObjective(dic[v(c)])
                    # problem.writeLP('hexcells' + v(c) + 'plus.lp')
                    problem.solve(solver=self.getSolver())
                    
                    if (value(problem.objective) > 0.5):
                        uncover += [(c,Cell.full)]
                    
                    problem.setObjective(-dic[v(c)])
                    # problem.writeLP('hexcells' + v(c) + 'minus.lp')
                    problem.solve(solver=self.getSolver())
                    
                    if(-value(problem.objective) < 0.5):
                        uncover += [(c,Cell.empty)]
            
            for c,v in uncover:
                c.proven(v)
                yield (c,v)
            
            # Yield Nothing once to show that we need to start over now.
            yield (None,None)
            # If they want us to continue, these are the cells for which we now have new info:
            known = [c for (c,v) in uncover]
            
        # anything = True
        # while anything:
        #     anything = False
        #     for _ in self.solve_simple():
        #         anything = True
        #         yield
            
            #for _ in self.solve_negative_proof():
                #anything = True
                #yield
                #break
    
    def do_SolveStep(self):
        progress = False
        for (cell, value) in self.solve():
            if cell is None:
                return progress
            progress = True
    
    def do_SolveComplete(self):
        while self.do_SolveStep():
            continue
        # If he identified all blue cells, he'll have the rest uncovered as well
        return self.remaining == 0 
    
    def do_solve(self):
        self.do_SolveStep()


class View(QGraphicsView):
    def __init__(self, scene):
        QGraphicsView.__init__(self, scene)
        self.scene = scene
        self.scene.text_changed.connect(lambda: self.resizeEvent(None)) # ensure a full redraw
        self.setRenderHints(self.renderHints()|QPainter.Antialiasing)

    def resizeEvent(self, e):
        QGraphicsView.resizeEvent(self, e)
        self.fit()

    def fit(self):
        self.fitInView(self.scene.itemsBoundingRect().adjusted(-0.5, -0.5, 0.5, 0.5), qt.KeepAspectRatio)
    
    def paintEvent(self, e):
        QGraphicsView.paintEvent(self, e)
        g = QPainter(self.viewport())
        g.setRenderHints(self.renderHints())
        try:
            font = self._text_font
        except AttributeError:
            self._text_font = font = g.font()
            font.setPointSize(font.pointSize()*3 if font.pointSize()>0 else 30)
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
        
        menu = self.menuBar().addMenu("File")
        action = menu.addAction("Open...", self.open_file, QKeySequence.Open)
        menu.addSeparator()
        action = menu.addAction("Quit", self.close, QKeySequence('Tab'))
        QShortcut(QKeySequence('`'), self, action.trigger)
        QShortcut(QKeySequence.Close, self, action.trigger)
        QShortcut(QKeySequence.Quit, self, action.trigger)
        
        action = self.menuBar().addAction("Solve", self.scene.do_solve)
        QShortcut(QKeySequence("S"), self, action.trigger)

        menu = self.menuBar().addMenu("Help")
        action = menu.addAction("Instructions", help, QKeySequence.HelpContents)
        action = menu.addAction("About", lambda: about(self.windowTitle()))
        
    
    def open_file(self, fn=None):
        if not fn:
            try:
                dialog = QFileDialog.getOpenFileNameAndFilter
            except AttributeError:
                dialog = QFileDialog.getOpenFileName
            fn, _ = dialog(self, "Open", filter=file_filter)
        if not fn:
            return
        self.scene.clear()
        try:
            gz = fn.endswith('.gz')
        except AttributeError:
            gz = False
        load(fn, self.scene, gz=gz, Cell=Cell, Column=Column)
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