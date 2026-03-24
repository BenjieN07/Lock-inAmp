#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 27 12:13:49 2018

@author: Sivan
"""

import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import pyvisa
import codecs
import instruments


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        #set the size and title of the window
        self.setGeometry(300, 100, 400, 10)
        self.setWindowTitle('PEM Control')
        self.show()
        
        instruments.pem_widget = PEMWidget(self)
        self.setCentralWidget(instruments.pem_widget)
        
        #define a settingsAction QAction that will call openSettings
        self.settingsAction = QAction('Instrument Settings', self)
        self.settingsAction.setStatusTip('Change settings of the connected PEM')
        self.settingsAction.triggered.connect(self.openSettings)
        self.settingsAction.setEnabled(False) #prevent user from changing settings until connected
        
        #add settings menu to allow user to change PEM settings
        mainMenu = self.menuBar()
        mainMenu.show()
        settingsMenu = mainMenu.addMenu('Settings')
        settingsMenu.addAction(self.settingsAction)
        
    def openSettings(self):
        self.settingsWindow = SettingsWindow()
    
    def closeEvent(self, event):
        try: #try to close settingsWindow if it exists and is open
            self.settingsWindow.close()
        except AttributeError:
            pass
        self.close()



class PEMWidget(QFrame):
    def __init__(self, main_window):
        super().__init__()
        #set the size and title of the window
        self.setGeometry(300, 100, 700, 10)
        self.setWindowTitle('PEM Control')
        self.show()
        
        self.main_window = main_window
        
        self.initUI()
    def initUI(self):
        #create main grid to organize layout
        main_grid = QGridLayout()
        main_grid.setSpacing(10)
        self.setLayout(main_grid)
        
        #create resource manager to connect to the instrument and store resources in a list
        instruments.rm = pyvisa.ResourceManager()
        resources = instruments.rm.list_resources()
        
        #create a combo box to allow the user to connect with a given instrument then add all resources
        self.connection_box = QComboBox()
        self.connection_box.addItem('Connect to PEM...')
        self.connection_box.addItems(resources)  
        self.connection_box.currentIndexChanged.connect(self.connectInstrument)
        main_grid.addWidget(self.connection_box, 0, 0)
        
        #create a label to show connection of the instrument with check or cross mark
        self.connection_indicator = QLabel(u'\u274c ') #cross mark by default because not connected yet
        main_grid.addWidget(self.connection_indicator, 0, 1, 1, 1)

        #add labels for PEM info
        self.idn_info = QLabel('PEM Info - Not connected.')
        font_name = self.idn_info.fontInfo().styleName()
        self.idn_info.setFont(QFont(font_name, 11))
        main_grid.addWidget(self.idn_info, 1, 0, 1, 2)
        
        #create tab screen
        self.tabs = QTabWidget()
        
        #create the other tabs
        self.initBasicTab()
        
        #set tool tips for the tabs
        self.tabs.setTabToolTip(0, 'Change wavenumber, retardation, and frequency.')
        
        main_grid.addWidget(self.tabs, 2, 0, 1, 2)
    
    def connectInstrument(self):
        #if a selection is chosen that is not just the default prompt
        if (self.connection_box.currentText() != 'Connect to PEM...'):
            #get the laser name and connect the laser
            instruments.pem_name = self.connection_box.currentText()
            instruments.pem = instruments.rm.open_resource(instruments.pem_name)
            
            if instruments.pem.resource_name[:4] == 'GPIB':
                return #pem can't be a GPIB port, so exit function
            
            #set baud rate to 2400 by default
            instruments.pem.baud_rate = 2400
            
            #allow user to change settings
            self.main_window.settingsAction.setEnabled(True)
            
            #change the PEM info label
            instruments.pem.query('Z')
            info = instruments.pem.read().strip()

            
            heads = {'002':'ZnSe','000':'FS','003':'CF','001':'IS','010':'Si','011':'CF'}
            
            self.idn_info.setText('PEM: ' + info + ' <b>(Optical Head: ' + heads[info[-7:-4]] + ')</b>')
            
            #change connection indicator to a check mark from a cross mark
            self.connection_indicator.setText(u'\u2705 ')
            
            #enable the submit button
            self.submit_btn.setEnabled(True)
            
            #call updateFreqDisplay every second
            self.timer = QTimer()
            self.timer.timeout.connect(self.updateFreqDisplay)
            self.timer.start(1000)
            
            #update the displays
            self.updateDisplay()
       
        
    def initBasicTab(self):
        #create basic tab and add it to the screen
        self.basic_tab = QWidget()
        self.tabs.addTab(self.basic_tab, 'Basic')
        
        #create a grid to add everything onto the tab
        basic_grid = QGridLayout()
        basic_grid.setSpacing(10)
        self.basic_tab.setLayout(basic_grid)
        
        #wavenumber, retardation, frequency
        wnum = QLabel('Wavenumber\n' + '(cm^-1)')
        self.wnum_le = QLineEdit()
        self.wnum_le.setMaxLength(7)
        self.wnum_le.setFixedWidth(70)
        basic_grid.addWidget(wnum, 1, 0)
        basic_grid.addWidget(self.wnum_le, 1, 1,1,1,Qt.AlignLeft)
        
        rtard = QLabel('Retardation\n' + u'(0.000-1.000 \u03BB)')
        self.rtard_le = QLineEdit()
        self.rtard_le.setMaxLength(5)
        self.rtard_le.setFixedWidth(70)
        basic_grid.addWidget(rtard, 2, 0)
        basic_grid.addWidget(self.rtard_le, 2, 1,1,1,Qt.AlignLeft)
        
        freq = QLabel('Frequency (kHz)')
      
        #displays
        self.wnum_disp = QLCDNumber()
        self.wnum_disp.setNumDigits(7)
        self.wnum_disp.setFixedHeight(50)
        self.wnum_disp.setMinimumWidth(150)
        self.rtard_disp = QLCDNumber()
        self.rtard_disp.setNumDigits(4)
        self.rtard_disp.setFixedHeight(50)
        self.rtard_disp.setMinimumWidth(150)
        self.freq_disp = QLCDNumber()
        self.freq_disp.setNumDigits(6)
        self.freq_disp.setFixedHeight(50)
        self.freq_disp.setFixedWidth(200)
        basic_grid.addWidget(self.wnum_disp, 1, 2)
        basic_grid.addWidget(self.rtard_disp, 2, 2)
        basic_grid.setColumnStretch(2, 2)
        
        #make vboxlayout for frequency
        freq_vbox = QVBoxLayout()
        freq_vbox.addWidget(freq, alignment=Qt.AlignCenter | Qt.AlignBottom)
        freq_vbox.addWidget(self.freq_disp, alignment=Qt.AlignCenter | Qt.AlignTop)
        basic_grid.addLayout(freq_vbox, 0, 0, 1, 3)
        
        
        #submit button (disabled until instruments.pem is connected)
        self.submit_btn = QPushButton('Submit')
        self.submit_btn.setFixedWidth(100)
        self.submit_btn.setEnabled(False)
        basic_grid.addWidget(self.submit_btn, 3, 0)
        self.submit_btn.clicked.connect(self.writeBasic)
        
        
    def updateFreqDisplay(self):
        try:
            instruments.pem.query('F')
            self.freq_disp.display(instruments.pem.read())
        except AttributeError:
            pass
    
    def updateDisplay(self):
        instruments.pem.query('W')
        wlength = instruments.pem.read().strip()
        real_wlength = wlength[:-1] + '.' + wlength[-1]
        self.wnum_disp.display(self.to_inv_cm(real_wlength))
        
        instruments.pem.query('R')
        self.rtard_disp.display('%.3f' % (float(instruments.pem.read())/1000))
        
        instruments.pem.query('F')
        self.freq_disp.display(instruments.pem.read())
        
    def writeBasic(self):
        #wavenumber will be slightly different from user input due to lack of precision
        wnum_input = self.wnum_le.text()
        if wnum_input != '':
            wnum_input = self.to_nm(self.wnum_le.text())
            instruments.pem.query('W:{}'.format(wnum_input))
            
            try:
                if instruments.pem.read().strip() == '?':
                    QMessageBox.warning(self, 'Input Error', 'Input is incorrect. Please check user manual' + 
                                        ' to ensure the correct range is being used, or check the instrument settings.')
            except: #timeout error
                pass
            
        rtard_input = self.rtard_le.text()
        if rtard_input != '':
            rtard_input = str(int(float(self.rtard_le.text())*1000))
            instruments.pem.query('R:{}'.format(rtard_input))
            
            try:
                if instruments.pem.read().strip() == '?':
                    QMessageBox.warning(self, 'Input Error', 'Input is incorrect. Please check user manual' + 
                                        ' to ensure the correct range is being used, or check the intrument settings.')
            except: #timeout error
                pass
            
        self.updateDisplay()
        
    def to_inv_cm(self, nm):
        if type(nm) == str:
            nm = float(nm)
        return round(1e7/nm, 1)
    
    def to_nm(self, wnum):
        if type(wnum) == str:
            wnum = float(wnum)
        return round(1e7/wnum, 1) #when using to_nm to query the PEM, the wavenumber will be slightly
        #different from user input due to lack of precision
        
    def convertFloat(self, num):
        return str(num).replace('.','')
        
        
        
        
        
        
        
        
class SettingsWindow(QDialog):
    def __init__(self):
        super().__init__()
        
        #set the size and title of the window
        self.setGeometry(350, 150, 300, 200)
        self.setWindowTitle('Instrument Settings')
        self.show()
        
        self.initUI()
        
    def initUI(self):
        #create main grid to organize layout
        main_grid = QGridLayout()
        main_grid.setSpacing(10)
        self.setLayout(main_grid)
        
        #baud rate, data bits, read termination, write termination
        baud_rate = QLabel('Baud Rate')
        self.baud_rate_le = QLineEdit()
        self.baud_rate_le.setPlaceholderText(str(instruments.pem.baud_rate))
        main_grid.addWidget(baud_rate, 0, 0)
        main_grid.addWidget(self.baud_rate_le, 0, 1)
        
        data_bits = QLabel('Data Bits')
        self.data_bits_le= QLineEdit()
        self.data_bits_le.setPlaceholderText(str(instruments.pem.data_bits))
        main_grid.addWidget(data_bits, 1, 0)
        main_grid.addWidget(self.data_bits_le, 1, 1)
        
        read_term = QLabel('Read Termination')
        self.read_term_le = QLineEdit()
        read_term_str = ('%r' % str(instruments.pem.read_termination)).strip("'")
        self.read_term_le.setPlaceholderText(read_term_str)
        main_grid.addWidget(read_term, 2, 0)
        main_grid.addWidget(self.read_term_le, 2, 1)
        
        write_term = QLabel('Write Termination')
        self.write_term_le = QLineEdit()
        write_term_str = ('%r' % str(instruments.pem.write_termination)).strip("'")
        self.write_term_le.setPlaceholderText(write_term_str)
        main_grid.addWidget(write_term, 3, 0)
        main_grid.addWidget(self.write_term_le, 3, 1)
        
        applyChangesBtn = QPushButton('Apply Changes')
        applyChangesBtn.clicked.connect(self.changeSettings)
        main_grid.addWidget(applyChangesBtn, 4, 0)
        
    def changeSettings(self):
        baud_rate = self.baud_rate_le.text()
        if (baud_rate == ''):
            baud_rate = instruments.pem.baud_rate
            instruments.pem.baud_rate = baud_rate
        else:
            try:
                baud_rate = int(baud_rate)
                instruments.pem.baud_rate = baud_rate
            except ValueError: #give warning and don't change
                QMessageBox.warning(self, 'Input Error', 'Baud rate must be an integer')
        
        data_bits = self.data_bits_le.text()
        if (data_bits == ''):
            data_bits = instruments.pem.data_bits
            instruments.pem.data_bits = data_bits
        else:
            try:
                data_bits = int(data_bits)
                instruments.pem.data_bits = data_bits
            except ValueError: #give warning and don't change
                QMessageBox.warning(self, 'Input Error', 'Data bits must be an integer')
        
        read_term = codecs.decode(self.read_term_le.text(), 'unicode_escape')
        if (read_term == ''):
            read_term = instruments.pem.read_termination
            
        write_term = codecs.decode(self.write_term_le.text(), 'unicode_escape')
        if (write_term == ''):
            write_term = instruments.pem.write_termination
            
        instruments.pem.read_termination = read_term
        instruments.pem.write_termination = write_term
        
        print([baud_rate, data_bits, read_term, write_term])



##create a subclass of QLineEdit that always has a fixed amount of numbers
#class QFixedLineEdit(QLineEdit):
#    def __init__(self, length):
#        '''length is an int that specifies the number of digits'''
#        super().__init__()
#        
#        self.textEdited.connect(self.formatText)
#        self.editingFinished.connect(self.clearText)
#        
#        self.setMaxLength(length)
#        self.setText('0'*length)
#        
#        self.pos = -1
#        self.cleared = False
#        
#    def formatText(self):
#        print('text changed')
#        
#    def clearText(self):
#        print('editing finished')
    

        
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()    
    sys.exit(app.exec_())