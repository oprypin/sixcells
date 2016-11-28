This folder contains scripts that produce the Windows releases of SixCells.

**Step 1:** Run *make_runners.cmd* on Windows with Visual Studio installed (adjust its location as needed) to produce *editor.exe* and *player.exe* which simply run `python\python.exe editor.py` etc.
Or just copy these from a previous release.

**Step 2:** Run *make_bundle.sh* on Linux to produce a *sixcells* folder one level above, with all the files needed to run SixCells on Windows.

Requirements: *wget*, *wine*, *unzip*, *git*
