# SixCells

Level editor for [Hexcells](http://store.steampowered.com/sub/50074/).

![Logo](https://raw.githubusercontent.com/BlaXpirit/sixcells/master/resources/logo.png)

---

### Contents

- [How to Use](#usage)
  - [Player](#player)
  - [Editor](#editor)
- [Installation](#installation)
  - [Windows](#windows)
  - [Linux](#linux)
  - [Mac](#mac)
- [Sharing Levels](#sharing-levels)
- [Technical Details](#technical-details)
  - [Level File Structure](#level-file-structure)

---

## How to Use

### Player

Open a level or paste one from clipboard and play it.

Left-click/right-click an orange cell to mark it as blue/black. Right click to revert a cell to yellow.

If you use the *Player* to playtest right from *Editor*, it will save state between sessions.  
Right click to revert a cell to yellow.  

Full auto-solving capabilities are present.

### Editor

[Video demonstration](http://youtu.be/fFq36x8fSew)

##### Creating and Deleting Items

Action | Button
-------| -----------
Create blue cell | Left-click
Create black cell | Right-click
Create column number | Left-click on cell and drag outwards
Delete cell/column number | Right-click

##### Modifying Items

Action | Button
-------| -----------
Cycle through information display | Left-click on cell/column number
Mark/unmark cell as revealed | Alt + left-click on cell

##### Selection

Action | Button
-------| -----------
Freehand selection | Shift + drag on empty space
Select/deselect a cell | Shift + left-click on cell
Deselect all | Shift + left-click on empty space
Drag and drop selected | Left-click and drag

##### Navigation

Action | Button
------ | -------
Pan the view | Press and drag mouse wheel
Zoom in/out | Mouse wheel up/down

##### Play Test Mode

Action | Button
------ | -------
Toggle playtest mode | Tab
Play from start | Ctrl + Tab

---

## Installation

### **Windows**

Download the latest [release](https://github.com/BlaXpirit/sixcells/releases), extract the folder and you're ready to go!

### **Linux**

Install `git`, `python-pyside` or `python-pyqt4`, `python-pulp` (`pip install pulp`), optionally `glpk`:

- Debian, Ubuntu

  ```bash
  sudo apt-get update
  sudo apt-get install git python-pyside glpk-utils python-pip
  sudo pip install pulp
  ```

- Arch Linux

  ```bash
  sudo pacman -Sy git python-pyqt4 glpk python-pip
  pip install --user pulp
  ```

Go to a folder where you would like *SixCells* to be and obtain the source code:

```bash
git clone --recursive https://github.com/BlaXpirit/sixcells
  ```

Now you can start `editor.py` and `player.py` by opening them in a file explorer or from command line.

### **Mac**
  
*SixCells* should work under Mac if the needed libraries are available. Try to adapt the instructions for Linux.

---

## Sharing Levels

To find levels to play and share your own, visit [reddit.com/r/hexcellslevels](http://reddit.com/r/hexcellslevels).

---

## Technical Details

*SixCells* is written using [Python](http://python.org/) and [Qt](http://qt-project.org/).  
[PuLP](https://pypi.python.org/pypi/PuLP) is used for solving.  

It is guaranteed to work on Python 3.3 and later; Versions 2.7 and 3.* should also work.

*SixCells* supports Qt 4 and Qt 5, and can work with either [PySide](http://pyside.org/), [PyQt4](http://www.riverbankcomputing.co.uk/software/pyqt/download) or [PyQt5](http://www.riverbankcomputing.co.uk/software/pyqt/download5).  

License: GNU General Public License Version 3.0 (GPLv3)


### Level File Structure

#### *.hexcells format

Encoding: UTF-8

A level is a sequence of 39 lines, separated with '\n' character:

- "Hexcells level v1"
- Level title
- Author
- Level custom text, part 1
- Level custom text, part 2
- 33 level lines follow:
    - A line is a sequence of 33 2-character groups.
        - '.' = nothing, 'o' = black, 'O' = black revealed, 'x' = blue, 'X' = blue revealed, '\','|','/' = column number at 3 different angles (-60, 0, 60)
        - '.' = blank, '+' = has number, 'c' = consecutive, 'n' = not consecutive

#### *.sixcells format

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
      
      "angle": number
      # Angle of rotation in degrees
      # (only -60, 0, 60 are possible).
    },
    ...
  ]
}
```
