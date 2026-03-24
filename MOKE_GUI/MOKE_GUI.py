#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 30 14:59:21 2018

@author: Sivan
"""

from QCL_interface import *
from PEM_interface import *
from zi_plotter import *
from cryostat import *
import time
import socket
import numpy as np
from PyQt5.QtTest import *



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        #set the size and title of the window
        self.setGeometry(20, 40, 1400, 850)
        self.setWindowTitle('MOKE Interface')
        self.show()
        
        #create the main splitter: the left will have the qcl, pem, and chopper, right will have ZI and cryostat
        splitter = QSplitter(Qt.Horizontal)
        #create a left splitter for the qcl, pem, and chopper screens
        left_splitter = QSplitter(Qt.Vertical)
        #create a splitter to separate the pem and the chopper in the top
        left_top_splitter = QSplitter(Qt.Horizontal)
        #right splitter for control widget and data recording widget
        right_splitter = QSplitter(Qt.Vertical)
        
        self.setCentralWidget(splitter)
        
        global pem_widget
        global chp_widget
        global qcl_widget
        global rotr_widget
        global zi_widget
        global cryostat_widget
        global data_recording_widget
        
        pem_widget = PEMWidget(self)
        pem_widget.setFrameStyle(QFrame.Panel | QFrame.Raised)
        rotr_widget = Rotator()
        rotr_widget.setFrameStyle(QFrame.Panel | QFrame.Raised)
        left_top_splitter.addWidget(pem_widget)
        left_top_splitter.addWidget(rotr_widget)
        left_splitter.addWidget(left_top_splitter)
        
        qcl_widget = QCLWidget()
        qcl_widget.setFrameStyle(QFrame.Panel | QFrame.Raised)
        left_splitter.addWidget(qcl_widget)
        
        middle_widget = MiddlePanel(self)
        middle_widget.setFrameStyle(QFrame.Panel | QFrame.Raised)
        
        
        control_widget = ControlWidget(self)
        control_widget.setFrameStyle(QFrame.Panel | QFrame.Raised)
        data_recording_widget = DataRecordingWidget(self)
        data_recording_widget.setFrameStyle(QFrame.Panel | QFrame.Raised)
        right_splitter.addWidget(control_widget)
        right_splitter.addWidget(data_recording_widget)
        
        splitter.addWidget(left_splitter)
        splitter.addWidget(middle_widget)
        splitter.addWidget(right_splitter)
        
        #define a settingsAction QAction that will call openSettings
        self.settingsAction = QAction('PEM Settings', self)
        self.settingsAction.setStatusTip('Change settings of the connected PEM')
        self.settingsAction.triggered.connect(self.openSettings)
        self.settingsAction.setEnabled(False) #prevent user from changing settings until connected
        #define a QAction called plotSettingsAction that changes how often the plot is updated
        self.plotSettingsAction = QAction('Cryostat Plot Settings', self)
        self.plotSettingsAction.setStatusTip('Change how often the plot of the cryostat is updated')
        self.plotSettingsAction.triggered.connect(self.changePlotSettings)
        self.plotSettingsAction.setEnabled(False) #prevent user from changing settings until plot is started
        #define a qaction called ziSettings that changes how much data is plotted in seconds
        self.ziSettings = QAction('ZI Plot Settings', self)
        self.ziSettings.setStatusTip('Change how many seconds of data are ploted in the ZI Panel')
        self.ziSettings.triggered.connect(self.changeZISettings)
        
        #add settings menu to allow user to change PEM settings
        mainMenu = self.menuBar()
        mainMenu.show()
        settingsMenu = mainMenu.addMenu('Settings')
        settingsMenu.addAction(self.settingsAction)
        settingsMenu.addAction(self.plotSettingsAction)
        settingsMenu.addAction(self.ziSettings)
        
    def openSettings(self):
        self.settingsWindow = SettingsWindow()
        
    def changeZISettings(self):
        num,ok = QInputDialog.getInt(self,"ZI Plot Settings","Enter how much data you want " + 
                                     'to be plotted in seconds.')
        
        try:
            instruments.zi_widget.plot_dur = num * instruments.zi_widget.rate
            instruments.zi_widget.y2_data = np.empty(instruments.zi_widget.plot_dur)
            instruments.zi_widget.y3_data = np.empty(instruments.zi_widget.plot_dur)
        except AttributeError: #rate not defined yet
            instruments.zi_widget.plot_dur = num * instruments.zi_widget.rate_sb.value() #use 600 as default
            instruments.zi_widget.y2_data = np.empty(instruments.zi_widget.plot_dur)
            instruments.zi_widget.y3_data = np.empty(instruments.zi_widget.plot_dur)
        except Exception as e:
            QMessageBox.warning(self,'Error',str(e))
        
    def changePlotSettings(self):
        num,ok = QInputDialog.getInt(self,"Cryostat Plot Settings","Enter how often you want the " + 
                                     'plot to update in ms.')
        
        try:
            instruments.cryostat_widget.plotTimer.start(num)
        except Exception as e:
            QMessageBox.warning(self, 'Cryostat Plot Timer Error', 'Error: ' + str(e) + 
                                '\nMake sure the cryostat is connected.')
    
    def closeEvent(self, event):        
        try: #try to close settingsWindow if it exists and is open
            self.settingsWindow.close()
        except AttributeError:
            pass
        try:
            self.plotSettingsWindow.close()
        except AttributeError:
            pass
        
        try:
            if (qcl_widget.outp): #if power is still on
                question_box = QMessageBox()
                question_box.setText('Turn off laser before closing?')
                question_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                retval = question_box.exec_()
            else: #if power is off
                self.close()
                return
        except AttributeError: #outp may not be defined yet
            self.close()
            return
            
        if (retval == 65536): #user selected no
            pass
        elif (retval == 16384): #user selected yes
            qcl_widget.toggleLaser()
        
        self.close()



class PEMWidget(PEMWidget): #some functions overriden to keep wavenumber constant between both instruments
    def writeBasic(self): #the same, but changes wavenumber on QCL to match the PEM wavneumber
        #wavenumber will be slightly different from user input due to lack of precision
        wnum_input = self.wnum_le.text()
        if wnum_input != '':
            wlength_input = self.convertFloat(self.to_nm(self.wnum_le.text()))
            instruments.pem.query('W:{}'.format(wlength_input))
            
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
        
    def connectInstrument(self):
        super().connectInstrument()
        
        try: #sync wavenumber if laser is connected
            wnum = instruments.my_laser.query(':laser:set?').rstrip('\n')[:-4]
            qcl_widget.sync_wnum(wnum)
        except AttributeError:
            pass
    
    def sync_wnum(self, wnum): #sync the QCL wavenumber if connected
        wnum = round(float(wnum), 2)
        try:
            instruments.my_laser.write(':laser:set {}'.format(wnum))
            qcl_widget.updateDisplay()
        except AttributeError:
            pass
        


class QCLWidget(QCLWidget): #some functions overriden to keep wavenumber constant between both instruments
    def __init__(self):
        super().__init__()
        self.qcl_wnum_data = []
        self.qcl_curr_data = []
        self.pem_wlength_data = []
        self.pem_wnum_data = []
        
        self.scan_in_progress = False
        
    def connectInstrument(self):
        super().connectInstrument()
        
        try: #sync pem wavenumber if connected
            wnum = instruments.my_laser.query(':laser:set?').rstrip('\n')[:-4]
            self.sync_wnum(wnum)
        except AttributeError:
            pass
        
    def getWnum(self):
        if self.scan_in_progress == False:
            return float(instruments.my_laser.query(':laser:set?').rstrip('\n')[:-4])
        else:
            return self.qcl_wnum_data[-1]
    
    def getCurr(self):
        if self.scan_in_progress == False:
            return float(instruments.my_laser.query(':laser:curr?').rstrip('\n')[:-2])
        else:
            return self.qcl_curr_data[-1]
        
    def getPEMData(self):
        if self.scan_in_progress == False:
            instruments.pem.query('W')
            pem_wlength = float(instruments.pem.read().strip())
            pem_wnum = pem_widget.to_inv_cm(pem_wlength)
            
            return pem_wlength, pem_wnum
        else:
            return self.pem_wlength_data[-1], self.pem_wnum_data[-1]
        
        
    def setBasicWnum(self):
        val = self.basic_wnum_val
        if (val >= self.wnum_min and val <= self.wnum_max):
            instruments.my_laser.write(':laser:set {}'.format(val))
            self.wnum_disp.display(instruments.my_laser.query(':laser:set?')[:-4])
            self.sync_wnum(val)
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
            self.sync_wnum(val)
        else:
            warning_box = QMessageBox.warning(self, "Error", "Start wavenumber is out of range")
            raise ValueError
    def updateScan(self):
        if self.step < self.num_steps:
            #display the present wavenumber
            pres_wnum = round(float(instruments.my_laser.query(':scan:start?')[:-4]), 2)
            pres_wnum += (self.step * round(float(instruments.my_laser.query(':scan:step?')[:-4]), 2))
            self.wnum_disp.display(str(pres_wnum))
            self.sync_wnum(pres_wnum)
            
            #change current if using interpolation scan
            if self.scan_constant == 'power':
                self.curr_val = self.curr_list[self.step]
                self.setCurr()
            
            #get pem wavelength and pem freq
            try:
                instruments.pem.query('W')
                pem_wlength = float(instruments.pem.read().strip())
                pem_wnum = pem_widget.to_inv_cm(pem_wlength)
            except AttributeError: #if pem not connected, make values NA
                pem_wlength = 'NA'
                pem_wnum = 'NA'
            
            #get qcl current
            pres_curr = instruments.my_laser.query(':laser:curr?').strip()[:-2]
            
            self.qcl_wnum_data.append(pres_wnum)
            self.qcl_curr_data.append(pres_curr)
            self.pem_wlength_data.append(pem_wlength)
            self.pem_wnum_data.append(pem_wnum)
            
            if self.data_recording.isChecked():
                file_name = self.data_recording_le.text()
                f = open(file_name + '.txt', 'a+')
                f.write('\n{}\t{}\t{}\t{}'.format(pres_wnum, pres_curr,
                        pem_wlength, pem_wnum))
                f.close()
            

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
            if self.dialog: #default is true, unless called from control widget
                self.scan_complete = QMessageBox.information(self, 'Scan Completion', 'The scan has been completed')
            #update display
            self.wnum_disp.display(instruments.my_laser.query(':laser:set?')[:-4])
            self.sync_wnum(instruments.my_laser.query(':laser:set?')[:-4])
            #enable checkbox for recording data
            self.data_recording.setEnabled(True)
            self.data_recording_le.setEnabled(True)
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
            self.sync_wnum(instruments.my_laser.query(':laser:set?')[:-4])
            self.toggleLaser()
            self.data_recording.setEnabled(True)
            self.data_recording_le.setEnabled(True)
            
    def sync_wnum(self, wnum): #sync the PEM wavenumber if connected
        wnum = round(float(wnum), 1)
        nm = pem_widget.convertFloat(pem_widget.to_nm(wnum))
        try:
            instruments.pem.query('W:{}'.format(nm))
            pem_widget.updateDisplay()
        except AttributeError:
            pass




class OpticalChopper(QFrame):
    def __init__(self):
        super().__init__()
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
        self.connection_box.addItem('Connect to an instrument...')
        self.connection_box.addItems(resources)  
        self.connection_box.currentIndexChanged.connect(self.connectInstrument)
        main_grid.addWidget(self.connection_box, 0, 0)
        
        #create a label to show connection of the instrument with check or cross mark
        self.connection_indicator = QLabel(u'\u274c ') #cross mark by default because not connected yet
        main_grid.addWidget(self.connection_indicator, 0, 1)

        #add labels for Chopper info
        self.idn_info = QLabel('Chopper Info - Not connected.')
        font_name = self.idn_info.fontInfo().styleName()
        self.idn_info.setFont(QFont(font_name, 12))
        main_grid.addWidget(self.idn_info, 1, 0, 1, 2)
        
        #label, line edit, and slider for frequency
        freq = QLabel('Frequency (Hz, 0-10000)')
        self.freq_sb = QSpinBox()
        self.freq_sb.setMaximumWidth(100)
        self.freq_sb.setRange(0, 10000)
        self.freq_sb.setEnabled(False)
        self.freq_sld = QSlider(Qt.Vertical)
        self.freq_sld.setRange(0, 10000)
        self.freq_sld.setTickInterval(1000)
        self.freq_sld.setTickPosition(QSlider.TicksRight)
        self.freq_sld.setEnabled(False)
        
        freq_sb_vb = QVBoxLayout()
        freq_sb_vb.addWidget(freq)
        freq_sb_vb.addWidget(self.freq_sb)
        freq_sb_vb.setSpacing(0)
        freq_sb_vb.setAlignment(freq, Qt.AlignHCenter)
        freq_sb_vb.setAlignment(self.freq_sb, Qt.AlignHCenter)
        main_grid.addLayout(freq_sb_vb,3,0,1,1,Qt.AlignCenter)
        main_grid.addWidget(self.freq_sld,3,1)
        
        #combo box to select blade type
        blades = QLabel('Blade Type')
        self.blades_cb = QComboBox()
        self.blades_dict = {'MC1F2':'0','MC1F10':'1','MC1F30':'3','MC1F60':'4',
                            'MC1F100':'5','MC1F10HP':'6','MC1F2P10':'7','MC1F6P10':'8',
                            'MC1F10A':'9','MC2F330':'10','MC2F47':'11','MC2F57B':'12',
                            'MC2F860':'13','MC2F5360':'14'}
        self.blades_cb.addItem('Choose blade type...')
        self.blades_cb.addItem('MC1F15')
        self.blades_cb.setCurrentIndex(1)
        self.blades_cb.addItems(self.blades_dict.keys())
        self.blades_dict['MC1F15'] = '2'
        blades_hb = QHBoxLayout()
        blades_hb.addWidget(blades)
        blades_hb.addWidget(self.blades_cb)
        blades_hb.addStretch(1)
        main_grid.addLayout(blades_hb,2,0,1,2)
        self.blades_cb.currentIndexChanged.connect(self.setBladeType)
        
    def connectInstrument(self):
        #if a selection is chosen that is not just the default prompt
        if (self.connection_box.currentText() != 'Connect to an instrument...'):
            #get the chopper name and connect the chopper
            chp_name = self.connection_box.currentText()
            instruments.chp = instruments.rm.open_resource(chp_name)
            
            if instruments.chp.resource_name[:4] == 'GPIB':
                return #pem can't be a GPIB port, so exit function
            
            #set baud rate to 115.2K by default
            instruments.chp.baud_rate = 115200
            
            #change the chopper info label
            chp_info = instruments.chp.query('id?')
            self.idn_info.setText('Chopper Info - {}'.format(chp_info))
            
            #update spinbox and slider to show frequency
            self.freq_sb.setEnabled(True)
            self.freq_sld.setEnabled(True)
            self.freq_sb.valueChanged[int].connect(self.setSpinboxFreq)
            self.freq_sld.sliderReleased.connect(self.setSliderFreq)
            freq = self.getFreq()
            print(freq)
            self.freq_sb.setValue(freq)
            
            #change connection indicator to a check mark from a cross mark
            self.connection_indicator.setText(u'\u2705 ')
                        
    def setBladeType(self):
        #if user selected a valid blade type
        if (self.blades_cb.currentText() != 'Choose blade type...'):
            blade_name = self.blades_cb.currentText()
            blade_index = self.blades_dict[blade_name]
            
            try:
                instruments.chp.write('blade={}'.format(blade_index))
            except AttributeError:
                QMessageBox.warning(self, 'Connection Error', 'Must connect to chopper before ' +
                                    'setting blade type.')
            
    def setFreq(self, val):
        try:
            instruments.chp.write('freq={}'.format(val))
        except AttributeError:
            QMessageBox.warning(self, 'Connection Error', 'Must connect to chopper before ' +
                                'setting frequency.')
        
    def getFreq(self):
        try:
            return float(instruments.chp.query('freq?'))
        except AttributeError:
            QMessageBox.warning(self, 'Connection Error', 'Must connect to chopper before ' +
                                'getting frequency.')
            
    def setSpinboxFreq(self, val):
        '''Changes frequency of slider based on the value that the user entered into the spinbox'''
        self.freq_sld.setValue(val)
        self.setFreq(val)
    
    def setSliderFreq(self):
        '''Changes frequency of spinbox based on the value that the user slid to'''
        val = self.freq_sld.value()
        self.freq_sb.setValue(val)
        self.setFreq(val)
        
class Rotator(QFrame):
    def __init__(self):
        super().__init__()
        self.show()
        self.initUI()
        self.angle_data = []
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
        self.connection_box.addItem('Connect to rotator...')
        self.connection_box.addItems(resources)  
        self.connection_box.currentIndexChanged.connect(self.connectInstrument)
        main_grid.addWidget(self.connection_box, 0, 0)
        
        #create a label to show connection of the instrument with check or cross mark
        self.connection_indicator = QLabel(u'\u274c ') #cross mark by default because not connected yet
        main_grid.addWidget(self.connection_indicator, 0, 1)
        
        #position labels
        curr_pos = QLabel('Current Position') #above the slider
        rel_pos = QLabel('Relative Position') #below slider
        main_grid.addWidget(curr_pos,1,0)
        main_grid.addWidget(rel_pos,3,0,1,1,Qt.AlignBottom)
        
        #enable/disable button
        self.enable_btn = QPushButton('Enable/Disable')
        self.enable_btn.setEnabled(False)
        self.enable_btn.clicked.connect(self.toggleEnabled)
        main_grid.addWidget(self.enable_btn,1,1,1,2,Qt.AlignCenter)
        
        #absolute position slider
        self.abs_pos_sld = QDoubleSlider(Qt.Horizontal)
        self.abs_pos_sld.setTickPosition(QSlider.TicksBelow)
        self.abs_pos_sld.setEnabled(False)
        self.abs_pos_sld.sliderReleased.connect(self.setSliderPos)
        self.abs_pos_sld.setTickInterval(500)
        self.min_pos = QLabel('Min') #bottom left of slider
        self.max_pos = QLabel('Max') #bottom right of slider
        slider_vbox = QVBoxLayout()
        slider_vbox.addWidget(self.abs_pos_sld)
        min_max_hbox = QHBoxLayout()
        min_max_hbox.addWidget(self.min_pos)
        min_max_hbox.addStretch()
        min_max_hbox.addWidget(self.max_pos)    
        slider_vbox.addLayout(min_max_hbox)
        main_grid.addLayout(slider_vbox,2,0)
        
        #absolute position spin box
        self.abs_pos_sb = QDoubleSpinBox() #right of slider
        self.abs_pos_sb.setDecimals(4)
        self.abs_pos_sb.setSingleStep(0.0001)
        self.abs_pos_sb.setEnabled(False)
        self.abs_pos_sb.editingFinished.connect(self.setSpinboxPos)
        main_grid.addWidget(self.abs_pos_sb,2,1)
        
        #led indicator
        self.rotr_ind = QLedIndicator('orange')
        main_grid.addWidget(self.rotr_ind,2,2)
        
        
        
        #relative position buttons and spinbox
        self.rel_left = QPushButton(u'\u25C0') #left of relative position spinbox
        self.rel_left.setFixedWidth(20)
        self.rel_left.clicked.connect(self.moveRelLeft)
        self.rel_right = QPushButton(u'\u25B6') #right of relative position spinbox
        self.rel_right.setFixedWidth(20)
        self.rel_right.clicked.connect(self.moveRelRight)
        self.rel_left.setEnabled(False)
        self.rel_right.setEnabled(False)
        self.rel_pos_sb = QDoubleSpinBox() #below slider
        self.rel_pos_sb.setDecimals(4)
        self.rel_pos_sb.setSingleStep(0.0001)
        self.rel_pos_sb.setAlignment(Qt.AlignHCenter)
        rel_pos_hbox = QHBoxLayout()
        rel_pos_hbox.addWidget(self.rel_left)
        rel_pos_hbox.addWidget(self.rel_pos_sb)
        rel_pos_hbox.addWidget(self.rel_right)
        main_grid.addLayout(rel_pos_hbox,4,0,2,1)
        
        #led indicator and current state labels
        curr_state_head = QLabel('Current State')
        self.curr_state = QLineEdit('')
        self.curr_state.setAlignment(Qt.AlignHCenter)
        self.curr_state.setReadOnly(True)
        main_grid.addWidget(curr_state_head,4,1,1,2,Qt.AlignBottom | Qt.AlignHCenter)
        main_grid.addWidget(self.curr_state,5,1,1,2,Qt.AlignTop | Qt.AlignHCenter)
        
        
        
        
        
        
    def connectInstrument(self):
        #if a selection is chosen that is not just the default prompt
        if (self.connection_box.currentText() != 'Connect to rotator...'):
            #get the chopper name and connect the chopper
            rotr_name = self.connection_box.currentText()
            
            if rotr_name[:4] == 'GPIB':
                return #rotator can't be a GPIB port, so exit function
            
            instruments.rotr = instruments.rm.open_resource(rotr_name)
            
            #set baud rate to 921600 by default
            instruments.rotr.baud_rate = 921600
            
            left_lim = float(instruments.rotr.query('1SL?')[3:])
            right_lim = float(instruments.rotr.query('1SR?')[3:])
            
            self.abs_pos_sb.setRange(left_lim, right_lim)
            self.rel_pos_sb.setRange(left_lim, right_lim)
            self.abs_pos_sld.setRange(left_lim, right_lim)
            
            self.min_pos.setText(str(left_lim))
            self.max_pos.setText(str(right_lim))
            
            self.updatePosDisplay()
            
            #store controller states to tell when rotator is moving, disabled, ready, etc.
            self.controller_states = {'0a': 'NOT REFERENCED from reset',
                                      '0b': 'NOT REFERENCED from HOMING',
                                      '0c': 'NOT REFERENCED from CONFIGURATION',
                                      '0d': 'NOT REFERENCED from DISABLE',
                                      '0e': 'NOT REFERENCED from READY',
                                      '0f': 'NOT REFERENCED from MOVING',
                                      '10': 'NOT REFERENCED no parameters',
                                      '14': 'CONFIGURATION',
                                      '1e': 'HOMING',
                                      '28': 'MOVING',
                                      '32': 'READY from HOMING',
                                      '33': 'READY from MOVING',
                                      '34': 'READY from DISABLE',
                                      '3c': 'DISABLE from READY',
                                      '3d': 'DISABLE from MOVING' }
            
            
            
            #change connection indicator to a check mark from a cross mark
            self.connection_indicator.setText(u'\u2705')
            
            #turn led indicator on and set appropriate color based on state
            ctrl_state = self.controller_states[instruments.rotr.query('1mm?')[3:].strip()]
            self.ready = (ctrl_state.split(' ')[0] == 'READY')

            if (self.ready):
                self.rotr_ind.changeColor('green')
                #enable position spinbox, slider, and buttons
                self.abs_pos_sb.setEnabled(True)
                self.abs_pos_sld.setEnabled(True)
                self.rel_left.setEnabled(True)
                self.rel_right.setEnabled(True)
                self.enable_btn.setText('Disable')
            else:
                self.enable_btn.setText('Enable')
                
            self.rotr_ind.setChecked(True)
            self.enable_btn.setEnabled(True)
            
            
            #update controller state every second (1000 ms)
            self.timer = QTimer()
            self.timer.timeout.connect(self.updateState)
            self.timer.start(1000)
            
    def moveRelLeft(self):
        val = self.rel_pos_sb.value() * (-1)
        instruments.rotr.write('1PR{}'.format(val))
        self.updatePosDisplay()
    
    def moveRelRight(self):
        val = self.rel_pos_sb.value()
        instruments.rotr.write('1PR{}'.format(val))
        self.updatePosDisplay()
    
    def setSpinboxPos(self):
        val = self.abs_pos_sb.value()
        self.abs_pos_sld.setValue(val)
        self.angle_data.append(val)
        instruments.rotr.write('1PA{}'.format(val))
    
    def setSliderPos(self):
        val = self.abs_pos_sld.value()
        self.abs_pos_sb.setValue(val)
        self.angle_data.append(val)
        instruments.rotr.write('1PA{}'.format(val))
        
    def updateState(self):
        ctrl_state = self.controller_states[instruments.rotr.query('1mm?')[3:].strip()]
        self.curr_state.setText(ctrl_state)
        self.ready = (ctrl_state.split(' ')[0] == 'READY')
        
        if (self.ready):
            #enable position spinbox, slider, and buttons
            self.abs_pos_sb.setEnabled(True)
            self.abs_pos_sld.setEnabled(True)
            self.rel_left.setEnabled(True)
            self.rel_right.setEnabled(True)
        else:
            #disable position spinbox, slider, and buttons
            self.abs_pos_sb.setEnabled(False)
            self.abs_pos_sld.setEnabled(False)
            self.rel_left.setEnabled(False)
            self.rel_right.setEnabled(False)
            
    def updatePosDisplay(self):
        abs_pos = float(instruments.rotr.query('1PA?')[3:])
        self.abs_pos_sb.setValue(abs_pos)
        self.abs_pos_sld.setValue(abs_pos)
            
    
    def toggleEnabled(self):
        ctrl_state = self.controller_states[instruments.rotr.query('1mm?')[3:].strip()]
        
        if (self.ready or ctrl_state == 'MOVING'): #disable, then change text to enable
            instruments.rotr.write('1mm0')
            self.enable_btn.setText('Enable')
            self.rotr_ind.changeColor('orange')
        else: #enable, then change text to disable
            instruments.rotr.write('1mm1')
            self.enable_btn.setText('Disable')
            self.rotr_ind.changeColor('green')
            
class MiddlePanel(QFrame):
    '''The middle panel of the interface, which holds the ZIWidget and the Cryostat'''
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        instruments.zi_widget = ZIWidget()
        instruments.cryostat_widget = Cryostat(main_window)
        self.initUI()
        
        
    
    def initUI(self):
        #create main grid to organize lainyout
        main_grid = QGridLayout()
        main_grid.setSpacing(10)
        self.setLayout(main_grid)
        
        #create tab screen
        self.tabs = QTabWidget()
        main_grid.addWidget(self.tabs,0,0)
        
        #add tabs to menu
        self.tabs.addTab(instruments.zi_widget, 'Oscope (Zurich Instruments)')
        self.tabs.addTab(instruments.cryostat_widget, 'Cryostat (Montana Instruments)')
        
        
        #set tool tips for the tabs
        self.tabs.setTabToolTip(0, 'Plot the demodulator signal from the oscope')
        self.tabs.setTabToolTip(1, 'Plot the temperature from the cryostat.')
        
        
        
        
class ZIWidget(ZIWidget): #overwrite initUI to add a stretch at the bottom for spacing        
    def initUI(self):
        #create main grid to organize layout
        main_grid = QGridLayout()
        main_grid.setSpacing(10)
        self.setLayout(main_grid)
        
        #create labels, line edits, and a button to connect to data server
        self.daq_lbl = QLabel(u'Data Server Connection: \u274c') #cross mark to show daq not connected yet
        host_lbl = QLabel('Host')
        self.host_le = QLineEdit()
        self.host_le.setText('192.168.1.10')
        port_lbl = QLabel('Port')
        self.port_le = QLineEdit()
        self.port_le.setText('8004')
        connect_daq_btn = QPushButton('Connect')
        connect_daq_btn.clicked.connect(self.connectDAQ)
        
        main_grid.addWidget(self.daq_lbl,0,0,1,2)
        main_grid.addWidget(host_lbl,1,0)
        main_grid.addWidget(self.host_le,1,1)
        main_grid.addWidget(port_lbl,2,0)
        main_grid.addWidget(self.port_le,2,1)
        main_grid.addWidget(connect_daq_btn,3,0)
        
        
        #create labels, line edits, and a button to start plotting and collect intrument data
        instr_lbl = QLabel('Instrument Info')
        serial_lbl = QLabel('Device Serial')
        self.serial_le = QLineEdit()
        self.serial_le.setText('3436')
        demodulator_lbl = QLabel('Demodulator Path')
        self.demodulator_le = QLineEdit()
        self.demodulator_le.setText('/dev3436/demods')
        self.plot_btn = QPushButton('Start Plotting')
        self.plot_btn.clicked.connect(self.startPlot)
        self.stop_plot_btn = QPushButton('Stop Plotting')
        self.stop_plot_btn.clicked.connect(self.stopPlot)
        
        main_grid.addWidget(instr_lbl,0,2)
        main_grid.addWidget(serial_lbl,1,2)
        main_grid.addWidget(self.serial_le,1,3)
        main_grid.addWidget(demodulator_lbl,2,2)
        main_grid.addWidget(self.demodulator_le,2,3)
        main_grid.addWidget(self.plot_btn,3,2)
        main_grid.addWidget(self.stop_plot_btn,3,3)
        
        
        #create canvas and toolbar to plot data
        #no xlabels to save space
        self.fig = plt.Figure()
        ax1 = self.fig.add_subplot(311)
#        ax1.set_xlabel('Time')
        ax1.set_ylabel(r'$V_0 (volts)$',fontsize=14)
        ax1.set_title('Demodulator 1')
        ax2 = self.fig.add_subplot(312)
#        ax2.set_xlabel('Time')
        ax2.set_ylabel(r'$V_2/V_0$',fontsize=14)
        ax2.set_title('Demodulator 2')
        ax3 = self.fig.add_subplot(313)
#        ax3.set_xlabel('Time')
        ax3.set_ylabel(r'$V_3/V_0$',fontsize=14)
        ax3.set_title('Demodulator 3')
        self.axes = [ax1, ax2, ax3]
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setMinimumHeight(700)
        self.canvas.setMaximumWidth(800)  # width of the plot windows
        self.toolbar = NavigationToolbar(self.canvas, self)
#        self.fig.tight_layout()
        #tight_layout doesn't work
        self.fig.subplots_adjust(top=0.938,bottom=0.039,left=0.188,right=0.954,
                                hspace=0.307,wspace=0.2)
        
        #hbox to store toolbar and rate label and spinbox, as well as plot update label and spinbox
        toolbar_hb = QHBoxLayout()
        toolbar_hb.addWidget(self.toolbar)
        
        rate = QLabel('Rate (samples/sec)')
        self.rate_sb = QSpinBox()
        self.rate_sb.setMinimum(0)
        self.rate_sb.setMaximum(10000)  # maximum sampling rate 10k
        self.rate_sb.setValue(100)      # default sampling rate 100
        self.rate_sb.editingFinished.connect(self.changeRate)
        
        plot_update = QLabel('Plot update (sec)')
        plot_update.setToolTip('Updates the plot after the specified amount of seconds')
        self.plot_update_sb = QSpinBox()
        self.plot_update_sb.setMinimum(0)
        self.plot_update_sb.setValue(1)  # default update rate 1 sec
        self.plot_update_rate = 1*1000
        self.plot_update_sb.editingFinished.connect(self.changePlotUpdateRate)
        
        rate_vb = QVBoxLayout()
        rate_vb.addWidget(rate)
        rate_vb.addWidget(self.rate_sb)
        rate_vb.addStretch()
        
        plot_update_vb = QVBoxLayout()
        plot_update_vb.addWidget(plot_update)
        plot_update_vb.addWidget(self.plot_update_sb)
        plot_update_vb.addStretch()
        
        toolbar_hb.addLayout(rate_vb)
        toolbar_hb.addLayout(plot_update_vb)
        toolbar_hb.addStretch()
        
        
        main_grid.addLayout(toolbar_hb,4,0,1,4)
        main_grid.addWidget(self.canvas,5,0,1,4,Qt.AlignCenter)
        
        
        #add a stretch to the bottom to push everything to the top
        spacer = QVBoxLayout()
        spacer.addStretch()
        main_grid.addLayout(spacer,6,0)
        
        #set minimum width to 600
        self.setMinimumWidth(600)
        
    def connectDAQ(self): #also connects to Zurich dataAcquisitionModule for aligned data
        if (self.host_le.text() == '' or self.port_le.text() == ''):
            QMessageBox.warning(self, 'Data Server Settings Error',
                                'Do not leave host or port blank')
            return
        
        host = self.host_le.text()
        api_level = 6
        
        self.device_id = 'dev{}'.format(self.serial_le.text())
        
        try:
            port = int(self.port_le.text())
        except ValueError:
            QMessageBox.warning(self, 'Port Value Error', 'Port must be a number')
            return
        
        try:
            instruments.daq = ziPython.ziDAQServer(host, port, api_level)
            instruments.dataAcq = instruments.daq.dataAcquisitionModule()
            self.daq_lbl.setText(u'Data Server Connection: \u2705')
        except Exception as e:
            QMessageBox.warning(self, 'Connection Error', str(e))
    
    def changeRate(self):
        try: #has to be called before the user starts plotting
            self.rate = self.rate_sb.value()
        except AttributeError:
            pass
        
    def changePlotUpdateRate(self):
        self.plot_update_rate = self.plot_update_sb.value()*1000
        try: #restart plotTimer if it exists
            self.plotTimer.stop()
            self.plotTimer.start(self.plot_update_rate)
        except AttributeError:
            pass
    
    def stopPlot(self):
        self.timer.stop()
        self.plotTimer.stop()
        self.rate_sb.setEnabled(True)
        
        for ax in self.axes:
            ax.clear()
        
        self.time_data = [[],[],[]]
        self.volt_data = [[],[],[]]
        #self.volt_dataY = [[],[],[]]    # 20180918 store demods Y output 
    
    def startPlot(self):
        #get demodulator path from line edit
        demod_path = self.demodulator_le.text()
        
        #create list of signal paths to get the x value from each demodulator
        #TODO: check sample.r.avg
        self.signal_paths = []
        #self.signal_pathsY = []    # 20180918 store demods Y output 
        for i in range(3):
            self.signal_paths.append(demod_path + '/{}/sample.x'.format(i))   # changed from x output to x and y outputs
            #self.signal_pathsY.append(demod_path + '/{}/sample.y'.format(i))  # 20180918 store demods Y output 
        #disable rate spinbox
        self.rate_sb.setEnabled(False)
        
        try:
            self.rate = self.rate
        except AttributeError:
            module_sampling_rate = 100  # Number of points/second
            self.rate = module_sampling_rate
        burst_duration = 0.2  # Time in seconds for each data burst/segment. 
        num_cols = int(np.ceil(self.rate*burst_duration))
        self.data_length = num_cols #used to add data from other instruments later to lists
        try:
            self.plot_dur
        except AttributeError:
            self.plot_dur = self.rate * 10 #10 seconds default
        
        try:
            instruments.dataAcq.set("dataAcquisitionModule/device", self.device_id)
            instruments.dataAcq.set("dataAcquisitionModule/type", 0)    # continuous mode
            instruments.dataAcq.set("dataAcquisitionModule/grid/mode", 2)
            instruments.dataAcq.set("dataAcquisitionModule/endless", 1)
            instruments.dataAcq.set("dataAcquisitionModule/duration", burst_duration)
            instruments.dataAcq.set("dataAcquisitionModule/grid/cols", num_cols)
        except AttributeError:#exit function if not connected yet
            return
            
        self.data = {}
        #self.dataY = {}    # 20180918 store demods Y output 
        
        try:
            for signal_path in self.signal_paths:
                instruments.dataAcq.subscribe(signal_path)
                self.data[signal_path] = []
            # for signal_pathY in self.signal_pathsY:    # 20180918 store demods Y output 
            #     instruments.dataAcq.subscribe(signal_pathY)
            #     self.dataY[signal_pathY] = []
                
        except RuntimeError as e:
            QMessageBox.warning(self, 'Path Error', 'Incorrect path:\n' + str(e))
            return
        except AttributeError:
            QMessageBox.warning(self, 'Data Server Connection Error',
                                'Must connect to data server before plotting instrument data')
            return
        
        self.clockbase = instruments.daq.getInt("/{}/clockbase".format(self.device_id))
        
        #start recording data
        self.timestamp0 = np.nan
        instruments.dataAcq.execute()
        
        #create empty lists to store time data and volt data
        self.time_data = [[],[],[]]
        self.volt_data = [[],[],[]]
        #self.volt_dataY = [[],[],[]]    # 20180918 store demods Y output 
        
        #create empty lists to keep track of temperature data from cryostat and qcl data
        self.temp_data = [[],[],[]]
        self.qcl_wnum = []
#        self.qcl_curr = []
#        self.pem_wlength = []
#        self.pem_wnum = []
        
        #create empty numpy arrays, which will be used to store and plot the most recent data
        self.y2_data = np.empty(self.plot_dur)
        self.y3_data = np.empty(self.plot_dur)
        
        #call get data function every second
        self.timer = QTimer()
        self.timer.timeout.connect(self.getData)
        self.timer.start(1000)
        #call plot function every 1 seconds
        self.plotTimer = QTimer()
        self.plotTimer.timeout.connect(self.plot)
        self.plotTimer.start(self.plot_update_rate)
        
        
    def getData(self):
        self.data, self.timestamp0 = self.read_data_update_plot(self.data, self.timestamp0)
        
    def pausePlot(self):
        instruments.dataAcq.finish()
        try:
            self.timer.stop() #stop the plot
            self.plotTimer.stop()
        except AttributeError:
            pass
        
    def resumePlot(self):
        instruments.dataAcq.execute()
        self.timer.start(1000)
        self.plotTimer.start(self.plot_update_rate)
        
    def read_data_update_plot(self, data, timestamp0):
        """
        Read the acquired data out from the module and plot it. Raise an
        AssertionError if no data is returned.
        """
        data_read = instruments.dataAcq.read(True)
        returned_signal_paths = [signal_path.lower() for signal_path in data_read.keys()]
        progress = instruments.dataAcq.progress()[0]
        # Loop over all the subscribed signals:
        i = 0
        
        for signal_path in self.signal_paths:
            if signal_path.lower() in returned_signal_paths:
                # Loop over all the bursts for the subscribed signal. More than
                # one burst may be returned at a time, in particular if we call
                # read() less frequently than the burst_duration.
                for index, signal_burst in enumerate(data_read[signal_path.lower()]):
                    if np.any(np.isnan(timestamp0)):
                        # Set our first timestamp to the first timestamp we obtain.
                        timestamp0 = signal_burst['timestamp'][0, 0]
                    # Convert from device ticks to time in seconds.
                    t = (signal_burst['timestamp'][0, :] - timestamp0)/self.clockbase
                    value = signal_burst['value'][0, :]
                    
                    #append new data to data lists
                    self.time_data[i] += list(t)
                    self.volt_data[i] += list(value)
                                        
                
                    try: #add last recorded temperature to list of temperature data
                        if i == 0:
                            self.temp_data[0].append(instruments.cryostat_widget.temp_data[0][-1])
                            self.temp_data[1].append(instruments.cryostat_widget.temp_data[1][-1])
                            self.temp_data[2].append(instruments.cryostat_widget.temp_data[2][-1])
                    except Exception as e: #if not connected, add none to list
                        if i == 0:
                            self.temp_data[0].append(None)
                            self.temp_data[1].append(None)
                            self.temp_data[2].append(None)
                        
                    try: #add qcl data to list
                        if i == 0:
                            self.qcl_wnum.append(qcl_widget.getWnum())
#                        self.qcl_curr.append(qcl_widget.getCurr())
                    except Exception as e: #if not connected, add none to list
                        if i == 0:
                            self.qcl_wnum.append(None)
#                        self.qcl_curr.append(None)
                        
#                    try: #add pem data to list
#                        pem_wlength, pem_wnum = qcl_widget.getPEMData()
#                        self.pem_wlength.append(pem_wlength)
#                        self.pem_wnum.append(pem_wnum)
#                    except Exception as e:
#                        self.pem_wlength.append(None)
#                        self.pem_wnum.append(None)
#                        print(str(e))
                    
                    #append data
                    data[signal_path].append(signal_burst)
            else:
                # Note: If we read before the next burst has finished, there may be no new data.
                # No action required.
                pass
            
            i += 1
        
        
        return data, timestamp0
            
    
    def plot(self):
        #clear previous axes and set title
        for i in range(3):
            self.axes[i].clear()
            self.axes[i].set_title('Demodulator {}'.format(i+1))
        
            #reset ylabels since they were just cleared
            if i==0:
                self.axes[i].set_ylabel(r'$V_0 (volts)$')
            elif i==1:
                self.axes[i].set_ylabel(r'$V_2/V_0$')
            elif i==2:
                self.axes[i].set_ylabel(r'$V_3/V_0$')
        
            #make sure scale is normal and does not use scientific notation
            self.axes[i].get_yaxis().get_major_formatter().set_useOffset(False)
            self.axes[i].get_yaxis().get_major_formatter().set_scientific(False)
        
        v0_data = self.volt_data[0][-self.plot_dur:]
        v0_len = len(v0_data)

        self.y2_data[:v0_len] = self.volt_data[1][-self.plot_dur:]
        self.y2_data[:v0_len] /= v0_data    # V2/V0
        self.y3_data[:v0_len] = self.volt_data[2][-self.plot_dur:]
        self.y3_data[:v0_len] /= v0_data    # V3/V0
        

        #plot data
        try:
            # demod 1: V0
            self.axes[0].plot(self.time_data[0][-self.plot_dur:], v0_data,'k')
            # demod 2/demod 1: V2/V0
            self.axes[1].plot(self.time_data[1][-self.plot_dur:], self.y2_data[:v0_len],'C0')
            # demod 3/demod 1: V3/V0
            self.axes[2].plot(self.time_data[2][-self.plot_dur:], self.y3_data[:v0_len],'C1')
    
        except Exception as e: #exception might be because one or demodulators are not connected
            pass
        
        #Update the plot
        self.fig.tight_layout()
        self.canvas.draw()
        

class Cryostat(Cryostat):
    def initUI(self):
        #create main grid to organize layout
        main_grid = QGridLayout()
        main_grid.setSpacing(10)
        self.setLayout(main_grid)
        
        #allow user to enter IP address and create stop execution button
        ip_lbl = QLabel("Input the IP address of the Cryostation PC")
        ip_lbl.setToolTip('Port is set to 7773 and buffer size is set to 80 for connection. Press return key to change IP address if not yet connected.')
        self.ip_le = QLineEdit()
        self.ip_le.setText('192.168.0.3')
        self.ip_le.setToolTip('Port is set to 7773 and buffer size is set to 80 for connection. Press return key to change IP address if not yet connected.')
        stop_exec_btn = QPushButton()
        stop_exec_btn.setToolTip('Stop Execution')
        self.ip_le.returnPressed.connect(self.connectInstrument)
        
        #add stop execution image to button and connect to function
        stop_exec_img = QPixmap(os.path.join('img', 'stop_execution.png'))
        stop_exec_icn = QIcon(stop_exec_img)
        stop_exec_btn.setIcon(stop_exec_icn)
        stop_exec_btn.setIconSize(QSize(stop_exec_img.width()+2, stop_exec_img.height()))
        stop_exec_btn.setStyleSheet("QPushButton{background: transparent;}")
        stop_exec_btn.clicked.connect(self.stopExec)
        
        ip_vbox = QVBoxLayout()
        ip_vbox.addWidget(ip_lbl)
        ip_vbox.addWidget(self.ip_le)
        main_grid.addLayout(ip_vbox,0,0)
        main_grid.addWidget(stop_exec_btn,0,1,1,1, Qt.AlignRight | Qt.AlignTop)
        
        
        
        
        #add cool down, warm up, standby, and stop button
        cool_down_btn = QPushButton()
        cool_down_btn.setToolTip('Cool Down')
        cool_down_img = QPixmap(os.path.join('img', 'cool_down.png'))
        cool_down_icn = QIcon(cool_down_img)
        cool_down_btn.setIcon(cool_down_icn)
        cool_down_btn.setIconSize(QSize(cool_down_img.width(), cool_down_img.height()))
        cool_down_btn.setFixedSize(QSize(cool_down_img.width()+2, cool_down_img.height()))
        cool_down_btn.setStyleSheet("QPushButton{background: transparent;}")
        cool_down_btn.clicked.connect(self.coolDown)
        
        warm_up_btn = QPushButton()
        warm_up_btn.setToolTip('Warm Up')
        warm_up_img = QPixmap(os.path.join('img', 'warm_up.png'))
        warm_up_icn = QIcon(warm_up_img)
        warm_up_btn.setIcon(warm_up_icn)
        warm_up_btn.setIconSize(QSize(warm_up_img.width(), warm_up_img.height()))
        warm_up_btn.setFixedSize(QSize(warm_up_img.width()+2, warm_up_img.height()))
        warm_up_btn.setStyleSheet("QPushButton{background: transparent;}")
        warm_up_btn.clicked.connect(self.warmUp)
        
        standby_btn = QPushButton()
        standby_btn.setToolTip('Standby')
        standby_img = QPixmap(os.path.join('img', 'standby.png'))
        standby_icn = QIcon(standby_img)
        standby_btn.setIcon(standby_icn)
        standby_btn.setIconSize(QSize(standby_img.width(), standby_img.height()))
        standby_btn.setFixedSize(QSize(standby_img.width()+2, standby_img.height()))
        standby_btn.setStyleSheet("QPushButton{background: transparent;}")
        standby_btn.clicked.connect(self.standby)
        
        stop_btn = QPushButton()
        stop_btn.setToolTip('Stop')
        stop_img = QPixmap(os.path.join('img', 'stop.png'))
        stop_icn = QIcon(stop_img)
        stop_btn.setIcon(stop_icn)
        stop_btn.setIconSize(QSize(stop_img.width(), stop_img.height()))
        stop_btn.setFixedSize(QSize(stop_img.width()+2, stop_img.height()))
        stop_btn.setStyleSheet("QPushButton{background: transparent;}")
        stop_btn.clicked.connect(self.stop)


        #add buttons to layout
        btns_hbox = QHBoxLayout()
        btns_hbox.addWidget(cool_down_btn)
        btns_hbox.addWidget(warm_up_btn)
        btns_hbox.addWidget(standby_btn)
        btns_hbox.addWidget(stop_btn)
        btns_hbox.addStretch()
        main_grid.addLayout(btns_hbox,1,0)
        
        
        
        #create qspinbox and button to allow user to control temperature set point
        self.temp_sb = QDoubleSpinBox()
        self.temp_sb.setRange(3.2, 350)
        self.temp_sb.setDecimals(2)
        self.temp_sb.setValue(270.0)
        self.temp_sb.setToolTip('Temperature Set Point')
        kelvin_lbl = QLabel('K')
        temp_btn = QPushButton()
        temp_btn.setToolTip('Send the temperature set point')
        temp_img = QPixmap(os.path.join('img', 'set_temp.png'))
        temp_icn = QIcon(temp_img)
        temp_btn.setIcon(temp_icn)
        temp_btn.setIconSize(QSize(temp_img.width(), temp_img.height()))
        temp_btn.setFixedSize(QSize(temp_img.width()+2, temp_img.height()))
        temp_btn.setStyleSheet("QPushButton{background: transparent;}")
        temp_btn.clicked.connect(self.setTemp)
        
        temp_hbox = QHBoxLayout()
        temp_hbox.addWidget(self.temp_sb)
        temp_hbox.addWidget(kelvin_lbl)
        temp_hbox.addWidget(temp_btn)
        temp_hbox.addStretch()
        main_grid.addLayout(temp_hbox,1,1)
        
        
        #create label for data table
        self.data_table = QLabel()
        self.displayData(empty=True)
        main_grid.addWidget(self.data_table,2,0,1,2)
        
        
        #add vbox to fill the bottom part of the window and squish everything else to the top
        filler_vbox = QVBoxLayout()
        filler_vbox.addStretch()
        main_grid.addLayout(filler_vbox,3,0)
        
        #make plot to plot temperature vs. time for sample, user, and platform
        self.fig = plt.Figure()
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel('Time ($s$)')
        self.ax.set_ylabel(r'Temperature ($K$)')
        self.ax.set_title('Temperature vs. Time')
        self.ax.set_ylim((-5, 360))
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.fig.subplots_adjust(top=0.883,bottom=0.194,left=0.138,right=0.946,
                                hspace=0.2,wspace=0.2) #tight_layout doesn't work
                
        self.setMinimumWidth(500)
        
        #give user the option to select which data to plot from platform, sample, and user
        platform_hb = QHBoxLayout()
        sample_hb = QHBoxLayout()
        user_hb = QHBoxLayout()
        data_checkboxes_vb = QVBoxLayout()
        
        #make checkboxes
        self.platform_cb = QCheckBox()
        self.platform_cb.setChecked(True)
        self.sample_cb = QCheckBox()
        self.user_cb = QCheckBox()
        
        #make labels
        platform_lbl = QLabel('Platform')
        sample_lbl = QLabel('Sample')
        user_lbl = QLabel('User')
        
        #put checkboxes and labels in their hboxes
        platform_hb.addWidget(self.platform_cb)
        platform_hb.addWidget(platform_lbl)
        sample_hb.addWidget(self.sample_cb)
        sample_hb.addWidget(sample_lbl)
        user_hb.addWidget(self.user_cb)
        user_hb.addWidget(user_lbl)
        
        data_checkboxes_vb.addLayout(platform_hb)
        data_checkboxes_vb.addLayout(sample_hb)
        data_checkboxes_vb.addLayout(user_hb)
        data_checkboxes_vb.setSpacing(5)
        
        toolbar_hb = QHBoxLayout() #will have toolbar and checkboxes
        toolbar_hb.addWidget(self.toolbar)
        toolbar_hb.addLayout(data_checkboxes_vb)
        
        
        #make button to restart plot
        restart_plot_btn = QPushButton('Restart Plot')
        restart_plot_btn.clicked.connect(self.restartPlot)
        restart_plot_btn.setFixedWidth(150)
        
        
        plot_vb = QVBoxLayout() #has toolbar, data checkboxes, plot, and restart plot button
        plot_vb.addLayout(toolbar_hb)
        plot_vb.addWidget(self.canvas)
        plot_vb.addWidget(restart_plot_btn, Qt.AlignLeft)
        plot_vb.addStretch()
        main_grid.addLayout(plot_vb,3,0,1,2)
        
    
    
    def restartPlot(self):
        '''Restarts the plot by stopping timer and calling startPlot again'''
        #clear the plot and stop the plot timer
        self.plotTimer.stop()
        self.ax.clear()
        
        #start plotting again
        self.startPlot()
        
    def stopExec(self):
        '''Stops execution of the cryostat and allows user to connect to a different ip address'''
        self.timer.stop()
        self.plotTimer.stop()
        instruments.cryostat = None
        self.ip_le.setText(self.ip_le.text().rstrip(' (Connected)'))
        self.ax.clear()
        
        self.ip_le.setEnabled(True)
    
    def plotData(self):
        '''Plots temperature vs. time'''
        #append time to time_data then update x axis end labels
        self.time_data.append(time.time() - self.start_time)
        
        #append temperature data to each list within the 2d temp_data list
        try:
            self.temp_data[0].append(float(self.getPlatformTemperature()))
            self.temp_data[1].append(float(self.getSampleTemperature()))
            self.temp_data[2].append(float(self.getUserTemperature()))
        except ValueError:
            pass
        
        #append stabity data to list
        self.stability_data.append(float(self.getPlatformStability()))
        
        #clear previous plot and replot the data from last 20000 data points (should be a little over 5 hours)
        self.ax.clear()
        if self.platform_cb.isChecked():
            self.ax.plot(self.time_data[-20000:], self.temp_data[0][-20000:], label="Platform")
        if self.sample_cb.isChecked():
            self.ax.plot(self.time_data[-20000:], self.temp_data[1][-20000:], label="Sample")
        if self.user_cb.isChecked():
            self.ax.plot(self.time_data[-20000:], self.temp_data[2][-20000:], label="User")
        
        #change x and y labels, change x ticks to only show first and last one, and add legend
        self.ax.set_xlabel(r'Time ($s$)')
        self.ax.set_ylabel(r'Temperature ($K$)')
        self.ax.set_title('Temperature vs. Time')
        self.ax.get_yaxis().get_major_formatter().set_useOffset(False)
        self.ax.get_yaxis().get_major_formatter().set_scientific(False)
        self.ax.legend()
        self.fig.tight_layout()
        self.canvas.draw()
        
    def connectInstrument(self): #overwrite to enable plot settings after connection
        super().connectInstrument()
        self.main_window.plotSettingsAction.setEnabled(True)
        


class ControlWidget(QFrame):
    '''Allows user to list commands and control the other widgets'''
    command_started = pyqtSignal()
    
    
    def __init__(self, main_window):
        super().__init__()
        
        self.main_window = main_window
        self.setMinimumWidth(450)
        self.initUI()
        
    def initUI(self):
        #create main grid to organize layout
        main_vbox = QVBoxLayout()
        main_vbox.setSpacing(10)
        self.setLayout(main_vbox)
        
        #create list of commands
        self.commands = []
        
        #create tab screen
        self.tabs = QTabWidget()
        self.tabs.setMaximumHeight(500)
        main_vbox.addWidget(self.tabs)
        

        
        #create display for list of commands
        commands_scroll = QScrollArea()
        commands_scroll.setWidgetResizable(True)
        commands_scroll.setAlignment(Qt.AlignTop)
        self.command_display = QLabel('<b>Commands:</b><ol style="margin:0px;"></ol>')
        self.command_display.setAlignment(Qt.AlignTop)
        self.command_display.setWordWrap(True)
        commands_scroll.setWidget(self.command_display)
        main_vbox.addWidget(commands_scroll)
        
        
        
        #initalize all tabs
        self.initAutoScanTab()
        self.initInterpScanTab()
        self.initRotatorTab()
        self.initTempTab()
        
        
        #make hbox layout for buttons to run all commands, remove last command, and clear all
        commands_hb = QHBoxLayout()
        
        #add button to run all commands
        run_commands_btn = QPushButton('Run Commands')
        run_commands_btn.setFixedWidth(90)
        run_commands_btn.clicked.connect(self.runCommands)
        commands_hb.addWidget(run_commands_btn)
        
        #add button to remove last
        remove_last_btn = QPushButton('Remove Last')
        remove_last_btn.setFixedWidth(90)
        remove_last_btn.clicked.connect(self.removeLast)
        commands_hb.addWidget(remove_last_btn)
        
        #add button to clear all
        clear_all_btn = QPushButton('Clear All')
        clear_all_btn.setFixedWidth(90)
        clear_all_btn.clicked.connect(self.clearAll)
        commands_hb.addWidget(clear_all_btn)
        
        #allow user to save commands list
        save_commands_btn = QPushButton('Save List')
        save_commands_btn.setFixedWidth(70)
        save_commands_btn.clicked.connect(self.saveCommandsList)
        commands_hb.addWidget(save_commands_btn)
        
        #allow user to load commands list
        load_commands_btn = QPushButton('Load List')
        load_commands_btn.setFixedWidth(70)
        load_commands_btn.clicked.connect(self.loadCommandsList)
        commands_hb.addWidget(load_commands_btn)
                
        #create list of buttons to disable when in the middle of running commands
        self.buttons = [run_commands_btn, remove_last_btn, clear_all_btn]
        
        commands_hb.addStretch()
        main_vbox.addLayout(commands_hb)
        
        
        #connect currentChanged to a function so that the line edits move from autoscan to interpscan
        self.tabs.currentChanged.connect(self.moveScanInfo)
        
    def saveCommandsList(self):
        filename, ok = QInputDialog.getText(self, 'Commands List Filename', 'Enter filename for commands list:')
        
        if ok:
            f = open(filename + '.txt', 'w+')
            
            commands = self.command_display.text()
            commands = commands.lstrip('<b>Commands:</b><ol style="margin:0px;">').rstrip('</ol>')
            commands = commands.replace('<li>', '')
            
            commands = commands.split('</li>')
            commands[-1] = commands[-1].replace('</li','')
            f.write('Commands:\n')
            
            for i in range(len(commands)):
                f.write('{}. {}\n'.format(i+1, commands[i]))
                
            f.close()
            
    def loadCommandsList(self):
        file_info = QFileDialog.getOpenFileName(self, 'Open File')
        filename = file_info[0]
        f = open(filename, 'r+')
        
        for line in f.readlines():
            period_ind = line.find('.')
            command = line[period_ind + 2:]
            
            colon_ind = command.find(':')
            command_type = command[:colon_ind]
            command = command[colon_ind + 2:]
            
            vals = command.split(', ')
                        
            if command_type == 'Rotator':
                angle = float(vals[0][:-3])
                pause = int(vals[1].rstrip()[:-1])
                
                self.addRotatorCommand(angle, pause)
                
            elif command_type == 'Automatic Scan':
                dash_ind = vals[0].find('-')
                start = vals[0][:dash_ind]
                stop = vals[0][dash_ind + 1:-5]
                curr = vals[1][:-2]
                res = vals[2][:-5]
                pause = vals[3].rstrip()[:-3]
                
                self.addAutoScanCommand(start, stop, curr, res, pause)
                
            elif command_type == 'Set Temperature':
                temp = float(vals[0][:-1])
                pause = float(vals[1].rstrip()[:-1])
                
                self.temp_pause_sb.setValue(pause)
                self.addTempCommand(temp)
            
            elif command_type == 'Interpolation Scan':
                dash_ind = vals[0].find('-')
                start = vals[0][:dash_ind]
                stop = vals[0][dash_ind + 1:-5]
                power = vals[1][:-2]
                res = vals[2][:-5]
                pause = vals[3].rstrip()[:-3]
                
                self.addInterpScanCommand(start, stop, power, res, pause)
        
        f.close()
        
    def initAutoScanTab(self):
        #create tab
        autoscan_tab = QWidget()
        
        #create main grid to organize layout
        self.scan_grid = QGridLayout()
        self.scan_grid.setSpacing(10)
        autoscan_tab.setLayout(self.scan_grid)
                        
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
        
        self.scan_grid.addWidget(start_wnum,0,0)
        self.scan_grid.addWidget(self.start_wnum_le,0,1)
        self.scan_grid.addWidget(end_wnum,1,0)
        self.scan_grid.addWidget(self.end_wnum_le,1,1)
        self.scan_grid.addWidget(current,2,0)
        self.scan_grid.addWidget(self.current_le,2,1)
        self.scan_grid.addWidget(wnum_res,3,0)
        self.scan_grid.addWidget(self.wnum_res_le,3,1)
        self.scan_grid.addWidget(sc_pause,4,0)
        self.scan_grid.addWidget(self.sc_pause_le,4,1)
        
        #create button to add command
        add_command_btn = QPushButton('Add Command')
        add_command_btn.setFixedWidth(150)
        add_command_btn.clicked.connect(lambda: self.addAutoScanCommand(self.start_wnum_le.text(),
                self.end_wnum_le.text(), self.current_le.text(), self.wnum_res_le.text(), self.sc_pause_le.text()))
        
        add_command_vb = QVBoxLayout() #has add command button and stretch to fill the rest of the space
        add_command_vb.addWidget(add_command_btn, Qt.AlignLeft)
        add_command_vb.addStretch()
        
        
        self.scan_grid.addLayout(add_command_vb,5,0)
        
        
        
        self.tabs.addTab(autoscan_tab, 'Automatic Scan')
    
    def initInterpScanTab(self):
        #create tab
        interpscan_tab = QWidget()
        
        #create main grid to organize layout
        self.power_scan_grid = QGridLayout()
        self.power_scan_grid.setSpacing(10)
        interpscan_tab.setLayout(self.power_scan_grid)
                        
        #create labels and line edit widgets for start and end wavenumbers, current, wavenumber resolution, and scan pause
        start_wnum = QLabel('Start Wavenumber (cm^-1):')
        end_wnum = QLabel('End Wavenumber (cm^-1):')
        power = QLabel('Power (mW):')
        self.power_le = QLineEdit(self)
        self.power_le.setFixedWidth(70)
        wnum_res = QLabel('Wavenumber Resolution (cm^-1):')
        sc_pause = QLabel('Scan Pause (min)')
        
        self.power_scan_grid.addWidget(start_wnum,0,0)
        self.power_scan_grid.addWidget(end_wnum,1,0)
        self.power_scan_grid.addWidget(power,2,0)
        self.power_scan_grid.addWidget(self.power_le,2,1)
        self.power_scan_grid.addWidget(wnum_res,3,0)
        self.power_scan_grid.addWidget(sc_pause,4,0)
        
        #create button to add command
        add_command_btn = QPushButton('Add Command')
        add_command_btn.setFixedWidth(150)
        add_command_btn.clicked.connect(lambda: self.addInterpScanCommand(self.start_wnum_le.text(),
                self.end_wnum_le.text(), self.power_le.text(), self.wnum_res_le.text(), self.sc_pause_le.text()))
        
        add_command_vb = QVBoxLayout() #has add command button and stretch to fill the rest of the space
        add_command_vb.addWidget(add_command_btn, Qt.AlignLeft)
        add_command_vb.addStretch()
        
        
        self.power_scan_grid.addLayout(add_command_vb,5,0)
        
        
        self.tabs.addTab(interpscan_tab, 'Interpolation Scan')
    
    def initRotatorTab(self):
        #create tab
        rotator_tab = QWidget()
        
        #create main hbox and main vbox to organize layout
        main_hbox = QHBoxLayout()
        main_hbox.setSpacing(10)
        rotator_tab.setLayout(main_hbox)
        
        main_vbox = QVBoxLayout()
        
        #absolute position label
        pos = QLabel('Absolute Position (deg)')
        
        #absolute position spin box
        abs_pos_sb = QDoubleSpinBox()
        abs_pos_sb.setDecimals(4)
        abs_pos_sb.setRange(0, 340)
        
        pos_hb = QHBoxLayout()
        pos_hb.addWidget(pos)
        pos_hb.addWidget(abs_pos_sb)
        main_vbox.addLayout(pos_hb)
        
        #create button to add command
        add_command_btn = QPushButton('Add Command')
        add_command_btn.setFixedWidth(150)
        add_command_btn.clicked.connect(lambda: self.addRotatorCommand(abs_pos_sb.value(),self.pause_sb.value()))
        main_vbox.addWidget(add_command_btn, Qt.AlignLeft)
        
        or_lbl = QLabel('<b>OR</b>')
        main_vbox.addWidget(or_lbl,Qt.AlignCenter)
        
        #start position label
        start_pos = QLabel('Start Position (deg)')
        #start position spin box
        self.start_pos_sb = QDoubleSpinBox()
        self.start_pos_sb.setDecimals(4)
        self.start_pos_sb.setRange(0, 340)
        #start position hbox
        start_pos_hb = QHBoxLayout()
        start_pos_hb.addWidget(start_pos)
        start_pos_hb.addWidget(self.start_pos_sb)
        main_vbox.addLayout(start_pos_hb)
        
        
        #stop position label
        stop_pos = QLabel('Stop Position (deg)')
        #stop position spin box
        self.stop_pos_sb = QDoubleSpinBox()
        self.stop_pos_sb.setDecimals(4)
        self.stop_pos_sb.setRange(0, 340)
        #stop position hbox
        stop_pos_hb = QHBoxLayout()
        stop_pos_hb.addWidget(stop_pos)
        stop_pos_hb.addWidget(self.stop_pos_sb)
        main_vbox.addLayout(stop_pos_hb)
        
        #step label
        step = QLabel('Step (deg)')
        #step spin box
        self.step_sb = QDoubleSpinBox()
        self.step_sb.setDecimals(4)
        self.step_sb.setRange(0, 340)
        #start position hbox
        step_hb = QHBoxLayout()
        step_hb.addWidget(step)
        step_hb.addWidget(self.step_sb)
        main_vbox.addLayout(step_hb)
        
        #pause label
        pause = QLabel('Pause (sec)')
        #pause line edit
        self.pause_sb = QSpinBox()
        self.pause_sb.setMinimum(0)
        self.pause_sb.setFixedWidth(50)
        self.pause_sb.setAlignment(Qt.AlignTop)
        right_vbox = QVBoxLayout()
        right_vbox.addWidget(pause, Qt.AlignHCenter)
        right_vbox.addWidget(self.pause_sb, Qt.AlignHCenter)
        right_vbox.addStretch()
        
        add_commands_btn = QPushButton('Add Commands')
        add_commands_btn.setFixedWidth(150)
        main_vbox.addWidget(add_commands_btn, Qt.AlignLeft)
        add_commands_btn.clicked.connect(self.addRotatorCommands)
        
        main_vbox.addStretch()
        
        main_hbox.addLayout(main_vbox)
        main_hbox.addLayout(right_vbox, Qt.AlignCenter)
        
        self.tabs.addTab(rotator_tab, 'Rotator')
        
    
    def initTempTab(self):
        #create tab
        temp_tab = QWidget()
        
        #create main vbox to organize layout
        main_vbox = QVBoxLayout()
        main_vbox.setSpacing(10)
        temp_tab.setLayout(main_vbox)
        
        #give a note to the user that this will not cool down or warm up the cryostat automatically
        note = QLabel('Note: This command will not cool down or warm up the cryostat ' +
                      'automatically. It is recommended to cool down the cryostat to the ' +
                      'desired temperature before running all commands.')
        note.setWordWrap(True)
        main_vbox.addWidget(note)
        
        #allow user to input a temperature for the setpoint
        temp_lbl = QLabel('Temperature (K)')
        temp_sb = QDoubleSpinBox()
        temp_sb.setRange(3.2, 350)
        temp_sb.setDecimals(2)
        temp_sb.setValue(270.0)
        temp_sb.setToolTip('Temperature Set Point')
        
        temp_hb = QHBoxLayout()
        temp_hb.addWidget(temp_lbl)
        temp_hb.addWidget(temp_sb)
        main_vbox.addLayout(temp_hb)
        
        pause_lbl = QLabel('Pause (sec)')
        
        self.temp_pause_sb = QSpinBox()
        self.temp_pause_sb.setMinimum(0)
        self.temp_pause_sb.setFixedWidth(50)
        
        pause_hb = QHBoxLayout()
        pause_hb.addWidget(pause_lbl)
        pause_hb.addWidget(self.temp_pause_sb)
        
        main_vbox.addLayout(pause_hb)
        
        #create button to add command
        add_command_btn = QPushButton('Add Command')
        add_command_btn.setFixedWidth(150)
        add_command_btn.clicked.connect(lambda: self.addTempCommand(temp_sb.value()))
        main_vbox.addWidget(add_command_btn, Qt.AlignLeft)
        main_vbox.addStretch()
        
        self.tabs.addTab(temp_tab, 'Temperature Set Point')
        
    def addAutoScanCommand(self, start_wnum, end_wnum, current, res, pause):
        #create text for command and add it to display
        newText = self.command_display.text().replace('</ol>','')
        newText += '<li>Automatic Scan: {}-{}cm^-1, {}mA, {}cm^-1, {}min</li>'.format(start_wnum,
                                        end_wnum, current, res, pause)
        newText += '</ol>'
        self.command_display.setText(newText)
        
        #create actual command and append it to list of commands
        command = AutoScanCommand(self.main_window, start_wnum, end_wnum, current, res, pause)
        self.commands.append(command)
    
    def addInterpScanCommand(self, start_wnum, end_wnum, power, res, pause):
        #create text for command and add it to display
        newText = self.command_display.text().replace('</ol>','')
        newText += '<li>Interpolation Scan: {}-{}cm^-1, {}mW, {}cm^-1, {}min</li>'.format(start_wnum,
                                        end_wnum, power, res, pause)
        newText += '</ol>'
        self.command_display.setText(newText)
        
        #create actual command and append it to list of commands
        command = InterpScanCommand(self.main_window, start_wnum, end_wnum, power, res, pause)
        self.commands.append(command)
    
    def addRotatorCommand(self, angle, pause=0):
        #create text for command and add it to display
        newText = self.command_display.text().replace('</ol>','')
        newText += '<li>Rotator: {}deg, {}s</li>'.format(angle, pause)
        newText += '</ol>'
        self.command_display.setText(newText)
        
        #create actual command and append it to list of commands
        command = RotatorCommand(self.main_window, angle, pause)
        self.commands.append(command)
        
    def addRotatorCommands(self):
        startAngle = self.start_pos_sb.value()
        stopAngle = self.stop_pos_sb.value()
        step = self.step_sb.value()
        pause = self.pause_sb.value()
        
        if step == 0:
            QMessageBox.warning(self, 'Step Error', 'Step cannot be 0')
            return
        
        for angle in np.arange(startAngle, stopAngle + step, step):
            self.addRotatorCommand(angle, pause)
    
    def addTempCommand(self, temp):
        pause = self.temp_pause_sb.value()
        
        #create text for command and add it to display
        newText = self.command_display.text().replace('</ol>','')
        newText += '<li>Set Temperature: {}K, {}s</li>'.format(temp, pause)
        newText += '</ol>'
        self.command_display.setText(newText)
        
        #create actual command and append it to list of commands
        command = SetTemperatureCommand(self.main_window, temp, pause)
        self.commands.append(command)
        
        
    def moveScanInfo(self, index):
        '''Moves line edits from the autoscan tab to the interpscan tab'''
        if index == 0:
            self.scan_grid.addWidget(self.start_wnum_le,0,1)
            self.scan_grid.addWidget(self.end_wnum_le,1,1)
            self.current_le.setTabOrder(self.end_wnum_le, self.current_le)
            self.scan_grid.addWidget(self.current_le,2,1)
            self.current_le.setTabOrder(self.current_le, self.wnum_res_le)
            self.scan_grid.addWidget(self.wnum_res_le,3,1)
            self.scan_grid.addWidget(self.sc_pause_le,4,1)
            
        elif index == 1:
            self.power_scan_grid.addWidget(self.start_wnum_le,0,1)
            self.power_scan_grid.addWidget(self.end_wnum_le,1,1)
            self.power_le.setTabOrder(self.end_wnum_le, self.power_le)
            self.power_scan_grid.addWidget(self.power_le,2,1)
            self.power_le.setTabOrder(self.power_le, self.wnum_res_le)
            self.power_scan_grid.addWidget(self.wnum_res_le,3,1)
            self.power_scan_grid.addWidget(self.sc_pause_le,4,1)
            
            
    @pyqtSlot()
    def executeScan(self):
        #write info into automatic scan tab in qcl interface
        qcl_widget.writeAutoScanInfo(False, dialog=False) #equivalent to submit button (first arg is usually sent by signal when button is clicked)
        qcl_widget.startScan() #start scan (equivalent to start scan button)
        
        self.command_started.emit()
        
        
    @pyqtSlot()
    def emitCommandStarted(self):
        time.sleep(1) #1 second delay to make sure command starts
        instruments.zi_widget.pausePlot() #stop recording data while temperature or rotator is changed
        self.command_started.emit()
        
        
    @pyqtSlot() 
    def resumePlot(self):
        instruments.zi_widget.resumePlot()
        
    
    def runCommands(self):
#        self.threads = [] #list of threads
        #create a copy of self.commands called self.commands_copy
        self.commands_copy = [command.copy() for command in self.commands]
        
        #disable buttons until commands are finished
        for button in self.buttons:
            button.setEnabled(False)
        
        for i in range(len(self.commands)):
            #append a new thread to self.threads, then move the command to that thread
            #when the command is finished (emits its finished signal), quit the thread
            command = self.commands[i]
#            self.threads.append(QThread())
#            command.moveToThread(self.threads[i])
#            command.finished.connect(self.threads[i].quit, Qt.DirectConnection)
            
            #connect commands to functions which will emit signals back to the command object
            #to tell the program that the command has been executed so that the program can
            #start checking when the command is finished
#            try: #allows program to do a scan if needed by the command
#                command.scan_ready.connect(self.executeScan)
#            except AttributeError:
#                pass
#            try:
#                command.rotator_ready.connect(self.emitCommandStarted)
#                command.resume_plot.connect(self.resumePlot)
#            except AttributeError:
#                pass
#            try:
#                command.cryostat_ready.connect(self.emitCommandStarted)
#                command.resume_plot.connect(self.resumePlot)
#            except AttributeError:
#                pass
            
            
            #for each command, when the thread which has the command is started, the command will
            #execute using the execute function specified in its class
            #when the thread is finished, call the function runNextCommand to run the command in
            #the next thread in self.threads
#            self.threads[i].started.connect(command.execute)
#            self.threads[i].finished.connect(self.runNextCommand, Qt.DirectConnection)
            
            #signal so that while loop starts after the command has actually started
            #starts after scan_ready, rotator_ready, or crysotat_ready is emitted
#            self.command_started.connect(command.checkIfDone)
        
        
        
        #run first command
        self.i = -1
        self.runNextCommand()
        
    @pyqtSlot()
    def runNextCommand(self):
        self.i += 1
        
        if self.i < len(self.commands): #call next command if there is one
            self.thread = QThread()
            self.commands[self.i].moveToThread(self.thread)
            self.commands[self.i].finished.connect(self.thread.quit)
            
            
            #connect commands to functions which will emit signals back to the command object
            #to tell the program that the command has been executed so that the program can
            #start checking when the command is finished
            try: #allows program to do a scan if needed by the command
                self.commands[self.i].scan_ready.connect(self.executeScan)
            except AttributeError:
                pass
            try:
                self.commands[self.i].rotator_ready.connect(self.emitCommandStarted)
                self.commands[self.i].resume_plot.connect(self.resumePlot)
            except AttributeError:
                pass
            try:
                self.commands[self.i].cryostat_ready.connect(self.emitCommandStarted)
                self.commands[self.i].resume_plot.connect(self.resumePlot)
            except AttributeError:
                pass
            
            #when the thread (which contains the command) is started, the command will
            #execute using the execute function specified in its class
            #when the thread is finished, call the function runNextCommand to run the command in
            #the next thread in self.threads
            self.thread.started.connect(self.commands[self.i].execute)
            self.thread.finished.connect(self.runNextCommand)
            
            #signal so that while loop starts after the command has actually started
            #starts after scan_ready, rotator_ready, or crysotat_ready is emitted
            self.command_started.connect(self.commands[self.i].checkIfDone)
            
            self.thread.start()
            
            if self.i > 0:
                data_recording_widget.recordData(dialog=False)
        else: #otherwise clear self.threads and show that commands are finished
#            self.threads.clear()
            self.commands = self.commands_copy #set self.commands to commands_copy because commands are now in different threads
            for button in self.buttons: #enable all buttons again
                button.setEnabled(True)
            QMessageBox.information(self, 'Run Commands', 'Finished running commands.')
            data_recording_widget.recordData(dialog=True)

            
            
    def removeLast(self):
        try:
            #remove last command from list of commands by popping
            self.commands.pop()
            
            #update the display
            oldText = self.command_display.text()
            newText = oldText[:oldText.rfind('<li>')] + '</ol>'
            self.command_display.setText(newText)
        except IndexError: #do nothing if list was already empty
            pass
        
    
    def clearAll(self):
        #clear the list of commands
        self.commands.clear()
        
        #reset text of display to an empty list
        self.command_display.setText('<b>Commands:</b><ol style="margin:0px;"></ol>')
        
            
        

      
class AutoScanCommand(QObject):
    finished = pyqtSignal()
    scan_ready = pyqtSignal()
    
    def __init__(self, main_window, start_wnum, end_wnum, current, res, pause):
        super().__init__()
        self.main_window = main_window
        self.start_wnum = start_wnum
        self.end_wnum = end_wnum
        self.current = current
        self.res = res
        self.pause = pause
        
    def copy(self):
        return AutoScanCommand(self.main_window, self.start_wnum, self.end_wnum, self.current,
                               self.res, self.pause)
        
    def execute(self):
        try:
            qcl_widget.start_wnum_le.setText(self.start_wnum)
            qcl_widget.end_wnum_le.setText(self.end_wnum)
            qcl_widget.current_le.setText(self.current)
            qcl_widget.wnum_res_le.setText(self.res)
            qcl_widget.sc_pause_le.setText(self.pause)
            qcl_widget.scan_constant = 'current'
            self.scan_ready.emit()
            
            
        except Exception as e:
            QMessageBox.warning(self.main_window, 'Error', str(e) + '\nMake sure you are connected to the QCL')
    
    @pyqtSlot()
    def checkIfDone(self):
        try:
            qcl_widget.scan_in_progress = True #set scan_in_progress to True to avoid while loop ending too soon
            while True:
                if qcl_widget.scan_in_progress == False:
                    self.finished.emit()
                    break
            
        except Exception as e:
            QMessageBox.warning(self.main_window, 'Error', str(e) + '\nMake sure you are connected to the QCL')



class InterpScanCommand(QObject):
    finished = pyqtSignal()
    scan_ready = pyqtSignal()

    
    def __init__(self, main_window, start_wnum, end_wnum, power, res, pause):
        super().__init__()
        self.main_window = main_window
        self.start_wnum = start_wnum
        self.end_wnum = end_wnum
        self.power = power
        self.res = res
        self.pause = pause
        
    def copy(self):
        return InterpScanCommand(self.main_window, self.start_wnum, self.end_wnum, self.power,
                                 self.res, self.pause)
        
    def execute(self):
        try:
            qcl_widget.start_wnum_le.setText(self.start_wnum)
            qcl_widget.end_wnum_le.setText(self.end_wnum)
            qcl_widget.power_le.setText(self.power)
            qcl_widget.wnum_res_le.setText(self.res)
            qcl_widget.sc_pause_le.setText(self.pause)
            qcl_widget.scan_constant = 'power'
            self.scan_ready.emit()
            
            
        except Exception as e:
            QMessageBox.warning(self.main_window, 'Error', str(e) + '\nMake sure you are connected to the QCL')

    @pyqtSlot()
    def checkIfDone(self):
        try:
            qcl_widget.scan_in_progress = True #set scan_in_progress to True to avoid while loop ending too soon
            while True:
                    if qcl_widget.scan_in_progress == False:
                        self.finished.emit()
                        break
                
        except Exception as e:
            QMessageBox.warning(self.main_window, 'Error', str(e) + '\nMake sure you are connected to the QCL')


class RotatorCommand(QObject):
    finished = pyqtSignal()
    rotator_ready = pyqtSignal()
    resume_plot = pyqtSignal()
    
    def __init__(self, main_window, angle, pause):
        super().__init__()
        self.main_window = main_window
        self.angle = angle
        self.pause = pause        
        
    def copy(self):
        return RotatorCommand(self.main_window, self.angle, self.pause)
        
    def execute(self):
        try:
            rotr_widget.abs_pos_sb.setValue(self.angle)
            rotr_widget.abs_pos_sb.editingFinished.emit()
            
            self.rotator_ready.emit()
                
        except Exception as e:
            QMessageBox.warning(self.main_window, 'Error', 'Error: ' + str(e) + 
                                '\nMake sure rotator is connected and enabled.')
            
    @pyqtSlot()    
    def checkIfDone(self):
        try:
             while True:
                    ctrl_state = rotr_widget.controller_states[instruments.rotr.query('1mm?')[3:].strip()]
                    if ctrl_state.split(' ')[0] == 'READY':
                        self.resume_plot.emit()
                        QTest.qWait(self.pause*1000)
                        self.finished.emit()
                        break
                
        except Exception as e:
            QMessageBox.warning(self.main_window, 'Error', 'Error: ' + str(e) + 
                                '\nMake sure rotator is connected and enabled.')



class SetTemperatureCommand(QObject):
    finished = pyqtSignal()
    cryostat_ready = pyqtSignal()
    resume_plot = pyqtSignal()
    
    def __init__(self, main_window, temp, pause):
        super().__init__()
        self.main_window = main_window
        self.temp = temp
        self.pause = pause
        
    def copy(self):
        return SetTemperatureCommand(self.main_window, self.temp, self.pause)
        
    def execute(self):
        try:
            if instruments.cryostat is None:
                QMessageBox.warning(self.main_window, 'Connection Error', 'Not connected to cryostat.')
                return
            instruments.cryostat_widget.temp_sb.setValue(self.temp)
            instruments.cryostat_widget.setTemp()
            
            self.cryostat_ready.emit()
                
        except Exception as e:
            QMessageBox.warning(self.main_window, 'Error', 'Error: ' + str(e))
      
    @pyqtSlot()
    def checkIfDone(self):
        #create timer to check temperature every 3 seconds because socket will timeout
        #if there are too many requests
        self.timer = QTimer()
        self.timer.timeout.connect(self.delayedCheckIfDone)
        self.timer.start(3000)
            
    def delayedCheckIfDone(self):
        try:
            current_temp = instruments.cryostat_widget.temp_data[0][-1]
            stability = instruments.cryostat_widget.stability_data[-1]

            if current_temp == -0.1:
                time.sleep(1)
            
            if round(current_temp, 2)==round(self.temp,2) and stability < 150 and stability > 0:
                self.resume_plot.emit()
                QTest.qWait(self.pause*1000)
                self.finished.emit()
                
        except Exception as e:
            QMessageBox.warning(self.main_window, 'Error', 'Error: ' + str(e))
            
        except socket.timeout:
            time.sleep(1)








class DataRecordingWidget(QFrame):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.initUI()
        self.setFixedHeight(230)
        
    def initUI(self):
        #create main grid to organize layout
        main_grid = QGridLayout()
        main_grid.setSpacing(10)
        self.setLayout(main_grid)
        
        #data recording text label
        data_recording_lbl = QLabel('<b>Data Recording</b>')
        main_grid.addWidget(data_recording_lbl,0,0,1,3)
        
        #qcl data recording
        self.qcl_lbl = QLabel('QCL')
        self.qcl_cb = QCheckBox()
        self.qcl_le = QLineEdit()
        self.qcl_le.setPlaceholderText('File name')
        main_grid.addWidget(self.qcl_lbl,1,0)
        main_grid.addWidget(self.qcl_cb,1,1)
        main_grid.addWidget(self.qcl_le,1,2)
        
        #zurich oscope data recording
        self.zi_lbl = QLabel('ZI Oscope')
        self.zi_cb = QCheckBox()
        self.zi_le = QLineEdit()
        self.zi_le.setPlaceholderText('File name')
        main_grid.addWidget(self.zi_lbl,2,0)
        main_grid.addWidget(self.zi_cb,2,1)
        main_grid.addWidget(self.zi_le,2,2)
        
        #montana cryostat data recording
        self.cryostat_lbl = QLabel('Crysotat')
        self.cryostat_cb = QCheckBox()
        self.cryostat_le = QLineEdit()
        self.cryostat_le.setPlaceholderText('File name')
        main_grid.addWidget(self.cryostat_lbl,3,0)
        main_grid.addWidget(self.cryostat_cb,3,1)
        main_grid.addWidget(self.cryostat_le,3,2)
        
        #rotator data recording
        self.rotator_lbl = QLabel('Rotator')
        self.rotator_cb = QCheckBox()
        self.rotator_le = QLineEdit()
        self.rotator_le.setPlaceholderText('File name')
        main_grid.addWidget(self.rotator_lbl,4,0)
        main_grid.addWidget(self.rotator_cb,4,1)
        main_grid.addWidget(self.rotator_le,4,2)
        
        #combined data recording
        self.combined_lbl = QLabel('Combined')
        self.combined_cb = QCheckBox()
        self.combined_le = QLineEdit()
        self.combined_le.setPlaceholderText('File name')
        main_grid.addWidget(self.combined_lbl,5,0)
        main_grid.addWidget(self.combined_cb,5,1)
        main_grid.addWidget(self.combined_le,5,2)
        
        
        #save data button
        save_data_btn = QPushButton('Save Data')
        save_data_btn.setFixedWidth(150)
        save_data_btn.clicked.connect(self.recordData)
        main_grid.addWidget(save_data_btn,6,0,1,3,Qt.AlignLeft)
        
        spacer = QVBoxLayout()
        spacer.addStretch()
        main_grid.addLayout(spacer,7,0,1,3)
        
        
    def recordData(self, dialog=True):
        '''Record data when main window is closed'''
        data_recorded = False
        
        if self.qcl_cb.isChecked():
            self.recordQCLData()
            data_recorded = True
        if self.zi_cb.isChecked():
            self.recordZIData()
            data_recorded = True
        if self.cryostat_cb.isChecked():
            self.recordCryoData()
            data_recorded = True
        if self.rotator_cb.isChecked():
            self.recordRotatorData()
            data_recorded = True
        if self.combined_cb.isChecked():
            self.recordCombinedData()
            data_recorded = True
            
        if dialog and data_recorded:
            QMessageBox.information(self,'Confirmation','The data has been saved')
        
    def recordQCLData(self):
        #get filename from line edit and add .txt extension, then create file
        filename = self.qcl_le.text() + '.txt'
        f = open(filename, 'w+')
        
        #write header for the file
        f.write('QCL Wavenumber(cm^-1),QCL Current(mA),PEM Wavelength(nm),PEM Wavenumber(cm^-1)\n')
        
        #get data from QCL widget
        qcl_wnum = qcl_widget.qcl_wnum_data
        qcl_curr = qcl_widget.qcl_curr_data
        pem_wlength = qcl_widget.pem_wlength_data
        pem_wnum = qcl_widget.pem_wnum_data
        
        #write each row of data
        for data in zip(qcl_wnum,qcl_curr,pem_wlength,pem_wnum):
            f.write('{},{},{},{}\n'.format(data[0],data[1],data[2],data[3]))
            
        #close file
        f.close()
        
        #add checkmark to qcl label to show that data has been recorded
        self.qcl_lbl.setText(u'QCL \u2705')
    
    def recordZIData(self):
        #get filename from line edit and add .txt extension, then create file
        filename = self.zi_le.text() + '.txt'
        f = open(filename, 'w+')
        
        #write header for the file
        f.write('Timestamp,V0,V2,V3\n')
        
        #get data from ZI widget
        time_data = instruments.zi_widget.time_data[0] #might have to add [0]
        volt_data = instruments.zi_widget.volt_data
        
        #write each row of data
        for data in zip(time_data, volt_data[0], volt_data[1], volt_data[2]):
            f.write('{:.4f},{:.8e},{:.8e},{:.8e}\n'.format(data[0],data[1],data[2],data[3]))
            
        #close file
        f.close()
        
        #add checkmark to zi label to show that data has been recorded
        self.zi_lbl.setText(u'ZI Oscope \u2705')
        
        
    
    def recordCryoData(self):
        #get filename from line edit and add .txt extension, then create file
        filename = self.cryostat_le.text() + '.txt'
        f = open(filename, 'w+')
                    
        #write header for the file
        f.write('Time(s),Platform Temperature(K),Sample Temperature(K),User Temperature(K)\n')
        
        #get data from crysotat widget
        time_data = instruments.cryostat_widget.time_data
        temp_data = instruments.cryostat_widget.temp_data
        
        #write each row of data
        for data in zip(time_data, temp_data[0], temp_data[1], temp_data[2]):
            f.write('{},{},{},{}\n'.format(data[0],data[1],data[2],data[3]))
            
        #close file
        f.close()
            
        #add checkmark to cryostat label to show that data has been recorded
        self.cryostat_lbl.setText(u'Cryostat \u2705')
        
    def recordRotatorData(self):
        #get filename from line edit and add .txt extension, then create file
        filename = self.rotator_le.text() + '.txt'
        f = open(filename, 'w+')
            
        #write header for the file
        f.write('Angle(deg)\n')
        
        #get data from crysotat widget
        angle_data = rotr_widget.angle_data
        
        #write each row of data
        for angle in angle_data:
            f.write('{}\n'.format(angle))
            
        #close file
        f.close()
            
        #add checkmark to cryostat label to show that data has been recorded
        self.rotator_lbl.setText(u'Rotator \u2705')
        
    def recordCombinedData(self):
        #get filename from line edit and add .txt extension, then create file
        filename = self.combined_le.text() + '.txt'
        f = open(filename, 'w+')
            
        #write header for the file
        f.write('Time(s),V0,V2,V3,Platform Temperature(K),Sample Temperature(K)' + 
                ',User Temperature(K),QCL Wavenumber(cm^-1)\n')
        
        data_length = instruments.zi_widget.data_length
        
        #get data from crysotat widget
        time_data = instruments.zi_widget.time_data[0]
        volt_data = instruments.zi_widget.volt_data
        temp_data = instruments.zi_widget.temp_data
        qcl_wnum_data = instruments.zi_widget.qcl_wnum
        #rotator_data = instruments.zi_widget.   #20190920 add rotator to saved data
#        qcl_curr_data = instruments.zi_widget.qcl_curr
#        pem_wlength_data = instruments.zi_widget.pem_wlength
#        pem_wnum_data = instruments.zi_widget.pem_wnum
        
        
        #write each row of data
        for i,data in enumerate(zip(time_data, volt_data[0], volt_data[1], volt_data[2])):
            plat_temp = temp_data[0][i//data_length]
            samp_temp = temp_data[1][i//data_length]
            user_temp = temp_data[2][i//data_length]
            qcl_wnum = qcl_wnum_data[i//data_length]
#            qcl_curr = qcl_curr_data[i//data_length]
#            pem_wlength = pem_wlength_data[i//data_length]
#            pem_wnum = pem_wnum_data[i//data_length]
            f.write('{:.4f},{:.8e},{:.8e},{:.8e},{:.2f},{:.2f},{:.2f},{:.1f}\n'.format(data[0],data[1],data[2],
                    data[3],plat_temp,samp_temp,user_temp,qcl_wnum))
            
        #close file
        f.close()
            
        #add checkmark to cryostat label to show that data has been recorded
        self.combined_lbl.setText(u'Connected \u2705')
    
    
        
        
        
















#from https://gist.github.com/dennis-tra/994a65d6165a328d4eabaadbaedac2cc
class QDoubleSlider(QSlider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.decimals = 4
        self._max_int = 10 ** self.decimals

        super().setMinimum(0)
        super().setMaximum(self._max_int)

        self._min_value = 0.0
        self._max_value = 1.0

    @property
    def _value_range(self):
        return self._max_value - self._min_value

    def value(self):
        return float(super().value()) / self._max_int * self._value_range + self._min_value

    def setValue(self, value):
        super().setValue(int((value - self._min_value) / self._value_range * self._max_int))

    def setMinimum(self, value):
        if value > self._max_value:
            raise ValueError("Minimum limit cannot be higher than maximum")

        self._min_value = value
        self.setValue(self.value())

    def setMaximum(self, value):
        if value < self._min_value:
            raise ValueError("Minimum limit cannot be higher than maximum")

        self._max_value = value
        self.setValue(self.value())
        
    def setRange(self, minval, maxval):
        self.setMinimum(minval)
        self.setMaximum(maxval)

    def minimum(self):
        return self._min_value

    def maximum(self):
        return self._max_value
    
    def setDecimals(self, value):
        if type(value != int):
            raise ValueError('Number of decimals must be an int')
        else:
            self.decimals = value






#from https://github.com/nlamprian/pyqt5-led-indicator-widget/blob/master/LedIndicatorWidget.py
class QLedIndicator(QAbstractButton):
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

    def changeColor(self, color):
        '''change color by inputting a string only for red, orange, and green'''
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
        elif color.lower() == 'green':
            self.on_color_1 = QColor(0, 255, 0)
            self.on_color_2 = QColor(0, 192, 0)
            self.off_color_1 = QColor(0, 28, 0)
            self.off_color_2 = QColor(0, 128, 0)
            
        self.update()

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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()    
    sys.exit(app.exec_())