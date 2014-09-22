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
# i.e.: throwing the big-boy-tools at inocent little Hexcells levels

from __future__ import division, print_function

import os.path
import distutils.spawn

from pulp import *

from common import *


# Should return the solver that will be
# invoked by PuLP to solve the MILPs.
def get_solver():
    global solver
    try:
        return solver
    except NameError:
        pass
    
    # Windows: The glpsol.exe and glpsol*.dll should be
    #          provided by user. However, PuLP will not
    #          find them, even if they are in the current
    #          directory, unless we explicitly tell PuLP
    #          where to look.
    
    # 
    path = here('pulp', 'solverdir', 'glpsol.exe')
    solver = GLPK(path, msg=0, options=['--cuts'])
    if solver.available():
        print("Using GLPK:", path)
        return solver
    
    # Try to find glpsol in PATH
    path = distutils.spawn.find_executable('glpsol')
    if path:
        path = os.path.abspath(path)
        solver = GLPK(path, msg=0, options=['--cuts'])
        if solver.available():
            print("Using GLPK:", path)
            return solver
    
    # Other OS: There will be no glpsol.exe, but we don't need one:
    #           Assume there is a solver installed and
    #           have pulp find and decide on one.
    print("No solver found; a default may be found")
    solver = None
    return None



def solve_simple(scene):
    for cur in itertools.chain(scene.all_cells, scene.all_columns):
        if isinstance(cur, Cell) and cur.kind is Cell.unknown:
            continue
        if cur.value is not None and any(x.kind is Cell.unknown for x in cur.members):
            # Fill up remaining fulls
            if cur.value==sum(1 for x in cur.members if x.kind is not Cell.empty):
                for x in cur.members:
                    if x.kind is Cell.unknown:
                        yield x, Cell.full
            # Fill up remaining empties
            if len(cur.members)-cur.value==sum(1 for x in cur.members if x.kind is not Cell.full):
                for x in cur.members:
                    if x.kind is Cell.unknown:
                        yield x, Cell.empty


