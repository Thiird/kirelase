#!/usr/bin/env python

from os import listdir, getcwd, mkdir, path, rename
import sys
import time
import csv
import shutil
import zipfile
import tempfile

import kicad_netlist_reader
import pcbnew

from utils import xdotool, PopenContext, waitForWindow

KICAD_SCH_EXTENSION = '.kicad_sch'
KICAD_PCB_EXTENSION = '.kicad_pcb'
RELEASE_DIRECTORY_NAME = 'release'
pcb_file = ''


def getProjectName(outputDir):
    # expected format: 'projectName_release_0', 'projectName_release_1', ...
    releaseFiles = listdir(outputDir)
    if len(releaseFiles) != 0:
        temp = releaseFiles[0].split('_')
        if len(temp) != 0 and temp[0] != '':
            print("Project name is '" +
                  temp[0] + "'. Got it from previous releases.")
            return temp[0]

    if len(sys.argv) >= 4:
        return sys.argv[3]
    else:
        print("Missing <projectName>, must be specified at first release.\n"
              "Use kirelease help for usage.")
        exit(0)


def getReleaseNumber(outputDir):
    nextRelease = -1

    # expected format: 'projectName_release_0', 'projectName_release_1', ...
    for f in listdir(outputDir):
        temp = f.split('_')
        temp = int(temp[len(temp) - 1])
        if temp > nextRelease:
            nextRelease = temp

    if nextRelease == -1:
        return 0
    else:
        return nextRelease + 1


def checkForOutputFolder(outputDir):
    # check for release folder
    if not path.isdir(outputDir):
        mkdir(RELEASE_DIRECTORY_NAME)
        print("'release' directory created")


def export_step(pcbFile, outputDir):
    with PopenContext(['kicad2step', pcbFile + '.kicad_pcb', '-o' + outputDir + '/model']) as kicad2step:
        time.sleep(5)
        kicad2step.terminate()

    print("Exported model.step")


def export_gerbers(pcbFile, outputDir, withSilkScreen):
    board = pcbnew.LoadBoard(pcbFile + KICAD_PCB_EXTENSION)

    withPaste = True
    with4layers = board.GetDesignSettings().GetCopperLayerCount() == 4

    # configure plotter
    pctl = pcbnew.PLOT_CONTROLLER(board)
    popt = pctl.GetPlotOptions()

    # set plot options
    popt.SetPlotFrameRef(False)
    # popt.SetLineWidth(pcbnew.FromMM(0.05))
    popt.SetAutoScale(False)
    popt.SetScale(1)

    popt.SetMirror(False)
    popt.SetUseGerberAttributes(False)
    popt.SetUseGerberProtelExtensions(True)
    popt.SetExcludeEdgeLayer(True)
    popt.SetUseAuxOrigin(False)
    popt.SetDrillMarksType(pcbnew.PCB_PLOT_PARAMS.NO_DRILL_SHAPE)
    popt.SetSkipPlotNPTH_Pads(True)

    # set plot layers
    tempdir = tempfile.mkdtemp()
    popt.SetOutputDirectory(tempdir)

    plotPlan = [
        ("F_Cu", pcbnew.F_Cu, "Top layer"),
        ("B_Cu", pcbnew.B_Cu, "Bottom layer"),
        ("F_Mask", pcbnew.F_Mask, "Mask top"),
        ("B_Mask", pcbnew.B_Mask, "Mask bottom"),
        ("Edge_Cuts", pcbnew.Edge_Cuts, "Edges"),
    ]
    if with4layers:
        plotPlan += [
            ("In1_Cu", pcbnew.In1_Cu, "Top internal layer"),
            ("In2_Cu", pcbnew.In2_Cu, "Bottom internal layer"),
        ]
    if withSilkScreen:
        plotPlan += [
            ("F_Silk", pcbnew.F_SilkS, "Silk top"),
            ("B_Silk", pcbnew.B_SilkS, "Silk top"),
        ]
    if withPaste:
        plotPlan += [
            ("F_Paste", pcbnew.F_Paste, "Paste top"),
            ("B_Paste", pcbnew.B_Paste, "Paste Bottom"),
        ]

    for layerInfo in plotPlan:
        pctl.SetLayer(layerInfo[1])
        pctl.OpenPlotfile(
            layerInfo[0], pcbnew.PLOT_FORMAT_GERBER, layerInfo[2])
        pctl.PlotLayer()

    # plot drill files
    drlWriter = pcbnew.EXCELLON_WRITER(board)
    drlWriter.SetMapFileFormat(pcbnew.PLOT_FORMAT_GERBER)
    drlWriter.SetOptions(aMirror=False, aMinimalHeader=False,
                         aOffset=pcbnew.wxPoint(0, 0), aMerge_PTH_NPTH=False)
    drlWriter.SetFormat(True, pcbnew.EXCELLON_WRITER.DECIMAL_FORMAT, 3, 3)
    drlWriter.CreateDrillandMapFilesSet(pctl.GetPlotDirName(), True, False)

    pctl.ClosePlot()

    # zip files
    files = listdir(tempdir)
    with zipfile.ZipFile(path.join(tempdir, "zip"), 'w', zipfile.ZIP_DEFLATED) as myzip:
        for file in files:
            myzip.write(path.join(tempdir, file), file)

    shutil.move(path.join(tempdir, "zip"), outputDir + '/gerbers.zip')

    # remove tempdir
    shutil.rmtree(tempdir)

    print("Exported gerbers.zip")


