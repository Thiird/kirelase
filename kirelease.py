#!/usr/bin/env python

from asyncio import subprocess
from ctypes import ArgumentError
from genericpath import isdir
import sys
from os import listdir, getcwd, mkdir, path, system
from os.path import isfile, join
import time
from xvfbwrapper import Xvfb

from utils import (
    PopenContext,
    xdotool
)

RELEASE_DIRECTORY_NAME = 'release'

def getReleaseNumber(outputDir):
    releaseNumber = 0

    onlyfiles = [f for f in listdir(outputDir) if isfile(join(outputDir, f))]

    print(onlyfiles)

    return releaseNumber

def export_step():
    a = system('kicad2step')

    print(a)

def export_gerbers():
    print()

def export_schematic(mainSchFile, outputDir):
    with Xvfb(width=800, height=600, colordepth=24):
        with PopenContext(['eeschema', mainSchFile]) as eeschema:
            time.sleep(2)
            # search for eeschema window and focus it
            xdotool(['search', '--name', 'Schematic Editor'])

            # open plotting window
            xdotool(['key' ,'shift+ctrl+p'])
            time.sleep(1)

            # search for plotting window and focus it
            xdotool(['search', '--name', 'Plot Schematic Options'])

            # input output directory
            xdotool(['key' , outputDir])

            # move to plot button by tabbing and press enter
            cmd = ['key']
            for x in range(1,19):
                xdotool(['key','Tab'])
            xdotool(['key','enter'])

            # wait for export to take place, 2 seconds should suffice
            time.sleep(2)
            eeschema.terminate()

def export_bom():
    print()
    
if __name__ == '__main__':

    if (len(sys.argv) == 1):
        print("Missing arguemnts, use 'kirelease help' for a guide")
        exit(0)
    
    if (sys.argv[1] == 'help'):
        print("From the main directory of your KiCad project, use:\n\n"\
            "Kirelease main.sch\n\n"
            "where main.sch is the root sheet in the schematic hirearchy\n"\
            "If a 'release' folder is not present, one will be created.")
        exit(0)

    cwd = getcwd()
    outputDir = cwd + '/' + RELEASE_DIRECTORY_NAME

    # check for release folder
    if not path.isdir(outputDir):
        mkdir(RELEASE_DIRECTORY_NAME)
    
    projectName = sys.argv[1].split("/")
    projectName = projectName[len(projectName) - 1].split(".")[0]

    releaseNumber = getReleaseNumber(outputDir)        

    if not path.isdir(outputDir):
        mkdir(outputDir)

    export_schematic(outputDir)
    export_step()
    export_gerbers()
    export_bom()
