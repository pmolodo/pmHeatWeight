import os
import sys
import zipfile
import shutil
import re

#def makeHtmlContents(body, title="Title"):
##    bodySplit = body.replace('\r\n', '\n').replace('\r', '\n').split('\n')
##    bodySplit = [('<p>' + x + '</p>\r\n') for x in bodySplit]
##    body = ''.join(bodySplit)
#    
#    return '''
#<html>
#<head>
#<title> %(title)s </title>
#</head>
#<body>
#%(body)s
#</body>
#</html>
#''' % locals()

#def createHtmlFile(htmlPath, body, title):
#    htmlFile = open(htmlPath, "w")
#    htmlFile.write(makeHtmlContents(body, title=title))
#    htmlFile.close
#    return htmlPath

def createReadmeFile(readmePath, body):
    readmeFile = open(readmePath, "wb")
    # Convert to windows newlines as other systems usually do a better
    # job of reading windows newlines, while windows does a crappy job of
    # reading other system's newlines...
    readmeFile.write(convertToWindowsNewlines(body))
    readmeFile.close()
    return readmePath
    
def convertToWindowsNewlines(body):
    return body.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')
    
def makeDirectoryZip(zipFilePath, contentsDir):
    zipFile = zipfile.ZipFile(zipFilePath, "w", zipfile.ZIP_DEFLATED)
    for relPath in pathRelativeFiles(contentsDir, r"~$|\.pyc$"):
        print relPath
        zipFile.write(os.path.join(contentsDir, relPath), relPath)

def pathRelativeFiles(thisDir, exclude=None):
    if isinstance(exclude, basestring):
        exclude = re.compile(exclude)
        
    files = []
    for dirEntry in os.listdir(thisDir):
        dirEntryPath = os.path.join(thisDir, dirEntry)
        if os.path.isfile(dirEntryPath):
            files.append(dirEntry)
        elif os.path.isdir(dirEntryPath):
            for subFile in pathRelativeFiles(dirEntryPath):
                files.append(os.path.join(dirEntry, subFile))
    if exclude is not None:
        files = [x for x in files if not exclude.search(x)]
    return files

def makeZip():
    ADDMAYAPATHS = True
    startupFilePath = os.environ.get('PYTHONSTARTUP')
    if startupFilePath and os.path.isfile(startupFilePath):
        execfile(startupFilePath)
    
    projectDir =  os.path.dirname(__file__)
    sourceDir = os.path.join(projectDir, "src")
    sourceFile = os.path.join(sourceDir, 'PM_heatWeight.py')
    packagesDir = os.path.join(projectDir, "packages")
    contentsDir = os.path.join(packagesDir, "contents")
    scriptsDir = os.path.join(contentsDir, "scripts")
    pinocchioProjectDir = r"C:\Dev\Projects\Pinocchio"
    pinocchioBinariesDir = os.path.join(pinocchioProjectDir, "release")
    pinnocchioBinaries = ["AttachWeights.exe"]
    
    # import source file to get the version
    pmhLocals = {}
    pmhGlobals = {}
    try:
        execfile(sourceFile, pmhGlobals, pmhLocals)
    except ImportError:
        # We may get an import error when importing maya.*
        pass
    
    scriptFileFromPath = sourceFile
    scriptFileDir = os.path.dirname(scriptFileFromPath)
    sourceFileName = os.path.basename(scriptFileFromPath)
    scriptFileToPath = os.path.join(scriptsDir, sourceFileName)
    zipFilePath = os.path.join(packagesDir,
                        ("PM_heatWeight_v%s.zip" % pmhLocals['version']))

    
    readmeFileName = "README_PM_heatWeight.txt"
    readmeFilePath = os.path.join(contentsDir, readmeFileName)
    
    createReadmeFile(readmeFilePath, pmhLocals['__doc__'])
    shutil.copyfile(scriptFileFromPath, scriptFileToPath)
    for bin in pinnocchioBinaries:
        binSrcPth = os.path.join(pinocchioBinariesDir, bin)
        if os.path.isfile(binSrcPth):
            shutil.copyfile(binSrcPth, os.path.join(scriptsDir, bin))
            shutil.copyfile(binSrcPth, os.path.join(scriptFileDir, bin))
    
    makeDirectoryZip(zipFilePath, contentsDir)

if __name__ == '__main__':
    makeZip()