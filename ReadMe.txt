Hyperlist
Authors: Yinming Shao, Siyuan Qiu

Updates:
20250510: add notes in #6 about PyQt5 installations
20250511: add package pyvisa-py to the requirements.txt for mercuryITC
20250515: change pyvisa-py from 1.11.3 to 1.12.0 in requirements.txt
------
Instructions for installing Hyperlist program on PyCharm

1. Use a computer with Windows 10 (recommended).
2. Download python 3.7.4 x86 version(32bit) from official website.
3. Install python on the computer and record its path.(e.g. C:\Users\FTIR\AppData\Local\Programs\Python\Python37-32)
   Make sure this path and the powershell path is added to the environment variable "Path".
4. Install PyCharm Education version. Try open the terminal in Pycharm.
   If PyCharm cannot open either powershell or cmd terminal, first verify in File|Setings|Terminal that their path are correct.
   If the absolute paths are correct, then try Help|Find Action, type "registry", enter, Disable terminal.use.conpty.on.windows. Restart.
5. Create a new project in Pycharm, declare a proper path and project name without space. Select New environment
   using "Vitualenv" (or conda environment if you prefer to construct the environment with anaconda). Choose python 
   3.7.4 x86 version as the base interpreter. Click create.
6. Download and unzip the Hyperlist program. Move or copy the "requirements.txt" file into this new project just created.
   Turn to the terminal mode. Type in "python --version" to verify that the current python interpreter is indeed
   3.7.4. Type "python -m pip install -r requirements.txt" to install all the dependent packages. Please use a user name
   without space, otherwise this step might fail.
   Note1: PyQt5 may not install properly, follow the instruction in the terminal to update pip first, then check the error message for PyQt5-sip
   Note2: PyQt5 requires Microsoft Visual C++ 14.0 or greater, get it with Microsoft C++ Build Tools
7. Move or copy "testPythonbit.py" to the new project. Run this script and check the output. If the output is 4, it
   means the python is in 32bit, which is good; if the output is 8, it means the python is 64bit, and you need to double
   check the interpreter.
8. Move or copy "get_project_path.py" to the new project. Run this script and update the cwd_path following the instructions
   of the comments.
9. Move or copy the remaining files from Hyperlist to the new project, except ".idea", "_pycache_" and "venv", which are
   project dependent. 
10. Now you can run all these programs. If the PC is not connected to Bruker, please keep line 14 in "BrukerControlPanel.py".
   (self.directCommand = None)
   If the PC is connected to Bruker, replace line 14 with line 15 (self.directCommand = win32com.client.Dispatch("{}/OpusCMD334.DirectCommand".format(cwd_path))).
11.To export a .exe version of worklist.py, install pyinstaller using pip first. Then in command prompt, input "pyinstaller.exe
    --onefile --windowed --icon=worklist.ico worklist.py" and run.
12.If visa doesn't work, try pyvisa 
13.Try pip install pyvisa-py if pyvisa is not working. For the exe, the pyvisa-py may need to be used for mercury_driver.py inside mercuryitc
14.If you want to use the camera fucntion of pylon, rather than just the offset function, install pypylon using pip. Then
   comment on the first line in the "Pylon.py" script and change turn_on_pylon to True.

Tips on optimizing the generted exe file:

1. Reduce the size using UPX
Install UPX from https://github.com/upx/upx/releases/ and unzip it to the current folder.
In the pyinstaller command line, specify the directory to UPX (relative is fine):
"pyinstaller.exe --onefile --windowed --upx-dir "upx-4.2.3-win64" --icon=worklist.ico worklist.py"
If PyInstaller finds UPX, it will show "UPX is available" during the process.

Without UPX option, the generated worklist.exe is 219 MB.
With UPX option, the genrated worklist.exe is 180 MB.

2. Use --onedir instead of --onefile to speed up loading time
--onefile generates a single exe file that contains everything, so it takes a bit longer to run since it needs to unzip first.
--onedir generate all files including the exe inside the dist folder.

After using the --onedir option, I found that the lib package (pypylon) for the camera in Hyperion 2000 (Basel pylon) is huge (~400 MB).
Will remove that from now on and leave the space for future cameras in the GUI of Hyperlist.

After deleting the pypylon package for the camera:
Without UPX option, the generated worklist.exe is 126 MB.
With UPX option, the generated worklist.exe is 92 MB.