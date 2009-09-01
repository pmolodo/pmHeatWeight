#==============================================================================
#Copyright (c) 2009 Paul Molodowitch
#
#Permission is hereby granted, free of charge, to any person
#obtaining a copy of this software and associated documentation
#files (the "Software"), to deal in the Software without
#restriction, including without limitation the rights to use,
#copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the
#Software is furnished to do so, subject to the following
#conditions:
#
#The above copyright notice and this permission notice shall be
#included in all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#OTHER DEALINGS IN THE SOFTWARE.
#==============================================================================

'''
DESCRIPTION:
------------
This is an auto-weighting script for attaching a joint skeleton to a poly mesh
skin.  It acts as a front-end to Ilya Baran & Jovan Popovic's "Pinocchio"
auto-rigging and weighting library.  (see http://www.mit.edu/~ibaran/autorig/).
Specifically, it uses their heat-weighting algorithm (also implemented in
Blender) to provide MUCH better default weights than Maya's bind skin weights.

Currently, since it interface's to a Pinocchio executable, it is only
available on windows, intel-based Mac OSX, and Linux.  The source for building the
binary  is available at:
http://github.com/elrond79/Pinocchio/tree/master
... if you want to try compiling a binary for another system.
(Note - the source has only very minor modifications from that released by Ilya and
Jovan.)

SETUP:
------
Step 1: Copy the script files,
      /scripts/PM_heatWeight.py
      /scripts/AttachWeightsWin.exe  (if you're using windows)
      /scripts/AttachWeightsMac      (if you're using intel-based OSX)
      /scripts/AttachWeightsLinux    (if you're using linux)
   
   to the your scripts folder: it's exact location varies depending on your os.

On Windows XP:
   C:\Documents and Settings\[USER]\My Documents\maya\[VERSION]\scripts
On Vista:
   C:\Users\[USER]\Documents\maya\[VERSION]\scripts
On OSX:
   /Users/[USER]/Library/Preferences/Autodesk/maya/[VERSION]/scripts
On Linux:
   ~/maya/[VERSION]/scripts


Step 2: Copy In/Add to your userSetup.py

   If if you do not already have a 'userSetup.py' (NOTE- the ending is .py, NOT
   .mel!!!) in the above folder, copy in the provided one - otherwise, open it
   and add it's contents to the end of the existing userSetup.py (NOTE: On
   windows, use notepad or wordpad, NOT microsoft word!)

Step 3: Create a shelf icon
   With maya closed, copy:
      /prefs/icons/heatWeight.xpm
   into your maya icons folder:
      .../maya/[VERSION]/prefs/icons/heatWeight.xpm
   Also, copy:
      /prefs/shelves/shelf_heatWeight.mel
   into your shelves folder:
      .../maya/[VERSION]/prefs/shelves/shelf_heatWeight.mel
   (When you start maya, you may drag the shelf button to another shelf with
   the middle mouse button, and then delete the 'heatWeight' shelf, if so
   desired.)
   
USAGE:
------
Select the root of the skeleton you wish to weight to and the meshes you wish
to weight to the skeleton, then click the shelf button; wait a few moments for
the script to finish, and you're done.

Note that the method this works by weighting to bones, rather than joints.
This means that:
    a) End joints (joints with no child joints) are never weighted
    b) A vertex may not be weighted to the 'closest' joint, if there is a
       'closer' BONE
Keep this in mind when laying out your skeleton, if you intend to weight it
using this script.

You may also invoke the script from a python command-line / script editor, for
additional options:

>>> import PM_heatWeight; PM_heatWeight.heatWeight()

For full details on the additional options available, do:

>>> import PM_heatWeight; help(PM_heatWeight.heatWeight)


ALL HAIL TO:
------------
Most of the credit for this working  as nicely as it does goes to Ilya Baran &
Jovan Popovic, who published the algorithm / developed / released the source
code for the Pinocchio auto-rigging / weighting utility, which this script
makes use of!

Thanks to Sam Hodge (samhodge1972 on highend3d) for the initial linux port of
the binary!

RELEASE INFO:
-------------

version %s

New releases will be posted to creativecrash.com (formerly highend3d.com): go to
http://www.creativecrash.com/maya/downloads/scripts-plugins/character/c/pm-heatweight
...or search for 'PM_heatWeight' in the maya downloads if that link is outdated);
if you wish to contact me regarding this script, either leave a message on the
forum there, or email me at heatWeight DOT calin79, domain neverbox DOT com.
(If you're not a spam bot, you should hopefully be able to figure out the
correct formatting of that email address...) 

Changelog:

v0.6.4 - linux + Mac OSX binaries now included!
v0.6.3 - updated help file (no longer need a .dll since 0.6.2)
v0.6.2 - added an optional 'stiffness' parameter 
v0.6.1 - maya 8.5 / 2008 support
v0.6   - first public release! 
v0.5.2 - changed input format - now can select multiple meshes
v0.5.1 - automatically loads obj plugin, closes open poly borders
v0.5   - initial version
'''

