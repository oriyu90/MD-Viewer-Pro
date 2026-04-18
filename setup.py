from setuptools import setup

APP = ['main.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False, # Macでの起動エラーを防ぐためFalse
    'packages': ['PySide6', 'markdown'],
    # WebEngineの依存関係を明示的に含める
    'includes': [
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineCore',
        'PySide6.QtPrintSupport'
    ],
    'plist': {
        'CFBundleName': "MDViewerPro",
        'CFBundleDisplayName': "MD Viewer Pro",
        'CFBundleGetInfoString': "Markdown Viewer and Editor",
        'CFBundleIdentifier': "com.yuki.mdviewer",
        'CFBundleVersion': "1.1.0",
        'CFBundleShortVersionString': "1.1.0",
        'NSHighResolutionCapable': True,
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
