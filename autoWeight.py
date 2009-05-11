import subprocess
import tempfile
import os
import os.path

import maya.cmds as cmds
from pymel import *

import PMP.pyUtils
import PMP.maya.fileUtils
import PMP.maya.rigging

DEBUG = False
KEEP_PINOC_INPUT_FILES = True

_PINOCCHIO_DIR = os.path.join(os.path.dirname(__file__), 'Pinocchio')
_PINOCCHIO_BIN = os.path.join(_PINOCCHIO_DIR, 'AttachWeights.exe')

class DEFAULT_SKELETONS(object): pass
class HUMAN_SKELETON(DEFAULT_SKELETONS): pass

def pinocchioSkeletonExport(skeletonRoot, skelFile=None):
    """
    Exports the skeleton to a file format that pinocchio can understand.

    Returns (skelFile, skelList), where skelList is the list returned
    by  makePinocchioSkeletonList.
    """
    skeletonRoot = PyNode(skeletonRoot)
    if skelFile is None:
        skelFile = PMP.maya.fileUtils.browseForFile(m=1, actionName='Export')
    skelList = makePinocchioSkeletonList(skeletonRoot)
    fileObj = open(skelFile, mode="w")
    try:
        for jointIndex, (joint, parentIndex) in enumerate(skelList):
            jointCoords = joint.getTranslation(space='world')
            fileObj.write("%d %.5f %.5f %.5f %d\r\n" % (jointIndex,
                                                        jointCoords.x,
                                                        jointCoords.y,
                                                        jointCoords.z,
                                                        parentIndex))
    finally:
        fileObj.close()
    return (skelFile, skelList)

def pinocchioObjExport(mesh, objFilePath):
    mesh = PyNode(mesh)
    savedSel = selected()
    try:
        if (not isinstance(mesh, nodetypes.GeometryShape) and
                hasattr(mesh, 'getShape')):
            mesh = mesh.getShape()
        if not isinstance(mesh, nodetypes.GeometryShape):
            raise TypeError('cannot find a geometry shape for %s' % mesh)
            
        meshDup = duplicate(mesh, addShape=True)[0]
        polyTriangulate(meshDup, ch=0)
        select(meshDup, r=1)
        cmds.file(objFilePath,
                op="groups=0;ptgroups=0;materials=0;smoothing=0;normals=0",
                typ="OBJexport", es=True, f=1)
        delete(meshDup)
    finally:
        select(savedSel)
    return objFilePath


def makePinocchioSkeletonList(rootJoint):
    """
    Given a joint, returns info used for the pinocchio skeleton export.
    
    Each item in the list is a tuple ([x,y,z], parentIndex), where
    parentIndex is an index into the list.
    """
    return _makePinocchioSkeletonList([], rootJoint, -1)

def _makePinocchioSkeletonList(skelList, newJoint, newJointParent):
    newJoint = PyNode(newJoint)
    
    newIndex = len(skelList)
    skelList.append((newJoint, newJointParent))
    
    jointChildren = listRelatives(newJoint, type="joint",
                                  children=True,
                                  noIntermediate=True)
    for joint in jointChildren:
        _makePinocchioSkeletonList(skelList, joint, newIndex)
    return skelList

def pinocchioWeightsImport(mesh, skin, skelList, weightFile=None):
    mesh = PyNode(mesh)
    skin = PyNode(skin)
    
    #Ensure that all influences in the skelList are influences for the skin
    allInfluences = skin.influenceObjects()
    pinocInfluences = [joint for joint, parent in skelList]
    for joint in pinocInfluences:
        if joint not in allInfluences:
            skin.addInfluence(joint)
    
    if weightFile is None:
        weightFile = PMP.maya.fileUtils.browseForFile(m=0, actionName='Import')
    vertBoneWeights = readPinocchioWeights(weightFile)
    numVertices = len(vertBoneWeights)
    numBones = len(vertBoneWeights[0])
    numWeights = numVertices * numBones
    numJoints = len(skelList)
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
    skinPercent(skin, mesh, pruneWeights=100, normalize=False)

    if confirmNonUndoableMethod():
        apiWeights = api.MDoubleArray(numWeights, 0)
        for vertIndex, jointWeights in enumerate(vertJointWeights):
            for jointIndex, jointValue in enumerate(jointWeights):
                apiWeights.set(jointValue, vertIndex * numBones + jointIndex)
        apiJointIndices = api.MIntArray(numBones, 0)
        for apiIndex, joint in enumerate(skin.influenceObjects()):
            apiJointIndices.set(apiIndex, pinocInfluences.index(joint))
        apiComponents = api.MFnSingleIndexedComponent().create(api.MFn.kMeshVertComponent)
        apiVertices = api.MIntArray(mesh.numVertices(), 0)
        for i in xrange(mesh.numVertices()):
            apiVertices.set(i, i)
        api.MFnSingleIndexedComponent(apiComponents).addElements(apiVertices) 
        mfnSkin = skin.__apimfn__()
        oldWeights = api.MDoubleArray()
        undoState = undoInfo(q=1, state=1)
        undoInfo(state=False)
        try:
            mfnSkin.setWeights(mesh.__apimdagpath__(),
                               apiComponents,
                               apiJointIndices,
                               apiWeights,
                               False,
                               oldWeights)
        finally:
            cmds.flushUndo()
            undoInfo(state=undoState)
    else:
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

            skinPercent(skin, mesh.vtx[vertIndex], normalize=False,
                        transformValue=jointValues.items())
        cmds.progressWindow(endProgress=True)    

def confirmNonUndoableMethod():
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

def runPinocchioBin(meshFile, weightFile, fit=False):
    # Change current directory to ensure we know where attachment.out will be
    os.chdir(_PINOCCHIO_DIR)
    exeAndArgs = [_PINOCCHIO_BIN, meshFile, '-skel', weightFile]
    if fit:
        exeAndArgs.append('-fit')
    subprocess.check_call(exeAndArgs)

def autoWeight(rootJoint=None, mesh=None, skin=None, fit=False):
    if rootJoint is None or mesh is None:
        sel = selected()
        if rootJoint is None:
            rootJoint = sel.pop(0)
        if mesh is None:
            mesh = sel[0]
    
    if skin is None:
        skinClusters = PMP.maya.rigging.getSkinClusters(mesh)
        if skinClusters:
            skin = skinClusters[0]
        else:
            skin = skinCluster(mesh, rootJoint, rui=False)[0]
    
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
            
            runPinocchioBin(objFilePath, skelFilePath, fit=fit)
            pinocchioWeightsImport(mesh, skin, skelList,
                                   weightFile=os.path.join(_PINOCCHIO_DIR,
                                                           "attachment.out"))
        finally:
            if not KEEP_PINOC_INPUT_FILES and os.path.isfile(skelFilePath):
                os.remove(skelFilePath)
    finally:
        if not KEEP_PINOC_INPUT_FILES and os.path.isfile(objFilePath):
            os.remove(objFilePath)

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
#                for coord in joint.getTranslation(space='world'): 
#                    fileObj.write('%f ' % coord)
#            fileObj.write('\n')
#            currentTime(currentTime() + timeIncrement)
#    finally:
#        fileObj.close()