class Version(object):
    def __init__(self, *args):
        self.nums = args
    def __str__(self):
        return ".".join([str(x) for x in self.nums])

version = Version(0,6,4)
__doc__ = __doc__ % str(version)

import subprocess
import tempfile
import os
import os.path
import platform

import maya.cmds as cmds #@UnresolvedImport
import maya.mel as mel
import maya.OpenMaya as api
import maya.OpenMayaAnim as apiAnim

DEBUG = False
KEEP_PINOC_INPUT_FILES = True

_PINOCCHIO_DIR = os.path.join(os.path.dirname(__file__))
_PINOCCHIO_BIN = os.path.join(_PINOCCHIO_DIR, 'AttachWeights')
if os.name == 'nt':
    _PINOCCHIO_BIN += '.exe'
elif platform.system() == 'Linux':
    _PINOCCHIO_BIN += 'Linux'
elif platform.system() == 'Darwin':
    _PINOCCHIO_BIN += 'Mac'
else:
    raise RuntimeError('Unsupported OS: %s' % platform.system())

class PinocchioError(Exception): pass
class BinaryNotFoundError(PinocchioError): pass

def pinocchioSkeletonExport(skeletonRoot, skelFile=None):
    """
    Exports the skeleton to a file format that pinocchio can understand.

    Returns (skelFile, skelList), where skelList is the list returned
    by  makePinocchioSkeletonList.
    """
    if skelFile is None:
        skelFile = browseForFile(m=1, actionName='Export')
    skelList = makePinocchioSkeletonList(skeletonRoot)
    fileObj = open(skelFile, mode="w")
    try:
        for jointIndex, (joint, parentIndex) in enumerate(skelList):
            jointCoords = getTranslation(joint, space='world')
            if DEBUG:
                print joint, ":", jointIndex, jointCoords, parentIndex
            fileObj.write("%d %.5f %.5f %.5f %d\r\n" % (jointIndex,
                                                        jointCoords[0],
                                                        jointCoords[1],
                                                        jointCoords[2],
                                                        parentIndex))
    finally:
        fileObj.close()
    return (skelFile, skelList)

def pinocchioObjExport(mesh, objFilePath):
    loadObjPlugin()
    savedSel = cmds.ls(sl=1)
    try:
        if not isATypeOf(mesh, 'geometryShape'):
            subShape = getShape(mesh)
            if subShape:
                mesh = subShape
        if not isATypeOf(mesh, 'geometryShape'):
            raise TypeError('cannot find a geometry shape for %s' % mesh)
            
        meshDup = addShape(mesh)
        cmds.polyCloseBorder(meshDup, ch=0)
        cmds.polyTriangulate(meshDup, ch=0)
        cmds.select(meshDup, r=1)
        cmds.file(objFilePath,
                op="groups=0;ptgroups=0;materials=0;smoothing=0;normals=0",
                typ="OBJexport", es=True, f=1)
        cmds.delete(meshDup)
    finally:
        cmds.select(savedSel)
    return objFilePath