def export_bom(annotationFile, outputDir, projectName):
    # Generate an instance of a generic netlist
    net = kicad_netlist_reader.netlist(annotationFile)

    # Open a file to write to, if the file cannot be opened output to stdout
    try:
        f = open(outputDir + '/bom.csv', 'w')
    except IOError:
        print("Can't open output file: " + outputDir + '/bom.csv')
        exit(1)

    # Create a new csv writer object to use as the output formatter
    out = csv.writer(f, lineterminator='\n', delimiter=';',
                     quotechar='\"', quoting=csv.QUOTE_ALL)
    out.writerow(['Reference', 'Value', 'Rating', 'Footprint',
                 'Purchase URL', 'Quantity', 'Distributor Code', 'Vendor'])

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

    print("Exported bom.csv")


def export_schematic(mainSchFile, outputDir):
    with PopenContext(['eeschema', mainSchFile]) as eeschema:

        # search for eeschema window and focus it
        waitForWindow('Schematic Editor')

        # open plotting window
        xdotool(['key', 'shift+ctrl+p'])

        # search for plotting window and focus it
        waitForWindow('Plot Schematic Options')

        # input output directory
        xdotool(['type', outputDir + '/'])

        # move to plot button by tabbing and press enter
        for x in range(1, 19):
            xdotool(['key', 'Tab'])
        xdotool(['key', 'enter'])

        # wait for export to take place, 2 seconds should suffice
        time.sleep(3)
        eeschema.terminate()

    # rename the just exported schematic
    for f in listdir(outputDir):
        if '.pdf' in f:
            rename(outputDir + '/' + f, outputDir + '/' + 'schematic.pdf')
            break

    print("Exported schematic.pdf")


if __name__ == '__main__':

    schFile = ''
    pcbFile = ''
    projectName = ''
    cwd = getcwd()
    outputDir = cwd + '/' + RELEASE_DIRECTORY_NAME

    if (len(sys.argv) == 1):
        print("Missing arguemnts, use 'kirelease help' for a guide")
        exit(0)

    if (sys.argv[1] == 'help'):
        print("From root of the KiCad project, use:\n\n"
              "kirelease <schFile> <pcbFile> <projectName>\n\n"
              "<schFile> is the root .kicad_sch file in the schematic hirearchy\n"
              "<pcbFile> is the .kicad_pcb file\n"
              "<projectName> is the name for the output files, only needed for first release\n"
              "--no-silk to not plot silkscreen layers\n\n"
              "If a 'release' folder is not present, one will be created.")
        exit(0)

    schFile = cwd + '/' + sys.argv[1]
    pcbFile = cwd + '/' + sys.argv[2]

    checkForOutputFolder(outputDir)
    projectName = getProjectName(outputDir)
    releaseNumber = getReleaseNumber(outputDir)

    # update var with projectName and releaseNumber
    outputDir = outputDir + '/' + projectName + \
        '_release_' + str(releaseNumber)

    print("Exporting '" + projectName +
          '_release_' + str(releaseNumber) + "' ...")

    export_schematic(schFile, outputDir)
    export_step(pcbFile, outputDir)

    schAnnotated = False
    for f in listdir(cwd):
        if '.xml' in f:
            schAnnotated = True
            break
    if schAnnotated:
        export_bom(schFile + '.xml', outputDir, projectName)
    else:
        print("Generating BOM requires a fully annotated schematic. Missing .xml file.")
        exit(1)

    export_gerbers(pcbFile, outputDir,
                   False if '--no-silk' in sys.argv else True)

    print("Finished exporting '" + projectName +
          '_release_' + str(releaseNumber) + "'")
