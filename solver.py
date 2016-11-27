# Copyright (C) 2014 Stefan Walzer <sekti@gmx.net>
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


"""A linear programming solver for Hexcells"""
# i.e.: throwing the big-boy-tools at innocent little Hexcells levels

from __future__ import division, print_function

import itertools

from pulp import GLPK, LpProblem, LpMinimize, LpVariable, lpSum, value

from common import *


# Should return the solver that will be
# invoked by PuLP to solve the MILPs.
def get_solver():
    global solver
    try:
        return solver
    except NameError: pass

    solver = GLPK(None, msg=False, options=['--cuts'])
    if solver.available():
        print("Using solver from:", solver.path)
        return solver

    # There may be no glpsol. Let PuLP try to find another solver.
    print("Couldn't find 'glpsol' solver; a default may be found")
    solver = None


def solve(scene):
    cells   = scene.all_cells
    columns = scene.all_columns
    known   = [cell for cell in cells if cell.display is not Cell.unknown]
    unknown = [cell for cell in cells if cell.display is Cell.unknown]
    
    ####################################################
    #   -- Equivalence Class Optimisation --
    ####################################################
    
    # We say, two unknown cells are equivalent if they are subject
    # to the same constraints (not just equal, but the same)
    # if a cell can be blue/black then an equivalent cell has those
    # options too, since they can switch places without affecting constraints
    # *Unless* there are togetherness constraints involved (see below).
    # Idea: Have one variable for each class with range 0 to the size of the class
    # This models the number of cells in the class that are blue.
    # The cells of the class are blue (black)
    # iff we can prove the variable assumes its max (min)
    
    # cell_constraints: Maps a cell to all relevant
    # constraints (cells and columns) that it is a member of
    cell_constraints = collections.defaultdict(set)
    for cur in itertools.chain(known, columns):
        # Ignore uninformative constraints
        if cur.value is None:
            continue
        for x in cur.members:
            cell_constraints[x].add(cur)
    
    # Cells are now equivalent iff their cell_constraints match.
    # The leftmost cell in the collection is the representative,
    # i.e. rep_of[cell] points to the leftmost cell that is equivalent to cell.
    # note that this is well-defined since cells are equivalent to themselves.
    # rep_of[cell] is the representative of the equivalence class of cell.
    rep_of = {}
    for cell1 in unknown:
        cc1 = cell_constraints[cell1]
        for cell2 in unknown:
            if cc1 == cell_constraints[cell2]:
                rep_of[cell1] = cell2
    
    # since cells subject to togetherness constraints cannot swap places (they are a special case)
    # they must be their own representative and cannot be considered equivalent
    # to anyone but themselves.
    for cell in unknown:
        for constraint in cell_constraints[cell]:
           if constraint.together is not None:
                rep_of[cell] = cell
    
    # from now on it will suffice to find information on equivalence classes
    # a class is a pair of one representative and the size of the class
    classes = {rep: sum(1 for cell in unknown if rep_of[cell] is rep) for rep in unknown if rep_of[rep] is rep}
    
    ####################################################
    #     -- The MILP Problem (managed by PuLP) --
    ####################################################
    
    solver = get_solver()
    problem = LpProblem('HexcellsMILP', LpMinimize)
    
    # For every equivalence class of cells there is a integer variable,
    # modeling the number of blue cells in that class.
    # The class is blue (or black) iff we can prove that the variable
    # is necessarily the size of the class (or 0)
    # This Dictionary maps a cell id to the respective variable.
    dic = {rep.id: LpVariable('v'+str(rep.id), 0, size, 'Integer') for rep, size in classes.items()}
    
    # Convenience: Maps a cell to the corresponding variable or constant:
    # Note that the cells of a class will appear in the same constraints,
    # so we ignore every cell but the representative.
    def get_var(cell):
        if cell.display is not Cell.unknown: #cell is constant
            return 1 if cell.display is Cell.full else 0
        elif rep_of[cell] is cell: #cell is representative
            return dic[cell.id]
        else: # cell is non representative
            return 0
    
    # The number of remaining blue cells is known
    problem += lpSum(get_var(cell) for cell in unknown) == scene.remaining
    
    # Constraints from column number information
    for col in columns:
        # The sum of all cells in that column is the column value
        problem += lpSum(get_var(cell) for cell in col.members) == col.value
        
        # Additional information (together/seperated) available?
        if col.together is not None:
            if col.together:
                # For {n}: cells that are at least n appart cannot be both blue.
                # Example: For {3}, the configurations X??X, X???X, X????X, ... are impossible.
                for span in range(col.value, len(col.members)):
                    for start in range(len(col.members)-span):
                        problem += lpSum([get_var(col.members[start]), get_var(col.members[start+span])]) <= 1
            else:
                # For -n-, the sum of any range of n cells may contain at most n-1 blues
                for offset in range(len(col.members)-col.value+1):
                    problem += lpSum(get_var(col.members[offset+i]) for i in range(col.value)) <= col.value-1
    
    # Constraints from cell number information
    for cell in known:
        # If the displays a number, the sum of its neighbourhood (radius 1 or 2) is known
        if cell.value is not None:
            problem += lpSum(get_var(neighbour) for neighbour in cell.members) == cell.value
        
        # Additional togetherness information available?
        # Note: Only relevant if value between 2 and 4.
        # In fact: The following code would do nonsense for 0,1,5,6!
        if cell.together is not None and cell.value >= 2 and cell.value <= 4:
            # Note: Cells are ordered clockwise.
            # Convenience: Have it wrap around.
            m = cell.members+cell.members
            
            if cell.together:
                # note how togetherness is equivalent to the following
                # two patterns not occuring: "-X-" and the "X-X"
                # in other words: No lonely blue cell and no lonely gap
                for i in range(len(cell.members)):
                    # No lonely cell condition:
                    # Say m[i] is a blue.
                    # Then m[i-1] or m[i+1] must be blue.
                    # That means: -m[i-1] +m[i] -m[i+1] <= 0
                    # Note that m[i+1] and m[i-1] only count
                    # if they are real neighbours.
                    cond = get_var(m[i])
                    if m[i].is_neighbor(m[i-1]):
                        cond -= get_var(m[i-1])
                    if m[i].is_neighbor(m[i+1]):
                        cond -= get_var(m[i+1])
                        
                    # no isolated cell
                    problem += cond <= 0
                    # no isolated gap (works by a similar argument)
                    problem += cond >= -1
            else:
                # -n-: any circular range of n cells contains at most n-1 blues.
                for i in range(len(cell.members)):
                    # the range m[i], ..., m[i+n-1] may not all be blue if they are consecutive
                    if all(m[i+j].is_neighbor(m[i+j+1]) for j in range(cell.value-1)):
                        problem += lpSum(get_var(m[i+j]) for j in range(cell.value)) <= cell.value-1

    # First, get any solution.
    # Default solver can't handle no objective, so invent one:
    spam = LpVariable('spam', 0, 1, 'binary')
    problem += (spam == 1)
    problem.setObjective(spam) # no optimisation function yet
    problem.solve(solver)
    
    def get_true_false_classes():
        true_set  = set()
        false_set = set()
        
        for rep, size in classes.items():
            if value(get_var(rep)) == 0:
                false_set.add(rep)
            elif value(get_var(rep)) == size:
                true_set.add(rep)
        return true_set, false_set
    
    # get classes that are fully true or false
    # they are candidates for solvable classes
    true, false = get_true_false_classes()
    
    while true or false:
        # Now try to vary as much away from the
        # initial solution as possible:
        # We try to make the variables True, that were False before
        # and vice versa. If no change could be achieved, then
        # the remaining variables have their unique possible value.
        problem.setObjective(lpSum(get_var(t) for t in true)-lpSum(get_var(f) for f in false))
        problem.solve(solver)
        
        # all true variables stayed true and false stayed false?
        # Then they have their unique value and we are done!
        if value(problem.objective) == sum(classes[rep] for rep in true):
            for tf_set, kind in [(true, Cell.full), (false, Cell.empty)]:
                for rep in tf_set:
                    for cell in unknown:
                        if rep_of[cell] is rep:
                            yield cell, kind
            return
        
        true_new, false_new = get_true_false_classes()
        
        # remember only those classes that subbornly kept their pure trueness/falseness
        true &= true_new
        false &= false_new



def solve_simple(scene):
    for cur in itertools.chain(scene.all_cells, scene.all_columns):
        if isinstance(cur, Cell) and cur.display is Cell.unknown:
            continue
        if cur.value is not None and any(x.display is Cell.unknown for x in cur.members):
            # Fill up remaining fulls
            if cur.value == sum(1 for x in cur.members if x.display is not Cell.empty):
                for x in cur.members:
                    if x.display is Cell.unknown:
                        yield x, Cell.full
            # Fill up remaining empties
            if len(cur.members)-cur.value == sum(1 for x in cur.members if x.display is not Cell.full):
                for x in cur.members:
                    if x.display is Cell.unknown:
                        yield x, Cell.empty