def makePinocchioSkeletonList(rootJoint):
    """
    Given a joint, returns info used for the pinocchio skeleton export.
    
    Each item in the list is a tuple ([x,y,z], parentIndex), where
    parentIndex is an index into the list.
    """
    return _makePinocchioSkeletonList([], rootJoint, -1)

def _makePinocchioSkeletonList(skelList, newJoint, newJointParent):
    newIndex = len(skelList)
    skelList.append((newJoint, newJointParent))

    jointChildren = listForNone(cmds.listRelatives(newJoint, type="joint",
                                                   children=True,
                                                   noIntermediate=True,
                                                   fullPath=True))
    for joint in jointChildren:
        _makePinocchioSkeletonList(skelList, joint, newIndex)
    return skelList

def pinocchioWeightsImport(mesh, skin, skelList, weightFile=None,
                           undoable=False):
    #Ensure that all influences in the skelList are influences for the skin
    allInfluences = influenceObjects(skin)
    pinocInfluences = [joint for joint, parent in skelList]
    for joint in pinocInfluences:
        if not nodeIn(joint, allInfluences):
            cmds.skinCluster(skin, edit=1, addInfluence=joint)

    if weightFile is None:
        weightFile = browseForFile(m=0, actionName='Import')
    vertBoneWeights = readPinocchioWeights(weightFile)
    numVertices = len(vertBoneWeights)
    numBones = len(vertBoneWeights[0])
    numJoints = len(skelList)
    numWeights = numVertices * numJoints
    if DEBUG:
        print "numVertices:", numVertices
        print "numBones:", numBones
    assert(numBones == numJoints - 1,
           "numBones (%d) != numJoints (%d) - 1" % (numBones, numJoints))

    # Pinocchio sets weights per-bone... maya weights per joint.
    # Need to decide whether to assign the bone weight to the 'start' joint
    #   of the bone, or the 'end' joint
    boneIndexToJointIndex = [0] * numBones
    vertJointWeights = [[0] * numJoints for i in xrange(numVertices)]

    assignBoneToEndJoint = False
    if assignBoneToEndJoint:
        for jointIndex in xrange(1, numJoints):
            boneIndexToJointIndex[jointIndex - 1] = jointIndex
    else:
        for jointIndex in xrange(1, numJoints):
            parentIndex = skelList[jointIndex][1]
            boneIndexToJointIndex[jointIndex - 1] = parentIndex
    
    for vertIndex, boneWeights in enumerate(vertBoneWeights):
        assert(abs(sum(boneWeights) - 1) < 0.1,
               "Output for vert %d not normalized - total was: %.03f" %
               (vertIndex, sum(boneWeights)))
        for boneIndex, boneValue in enumerate(boneWeights):
            # multiple bones can correspond to a single joint -
            # make sure to add the various bones values together!
            jointIndex = boneIndexToJointIndex[boneIndex] 
            vertJointWeights[vertIndex][jointIndex] += boneValue

    if DEBUG:
        print "vertJointWeights:"
        for i, jointWeights in enumerate(vertJointWeights):
            if i < 20:
                print jointWeights
            else:
                print "..."
                break
            
    # Zero all weights
    cmds.skinPercent(skin, mesh, pruneWeights=100, normalize=False)

    if not undoable:
        # Use the api methods to set skin weights - MUCH faster than using
        # mel skinPercent, but api doesn't have built-in undo support, so
        # flush the undo queue
        apiWeights = api.MDoubleArray(numWeights, 0)
        for vertIndex, jointWeights in enumerate(vertJointWeights):
            for jointIndex, jointValue in enumerate(jointWeights):
                apiWeights.set(jointValue, vertIndex * numJoints + jointIndex)
        apiJointIndices = api.MIntArray(numJoints, 0)
        for apiIndex, joint in enumerate(influenceObjects(skin)):
            apiJointIndices.set(apiIndex, getNodeIndex(joint, pinocInfluences))
        if DEBUG:
            print "apiJointIndices:",
            pyJointIndices = []
            for i in xrange(apiJointIndices.length()):
                pyJointIndices.append(apiJointIndices[i])
            print pyJointIndices
        apiComponents = api.MFnSingleIndexedComponent().create(api.MFn.kMeshVertComponent)
        apiVertices = api.MIntArray(numVertices, 0)
        for i in xrange(numVertices):
            apiVertices.set(i, i)
        api.MFnSingleIndexedComponent(apiComponents).addElements(apiVertices) 
        mfnSkin = apiAnim.MFnSkinCluster(toMObject(skin))
        oldWeights = api.MDoubleArray()
        undoState = cmds.undoInfo(q=1, state=1)
        cmds.undoInfo(state=False)
        try:
            mfnSkin.setWeights(toMDagPath(mesh),
                               apiComponents,
                               apiJointIndices,
                               apiWeights,
                               False,
                               oldWeights)
        finally:
            cmds.flushUndo()
            cmds.undoInfo(state=undoState)
    else:
        # Use mel skinPercent - much slower, but undoable
        cmds.progressWindow(title="Setting new weights...", isInterruptable=True,
                            max=numVertices)
        lastUpdateTime = cmds.timerX()
        updateInterval = .5
        for vertIndex, vertJoints in enumerate(vertJointWeights):
            jointValues = {}
            if cmds.progressWindow( query=True, isCancelled=True ) :
                break
            #print "weighting vert:", vertIndex
            for jointIndex, jointValue in enumerate(vertJoints):
                if jointValue > 0:
                    jointValues[pinocInfluences[jointIndex]] = jointValue
    
            if cmds.timerX(startTime=lastUpdateTime) > updateInterval:
                progress = vertIndex
                cmds.progressWindow(edit=True,
                                    progress=progress,
                                    status="Setting Vert: (%i of %i)" % (progress, numVertices))
                lastUpdateTime = cmds.timerX()

            cmds.skinPercent(skin, mesh + ".vtx[%d]" % vertIndex, normalize=False,
                             transformValue=jointValues.items())
        cmds.progressWindow(endProgress=True)    

