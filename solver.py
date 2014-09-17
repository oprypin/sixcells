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
    solver = GLPK(path, msg=0)
    if solver.available():
        print("Using GLPK:", path)
        return solver
    
    # Try to find glpsol in PATH
    path = os.path.abspath(distutils.spawn.find_executable('glpsol'))
    if path:
        solver = GLPK(path, msg=0)
        if solver.available():
            print("Using GLPK:", path)
            return solver
    
    # Other OS: There will be no glpsol.exe, but we don't need one:
    #           Assume there is a solver installed and
    #           have pulp find and decide on one.
    print("No solver found; a default may be found")
    solver = None
    return None


def solve_assist(scene):
    cells   = list(scene.all(Cell))
    columns = list(scene.all(Column))
    
    # related contains all the active conditions
    # a cell is a part of
    related = collections.defaultdict(set)
    for cur in itertools.chain(cells, columns):
        # Ignore unrevealed or uninformative cells
        if isinstance(cur, Cell) and (cur.kind is Cell.unknown or cur.value is None):
            continue
        for x in cur.members:
            related[x].add(cur)
    
    known     = {it: it.kind for it in cells if it.kind is not Cell.unknown}
    unknown   = [cell for cell in cells if cell.kind is Cell.unknown]
    solver    = get_solver()
    return cells, columns, known, unknown, related, solver


def solve(scene):
    # Get Relevant Game Data:
    # cells: All cells regardless of state (TODO: Filter those that are done)
    # columns: All columns regardless of state (TODO: Filter those that are done)
    # known: revealed cells
    # unknown: unrevealed cells
    # related: Maps a cell to all relevant constraints (cells and columns) that it is a member of
    # solver: MILP program to use
    cells, columns, known, unknown, related, solver = solve_assist(scene)
    
    # The MILP Problem (managed by PuLP)
    # all variables and constraint will be added to this problem
    problem = LpProblem("HexcellsMILP", LpMinimize)
    
    # Dictionary of Variables.
    # For every unknown cell there is a boolean variable
    # The value of 1 means the cell is blue, 0 means the cell is black.
    # The eventual goal is to determine combinations of values fulfilling all constraints.
    dic     = LpVariable.dicts('v', [str(cell.id) for cell in cells if cell.kind is Cell.unknown], 0, 1, 'Binary')
    
    # Convenience: Maps a cell to the corresponding variable (or constant if its known already):
    def get_var(cell):
        return dic[str(cell.id)] if cell.kind is Cell.unknown else cell.kind
    
    problem += lpSum(get_var(cell) for cell in unknown) == scene.remaining
    
    # Constraints equivalent to column number information
    for col in columns:
        # The sum of all cells in that column is the column value
        problem += lpSum(get_var(cell) for cell in col.members) == col.value
        
        # Additional information (together/seperated) available?
        if col.together is not None:
            if col.together:
                # For {n}, cells that are at least n appart cannot be both blue.
                # Example: For {3}, the configurations X??X, X???X, X????X, ... are impossible.
                for span in range(col.value, len(col.members) - 1):
                    for start in range(len(col.members) - span):
                        problem += lpSum([get_var(col.members[start]), get_var(col.members[start+span])]) <= 1
            else:
                # For -n-, the sum of any range of n cells may contain at most n-1 blues
                for offset in range(len(col.members) - col.value + 1):
                    problem += lpSum(get_var(col.members[offset+i]) for i in range(col.value)) <= col.value - 1
    
    # Constraints equivalent to cell number information
    # Information only available when cell is revealed
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
                    # That means: -m(i-1) +m(i) -m(i+1) <= o
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

    # We say, two cells are equivalent if they are subject
    # to the same constraints (not just equal, but the same)
    # if a cell can be blue/black an equivalent cell has those
    # options two, since they can switch places without affecting constraints
    # *Unless* there are togetherness constraints involved (see below).
    eq_classes = {}
    
    # note: the leftmost cell in the collection is the representative
    #       i.e. eq_classes[cell] points to the leftmost cell that is equivalent to cell.
    #       note that this is welldefined since cells are equivalent to themselves.
    for cell1 in unknown:
        for cell2 in unknown:
            if related[cell1] == related[cell2]:
                eq_classes[cell1] = cell2
    
    # since cells subject to togetherness constraints cannot swap places
    # they must be their own representative and cannot be considered equivalent
    # to anyone but themselves.
    for cell in unknown:
        for constraint in related[cell]:
           if constraint.together is not None:
                eq_classes[cell] = cell
    
    # from now on it will suffice to find information on the representatives
    representatives = [cell for cell in unknown if eq_classes[cell] is cell]
    

    # First, get any solution
    problem.setObjective(lpSum(0)) # no optimisation function yet
    problem.solve(solver)
    
    def get_true_false_partition():
        true_set  = set()
        false_set = set()
        
        for cell in unknown:
            if value(get_var(cell)) == 0:
                false_set.add(cell)
            else:
                true_set.add(cell)
        return true_set, false_set
    
    T, F = get_true_false_partition()
    
    # Now try to vary as much away from the
    # initial solution as possible:
    # We try to make the variables True, that were False before
    # and vice versa. If no change could be achieved, then
    # the remaining variables have their unique possible value.
    
    while T or F:
        # new objective: try to vary as much from known values as possible
        problem.setObjective(lpSum(get_var(t) for t in T) - lpSum(get_var(f) for f in F))
        problem.solve(solver)
        
        if value(problem.objective) == len(T):
            break
        
        T_new, F_new = get_true_false_partition()
        
        # remove the cells from T that are now false
        T = T - F_new
        F = F - T_new

    
    # minimising T - F yielded T
    # i.e. the vars in T cannot help but be 1
    # and  the vars in F cannot help but be 0
    for t in T:
        yield t, Cell.full
    for f in F:
        yield f, Cell.empty
    

# This old code handled the variables independently
# creating tons of milps. The above solution tries
# to find more information per call to the solver and
# succeeds in doing so.
    
#    # Idea: For all cells that are unknown, we let the solver try to:
#    #  1.) Minimise its variable
#    #  2.) Maximise its variable
#    # If the maximum is 0 then we know the cell must be blue  (since var=1 not possible)
#    # If the minimum is 1 then we know the cell must be black (since var=0 not possible)
#    for cell in representatives:
#        # minimise variable of cell
#        problem.setObjective(get_var(cell))
#        # Debug: uncomment to output milp description
#        # problem.writeLP('hexcells' + str(cell.id) + 'plus.lp')
#        
#        # Let the solver do its work (this is the slow step)
#        problem.solve(solver)
#        
#        # Minimum is 1 => Cell being black is impossible => Cell is blue
#        if value(problem.objective) == 1:
#            for other in unknown:
#                if eq_classes[other] == cell:
#                    yield other, Cell.full
#        
#        # We now minimise (-variable), i.e. we maximise (variable)
#        problem.setObjective(-get_var(cell))
#        # Debug: uncomment to output milp description
#        # problem.writeLP('hexcells' + str(cell.id) + 'minus.lp')
#        problem.solve(solver)
#        
#        # Maximum is 0 => Cell is Black
#        if -value(problem.objective) == 0:
#            for other in unknown:
#                if eq_classes[other] == cell:
#                    yield other, Cell.empty
#