
# =====================================================================
# Example how to use Tango DLL in conjunction with Python version 3.7.3
# =====================================================================
import os.path
from ctypes import*                         # import ctypes (used to call DLL functions)
import sys
import clr

import comtypes.client
from comtypes.client import CreateObject
import os
from get_project_path import cwd_path

m_Tango = windll.LoadLibrary(r"{}\Tango_DLL.dll".format(cwd_path))  # give location of dll (current directory)

if m_Tango == 0:
    print("Error: failed to load DLL")
    sys.exit(0)
    
# Tango_DLL.dll loaded successfully

if m_Tango.LSX_CreateLSID == 0:
    print("unexpected error. required DLL function CreateLSID() missing")
    sys.exit(0)
# continue only if required function exists

LSID = c_int()
error = int     #value is either DLL or Tango error number if not zero
error = m_Tango.LSX_CreateLSID(byref(LSID))
if error > 0:
    print("Error: " + str(error))
    sys.exit(0)
    
# OK: got communication ID from DLL (usually 1. may vary with multiple connections)
# keep this LSID in mind during the whole session
    
if m_Tango.LSX_ConnectSimple == 0:
    print("unexepcted error. required DLL function ConnectSimple() missing")
    sys.exit(0)
# continue only if required function exists

error = m_Tango.LSX_ConnectSimple(LSID, -1, "COM4", 57600, 0)
if error > 0:
    print("Error: LSX_ConnectSimple " + str(error))
    sys.exit(0)
print("TANGO is now successfully connected to DLL")

error = m_Tango.LSX_SetPos(LSID, c_double(0), c_double(0), c_double(0), c_double(0))
if error > 0:
    print("Error: worng zero " + str(error))
    sys.exit(0)

m_Opus = windll.LoadLibrary(r"C:\Users\Administrator\Desktop\ProjOvld\OpusCMD334.dll")
m_Opus.DllRegisterServer()
m_Opus.StartOpus()