def useUndoableMethod():
    message = \
    '''This script works in two modes:
    slow, but undoable
    faster, but clears undo
    
Which do you prefer?'''
    undoable = 'Undoable'
    faster = 'Faster'
    button = cmds.confirmDialog(title='Confirm', message=message,
                                button=[undoable,faster],
                                defaultButton=undoable,
                                cancelButton=undoable,
                                dismissString=undoable)
    if button == faster:
        return False
    else:
        return True

def readPinocchioWeights(weightFile):
    weightList = []
    fileObj = open(weightFile)
    try:
        for line in fileObj:
            weightList.append([float(x) for x in line.strip().split(' ')])
    finally:
        fileObj.close()
    return weightList

def runPinocchioBin(meshFile, weightFile, fit=False, stiffness=1.0):
    # Change current directory to ensure we know where attachment.out will be
    if not os.path.isfile(_PINOCCHIO_BIN):
        raise BinaryNotFoundError("Could not find the binary: %s" %
                                  _PINOCCHIO_BIN)
    os.chdir(_PINOCCHIO_DIR)
    exeAndArgs = [_PINOCCHIO_BIN, meshFile, '-skel', weightFile,
                  '-stiffness', str(stiffness)]
    if fit:
        exeAndArgs.append('-fit')
    if DEBUG:
        print "Calling command line binary:"
        print 'subprocess.call(%r)' % exeAndArgs
        print ' '.join(exeAndArgs)
    returnVal = subprocess.call(exeAndArgs)
    if returnVal != 0:
        raise PinocchioError("return code: %d" % returnVal)

