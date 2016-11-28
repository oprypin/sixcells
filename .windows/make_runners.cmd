rem "Creates editor.exe and player.exe which simply run the bundled Python"

call "C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\vcvarsall.bat"

for %%e in (editor player) do (
    copy ..\resources\%%e.ico .
    echo MAINICON ICON "%%e.ico" > %%e.rc
    rc %%e.rc

    echo #define CMD "python\\pythonw.exe %%e.py" > %%e.c
    echo #include "runner.c" >> %%e.c
    cl /nologo /c /O1 /Os /GL /D /MT /GR- /TC %%e.c

    link /NOLOGO /LTCG /INCREMENTAL:NO /MANIFEST:NO /MACHINE:X86 %%e.obj %%e.res
)
