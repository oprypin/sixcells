#!/bin/bash

cd "$(dirname "$0")"

dest="$PWD/../sixcells"
mkdir -p "$dest"

# Copy runners to destination
cp *.exe "$dest"

function py {
    # Run Python Windows executable through Wine
    # Filter out numerous 'fixme' messages (Wine bugs)
    wine "$dest/python/python.exe" "$@" 2>&1 | grep -vE '^(fixme|err):'
}

if ! test -d "$dest/python"; then
    py_ver=3.5.3

    mkdir "$dest/python"
    pushd "$dest/python"

    # Download and extract Python portable binaries
    fn="python-$py_ver-embed-win32.zip"
    wget "https://www.python.org/ftp/python/$py_ver/$fn"
    unzip "$fn"
    rm "$fn"

    # Some libs don't work with the standard library in an archive, extract it
    fn=(python*.zip) # Need the array so the '*' is expanded
    mv "$fn" Lib.zip
    mkdir "$fn"
    unzip -d "$fn" Lib.zip
    rm Lib.zip

    # Install pip
    wget https://bootstrap.pypa.io/get-pip.py
    py get-pip.py
    rm get-pip.py

    py -m pip install pyqt5 https://github.com/oprypin/pulp/archive/master.zip

    # Obtain solver from GLPK
    wget https://sourceforge.net/projects/winglpk/files/latest/download --content-disposition
    fn=(winglpk-*.zip)  # Need the array so the '*' is expanded
    glpk_ver=${fn%.*}    # Drop extension
    glpk_ver=${glpk_ver##*-} # Start from the dash to get just the version
    unzip -j "$fn" "glpk-$glpk_ver/"{w32/glpsol.exe,w32/glpk_${glpk_ver/./_}.dll,COPYING} -d "Lib/site-packages/pulp/solverdir"
    rm "$fn"

    # Configure PuLP to use this solver on Windows
    rm Lib/site-packages/pulp/*.cfg.*
    rm -r Lib/site-packages/pulp/solverdir/cbc
    echo $'[locations]\nGlpkPath = %(here)s\solverdir\glpsol' > Lib/site-packages/pulp/pulp.cfg.win

    # Remove largest unneeded files
    rm -r Lib/site-packages/PyQt5/Qt/{translations,qml,bin/{*WebEngine*,Qt5{Designer,Quick,Qml,XmlPatterns,CLucene,QuickWidgets}.dll},plugins/{sqldrivers,position,geoservices,sensorgestures,sceneparsers},resources}
    rm -r Lib/site-packages/PyQt5/{*WebEngine*,Qt{Designer,Quick,Qml,XmlPatterns,QuickWidgets}.pyd}

    py -m pip uninstall --yes setuptools wheel pip
    rm -r Scripts

    popd
fi

pushd ..

find . -type d -name '__pycache__' -exec rm -r {} \;

cp --parents -- $(git ls-files) "$dest"
# Clean unneeded files
rm -r "$dest/"{.gitignore,.windows}

# Make a versioned archive
sixcells_ver="$(py -c 'from common import __version__; print(__version__)')"
zip -r "sixcells-$sixcells_ver-win32.zip" sixcells
