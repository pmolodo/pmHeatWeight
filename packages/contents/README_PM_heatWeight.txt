
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

version 0.6.5

New releases will be posted to creativecrash.com (formerly highend3d.com): go to
http://www.creativecrash.com/maya/downloads/scripts-plugins/character/c/pm-heatweight
...or search for 'PM_heatWeight' in the maya downloads if that link is outdated);
if you wish to contact me regarding this script, either leave a message on the
forum there, or email me at heatWeight DOT calin79, domain neverbox DOT com.
(If you're not a spam bot, you should hopefully be able to figure out the
correct formatting of that email address...) 

Changelog:

v0.6.5 - New parameters:
    tempOutputDir=None
        Specify a directory where temporary files used by the Pinocchio binary
        are stored
    tempDelete=True
        Whether or not to delete the temporary files used by the Pinocchio binary
        when finished
    tempOverwrite=True
        Whether or not to overwrite any existing temporary files
    Also, should now work with multi-threading (each thread will write temp files to it's
        own temp directory), and when exe/script file is in a location that you don't
        have write access to
v0.6.4 - linux + Mac OSX binaries now included!
v0.6.3 - updated help file (no longer need a .dll since 0.6.2)
v0.6.2 - added an optional 'stiffness' parameter 
v0.6.1 - maya 8.5 / 2008 support
v0.6   - first public release! 
v0.5.2 - changed input format - now can select multiple meshes
v0.5.1 - automatically loads obj plugin, closes open poly borders
v0.5   - initial version
