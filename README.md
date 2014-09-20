# SixCells

Level editor for [Hexcells](http://store.steampowered.com/sub/50074/).

Work in progress.

*SixCells Editor* allows creation of levels and outputs them in a JSON format.
These levels can be played using *SixCells Player*.  
It does not actually interact with *Hexcells* in any way.

![Logo](https://raw.githubusercontent.com/BlaXpirit/sixcells/master/logo.png)

## How to Use

### Editor

Left click on empty space to add a blue cell, right click to add a black cell (configurable).
(hold Alt to ignore collision between side-by-side cells, as seen in "FINISH" levels)  
Left click a cell to switch between 3 information display modes.  
Alt+click a cell to mark it as revealed.  

Drag from inside a cell to outside the cell to add a column number marker.  
Left click a column marker to toggle information display.  

Right click an item to remove it.  

Press and drag mouse wheel to navigate.  
Scroll to zoom.  

Shift+drag on empty space to start a freehand selection.  
Shift+click a cell to add or remove it from current selection.  
Shift+click on empty space to clear selection.  
Drag one of the selected cells to relocate them.  

Press Tab to switch to playtest mode (open *Player*).  

### Player

*Open* a level created in the *Editor* and play it.

Full auto-solving capabilities are present.  

If you use the *Player* to playtest right from *Editor*, it will save state between sessions.  
Right click to revert a cell to yellow.  


## Level File Structure

### *.hexcells format

Encoding: UTF-8

A level is a sequence of 39 lines, separated with '\n' character:

- "Hexcells level v1"
- Level title
- Author
- Level custom text, part 1
- Level custom text, part 2
- 33 level lines follow:
    - A line is a sequence of 33 2-character groups, separated with ' ' character.
        - '.' = nothing, 'o' = black, 'O' = black revealed, 'x' = blue, 'X' = blue revealed, '\','|','/' = column number at 3 different angles (-60, 0, 60)
        - '.' = blank, '+' = has number, 'c' = consecutive, 'n' = not consecutive

### *.sixcells format

Encoding: UTF-8

```python
{
  "version": 1,
  # Version of the level format.
  # To be incremented if backwards-incompatible changes are introduced.
  
  "title": text,
  # Name of the level. Optional.
  
  "author": text,
  # Name of the author. Optional.
  
  "information": text,
  # Custom text hints for the level. Optional.

  "cells": [ # Hexagonal cells
    {
      "id": integer,
      # Unique number that can be used to refer to this cell.
      
      "kind": integer,
      # 0: black, 1: blue, -1: yellow (never used).
      
      "neighbors": [integers],
      # List of IDs of cells that touch this cell
      # ordered clockwise.
      
      "members": [integers],
      # List of IDs of cells that are related to this cell:
      # same as neighbors for black, nearby in 2-radius for blue.
      # This key is present only for cells that have a number in them.
      
      "revealed": boolean,
      # Should this cell be initially revealed?
      # true: yes, (absent): no
      
      "value": integer,
      # The number written on the cell (absent if there is no number).
      # This is redundant; it may be deduced from "members",
      # but presence/absence of it still matters.

      "together": boolean,
      # Are the blue "members" all grouped together (touching)?
      # true: yes, false: no, (absent): no information given.
      # Can be present only if "value" is present.

      "x": number,
      "y": number
      # Absolute coordinates of the center of this cell.
    },
    ...
  ],
  
  "columns": [ # Column numbers
    {
      "members": [integers],
      # List of IDs of cells that are in this column
      # ordered from nearest to farthest.
      
      "value": integer,
      # The number written on the column.
      # This is redundant; it may be deduced from "members".

      "together": boolean,
      # Are the blue cells in this column all grouped together?
      # true: yes, false: no, (absent): no information given.
      
      "x": number,
      "y": number,
      # Absolute coordinates of the center
      # of the imaginary hexagon that contains this number.
      
      "angle": number,
      # Angle of rotation in degrees
      # (only -60, 0, 60 are possible).
    },
    ...
  ],
}
```


## Installation

- **Windows**

  Download the latest [release](https://github.com/BlaXpirit/sixcells/releases), extract the folder and you're ready to go!

- **Linux**

  Go to a folder where you would like *SixCells* to be and execute this (you will need `git`):

  ```bash
  git clone --recursive https://github.com/BlaXpirit/sixcells
  ```
  
  ...or just download the `win32` [release](https://github.com/BlaXpirit/sixcells/releases) and extract it. It works because the binary release also contains full source code.
  
  Install `python-pyside` or `python-pyqt4`, `python-pulp` (`pip install pulp`), optionally `glpk`.

- **Mac**
  
  *SixCells* should work under Mac if the needed libraries are available. Try to adapt the instructions for Linux.

  
## Technical Details

*SixCells* is written using [Python](http://python.org/) and [Qt](http://qt-project.org/).  
[PuLP](https://pypi.python.org/pypi/PuLP) is used for solving.  

It is guaranteed to work on Python 3.4 and later; Versions 2.7 and 3.* should also work.

*SixCells* supports Qt 4 and Qt 5, and can work with either [PySide](http://pyside.org/), [PyQt4](http://www.riverbankcomputing.co.uk/software/pyqt/download) or [PyQt5](http://www.riverbankcomputing.co.uk/software/pyqt/download5).  

License: GNU General Public License Version 3.0 (GPLv3)