def heatWeight(*args, **kwargs):
    """
    heatWeight(*rootAndMeshes, **kwargs)
    
    The non-keyword args should consist of exactly one skeleton root, and
    at least one mesh you wish to weight to that skeleton. If no args are
    given, the current selection is used.
    
    Valid keyword args:
    undoable=False
        Specify whether to assign skin weights using a slower, but undoable
        method, or a faster method that requires flushing the undo queue.
    stiffness=1.0
        Specify how 'stiff' to make the binding to the skeleton. The higher
        the value, the more tightly vertices will be bound to the joint
        deemed 'closest', and the less weights will 'bleed'.
        Note that if a joint is relatively 'far' from all bones, then modifying
        this value still may not have much effect, as (in essence) the computer
        is unsure WHICH bone the joint should be more stiffly bound to. This
        situation can result when, for instance, you have a very round, fat
        character.  In this case, the best idea is to either add bones which
        are 'closer' to the problem area, or simply correct it with weight
        painting afterward.  (This script is not meant to replace weight
        painting, but merely to give you a better place to start from!)
    """
    if not args:
        args = listForNone(cmds.ls(sl=1))
    
    fit = kwargs.pop('fit', False)
    stiffness = kwargs.pop('stiffness', 1.0)
    
    inputArgsMessage = "Select one root joint and meshes you wish to weight"
    meshes = []
    rootJoint = None
    for arg in args:
        if isATypeOf(arg, 'joint'):
            if rootJoint is None:
                rootJoint = arg
            else:
                api.MGlobal.displayError("multiple joints - " +
                                         inputArgsMessage)
                return False
        elif isATypeOf(arg, 'mesh'):
            meshes.append(arg)
        elif isATypeOf(arg, 'transform'):
            shapes = [x for x in getShapes(arg) if isATypeOf(x, 'mesh')]
            if len(shapes) == 0: 
                api.MGlobal.displayWarning(
                    "transform has no poly shape: %s" % arg)
            else:
                meshes.extend(shapes) 
        else:
            api.MGlobal.displayError(
                ("not a poly mesh, transform, or joint: %s - " % arg) +
                inputArgsMessage)
            return False
    if rootJoint is None:
        api.MGlobal.displayError("no root joint - "  + inputArgsMessage)
        return False
    if not meshes:
        api.MGlobal.displayError("no meshes - "  + inputArgsMessage)
        return False
    
    if 'undoable' in kwargs:
        undoable = kwargs['undoable']
    else:
        undoable = useUndoableMethod()
    
    for mesh in meshes:
        try:
            skinClusters = getSkinClusters(mesh)
            if skinClusters:
                skin = skinClusters[0]
            else:
                skin = cmds.skinCluster(mesh, rootJoint, rui=False)[0]
            
            tempArgs={}
            if KEEP_PINOC_INPUT_FILES:
                objFilePath = os.path.join(_PINOCCHIO_DIR, 'mayaToPinocModel.obj')
            else:
                objFileHandle, objFilePath = tempfile.mkstemp('.obj', **tempArgs)
                os.close(objFileHandle)
            try:
                if KEEP_PINOC_INPUT_FILES:
                    skelFilePath = os.path.join(_PINOCCHIO_DIR, 'mayaToPinocSkel.skel')
                else:
                    skelFileHandle, skelFilePath = tempfile.mkstemp('.skel',**tempArgs)
                    os.close(skelFileHandle)
                try:
                    skelFilePath, skelList = \
                        pinocchioSkeletonExport(rootJoint, skelFilePath)
                    objFilePath = pinocchioObjExport(mesh, objFilePath)
                    
                    runPinocchioBin(objFilePath, skelFilePath, fit=fit,
                                    stiffness=stiffness)
                    pinocchioWeightsImport(mesh, skin, skelList,
                                           weightFile=os.path.join(_PINOCCHIO_DIR,
                                                                   "attachment.out"))
                finally:
                    if not KEEP_PINOC_INPUT_FILES and os.path.isfile(skelFilePath):
                        os.remove(skelFilePath)
            finally:
                if not KEEP_PINOC_INPUT_FILES and os.path.isfile(objFilePath):
                    os.remove(objFilePath)
        except Exception, e:
            print("warning - encountered exception while weighting mesh %s:" %
                  mesh)
            if DEBUG:
                import traceback
                traceback.print_exc()
            else:
                print e
    return True

