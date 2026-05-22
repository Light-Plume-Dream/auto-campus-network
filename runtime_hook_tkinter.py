import os
import sys

if getattr(sys, 'frozen', False):
    base = sys._MEIPASS
    os.environ['TCL_LIBRARY'] = os.path.join(base, 'tcl', 'tcl8.6')
    os.environ['TK_LIBRARY'] = os.path.join(base, 'tcl', 'tk8.6')
