import maya.cmds as cmds
import os
import sys

MAYA_SEP = '/'

def correctSysPath():
    for i, path in enumerate(sys.path):
        if path[-1] in (MAYA_SEP, os.sep, os.altsep):
            sys.path[i] = sys.path[i][:-1]

correctSysPath()