# This doesn't work - apparently demoui can't take animation data for arbitrary
# skeletons - it requires exactly 114 entries per line??? 
#def exportPinocchioAnimation(skelList, filePath,
#                             startTime=None, endTime=None):
#    if startTime is None:
#        startTime = playbackOptions(q=1,  min=1)
#    if endTime is None:
#        endTime = playbackOptions(q=1,  max=1)
#
#    timeIncrement = playbackOptions(q=1, by=1)
#    
#    fileObj = open(filePath, mode='w')
#    try:
#        currentTime(startTime)
#        while currentTime() <= endTime:
#            for joint, parent in skelList:
#                for coord in getTranslation(joint, space='world'): 
#                    fileObj.write('%f ' % coord)
#            fileObj.write('\n')
#            currentTime(currentTime() + timeIncrement)
#    finally:
#        fileObj.close()

def nodeIn(node, nodeList):
    for compNode in nodeList:
        if isSameObject(node, compNode):
            return True
    else:
        return False
    
def getNodeIndex(node, nodeList):
    for i, compNode in enumerate(nodeList):
        if isSameObject(node, compNode):
            return i
    else:
        return None

def isSameObject(node1, node2):
    return mel.eval('isSameObject("%s", "%s")' % (node1, node2))
#==============================================================================
# Pymel Replacements
#==============================================================================

def listForNone( res ):
    if res is None:
        return []
    return res

def getTranslation(transform, **kwargs):
    space = kwargs.pop('space', None)
    if space == 'world':
        kwargs['worldSpace'] = True
    return cmds.xform(transform, q=1, translation=1, **kwargs)

def getShapes( transform, **kwargs ):
    kwargs['shapes'] = True
    noIntermediate = kwargs.get('noIntermediate', kwargs.get('ni', None))
    if noIntermediate is None:
        kwargs['noIntermediate'] = True
    return getChildren(transform, **kwargs )         

def getShape( transform, **kwargs ):
    kwargs['shapes'] = True
    shapes = getShapes(transform, **kwargs )
    if len(shapes) > 0:
        return shapes[0]
    else:
        return None      

def getChildren(self, **kwargs):
    kwargs['children'] = True
    kwargs.pop('c',None)
    fullPath = kwargs.get('fullPath', kwargs.get('f', None))
    if fullPath is None:
        kwargs['fullPath'] = True
    return listForNone(cmds.listRelatives( self, **kwargs))

def getParent(transform, **kwargs):
    kwargs['parent'] = True
    kwargs.pop('p', None)
    fullPath = kwargs.get('fullPath', kwargs.get('f', None))
    if fullPath is None:
        kwargs['fullPath'] = True
    return cmds.listRelatives( transform, **kwargs)[0]

