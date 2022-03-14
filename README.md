# Kirelease
Kirelease is a python script that allows you to quickly create a new release for your Kicad project.

# Usage

Position yourself in the root of your Kicad project, then run:

 `kirelease <schRootFile> <pcbFile> <projectName>`

 - `schRootFile`: name of the root `.kicad_sch` in the eeschema hirearchy

 - `pcbFile`: name of the `.kicad_pcb` file

 - `projectName`: name for the releases

Note that the order of the arguments is important.

Run `kirelease help` to get this infor in the terminal.

# How it works

Kirelease looks for a folder called `releases`, if not present it will be created. Inside of it a new folder named `<projectName>_release_#` will be created for each new release.

`projectName` is taken from other releases, on the first release this name must be provided as an argument.

Each realease consists of four files:
- schematic.pdf
- gerbers.zip (drills file and silkscreen included)
- bom.csv
- model.step

To remove the silkscreen use the `--no-silk` argument.

# Important notes

At the current moment, Kicad doesn't have a Python API for eeschema like it has for pcbnew, therefore, the plotting of the schematic in .pdf is done by opening in background an instance of eeschema and simulating keypresses on its UI with `xdotools` to input the output file name and navigating towards the Plot button. This requires all the different export options in eeschema to be already set before calling `kirelease`.

This also requires to change the code everytime the UI in eeschema changes.

Once the eeschema Python API will be ready, which currently planned for Kicad V7, this part will be rewritten to use it like the gerber export is doing already.

# Credits

This script has been assembled by gathering code from several public repos and putting it together in what I consider to be easily readable and extendable code.
