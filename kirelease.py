#!/usr/bin/env python

from asyncio import subprocess
from ctypes import ArgumentError
from genericpath import isdir
from platform import release
import sys
from os import listdir, getcwd, mkdir, path, system
from os.path import isdir, join
import time
from xvfbwrapper import Xvfb

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


def export_gerbers():
    print()

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
    # export_bom()
