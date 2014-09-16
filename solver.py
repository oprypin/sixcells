# A linear programming solver for hexcells
# i.e.: throwing the big-boy-tools at inocent little Hexcells levels
from pulp import *
from common import *

# Should return the solver that will be
# invoked by PuLP to solve the MILPs.
def getSolver():
    # Windows: The glpsol.exe and glpsol*.dll should be
    #          provided by use. However, PuLP will not
    #          find them, even if they are in the current
    #          directory, unless we explicitely tell PuLP
    #          where to look.
    if (GLPK(os.getcwd() + "\\glpsol.exe").available()):
        return GLPK(os.getcwd() + "\\glpsol.exe", msg=0)
    
    # Other OS: There will be no glpsol.exe, but we don't need one:
    #           Assume there is a solver installed and
    #           have pulp find and decide on one.
    # Todo: Test several solvers in non-windows Environments.
    return None
    
def solve(self):
    
    # Optimisation TODO: Determine equivalance classes of variables.
    # Optimisation TODO: Remember cases for variables that did happen.
    # Optimisation TODO: Try to minimise/maximise several vars at once.
    
    # Get Relevant Game Data:
    # cells: All cells regardless of state (Todo: Filter those that are done)
    # columns: All columns regardless of state (Todo: Filter those that are done)
    # known: revealed cells
    # related: Maps a cell to all relevant constraints (cells and columns) that it is a member of
    cells, columns, known, related = self.solve_assist()
    
    # The MILP Problem (managed by PuLP)
    # all variables and constraint will be added to this problem
    problem = LpProblem("HexcellsMILP", LpMinimize)
    
    # Dictionary of Variables.
    # For every cell there is a boolean variable
    # The value of 1 means the cell is blue, 0 means the cell is black.
    # The eventual goal is to determine combinations of values fulfilling all constraints.
    dic     = LpVariable.dicts("v", [str(cell.id) for cell in cells], 0, 1, 'Binary')
    
    # Convenience: Maps a cell to the corresponding variable:
    def getVar(cell):
        return dic[str(cell.id)]
    
    # Number of all (remaining) hexes is known.
    # Todo: Eliminate revealed cells from the model and use self.remaining as right hand side.
    total    = sum([1 for cell in cells if cell.actual == Cell.full])
    problem += lpSum(getVar(cell) for cell in cells) == total
    
    # Constraints equivalent to column number information
    for col in columns:
        # The sum of all cells in that column is the column value
        problem += lpSum(getVar(cell) for cell in col.members) == col.value
        
        # Additional information (together/seperated) available?
        if col.together is not None:
            if col.together:
                # For {n}, cells that are at least n appart cannot be both blue.
                # Example: For {3}, the configurations X??X, X???X, X????X, … are impossible.
                for span in range(col.value, len(col.members) - 1):
                    for start in range(len(col.members) - span):
                        problem += lpSum([getVar(col.members[start]), getVar(col.members[start+span])]) <= 1
            else:
                # For -n-, the sum of any range of n cells may contain at most n-1 blues
                for offset in range(len(col.members) - col.value + 1):
                    problem += lpSum(getVar(col.members[offset+i]) for i in range(col.value)) <= col.value - 1
    
    # Constraints equivalent to cell number information
    # Information only available when cell is revealed
    for cell in known:
        # The Obvious constraint: If the cell is revealed we know its variable already!
        # Optimisation Todo: Eliminate variables of known cells from the problem altogether
        problem += getVar(cell) == (1 if cell.kind == Cell.full else 0)
        
        # If the displays a number, the sum of its neighbourhood (radius 1 or 2) is known
        if cell.value is not None:
            problem += lpSum(getVar(neighbour) for neighbour in cell.members) == cell.value
        
        # Additional togetherness information available?
        # Note: Only relevant if value between 2 and 4.
        # In fact: The following code would do nonsense for 0,1,5,6!
        if cell.together is not None and cell.value >= 2 and cell.value <= 4:
            #        Note: Cells are ordered clockwise.
            # Convenience: Have it wrap around.
            def m(x): return cell.members[x % len(cell.members)]
            
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
                    cond = getVar(m(i))
                    if (m(i).is_neighbor(m(i-1))):
                        cond -= getVar  (m(i-1))
                    if (m(i).is_neighbor(m(i+1))):
                        cond -= getVar  (m(i+1))
                        
                    # no isolated cell
                    problem += cond <= 0
                    # no isolated gap (works by a similar argument)
                    problem += cond >= -1
            else:       
                # -n-: any circular range of n cells contains at most n-1 blues.
                for i in range(len(cell.members)):
                    # the range m(i), …, m(i+n-1) may not all be blue if they are consecutive
                    if all(m(i+j).is_neighbor(m(i+j+1)) for j in range(cell.value-1)):
                        problem += lpSum(getVar(m(i+j)) for j in range(cell.value)) <= cell.value-1
    
    # uncover holds all the deductions I can make.
    # Note: I do not want to yield them immediately,
    # since prove(...) will change the gamestate
    # and I don't want that to happen while working on it.
    uncover = []
    
    # For all cells that are unknown, we let the solver try to:
    #  1.) Minimise its variable
    #  2.) Maximise its variable
    # If the maximum is 0 then we know the cell must be blue  (since var=1 not possible)
    # If the minimum is 1 then we know the cell must be black (since var=0 not possible)
    for cell in cells:
        if cell.kind == Cell.unknown:
            # minimise variable of cell
            problem.setObjective(getVar(cell))
            # Debug: uncomment to output milp description
            # problem.writeLP('hexcells' + str(cell.id) + 'plus.lp')
            
            # Let the solver do its work (this is the slow step)
            problem.solve(solver=getSolver())
            
            # Minimum is 1 ⇒ Cell being black is impossible ⇒ Cell is blue
            if (value(problem.objective) > 0.5):
                uncover += [(cell,Cell.full)]
            
            # We now minimise (-variable), i.e. we maximise (variable)
            problem.setObjective(-getVar(cell))
            # Debug: uncomment to output milp description
            # problem.writeLP('hexcells' + str(cell.id) + 'minus.lp')
            problem.solve(solver=getSolver())
            
            # Maximum is 0 ⇒ Cell is Black
            if(-value(problem.objective) < 0.5):
                uncover += [(cell,Cell.empty)]
    
    # Yield the results
    # If yielding is guaranteed to not change the gamestate
    # it could be done in between
    for (c,val) in uncover:
        print(c.id, val)
        c.proven(val)
        yield (c,val)