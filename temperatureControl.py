from PyQt5 import QtCore, QtGui, QtWidgets
import sys
from mercuryitc.mercury_driver import MercuryITC
from mercurygui.config.main import *
from mercurygui.main import *

app = QtWidgets.QApplication(sys.argv)

#The IP address of mercury
#mercury_address = CONF.get("Connection", "VISA_ADDRESS")
mercury_address = "ASRL1::INSTR"
visa_library = CONF.get("Connection", "VISA_LIBRARY")

mercury = MercuryITC(mercury_address, visa_library, open_timeout=1)
#print(mercury.serl)

mercury_gui = MercuryMonitorApp(mercury)
mercury_gui.show()

app.exec_()