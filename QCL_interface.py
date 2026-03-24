#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jun 29 15:40:18 2018

@author: Sivan
"""

import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import pyvisa as visa
from interpolation import (getData, constPower, plotOrigData, plotModelData,
                           plotAllData, plotInterpolation)
from decimal import Decimal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import (FigureCanvasQT,NavigationToolbar2QT as NavigationToolbar)
import matplotlib.pyplot as plt
import instruments

class QCLWidget(QFrame):
    def __init__(self):
        super().__init__()
        
        #set the size and title of the window
        self.setGeometry(300, 100, 600, 450)
        self.setWindowTitle('Laser Control')
        self.show()
        
        self.initUI()
    def initUI(self):
        #create main grid to organize layout
        main_grid = QGridLayout()
        main_grid.setSpacing(10)
        self.setLayout(main_grid)
        
        #create resource manager to connect to the instrument and store resources in a list
        instruments.rm = visa.ResourceManager()
        resources = instruments.rm.list_resources()
        
        #create a combo box to allow the user to connect with a given instrument then add all resources
        self.connection_box = QComboBox()
        self.connection_box.addItem('Connect to QCL...')
        self.connection_box.addItems(resources)  
        self.connection_box.currentIndexChanged.connect(self.connectInstrument)
        main_grid.addWidget(self.connection_box, 0, 0)
        
        #create a label to show connection of the instrument with check or cross mark
        self.connection_indicator = QLabel(u'\u274c') #cross mark by default because not connected yet
        main_grid.addWidget(self.connection_indicator, 0, 1)
        
        #add labels for laser info
        laser_info_heading = QLabel('Laser Info -')
        main_grid.addWidget(laser_info_heading, 1, 0)
        self.idn_info = QLabel('Not connected.')
        main_grid.addWidget(self.idn_info, 2, 0)
        self.range_info = QLabel('')
        main_grid.addWidget(self.range_info, 3, 0)
        
        
        #add labels for laser status (standby/on)
        standby_lbl = QLabel('Standby')
        main_grid.addWidget(standby_lbl, 1, 2, 1, 1, Qt.AlignRight)
        on_lbl = QLabel('On')
        main_grid.addWidget(on_lbl, 2, 2, 1, 1, Qt.AlignTop | Qt.AlignRight)
        
        #add indicators for laser status
        self.red_ind = LedIndicator('orange') #red_ind is actually orange now
        main_grid.addWidget(self.red_ind, 1, 3, 1, 1, Qt.AlignLeft)
        self.green_ind = LedIndicator()
        main_grid.addWidget(self.green_ind, 2, 3, 1, 1, Qt.AlignLeft | Qt.AlignTop)
        
        #add button that prompts user to set the termination characters
        term_char_btn = QPushButton('Set Termination Characters')
        term_char_btn.setToolTip('Read and write termination characters are set to linefeed (\\n) by default')
        term_char_btn.clicked.connect(self.setTerminationCharacters)
        main_grid.addWidget(term_char_btn, 4, 0)
        
        #add button to toggle laser output
        laser_output_btn = QPushButton('Toggle Laser Output')
        laser_output_btn.clicked.connect(self.toggleLaser)
        main_grid.addWidget(laser_output_btn, 4, 2, 1, 2, Qt.AlignRight)
        
        #change column stretches
        main_grid.setColumnStretch(0, 4)
        main_grid.setColumnStretch(1, 6)
        main_grid.setColumnStretch(2, 1)
        main_grid.setColumnStretch(3, 1)
        
        #create tab screen
        self.tabs = QTabWidget()
        
        #create the other tabs
        self.initBasicTab()
        self.initScanTab()
        self.initConstPowerScanTab()
        self.initPlotTab()
        
        #set tool tips for the tabs
        self.tabs.setTabToolTip(0, 'Change the wavenumber and current.')
        self.tabs.setTabToolTip(1, 'Conduct a scan from one wavenumber to another by automatically changing' +
                                ' the wavenumber after a specified amount of time. Current is kept constant.')
        self.tabs.setTabToolTip(2, 'Conduct a scan from one wavenumber to another by automatically changing' +
                                ' the wavenumber after a specified amount of time. Power is kept constant.')
        self.tabs.setTabToolTip(3, 'View a 2d color map that shows the interpolation of data used to keep power' +
                                'constant during a scan.')
        
        #connect currentChanged to a function that moves the display from tab to tab
        self.tabs.currentChanged.connect(self.moveDisplay)
        
        #set scan in progress to False at initialization to prevent errors switching between tabs
        self.scan_in_progress = False
        
        #add the tabs to the grid     
        main_grid.addWidget(self.tabs, 5, 0, 1, 4)
        
    def connectInstrument(self):
        #if a selection is chosen that is not just the default prompt
        if (self.connection_box.currentText() != 'Connect to QCL...'):
            #get the laser name and connect the laser
            laser_name = self.connection_box.currentText()
            instruments.my_laser = instruments.rm.open_resource(laser_name)
            
            if instruments.my_laser.resource_name[0:4] != 'GPIB':
                del instruments.my_laser
                return #laser port must be GPIB, so exit function
            
            
            #set read and write termination to linefeed character by default
            instruments.my_laser.read_termination = '\n'
            instruments.my_laser.write_termination = '\n'
            
            #set units to wavenumbers and scan mode to manual
            instruments.my_laser.write(':disp:unit 0')
            instruments.my_laser.write(':scan:mode 2')
            
            #update display, laser info, and laser output
            self.updateDisplay()
            self.updateLaserInfo()
            self.updateLaserOutput()
            
            #change connection indicator to a check mark from a cross mark
            self.connection_indicator.setText(u'\u2705')
            
            #update range for basic wavenumner and current text		
            change_wnum = 'Change Wavenumber (cm^-1):'		
            wnum_range = '({} - {} cm^-1)'.format(self.wnum_min, self.wnum_max)		
            wnum_range = wnum_range.center(len(change_wnum))		
            change_curr = 'Change Current (mA):'		
            curr_range = '({} - {} mA)'.format(self.curr_min, self.curr_max)		
            curr_range = curr_range.center(len(change_curr))		
            self.basic_wnum_lbl.setText(change_wnum + '\n' + wnum_range)		
            self.basic_curr_lbl.setText(change_curr + '\n' + curr_range)
            
            #if model_dat is stored, delete it from memory
            try:
                del self.model_dat
            except AttributeError:
                pass
    
    def initBasicTab(self):
        #create basic tab and add it to the screen
        self.basic_tab = QWidget()
        self.tabs.addTab(self.basic_tab, 'Basic')
        
        #create labels and line edits to allow user to change wavenumber and current
        self.basic_wnum_lbl = QLabel('Change Wavenumber (cm^-1):')
        self.basic_wnum_le = QLineEdit(self)
        self.basic_wnum_le.setFixedWidth(70)
        self.basic_curr_lbl = QLabel('Change Current (mA):')
        self.basic_curr_le = QLineEdit(self)
        self.basic_curr_le.setFixedWidth(70)
        
        #create labels and displays to show the present values of the laser
        wnum_disp_lbl = QLabel('Present Wavenumber:')
        self.wnum_disp = QLCDNumber()
        self.wnum_disp.setNumDigits(7)
        self.wnum_disp.setMinimumWidth(250)
        current_disp_lbl = QLabel('Present Current:')
        self.current_disp = QLCDNumber()
        self.current_disp.setNumDigits(4)
        self.current_disp.setMinimumWidth(250)
        self.current_disp.setMinimumHeight(40)
        
        #create vboxes to reduce space between label and display in layout (number is to move display when tab changes)
        self.wnum_disp_vb0 = QVBoxLayout()
        self.wnum_disp_vb0.addWidget(wnum_disp_lbl, 1, Qt.AlignHCenter)
        self.wnum_disp_vb0.addWidget(self.wnum_disp, 4, Qt.AlignHCenter)
        self.current_disp_vb0 = QVBoxLayout()
        self.current_disp_vb0.addWidget(current_disp_lbl, 1, Qt.AlignHCenter)
        self.current_disp_vb0.addWidget(self.current_disp, 4, Qt.AlignHCenter)
        
        #create submit button to change the values of the laser and connect it to writeBasicInfo
        submit_btn = QPushButton('Submit')
        submit_btn.clicked.connect(self.writeBasicInfo)
        
        #create a grid to add everything onto the tab
        basic_grid = QGridLayout()
        basic_grid.setSpacing(10)
        self.basic_tab.setLayout(basic_grid)
        
        #left
        basic_grid.addWidget(self.basic_wnum_lbl, 0, 0, 3, 1)
        basic_grid.addWidget(self.basic_wnum_le, 0, 1, 3, 1, Qt.AlignLeft)
        basic_grid.addWidget(self.basic_curr_lbl, 3, 0, 2, 1)
        basic_grid.addWidget(self.basic_curr_le, 3, 1, 2, 1, Qt.AlignLeft)
        basic_grid.addWidget(submit_btn, 5, 0)
        
        #right
        basic_grid.addLayout(self.wnum_disp_vb0, 0, 2, 3, 1)
        basic_grid.addLayout(self.current_disp_vb0, 3, 2, 2, 1)
        
        #set column stretches
        basic_grid.setColumnStretch(0, 1)
        basic_grid.setColumnStretch(1, 1)
        basic_grid.setColumnStretch(2, 2)
        
            
    def initScanTab(self):
        #create scan tab and add it to the screen
        self.scan_tab = QWidget()
        self.tabs.addTab(self.scan_tab, "Automatic Scan")
        
        #create start and end buttons
        startBtn = QPushButton('Start Scan', self)
        startBtn.clicked.connect(self.startScan)
        endBtn = QPushButton('End Scan', self)
        endBtn.clicked.connect(self.stopScan)
        
        #put start and end buttons in an hbox
        start_end_hbox = QHBoxLayout()
        start_end_hbox.addWidget(startBtn)
        start_end_hbox.addWidget(endBtn)
        
        
        #create labels and line edit widgets for start and end wavenumbers, current, wavenumber resolution, and scan pause
        start_wnum = QLabel('Start Wavenumber (cm^-1):')
        self.start_wnum_le = QLineEdit(self)
        self.start_wnum_le.setFixedWidth(70)
        end_wnum = QLabel('End Wavenumber (cm^-1):')
        self.end_wnum_le = QLineEdit(self)
        self.end_wnum_le.setFixedWidth(70)
        current = QLabel('Current (mA):')
        self.current_le = QLineEdit(self)
        self.current_le.setFixedWidth(70)
        wnum_res = QLabel('Wavenumber Resolution (cm^-1):')
        self.wnum_res_le = QLineEdit(self)
        self.wnum_res_le.setFixedWidth(70)
        sc_pause = QLabel('Scan Pause (min)')
        self.sc_pause_le = QLineEdit(self)
        self.sc_pause_le.setFixedWidth(70)
        
        #create labels and displays to show the present values of the laser
        wnum_disp_lbl = QLabel('Present Wavenumber:')
        current_disp_lbl = QLabel('Present Current:')
        
        #create vboxes to reduce space between label and display in layout (number is to move display when tab changes)
        self.wnum_disp_vb1 = QVBoxLayout()
        self.wnum_disp_vb1.addWidget(wnum_disp_lbl, 1, Qt.AlignHCenter)
        self.current_disp_vb1 = QVBoxLayout()
        self.current_disp_vb1.addWidget(current_disp_lbl, 1, Qt.AlignHCenter)
        
        #create button to submit all the info
        submit_btn = QPushButton('Submit')
        submit_btn.clicked.connect(self.writeAutoScanInfo)
        
        #make info_written false until info is properly stored
        self.autoscan_info_written = False
        
        #create a timer to pause for the amount of time given by scan pause
        self.timer = QTimer()
        self.timer.timeout.connect(self.updateScan)
        
        #create a checkbox that allows the user to record data
        self.data_recording_lbl = QLabel('Record Parameters?')
        self.data_recording = QCheckBox()
        self.data_recording_le = QLineEdit()
        self.data_recording_le.setPlaceholderText('File Name')
        self.data_recording_le.setMinimumWidth(100)
        self.data_recording_hbox1 = QHBoxLayout()
        self.data_recording_hbox1.addWidget(self.data_recording_lbl)
        self.data_recording_hbox1.addWidget(self.data_recording)
        self.data_recording_hbox1.addWidget(self.data_recording_le)
        
        #create grid to organize layout for laser scan tab
        self.scan_grid = QGridLayout()
        self.scan_grid.setSpacing(10)
        self.scan_tab.setLayout(self.scan_grid)
        
        #add widgets and hboxes to grid
        #top
        self.scan_grid.addLayout(start_end_hbox, 0, 0, 1, 8)
        #left
        self.scan_grid.addWidget(start_wnum, 1, 0)
        self.scan_grid.addWidget(self.start_wnum_le, 1, 1, 1, 3, Qt.AlignLeft)
        self.scan_grid.addWidget(end_wnum, 2, 0)
        self.scan_grid.addWidget(self.end_wnum_le, 2, 1, 1, 3, Qt.AlignLeft)
        self.scan_grid.addWidget(current, 3, 0)
        self.scan_grid.addWidget(self.current_le, 3, 1, 1, 3, Qt.AlignLeft)
        self.scan_grid.addWidget(wnum_res, 4, 0)
        self.scan_grid.addWidget(self.wnum_res_le, 4, 1, 1, 3, Qt.AlignLeft)
        self.scan_grid.addWidget(sc_pause, 5, 0)
        self.scan_grid.addWidget(self.sc_pause_le, 5, 1, 1, 3, Qt.AlignLeft)
        #right
        self.scan_grid.addLayout(self.wnum_disp_vb1, 1, 4, 3, 4)
        self.scan_grid.addLayout(self.current_disp_vb1, 4, 4, 2, 4)
        #bottom
        self.scan_grid.addWidget(submit_btn, 6, 0)
        self.scan_grid.addLayout(self.data_recording_hbox1, 6, 4, 1, 4, Qt.AlignRight)
    
    def initConstPowerScanTab(self):
        #create scan tab and add it to the screen
        self.power_scan_tab = QWidget()
        self.tabs.addTab(self.power_scan_tab, "Automatic Interpolation Scan")
        
        #create start and end buttons
        startBtn = QPushButton('Start Scan', self)
        startBtn.clicked.connect(self.startScan)
        endBtn = QPushButton('End Scan', self)
        endBtn.clicked.connect(self.stopScan)
        
        #put start and end buttons in an hbox
        start_end_hbox = QHBoxLayout()
        start_end_hbox.addWidget(startBtn)
        start_end_hbox.addWidget(endBtn)
        
        
        #create labels and line edit widgets for start and end wavenumbers, current, wavenumber resolution, and scan pause
        start_wnum = QLabel('Start Wavenumber (cm^-1):')
        end_wnum = QLabel('End Wavenumber (cm^-1):')
        power = QLabel('Power (mW):')
        self.power_le = QLineEdit(self)
        self.power_le.setFixedWidth(70)
        wnum_res = QLabel('Wavenumber Resolution (cm^-1):')
        sc_pause = QLabel('Scan Pause (min)')
        
        #create labels and displays to show the present values of the laser
        wnum_disp_lbl = QLabel('Present Wavenumber:')
        current_disp_lbl = QLabel('Present Current:')
        
        #create vboxes to reduce space between label and display in layout (number is to move display when tab changes)
        self.wnum_disp_vb2 = QVBoxLayout()
        self.wnum_disp_vb2.addWidget(wnum_disp_lbl, 1, Qt.AlignHCenter)
        self.current_disp_vb2 = QVBoxLayout()
        self.current_disp_vb2.addWidget(current_disp_lbl, 1, Qt.AlignHCenter)
        
        #create button to submit all the info
        submit_btn = QPushButton('Submit')
        submit_btn.clicked.connect(self.writeAutoScanInfo)
        
        #make info_written false until info is properly stored
        self.power_autoscan_info_written = False
        
        #create a timer to pause for the amount of time given by scan pause
        self.timer = QTimer()
        self.timer.timeout.connect(self.updateScan)
        
        #create grid to organize layout for laser scan tab
        self.power_scan_grid = QGridLayout()
        self.power_scan_grid.setSpacing(10)
        self.power_scan_tab.setLayout(self.power_scan_grid)
        
        #create hbox that has checkbox allowing user to stored ata
        self.data_recording_hbox2 = QHBoxLayout()
        
        #add widgets and hboxes to grid
        #top
        self.power_scan_grid.addLayout(start_end_hbox, 0, 0, 1, 8)
        #left
        self.power_scan_grid.addWidget(start_wnum, 1, 0)
        self.power_scan_grid.addWidget(self.start_wnum_le, 1, 1, 1, 3, Qt.AlignLeft)
        self.power_scan_grid.addWidget(end_wnum, 2, 0)
        self.power_scan_grid.addWidget(self.end_wnum_le, 2, 1, 1, 3, Qt.AlignLeft)
        self.power_scan_grid.addWidget(power, 3, 0)
        self.power_scan_grid.addWidget(self.power_le, 3, 1, 1, 3, Qt.AlignLeft)
        self.power_scan_grid.addWidget(wnum_res, 4, 0)
        self.power_scan_grid.addWidget(self.wnum_res_le, 4, 1, 1, 3, Qt.AlignLeft)
        self.power_scan_grid.addWidget(sc_pause, 5, 0)
        self.power_scan_grid.addWidget(self.sc_pause_le, 5, 1, 1, 3, Qt.AlignLeft)
        #right
        self.power_scan_grid.addLayout(self.wnum_disp_vb2, 1, 4, 3, 4)
        self.power_scan_grid.addLayout(self.current_disp_vb2, 4, 4, 2, 4)
        #bottom
        self.power_scan_grid.addWidget(submit_btn, 6, 0)
        self.power_scan_grid.addLayout(self.data_recording_hbox2, 6, 4, 1, 4, Qt.AlignRight)
    
    def initPlotTab(self):
        #create plot tab and add it to the screen
        self.plot_tab = QWidget()
        self.tabs.addTab(self.plot_tab, "Interpolation Plot")
        
        #create buttons to view plot and to choose the folder with the data
        view_btn = QPushButton('View Plot', self)
        view_btn.clicked.connect(self.viewPlot)
        choose_data_btn = QPushButton('Choose Data Folder', self)
        choose_data_btn.clicked.connect(self.storeData)
        
        #create labels and line edit widgets for start and end wavenumbers, current, wavenumber resolution, and scan pause
        start_wnum = QLabel('Start Wavenumber (cm^-1):')
        end_wnum = QLabel('End Wavenumber (cm^-1):')
        power = QLabel('Power (mW):')
        self.power_le = QLineEdit(self)
        self.power_le.setFixedWidth(70)
        wnum_res = QLabel('Wavenumber Resolution (cm^-1):')
        
        #create button to add interpolation line onto plots
        interp_line_btn = QPushButton('Add Interpolation Line')
        interp_line_btn.clicked.connect(self.addInterpolationLine)
        
        #create grid to organize layout for plot tab
        self.plot_grid = QGridLayout()
        self.plot_grid.setSpacing(10)
        self.plot_tab.setLayout(self.plot_grid)
        
        self.plot_grid.addWidget(view_btn, 0, 0, 1, 2)
        self.plot_grid.addWidget(choose_data_btn, 0, 2, 1, 2)
        self.plot_grid.addWidget(start_wnum, 1, 0)
        self.plot_grid.addWidget(self.start_wnum_le, 1, 1, 1, 3)
        self.plot_grid.addWidget(end_wnum, 2, 0)
        self.plot_grid.addWidget(self.end_wnum_le, 2, 1, 1, 3)
        self.plot_grid.addWidget(power, 3, 0)
        self.plot_grid.addWidget(self.power_le, 3, 1, 1, 3)
        self.plot_grid.addWidget(wnum_res, 4, 0)
        self.plot_grid.addWidget(self.wnum_res_le, 4, 1, 1, 3)
        self.plot_grid.addWidget(interp_line_btn, 5, 0)
        
        
    def storeData(self, constPowerScan=False):
        QMessageBox.information(self, 'Data', 'Select folder of data to interpolate from after ' +
                                'closing this dialog.')
        folder = str(QFileDialog.getExistingDirectory(self, "Select data folder to interpolate from"))
        wnum_prec, curr_prec = self.getPrecision()
        
        sc_wnum_start,ok1 = QInputDialog.getDouble(self,"Data Folder Info","Enter start wavenumber used for this data")
        sc_wnum_end,ok2 = QInputDialog.getDouble(self,"integer input dualog","Enter end wavenumber used for this data")
        sc_wnum_res,ok3 = QInputDialog.getDouble(self,"integer input dualog","Enter the wavenumber resolution used for this data")
        
        try:
            self.orig_dat, self.model_dat = getData(sc_wnum_start, sc_wnum_end,
                                                    wnum_prec, curr_prec, sc_wnum_res, folder)
        except IndexError:
            QMessageBox.warning(self, 'Warning', 'Data files must be named in this format:\n"xmA.txt" where x is replaced by any number')
        except ValueError:
            QMessageBox.warning(self, 'Warning', 'Data files must be named in this format:\n"xmA.txt" where x is replaced by any number')
            
        
        if constPowerScan:
            try:
                wnum_list, self.curr_list = constPower(self.start_wnum_val, self.end_wnum_val, self.wnum_res_val,
                                                       self.power_val, self.model_dat)
            except AttributeError:
                QMessageBox.warning(self,'Data Error','No data folder chosen')
                return
            self.curr_val = self.curr_list[0] #for setCurr
            

    def writeBasicInfo(self):
        if self.outp == 0:
            self.toggleLaser()
        
        try:
            self.basic_wnum_val = float(self.basic_wnum_le.text())
            self.curr_val = int(self.basic_curr_le.text())

            try:
                self.setBasicWnum()
                self.setCurr()
            except ValueError:
                pass #error dialog will show up from setBasicWnum or setCurr
        
        except ValueError:
            warning_box = QMessageBox.warning(self, "Error", "Wavenumber and current must be numbers.")
        
    def writeAutoScanInfo(self, click, dialog=True):
        self.autoscan_info_written = False
        self.dialog = dialog
        
        try:
            self.start_wnum_val = float(self.start_wnum_le.text())
            self.end_wnum_val = float(self.end_wnum_le.text())
            self.wnum_res_val = round(float(self.wnum_res_le.text()), 2)
            self.sc_pause_val = round(float(self.sc_pause_le.text()), 2)
            
            if self.scan_constant == 'current':
                self.curr_val = int(self.current_le.text()) #int casting assumes precision is 0 digits
            if self.scan_constant == 'power':
                self.power_val = float(self.power_le.text())
                try:
                    wnum_list, self.curr_list = constPower(self.start_wnum_val, self.end_wnum_val,
                                                           self.wnum_res_val, self.power_val, self.model_dat)
                    self.curr_val = self.curr_list[0] #for setCurr
                except AttributeError: #if self.model_dat has not been stored yet
                    self.storeData(constPowerScan=True)

            try:
                self.setWnumStart()
                self.setWnumEnd()
                self.setCurr()
                self.setRes()
                self.setPause()
                
                #record info_written as true if all info has been stored without error
                self.autoscan_info_written = True
                if self.scan_constant == 'current' and dialog:
                    self.input_box = QMessageBox.information(self, 'Confirmation',
                        'Inputs submitted:\nStart Wavenumber - {}\nEnd Wavenumber - {}\nCurrent - {}\nResolution - {}\nPause - {}'.format(self.start_wnum_val,
                        self.end_wnum_val, self.curr_val, self.wnum_res_val, self.sc_pause_val))
                elif self.scan_constant == 'power' and dialog:
                    self.input_box = QMessageBox.information(self,'Confirmation',
                        'Inputs submitted:\nStart Wavenumber - {}\nEnd Wavenumber - {}\nPower - {}\nResolution - {}\nPause - {}'.format(self.start_wnum_val,
                        self.end_wnum_val, self.power_val, self.wnum_res_val, self.sc_pause_val))
                
            except ValueError: #otherwise set info_written as false
                self.autoscan_info_written = False
            
        except ValueError:
            warning_box = QMessageBox.warning(self, "Error", "All inputs must be numbers.")
            self.autoscan_info_written = False
            
    
    def viewPlot(self):
        self.plot_wind = PlotWindow()
        try:
            self.plot_wind.showPlot(self.orig_dat, self.model_dat)
        except AttributeError: #data hasn't been selected and stored yet (self.orig_dat, self.model_dat)
            QMessageBox.information(self, 'Missing Data', 'Select a folder of data first')
            
        
    def addInterpolationLine(self):
        try:
            st_wnum = float(self.start_wnum_le.text())
            end_wnum = float(self.end_wnum_le.text())
            wnum_res = round(float(self.wnum_res_le.text()), 2)
            power = float(self.power_le.text())
            
            try:
                self.plot_wind.showInterpolationLine(st_wnum, end_wnum, wnum_res, power, self.model_dat)
            except KeyError:		
                QMessageBox.warning(self, 'Key Error', 'The interpolation line cannot be added because all wavenumbers ' +
                                    'must be within the range used in the scans from the selected data folder.')
            except AttributeError: #nothing plotted yet (self.ax_o, self.ax_m) or no data stored
                QMessageBox.information(self, 'Missing Plot', 'You must plot data before adding the interpolation line')
    
        except ValueError:
            QMessageBox.warning(self, "Error", "All inputs must be numbers.")
            
    def setBasicWnum(self):
        val = self.basic_wnum_val
        if (val >= self.wnum_min and val <= self.wnum_max):
            instruments.my_laser.write(':laser:set {}'.format(val))
            self.wnum_disp.display(instruments.my_laser.query(':laser:set?')[:-4])
        else:
            warning_box = QMessageBox.warning(self, "Error", "Wavenumber is out of range")
            raise ValueError
    
    def setWnumStart(self):
        val = self.start_wnum_val
        if (val >= self.wnum_min and val <= self.wnum_max):
#            pass
            instruments.my_laser.write(':scan:start {}'.format(val))
            instruments.my_laser.write(':laser:set {}'.format(val))
            self.updateDisplay()
        else:
            warning_box = QMessageBox.warning(self, "Error", "Start wavenumber is out of range")
            raise ValueError
    def setWnumEnd(self):
        val = self.end_wnum_val
        if (val >= self.wnum_min and val <= self.wnum_max):
#            pass
            instruments.my_laser.write(':scan:end {}'.format(val))
        else:
            warning_box = QMessageBox.warning(self, "Error", "End wavenumber is out of range")
            raise ValueError

    def setCurr(self):
        val = self.curr_val
        if (val >= self.curr_min and val <= self.curr_max):
#            pass
            instruments.my_laser.write(':laser:curr {}'.format(val))
            self.current_disp.display(instruments.my_laser.query(':laser:curr?')[:-2])
        else:
            warning_box = QMessageBox.warning(self, "Error", "Current is out of range")
            raise ValueError
    def setRes(self):
        val = self.wnum_res_val
        wnum_diff = abs(self.end_wnum_val - self.start_wnum_val)
        
        if (val >= 0.5 and val <= wnum_diff):
#            pass
            instruments.my_laser.write(':scan:step {}'.format(val))
        elif (val < 0.5):
            warning_box = QMessageBox.warning(self, "Error", "Resolution is too small (must be at least 0.5")
            raise ValueError
        elif (val > wnum_diff):
            warning_box = QMessageBox.warning(self, "Error", "Resolution is too large")
            raise ValueError
    def setPause(self):
        val = self.sc_pause_val
        if (val >=0 and val <= 100):
#            pass
            instruments.my_laser.write(':scan:pause {}'.format(val))
        else:
            warning_box = QMessageBox.warning(self, "Error", "Scan pause should be between 0 and 100 seconds")
            raise ValueError
    def startScan(self):
        #const = power or current
        if (self.autoscan_info_written):
#            pass
#-----------------------------------------------------------------------------
            #turn laser on if it is off
            if (self.outp == 0):
                self.toggleLaser()
                
            instruments.my_laser.write(':scan:run 1')
            self.scan_in_progress = True
            self.num_steps = int(abs(self.end_wnum_val - self.start_wnum_val) // self.wnum_res_val) + 1
            self.step = 0
            
            if self.data_recording.isChecked(): #if user wants to record data
                file_name = self.data_recording_le.text()
                f = open(file_name + '.txt', 'w+')
                f.write('QCL_Wnum\tQCL_Current\tPEM_Wlength\tPEM_Wnum')
                f.close()
            
            #disable the record data checkbox after scan starts
            self.data_recording.setEnabled(False)
            self.data_recording_le.setEnabled(False)
            
            
            #call updateScan after each scan pause
            self.wnum_disp.display(instruments.my_laser.query(':scan:start?')[:-4]) #display the start wavenum (not working in updateScan)
            self.updateScan() #call once immediately to avoid unnecessary waiting
            self.timer.start(self.sc_pause_val * 60 * 1000) #convert from min to sec to ms
            
#-----------------------------------------------------------------------------
        else:
            warning_box = QMessageBox.warning(self, "Error", "You must enter data before you start the scan.")
    
    def updateScan(self):
        if self.step < self.num_steps:
            #display the present wavenumber
            pres_wnum = round(float(instruments.my_laser.query(':scan:start?')[:-4]), 2)
            pres_wnum += (self.step * round(float(instruments.my_laser.query(':scan:step?')[:-4]), 2))
            self.wnum_disp.display(str(pres_wnum))
            
            if self.scan_constant == 'power':
                self.curr_val = self.curr_list[self.step]
                self.setCurr()

            #continue to next step
            instruments.my_laser.write(':scan:step:next')   
            self.step += 1
            
        else:
            #stop the scan
            instruments.my_laser.write(':scan:run 0')
            self.scan_in_progress = False
            #stop timer
            self.timer.stop()
            #tell user scan is finished
            scan_complete = QMessageBox.information(self, 'Scan Completion', 'The scan has been completed')
            #update display
            self.wnum_disp.display(instruments.my_laser.query(':laser:set?')[:-4])
            #enable checkbox for recording data
            self.data_recording.setEnabled(True)
    def stopScan(self):
        warning_box = QMessageBox()
        warning_box.setText('Are you sure you want to stop the scan?')
        warning_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        retval = warning_box.exec_()
        
        if (retval == 65536): #user selected no
            pass
        elif (retval == 16384): #user selected yes
            instruments.my_laser.write(':scan:run 0')
            self.scan_in_progress = False
            self.timer.stop()
            scan_end = QMessageBox.information(self, 'Scan End', 'The scan has been ended')
            self.wnum_disp.display(instruments.my_laser.query(':laser:set?')[:-4])
            self.toggleLaser()
            self.data_recording.setEnabled(True)
    def toggleLaser(self):
        try: #will only work if self.outp is defined (if an instrument is connected)
            if (self.outp): #if laser power is on
                #turn laser power off and change variable
                self.outp = 0
                instruments.my_laser.write(':laser:outp 0')
                
                #change the color of the indicators
                self.red_ind.setChecked(True)
                self.green_ind.setChecked(False)
            else: #else if laser power is off
                #turn laser power on and change variable
                self.outp = 1
                instruments.my_laser.write(':laser:outp 1')
                
                #change the color of the indicators
                self.green_ind.setChecked(True)
                self.red_ind.setChecked(False)
        except AttributeError: #do nothing if no instrument is connected
            pass
            
    def updateDisplay(self):
        '''Updates the display of the wavenumber and the current'''
        self.wnum_disp.display(instruments.my_laser.query(':laser:set?')[:-4])
        self.current_disp.display(instruments.my_laser.query(':laser:curr?')[:-2])
    
    def updateLaserInfo(self):
        '''Updates the laser info at the top of the screen'''
        ilock_status = int(instruments.my_laser.query(':laser:ilock?'))
        if (ilock_status != 0):
            warning_box = QMessageBox.warning(self, "Ilock", "Must turn off ilock to control laser.")
        
        idn = instruments.my_laser.query('*idn?').split(';')
        idn_txt = 'Controller Model: ' + idn[1]
        idn_txt += '\nLaser Head Serial Number: ' + idn[4]

            
        self.idn_info.setText(idn_txt)
        
        #find the ranges for wavenumbers and current
        self.wnum_min = float(instruments.my_laser.query(':laser:set:min?').replace('cm-1', ''))
        self.wnum_max = float(instruments.my_laser.query(':laser:set:max?').replace('cm-1', ''))
        self.curr_min = float(instruments.my_laser.query(':laser:curr:min?').replace('mA', ''))
        self.curr_max = float(instruments.my_laser.query(':laser:curr:max?').replace('mA', ''))
        
        range_txt = 'Wavenumber Range: <b>{}-{}</b> (cm^-1)<br>Current Range: <b>{}-{}</b> (mA)'.format(self.wnum_min,
                                       self.wnum_max, self.curr_min, self.curr_max)
        self.range_info.setText(range_txt)
        
    def updateLaserOutput(self):
        '''Updates the laser output indicators when instrument is connected'''
        #store whether the output of the laser is on or off
        self.outp = int(instruments.my_laser.query(':laser:outp?'))
        
        #if on, turn on the green led, if off, turn on the red led
        if (self.outp):
            self.green_ind.setChecked(True)
        else:
            self.red_ind.setChecked(True)
            
    def setTerminationCharacters(self):
        '''Prompts user with input dialog to set termination characters'''
        read_text, read_val = QInputDialog.getText(self, 'Read Termination Character', 'Enter the read termination character:')
        write_text, write_val = QInputDialog.getText(self, 'Write Termination Character', 'Enter the write termination character:')
        instruments.my_laser.read_termination = read_val
        instruments.my_laser.write_termination= write_val

    def moveDisplay(self, index):
        '''Moves the wavenumber and current lcd displays since they cannot be on multiple
        layouts at once. Also keeps track of what is held constant during the scan and moves line edits.'''
        if index == 0:
            self.wnum_disp_vb0.addWidget(self.wnum_disp, 4)
            self.current_disp_vb0.addWidget(self.current_disp, 4)
        elif index == 1:
            self.wnum_disp_vb1.addWidget(self.wnum_disp, 4, Qt.AlignHCenter)
            self.current_disp_vb1.addWidget(self.current_disp, 6, Qt.AlignHCenter)
            self.data_recording_hbox1.addWidget(self.data_recording_lbl)
            self.data_recording_hbox1.addWidget(self.data_recording)
            self.data_recording_hbox1.addWidget(self.data_recording_le)
            
            self.scan_grid.addWidget(self.start_wnum_le, 1, 1, 1, 3, Qt.AlignLeft)
            self.scan_grid.addWidget(self.end_wnum_le, 2, 1, 1, 3, Qt.AlignLeft)
            self.current_le.setTabOrder(self.end_wnum_le, self.current_le)
            self.scan_grid.addWidget(self.current_le, 3, 1, 1, 3, Qt.AlignLeft)
            self.current_le.setTabOrder(self.current_le, self.wnum_res_le)
            self.scan_grid.addWidget(self.wnum_res_le, 4, 1, 1, 3, Qt.AlignLeft)
            self.scan_grid.addWidget(self.sc_pause_le, 5, 1, 1, 3, Qt.AlignLeft)
            
            if (not self.scan_in_progress):
                self.scan_constant = 'current'
        elif index == 2:
            self.wnum_disp_vb2.addWidget(self.wnum_disp, 4, Qt.AlignHCenter)
            self.current_disp_vb2.addWidget(self.current_disp, 6, Qt.AlignHCenter)
            self.data_recording_hbox2.addWidget(self.data_recording_lbl)
            self.data_recording_hbox2.addWidget(self.data_recording)
            self.data_recording_hbox2.addWidget(self.data_recording_le)
    
            self.power_scan_grid.addWidget(self.start_wnum_le, 1, 1, 1, 3, Qt.AlignLeft)
            self.power_scan_grid.addWidget(self.end_wnum_le, 2, 1, 1, 3, Qt.AlignLeft)
            self.power_le.setTabOrder(self.end_wnum_le, self.power_le)
            self.power_scan_grid.addWidget(self.power_le, 3, 1, 1, 3, Qt.AlignLeft)
            self.power_le.setTabOrder(self.power_le, self.wnum_res_le)
            self.power_scan_grid.addWidget(self.wnum_res_le, 4, 1, 1, 3, Qt.AlignLeft)
            self.power_scan_grid.addWidget(self.sc_pause_le, 5, 1, 1, 3, Qt.AlignLeft)
            
            if (not self.scan_in_progress):
                self.scan_constant = 'power'
        
        else:
            self.plot_grid.addWidget(self.start_wnum_le, 1, 1, 1, 3)
            self.plot_grid.addWidget(self.end_wnum_le, 2, 1, 1, 3)
            self.power_le.setTabOrder(self.end_wnum_le, self.power_le)
            self.plot_grid.addWidget(self.power_le, 3, 1, 1, 3)
            self.power_le.setTabOrder(self.power_le, self.wnum_res_le)
            self.plot_grid.addWidget(self.wnum_res_le, 4, 1, 1, 3)

    
    def turnLaserOff(self):
        '''Asks user to put laser output on standby before closing the program'''
        try:
            if (self.outp): #if power is still on
                question_box = QMessageBox()
                question_box.setText('Turn off laser before closing?')
                question_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                retval = question_box.exec_()
                
                if (retval == 65536): #user selected no
                    pass
                elif (retval == 16384): #user selected yes
                    self.toggleLaser()
        except AttributeError: #laser not connected yet
            pass
    
    def getPrecision(self):
        try:
            wnum_reading = instruments.my_laser.query(':laser:set?')
            curr_reading = instruments.my_laser.query(':laser:curr?')
            
            wnum_val = wnum_reading.rstrip('\n')[:-4] #assumes unit is cm-1
            curr_val = curr_reading.rstrip('\n')[:-2] #assumes unit is mA
            
            wnum_prec = abs(Decimal(wnum_val).as_tuple().exponent)
            curr_prec = abs(Decimal(curr_val).as_tuple().exponent)
            
            return wnum_prec, curr_prec
        except AttributeError: #not connected yet, instruments.my_laser not defined
            return 2, 0 #assume preicison is 2 and 0 decimal places


class PlotWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        #set the size and title of the window
        self.setGeometry(600, 150, 500, 600)
        self.setWindowTitle('Interpolation Plots')
        self.show()
        
        self.initUI()
        
    def initUI(self):
        #create temporary blank canvas
        fig = Figure()
        self.canvas = FigureCanvas(fig)
        
        #create toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        
        self.setLayout(self.layout)
    
    def showPlot(self, orig_dat, model_dat):
        fig, (self.ax_o, self.ax_m) = plotAllData(orig_dat, model_dat)
        fig.subplots_adjust(top=0.941,bottom=0.095,left=0.131,right=0.977,
                            hspace=0.367,wspace=0.2) #because fig.tight_layout isn't working
        self.canvas = FigureCanvas(fig)
        
        self.canvas.draw()
        
        #hide old toolbar and create new one
        self.toolbar.hide()
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.show()
        
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        
        
    def showInterpolationLine(self, st_wnum, end_wnum, wnum_res, power, model_dat):
        try: #remove previous line if it exists
            self.prev_interp_o.remove()
            self.prev_interp_m.remove()
        except AttributeError: #
            pass
        
        wnum_list, curr_list = constPower(st_wnum, end_wnum, wnum_res, power, model_dat)
        self.prev_interp_o, = plotInterpolation(self.ax_o, wnum_list, curr_list)
        self.prev_interp_m, = plotInterpolation(self.ax_m, wnum_list, curr_list)
        
        self.canvas.draw()
                


#from https://github.com/nlamprian/pyqt5-led-indicator-widget/blob/master/LedIndicatorWidget.py
class LedIndicator(QAbstractButton):
    scaledSize = 1000.0

    def __init__(self, color = 'green', parent=None): #added a color option to use red or orange
        QAbstractButton.__init__(self, parent)

        self.setMinimumSize(24, 24)
        self.setCheckable(True)

        #prevent user from changing indicator color by clicking    
        self.setEnabled(False)

        if color.lower() == 'red':
            self.on_color_1 = QColor(255, 0, 0)
            self.on_color_2 = QColor(192, 0, 0)
            self.off_color_1 = QColor(28, 0, 0)
            self.off_color_2 = QColor(128, 0, 0)
        elif color.lower() == 'orange':
            self.on_color_1 = QColor(255, 175, 0)
            self.on_color_2 = QColor(170, 115, 0)
            self.off_color_1 = QColor(90, 60, 0)
            self.off_color_2 = QColor(150, 100, 0)
        else: #default to green if user does not give valid option
            self.on_color_1 = QColor(0, 255, 0)
            self.on_color_2 = QColor(0, 192, 0)
            self.off_color_1 = QColor(0, 28, 0)
            self.off_color_2 = QColor(0, 128, 0)

    def resizeEvent(self, QResizeEvent):
        self.update()

    def paintEvent(self, QPaintEvent):
        realSize = min(self.width(), self.height())

        painter = QPainter(self)
        pen = QPen(Qt.black)
        pen.setWidth(1)

        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(realSize / self.scaledSize, realSize / self.scaledSize)

        gradient = QRadialGradient(QPointF(-500, -500), 1500, QPointF(-500, -500))
        gradient.setColorAt(0, QColor(224, 224, 224))
        gradient.setColorAt(1, QColor(28, 28, 28))
        painter.setPen(pen)
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(QPointF(0, 0), 500, 500)

        gradient = QRadialGradient(QPointF(500, 500), 1500, QPointF(500, 500))
        gradient.setColorAt(0, QColor(224, 224, 224))
        gradient.setColorAt(1, QColor(28, 28, 28))
        painter.setPen(pen)
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(QPointF(0, 0), 450, 450)

        painter.setPen(pen)
        if self.isChecked():
            gradient = QRadialGradient(QPointF(-500, -500), 1500, QPointF(-500, -500))
            gradient.setColorAt(0, self.on_color_1)
            gradient.setColorAt(1, self.on_color_2)
        else:
            gradient = QRadialGradient(QPointF(500, 500), 1500, QPointF(500, 500))
            gradient.setColorAt(0, self.off_color_1)
            gradient.setColorAt(1, self.off_color_2)

        painter.setBrush(gradient)
        painter.drawEllipse(QPointF(0, 0), 400, 400)

    @pyqtProperty(QColor)
    def onColor1(self):
        return self.on_color_1

    @onColor1.setter
    def onColor1(self, color):
        self.on_color_1 = color

    @pyqtProperty(QColor)
    def onColor2(self):
        return self.on_color_2

    @onColor2.setter
    def onColor2(self, color):
        self.on_color_2 = color

    @pyqtProperty(QColor)
    def offColor1(self):
        return self.off_color_1

    @offColor1.setter
    def offColor1(self, color):
        self.off_color_1 = color

    @pyqtProperty(QColor)
    def offColor2(self):
        return self.off_color_2

    @offColor2.setter
    def offColor2(self, color):
        self.off_color_2 = color

#run the GUI
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = QCLWidget()
    
    #turn laser on standby before quitting
    app.aboutToQuit.connect(window.turnLaserOff)
    
    sys.exit(app.exec_())