def solve(scene):
    # Get Relevant Game Data:
    # cells:   All cells (regardless of state)
    # columns: All columns
    # known: revealed cells
    # unknown: unrevealed cells
    # solver: MILP program to use
    
    cells   = scene.all_cells
    columns = scene.all_columns
    known   = [cell for cell in cells if cell.kind is not Cell.unknown]
    unknown = [cell for cell in cells if cell.kind is Cell.unknown]
    
    ####################################################
    #   -- Equivalance Class Optimisation --
    ####################################################
    
    # We say, two unknown cells are equivalent if they are subject
    # to the same constraints (not just equal, but the same)
    # if a cell can be blue/black then an equivalent cell has those
    # options two, since they can switch places without affecting constraints
    # *Unless* there are togetherness constraints involved (see below).
    # Idea: Have one variable for each class with range 0 to the size of the class
    # This models the number of hexes in the class that are blue.
    # The hexes of the class are blue (black)
    # iff we can prove the variable assumes its max (min)
    
    # cellConstraints: Maps a cell to all relevant
    # constraints (cells and columns) that it is a member of
    cellConstraints = collections.defaultdict(set)
    for cur in itertools.chain(known, columns):
        # Ignore uninformative constraints
        if (cur.value is None):
            continue
        for x in cur.members:
            cellConstraints[x].add(cur)
    
    # Cells are now equivalent iff their cellConstraints match.
    # The leftmost cell in the collection is the representative,
    # i.e. repOf[cell] points to the leftmost cell that is equivalent to cell.
    # note that this is well-defined since cells are equivalent to themselves.
    # repOf[cell] is the representative of the equivalance class of cell.
    repOf = {}
    for cell1 in unknown:
        for cell2 in unknown:
            if cellConstraints[cell1] == cellConstraints[cell2]:
                repOf[cell1] = cell2
    
    # since cells subject to togetherness constraints cannot swap places (they are a special case)
    # they must be their own representative and cannot be considered equivalent
    # to anyone but themselves.
    for cell in unknown:
        for constraint in cellConstraints[cell]:
           if constraint.together is not None:
                repOf[cell] = cell
    
    # from now on it will suffice to find information on equivalance classes
    # a class is a pair of one representative and the size of the class
    classes = {rep : sum(1 for cell in unknown if repOf[cell] is rep) for rep in unknown if repOf[rep] is rep}
    
    ####################################################
    #     -- The MILP Problem (managed by PuLP) --
    ####################################################
    
    solver  = get_solver()
    problem = LpProblem('HexcellsMILP', LpMinimize)
    
    # For every equivalance class of cells there is a integer variable,
    # modeling the number of blue cells in that class.
    # The class is blue (or black) iff we can prove that the variable
    # is necessarily the size of the class (or 0)
    # This Dictionary maps a cell id to the respective variable.
    dic = { rep.id : LpVariable('v'+str(rep.id), lowBound = 0, upBound = size, cat = 'Integer') for rep, size in classes.items() }
    
    # Convenience: Maps a cell to the corresponding variable or constant:
    # Note that the cells of a class will appear in the same constraints,
    # so we ignore every cell but the representative.
    def get_var(cell):
        if cell.kind is not Cell.unknown: #cell is constant
            return 1 if cell.kind is Cell.full else 0 
        elif repOf[cell] is cell: #cell is representative
            return dic[cell.id] 
        else: # cell is non representative
            return 0 
    
    # The number of remaining blue hexes is known
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
                    for start in range(len(col.members) - span):
                        problem += lpSum([get_var(col.members[start]), get_var(col.members[start+span])]) <= 1
            else:
                # For -n-, the sum of any range of n cells may contain at most n-1 blues
                for offset in range(len(col.members) - col.value + 1):
                    problem += lpSum(get_var(col.members[offset+i]) for i in range(col.value)) <= col.value - 1
    
    # Constraints from cell number information
    for cell in known:
        # If the displays a number, the sum of its neighbourhood (radius 1 or 2) is known
        if cell.value is not Cell.unknown:
            problem += lpSum(get_var(neighbour) for neighbour in cell.members) == cell.value
        
        # Additional togetherness information available?
        # Note: Only relevant if value between 2 and 4.
        # In fact: The following code would do nonsense for 0,1,5,6!
        if cell.together is not None and cell.value >= 2 and cell.value <= 4:
            #        Note: Cells are ordered clockwise.
            # Convenience: Have it wrap around.
            def m(x):
                return cell.members[x % len(cell.members)]
            
            if cell.together:
                # note how togetherness is equivalent to the following
                # two patterns not occuring: "-X-" and the "X-X"
                # in other words: No lonely blue cell and no lonely gap
                for i in range(len(cell.members)):
                    # No lonely cell condition:
                    # Say m(i) is a blue.
                    # Then m(i-1) or m(i+1) must be blue.
                    # That means: -m(i-1) +m(i) -m(i+1) <= 0
                    # Note that m(i+1) and m(i-1) only count
                    # if they are real neighbours.
                    cond = get_var(m(i))
                    if m(i).is_neighbor(m(i-1)):
                        cond -= get_var(m(i-1))
                    if m(i).is_neighbor(m(i+1)):
                        cond -= get_var(m(i+1))
                        
                    # no isolated cell
                    problem += cond <= 0
                    # no isolated gap (works by a similar argument)
                    problem += cond >= -1
            else:
                # -n-: any circular range of n cells contains at most n-1 blues.
                for i in range(len(cell.members)):
                    # the range m(i), ..., m(i+n-1) may not all be blue if they are consecutive
                    if all(m(i+j).is_neighbor(m(i+j+1)) for j in range(cell.value-1)):
                        problem += lpSum(get_var(m(i+j)) for j in range(cell.value)) <= cell.value-1

    # First, get any solution.
    # Shitty default solver can't handle no objective, so invent one:
    spam = LpVariable('spam', 0, 1, 'binary')
    problem += (spam == 1)
    problem.setObjective(spam) # no optimisation function yet
    problem.solve(solver)
    
    def get_true_false_classes():
        true_set  = set()
        false_set = set()
        
        for rep,size in classes.items():
            if value(get_var(rep)) == 0:
                false_set.add(rep)
            elif value(get_var(rep)) == size:
                true_set.add(rep)
        return true_set, false_set
    
    # get classes that are fully true or false
    # they are candidates for solvable classes
    T, F = get_true_false_classes()
    
    while T or F:
        # Now try to vary as much away from the
        # initial solution as possible:
        # We try to make the variables True, that were False before
        # and vice versa. If no change could be achieved, then
        # the remaining variables have their unique possible value.
        problem.setObjective(lpSum(get_var(t) for t in T) - lpSum(get_var(f) for f in F))
        problem.solve(solver)
        
        # all true variables stayed true and false stayed false?
        # Then they have their unique value and we are done!
        if value(problem.objective) == sum(classes[rep] for rep in T):
            for rep in T:
                for cell in unknown:
                    if repOf[cell] is rep:
                        yield cell, Cell.full
            for rep in F:
                for cell in unknown:
                    if repOf[cell] is rep:
                        yield cell, Cell.empty
            return
        
        T_new, F_new = get_true_false_classes()
        
        # remember only those classes that subbornly kept their pure trueness/falseness
        T = T & T_new
        F = F & F_new
            
        
#        # This old code handled the variables independently
#        # creating tons of milps. The above solution tries
#        # to find more information per call to the solver and
#        # succeeds in doing so.
#        
#        # Idea: For all cells that are unknown, we let the solver try to:
#        #  1.) Minimise its variable
#        #  2.) Maximise its variable
#        # If the maximum is 0 then we know the cell must be blue  (since var=1 not possible)
#        # If the minimum is 1 then we know the cell must be black (since var=0 not possible)
#        for cell,size in classes.items():
#            # minimise variable of cell
#            problem.setObjective(get_var(cell))
#            # Debug: uncomment to output milp description
#            # problem.writeLP('hexcells' + str(cell.id) + 'plus.lp')
#            
#            # Let the solver do its work (this is the slow step)
#            problem.solve(solver)
#            
#            # Minimum is 1 => Cell being black is impossible => Cell is blue
#            if value(problem.objective) == size:
#                for other in unknown:
#                    if repOf[other] == cell:
#                        yield other, Cell.full
#            
#            
#            # We now minimise (-variable), i.e. we maximise (variable)
#            problem.setObjective(-get_var(cell))
#            # Debug: uncomment to output milp description
#            # problem.writeLP('hexcells' + str(cell.id) + 'minus.lp')
#            problem.solve(solver)
#            
#            # Maximum is 0 => Cell is Black
#            if -value(problem.objective) == 0:
#                for other in unknown:
#                    if repOf[other] == cell:
#                        yield other, Cell.empty
# 