"""
PyInstaller hook to ensure tkinter DLLs are included
"""
from PyInstaller.utils.hooks import collect_dynamic_libs

binaries = collect_dynamic_libs('tkinter')
