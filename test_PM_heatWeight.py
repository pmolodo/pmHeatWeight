import PM_heatWeight

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds

cmds.file("C:/Dev/Projects/eclipse/workspace/heatWeightProject/testScenes/autoRig_test1.mb", o=True, f=True)
cmds.select('root', 'cubeMesh')
PM_heatWeight.heatWeight()