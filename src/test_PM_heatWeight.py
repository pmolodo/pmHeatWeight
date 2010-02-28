import PM_heatWeight

try:
    import maya.standalone
    maya.standalone.initialize()
except RuntimeError: pass

import maya.cmds as cmds

cmds.file("C:/Dev/Projects/eclipse/workspace/heatWeightProject/testScenes/scenes/autoRig_test3.mb", o=True, f=True)
cmds.select('root', 'cubeMesh')
PM_heatWeight.heatWeight(undoable=False,
    tempOutputDir='C:/Dev/Projects/eclipse/workspace/heatWeightProject/src',
    tempDelete=False)