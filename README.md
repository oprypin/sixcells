# SixCells

Level editor for [Hexcells](http://store.steampowered.com/sub/50074/).

Work in progress.

Right now it only allows creation of levels and outputs them in JSON. These levels can't even be played.  
It does not actually work with *Hexcells* in any way.

![Logo](https://raw.githubusercontent.com/BlaXpirit/sixcells/master/logo.png)

## How to Use

Left click to add a cell.  
Left click a cell to toggle blue/black.  
Double click a cell to switch between 3 information display modes.  

Drag from inside a cell to outside the cell to add a column number marker.  
Left click a column marker to toggle information display.  

Right click an item to remove it.  

Press and drag mouse wheel to navigate.  
Scroll to zoom.  


## Level File Structure

```python
{
  "hexs": [ # Hexagonal cells
    {
      "id": integer,
      # Number that can be used to refer to this cell
      
      "kind": integer,
      # 0: black, 1: blue, -1: yellow (never used)
      
      "members": [integers],
      # List of IDs of hexes that are related to it (neighbors for black, nearby in a circle for blue)
      # This key is present only for cells that have a number written on them
      
      "revealed": boolean,
      # Should this cell be initially revealed?
      # true: yes, (absent): no
      
      "together": boolean,
      # Are the neighboring ("members") cells all grouped together?
      # true: yes, false: no, (absent): no information given

      "x": number,
      "y": number,
      # Absolute coordinates of the center of this cell
      
      "value": integer
      # The number written on the cell (absent if there is no number)
      # This is redundant; it may be deduced from "members"
    },
    ...
  ], 
  "cols": [ # Column numbers
    {
      "members": [integers],
      # List of IDs of hexes that are in this column
      
      "together": boolean,
      # Are the cells in this column all grouped together?
      # true: yes, false: no, (absent): no information given
      
      "x": number,
      "y": number,
      # Absolute coordinates of the center of the hexagon that contains this number
      
      "value": integer
      # The number written on the column
      # This is redundant; it may be deduced from "members"
    }
  ]
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
  
  Install the library `python-pyside` or `python-pyqt4`.
  
  If you know what you're doing, you can make it work under Python 2 and 3, Qt 4 and 5 in any combination.

- **Mac**
  
  *SixCells* should work under Mac if the needed libraries are available. Try to adapt the instructions for Linux.

  
## Technical Details

*SixCells* is written using the [Python programming language](http://python.org/) and [Qt](http://qt-project.org/).

It is guaranteed to work on Python 3.4 and later; Versions 2.7 and 3.* should also work.

*SixCells* supports Qt 4 and Qt 5, and can work with either [PySide](http://pyside.org/), [PyQt4](http://www.riverbankcomputing.co.uk/software/pyqt/download) or [PyQt5](http://www.riverbankcomputing.co.uk/software/pyqt/download5).

License: GNU General Public License Version 3.0 (GPLv3)
