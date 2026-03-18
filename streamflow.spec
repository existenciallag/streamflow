# streamflow.spec
# PyInstaller specification for StreamFlow – Flow Cytometry Manager
#
# Build command (from the project root on Windows):
#   pyinstaller streamflow.spec
#
# Requirements:
#   pip install pyinstaller
#   pip install -r requirements.txt    (must be installed in the same environment)

import os
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# ── Collect everything Streamlit needs (frontend, templates, icons, etc.) ────
streamlit_datas, streamlit_binaries, streamlit_hiddenimports = collect_all("streamlit")

# ── Other packages that use dynamic imports ───────────────────────────────────
altair_datas, altair_binaries, altair_hiddenimports       = collect_all("altair")
plotly_datas,  plotly_binaries,  plotly_hiddenimports     = collect_all("plotly")

# ── Application source files to bundle alongside app.py ──────────────────────
app_datas = [
    ("app.py",       "."),
    ("schema.sql",   "."),
    ("ui",           "ui"),
    ("utils",        "utils"),
    ("models",       "models"),
    (".streamlit",   ".streamlit"),
    ("data",         "data"),          # CSV seed files (reagents, brands, etc.)
]

all_datas = (
    app_datas
    + streamlit_datas
    + altair_datas
    + plotly_datas
    + collect_data_files("pandas")
    + collect_data_files("numpy")
    + collect_data_files("pyarrow")
    + collect_data_files("tzdata", include_py_files=True)
)

all_binaries = streamlit_binaries + altair_binaries + plotly_binaries

all_hidden = (
    streamlit_hiddenimports
    + altair_hiddenimports
    + plotly_hiddenimports
    + collect_submodules("streamlit")
    + collect_submodules("pandas")
    + collect_submodules("numpy")
    + [
        "sqlite3",
        "pkg_resources.py2_warn",
        "packaging",
        "packaging.version",
        "packaging.specifiers",
        "packaging.requirements",
        "pydeck",
        "pyarrow",
        "pyarrow.lib",
    ]
)

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "PIL", "cv2"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="StreamFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,        # ← No black terminal window
    # icon="icon.ico",   # ← Uncomment and provide an .ico file for a custom icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="StreamFlow",
)
