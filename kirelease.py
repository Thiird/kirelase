#!/usr/bin/env python

from asyncio import subprocess
from ctypes import ArgumentError
from genericpath import isdir
from platform import release
import sys
from os import listdir, getcwd, mkdir, path, rename
from os.path import isdir, join
import time
from xvfbwrapper import Xvfb
# Import the KiCad python helper module and the csv formatter
import kicad_netlist_reader
import csv    
import shutil
import zipfile
import tempfile
import pcbnew


from utils import (
    PopenContext,
    xdotool
)

RELEASE_DIRECTORY_NAME = 'release'
pcb_file = ''

def getReleaseNumber(outDir):
    nextRelease = -1

    for f in listdir(outDir): # expected format is 'project_rev_0', 'project_rev_1', ...
        temp = f.split('_')
        temp = int(temp[len(temp) - 1])
        if temp > nextRelease:
            nextRelease = temp

    if nextRelease == -1:
        return 0
    else:
        return nextRelease + 1


def export_step(cwd, outputDir):
    pcbFile = ''
    for f in listdir(cwd):
        if '.kicad_pcb' in f:
            pcbFile = f.split('/')
            pcbFile = pcbFile[len(pcbFile) - 1]
            break 
    with PopenContext(['kicad2step', pcbFile , '-o' + outputDir + '/model']) as kicad2step:
        time.sleep(2)
        kicad2step.terminate()
    print("Exported 3D .step model in: " + outputDir + '/model')


def export_gerbers(pcbFile, outputDir):
    #!/Applications/Kicad/kicad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python

    board = pcbnew.LoadBoard(pcbFile)

    with_silkscreen = True # Silkscreen makes the boards slightly thicker
    with_paste = True
    with_4layers = board.GetDesignSettings().GetCopperLayerCount() == 4

    # Configure plotter
    pctl = pcbnew.PLOT_CONTROLLER(board)
    popt = pctl.GetPlotOptions()

    # Set some important plot options
    popt.SetPlotFrameRef(False)
    popt.SetLineWidth(pcbnew.FromMM(0.05))
    popt.SetAutoScale(False)
    popt.SetScale(1)

    popt.SetMirror(False)
    popt.SetUseGerberAttributes(False)
    popt.SetUseGerberProtelExtensions(True)
    popt.SetExcludeEdgeLayer(True)
    popt.SetUseAuxOrigin(False)
    popt.SetDrillMarksType(pcbnew.PCB_PLOT_PARAMS.NO_DRILL_SHAPE)
    popt.SetSkipPlotNPTH_Pads(True)

    # Render Plot Files
    tempdir = tempfile.mkdtemp()
    popt.SetOutputDirectory(tempdir)

    plot_plan = [
        ( "F_Cu", pcbnew.F_Cu, "Top layer" ),
        ( "B_Cu", pcbnew.B_Cu, "Bottom layer" ),
        ( "F_Mask", pcbnew.F_Mask, "Mask top" ),
        ( "B_Mask", pcbnew.B_Mask, "Mask bottom" ),
        ( "Edge_Cuts", pcbnew.Edge_Cuts, "Edges" ),
    ]
    if with_4layers:
        plot_plan += [
            ( "In1_Cu", pcbnew.In1_Cu, "Top internal layer" ),
            ( "In2_Cu", pcbnew.In2_Cu, "Bottom internal layer" ),
        ]
    if with_silkscreen:
        plot_plan += [
            ( "F_Silk", pcbnew.F_SilkS, "Silk top" ),
            ( "B_Silk", pcbnew.B_SilkS, "Silk top" ),
        ]
    if with_paste:
        plot_plan += [
            ( "F_Paste", pcbnew.F_Paste, "Paste top" ),
            ( "B_Paste", pcbnew.B_Paste, "Paste Bottom" ),
        ]

    for layer_info in plot_plan:
        pctl.SetLayer(layer_info[1])
        pctl.OpenPlotfile(layer_info[0], pcbnew.PLOT_FORMAT_GERBER, layer_info[2])
        pctl.PlotLayer()

    # Render Drill Files
    drlwriter = pcbnew.EXCELLON_WRITER(board)
    drlwriter.SetMapFileFormat(pcbnew.PLOT_FORMAT_GERBER)
    drlwriter.SetOptions(aMirror=False, aMinimalHeader=False,
                        aOffset=pcbnew.wxPoint(0, 0), aMerge_PTH_NPTH=False)
    drlwriter.SetFormat(True, pcbnew.EXCELLON_WRITER.DECIMAL_FORMAT, 3, 3)
    drlwriter.CreateDrillandMapFilesSet( pctl.GetPlotDirName(), True, False )

    pctl.ClosePlot()

    # Archive files
    files = listdir(tempdir)
    with zipfile.ZipFile(path.join(tempdir, "zip"), 'w', zipfile.ZIP_DEFLATED) as myzip:
        for file in files:
            myzip.write(path.join(tempdir, file), file)

    rename(path.join(tempdir, "zip"), outputDir)

    # Remove tempdir
    shutil.rmtree(tempdir)