def addShape( origShape, **kwargs ):
    """
    origShape will be duplicated and added under the existing parent transform
        (instead of duplicating the parent transform)
    """
    kwargs['returnRootsOnly'] = True
    kwargs.pop('rr', None)
    
    for invalidArg in ('renameChildren', 'rc', 'instanceLeaf', 'ilf',
                       'parentOnly', 'po', 'smartTransform', 'st'):
        if kwargs.get(invalidArg, False) :
            raise ValueError("addShape: argument %r may not be used with 'addShape' argument" % invalidArg)
    name=kwargs.pop('name', kwargs.pop('n', None))
                
    if 'shape' not in cmds.nodeType(origShape, inherited=True):
        raise TypeError('addShape argument to be a shape (%r)'
                        % origShape)

    # This is somewhat complex, because if we have a transform with
    # multiple shapes underneath it,
    #   a) The transform and all shapes are always duplicated
    #   b) After duplication, there is no reliable way to distinguish
    #         which shape is the duplicate of the one we WANTED to
    #         duplicate (cmds.shapeCompare does not work on all types
    #         of shapes - ie, subdivs)
    
    # To get around this, we:
    # 1) duplicate the transform ONLY (result: dupeTransform1)
    # 2) instance the shape we want under the new transform
    #    (result: dupeTransform1|instancedShape)
    # 3) duplicate the new transform
    #    (result: dupeTransform2, dupeTransform2|duplicatedShape)
    # 4) delete the transform with the instance (delete dupeTransform1)
    # 5) place an instance of the duplicated shape under the original
    #    transform (result: originalTransform|duplicatedShape)
    # 6) delete the extra transform (delete dupeTransform2)
    # 7) rename the final shape (if requested)
    
    # 1) duplicate the transform ONLY (result: dupeTransform1)
    dupeTransform1 = cmds.duplicate(origShape, parentOnly=1)[0]

    # 2) instance the shape we want under the new transform
    #    (result: dupeTransform1|instancedShape)
    cmds.parent(origShape, dupeTransform1, shape=True, addObject=True,
                relative=True)
    
    # 3) duplicate the new transform
    #    (result: dupeTransform2, dupeTransform2|duplicatedShape)
    dupeTransform2 = cmds.duplicate(dupeTransform1, **kwargs)[0]

    # 4) delete the transform with the instance (delete dupeTransform1)
    cmds.delete(dupeTransform1)

    # 5) place an instance of the duplicated shape under the original
    #    transform (result: originalTransform|duplicatedShape)
    newShape = cmds.parent(getShape(dupeTransform2),
                           getParent(origShape),
                           shape=True, addObject=True,
                           relative=True)[0]

    # 6) delete the extra transform (delete dupeTransform2)
    cmds.delete(dupeTransform2)
    
    # 7) rename the final shape (if requested)
    if name is not None:
        newShape = cmds.rename(newShape, name)
    
    cmds.select(newShape, r=1)
    return newShape

def influenceObjects(skinCluster):
    mfnSkin = apiAnim.MFnSkinCluster(toMObject(skinCluster))
    dagPaths = api.MDagPathArray()
    mfnSkin.influenceObjects(dagPaths)
    influences = []
    for i in xrange(dagPaths.length()):
        influences.append(dagPaths[i].fullPathName())
    return influences

def isValidMObject (obj):
    if isinstance(obj, api.MObject) :
        return not obj.isNull()
    else :
        return False

def toMObject (nodeName):
    """ Get the API MObject given the name of an existing node """ 
    sel = api.MSelectionList()
    obj = api.MObject()
    result = None
    try :
        sel.add( nodeName )
        sel.getDependNode( 0, obj )
        if isValidMObject(obj) :
            result = obj 
    except :
        pass
    return result

def toMDagPath (nodeName):
    """ Get an API MDagPAth to the node, given the name of an existing dag node """ 
    obj = toMObject (nodeName)
    if obj :
        dagFn = api.MFnDagNode (obj)
        dagPath = api.MDagPath()
        dagFn.getPath ( dagPath )
        return dagPath

def loadObjPlugin():
    if not cmds.pluginInfo('objExport', q=1, loaded=True ):
        cmds.loadPlugin('objExport')

#==============================================================================
# PM Scripts Replacements
#==============================================================================

def isATypeOf(node, type):
    """Returns true if node is of the given type, or inherits from it."""
    if isinstance(node, basestring) and cmds.objExists(node):
        return type in cmds.nodeType(node, inherited=True)
    else:
        return False
    
def getSkinClusters(mesh):
    """
    Returns a list of skinClusters attached the given mesh.
    """
    return [x for x in listForNone(cmds.listHistory(mesh))
            if isATypeOf(x, 'skinCluster')]

def browseForFile(actionName="Select", fileCommand=None, fileType=None,
                  **kwargs):
    """
    Open a window to browse for a file.
    
    Will use fileBrowserDialog if on windows, fileDialog if not.
    """
    if fileCommand is None:
        def fileCommand(*args, **kwargs): pass
        
    if os.name == 'nt':
        exportFileName = cmds.fileBrowserDialog(fileCommand=fileCommand,
                                                actionName=actionName,
                                                fileType=fileType, **kwargs)
    else:
        exportFileName = cmds.fileDialog(title=actionName)
        fileCommand(exportFileName, fileType)
    return exportFileName   