def export_bom(schFile, outputDir):
    # Generate an instance of a generic netlist
    net = kicad_netlist_reader.netlist(schFile)

    # Open a file to write to, if the file cannot be opened output to stdout
    try:
        f = open(outputDir, 'w')
    except IOError:
        e = "Can't open output file: " + outputDir
        print(__file__, ":", e, sys.stderr)
        f = sys.stdout

    # Create a new csv writer object to use as the output formatter
    out = csv.writer(f, lineterminator='\n', delimiter=';', quotechar='\"', quoting=csv.QUOTE_ALL)
    out.writerow(['Reference', 'Value', 'Rating', 'Footprint', 'Purchase URL', 'Quantity', 'Distributor Code', 'Vendor'])

    # Get all of the components in groups of matching parts + values
    grouped = net.groupComponents()

    # Output all of the component information
    for group in grouped:
        refs = ""

        # Add the reference of every component in the group and keep a reference
        # to the component so that the other data can be filled in once per group
        for component in group:
            refs += '-'
            refs += component.getRef()
            c = component
            
        refs = refs[1:]
        
        # Fill in the component groups common data
        out.writerow([refs,
                    c.getValue(),
                    c.getField("Rating"), 
                    c.getFootprint(),
                    c.getField("Purchase URL"),                  
                    len(group),
                    c.getField("Distributor Code"),
                    c.getField("Distributor")])

def export_schematic(mainSchFile, outputDir):
    #with Xvfb(width=1280, height=720, colordepth=24):
    with PopenContext(['eeschema', mainSchFile]) as eeschema:
        time.sleep(0.3)
        # search for eeschema window and focus it
        xdotool(['search', '--name', 'Schematic Editor'])
        time.sleep(0.3)

        # open plotting window
        xdotool(['key' ,'shift+ctrl+p'])
        time.sleep(0.3)

        # search for plotting window and focus it
        xdotool(['search', '--name', 'Plot Schematic Options'])
        time.sleep(0.3)

        # input output directory
        xdotool(['type' , outputDir + '/schematic.pdf'])
        time.sleep(0.3)

        # move to plot button by tabbing and press enter
        for x in range(1,19):   
            xdotool(['key','Tab'])
        xdotool(['key','enter'])

        # wait for export to take place, 2 seconds should suffice
        time.sleep(2)
        eeschema.terminate()
        print("Exported schematic .pdf in: " + outputDir + '/schematic.pdf')

def export_bom():
    print()
    
if __name__ == '__main__':

    if (len(sys.argv) == 1):
        print("Missing arguemnts, use 'kirelease help' for a guide")
        exit(0)
    
    if (sys.argv[1] == 'help'):
        print("From the main directory of your KiCad project, use:\n\n"\
            "Kirelease <root>.sch <project_name>\n\n"
            "where main.sch is the root sheet in the schematic hirearchy\n"\
            "If a 'release' folder is not present, one will be created.\n"\
            "If <project_name> is not specified, the name of the root.sch file will be used as the project name")
        exit(0)

    cwd = getcwd()
    outputDir = cwd + '/' + RELEASE_DIRECTORY_NAME

    # check for release folder
    if not path.isdir(outputDir):
        print("No 'realease' directory available, create one: (y/n)")
        choice = input().lower()
        if choice in ['y','n']:
            if choice == 'n':
                print("ok nevermind then!")
                exit(0)
            else:
                print("'release' directory created")
                mkdir(RELEASE_DIRECTORY_NAME)

    fileToOpen = sys.argv[1].split("/")
    fileToOpen = fileToOpen[len(fileToOpen) - 1].split(".")[0]

    # if not given as argument, take project name from root .sch file
    if (len(sys.argv) == 3):
        schPath = sys.argv[2]

    releaseNumber = getReleaseNumber(outputDir)     
    outputDir = outputDir + '/' + fileToOpen + '_' + str(releaseNumber)

    if not path.isdir(outputDir):
        mkdir(outputDir)

    export_schematic(schPath, outputDir)
    export_step(cwd, outputDir)
    # export_gerbers()
    export_bom(fileToOpen, outputDir)
