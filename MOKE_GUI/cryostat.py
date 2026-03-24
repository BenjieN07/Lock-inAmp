#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 20 10:46:53 2018

@author: Sivan
"""

import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import instruments
import socket
import os
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import (NavigationToolbar2QT as NavigationToolbar)
import matplotlib.pyplot as plt
import time


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        #set the size and title of the window
        self.setGeometry(300, 300, 500, 600)
        self.setWindowTitle('Cryostat')
        self.show()
        
        instruments.cryostat_widget = Cryostat(self)
        self.setCentralWidget(instruments.cryostat_widget)
        
        
class Cryostat(QFrame):
    def __init__(self, main_window):
        super().__init__()
        
        self.main_window = main_window
        self.initUI()
        
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
        stop_exec_btn.clicked.connect(self.closeEvent)
        
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
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.fig.subplots_adjust(top=0.883,bottom=0.194,left=0.138,right=0.946,
                                hspace=0.2,wspace=0.2) #tight_layout doesn't work
        
        main_grid.addWidget(self.toolbar,3,0,1,2)
        main_grid.addWidget(self.canvas,4,0,1,2)
        
        
        #add label, checkbox, and line edit to allow user to record data before closing
        record_data_lbl = QLabel('Record data before closing?')
        self.record_data = QCheckBox()
        self.file_name_le = QLineEdit()
        self.file_name_le.setPlaceholderText('file_name')
        data_recording_hbox = QHBoxLayout()
        data_recording_hbox.addWidget(record_data_lbl)
        data_recording_hbox.addWidget(self.record_data)
        data_recording_hbox.addWidget(self.file_name_le)
        data_recording_hbox.addStretch()
        main_grid.addLayout(data_recording_hbox,5,0,1,2)
        
        
    def connectInstrument(self):
        '''connect with a TCP/IP connection using the user entered IP address and 7773 as the port'''
        TCP_IP = self.ip_le.text()
        TCP_PORT = 7773
        self.BUFFER_SIZE = 80
        
        if instruments.cryostat is None:
            instruments.cryostat = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            instruments.cryostat.settimeout(5) #set timeout to 5 seconds by default
            
            try:
                instruments.cryostat.connect((TCP_IP, TCP_PORT))
            except: #if no connection is establish, display error and exit function
                QMessageBox.warning(self, 'Connection Error', 'Could not establish connection with Fusion computer')
                instruments.cryostat = None
                return
            
            #once a connection is established, disable user from changing the ip address
            self.ip_le.setText(self.ip_le.text() + ' (Connected)')
            self.ip_le.setEnabled(False)
        
        #set timer to update data table once every second
        self.timer = QTimer()
        self.timer.timeout.connect(self.displayData)
        self.timer.start(1000)
        
        self.startPlot()
        
    def startPlot(self):
        #create  data lists and set timer to update plot once every second
        self.time_data = list()
        #store first time value
        self.start_time = time.time()
        self.time_data.append(0.0) #set start_time as 0
        self.temp_data = [[], [], []]
        #store first temperature values
        self.temp_data[0].append(float(self.getPlatformTemperature()))
        self.temp_data[1].append(float(self.getSampleTemperature()))
        self.temp_data[2].append(float(self.getUserTemperature()))
        #create list stability data to keep track of stability in combined interface
        self.stability_data = []
        self.stability_data.append(float(self.getPlatformStability()))
        #set timer
        self.plotTimer = QTimer()
        self.plotTimer.timeout.connect(self.plotData)
        self.plotTimer.start(1000)
            
    def warmUp(self):
        try:
            instruments.cryostat.send('03SWU'.encode())
            response = instruments.cryostat.recv(self.BUFFER_SIZE).decode()
            if response != '02OK':
                raise ValueError(response)
        except AttributeError:
            QMessageBox.warning(self, 'Missing Instrument', 'Must connect to cryostat before ' +
                                'starting warm up.')
        except ValueError as e:
            QMessageBox.warning(self, 'Error', str(e)[2:])
        except:
            QMessageBox.warning(self, 'Error', 'Could not warm up instrument. Try resetting ' + 
                                'connection from Fusion computer.')
    
    def coolDown(self):
        try:
            instruments.cryostat.send('03SCD'.encode())
            response = instruments.cryostat.recv(self.BUFFER_SIZE).decode()
            if response != '02OK':
                raise ValueError(response)
            else:
                QMessageBox.information(self, 'Cooling Down', 'For temperatures above 30K, the '+
                                        'Montana Fusion cools down to 30K first to establish a vacuum.')
        except AttributeError:
            QMessageBox.warning(self, 'Missing Instrument', 'Must connect to cryostat before ' +
                                'starting cool down.')
        except ValueError as e:
            QMessageBox.warning(self, 'Error', str(e)[2:])
        except:
            QMessageBox.warning(self, 'Error', 'Could not cool downinstrument. Try resetting ' + 
                                'connection from Fusion computer.')
    
    def standby(self):
        try:
            instruments.cryostat.send('03SSB'.encode())
            response = instruments.cryostat.recv(self.BUFFER_SIZE).decode()
            if response != '02OK':
                raise ValueError(response)
        except AttributeError:
            QMessageBox.warning(self, 'Missing Instrument', 'Must connect to cryostat before ' +
                                'starting standby.')
        except ValueError as e:
            QMessageBox.warning(self, 'Error', str(e)[2:])
        except:
            QMessageBox.warning(self, 'Error', 'Could not put instrument on standby. Try resetting ' + 
                                'connection from Fusion computer.')
    
    def stop(self):
        try:
            instruments.cryostat.send('03STP'.encode())
            response = instruments.cryostat.recv(self.BUFFER_SIZE).decode()
            if response != '02OK':
                raise ValueError(response)
        except AttributeError:
            QMessageBox.warning(self, 'Missing Instrument', 'Must connect to cryostat before ' +
                                'stopping.')
        except ValueError as e:
            QMessageBox.warning(self, 'Error', str(e)[2:])
        except:
            QMessageBox.warning(self, 'Error', 'Could not stop current process. Try resetting ' + 
                                'connection from Fusion computer.')
    
    def setTemp(self):
        try:
            command = 'STSP' + str(self.temp_sb.value())
            length = len(command)
            if length < 10:
                command = '0' + str(length) + command
            else:
                command = str(length) + command
            
            instruments.cryostat.send(command.encode())
            response = instruments.cryostat.recv(self.BUFFER_SIZE).decode()
            if response[2:4] != 'OK':
                raise ValueError(response)
        except AttributeError:
            QMessageBox.warning(self, 'Missing Instrument', 'Must connect to cryostat before ' +
                                'starting warm up.')
        except ValueError as e:
            QMessageBox.warning(self, 'Error', str(e)[2:])
        except:
            QMessageBox.warning(self, 'Error', 'Could not set temperature point. Try resetting ' + 
                                'connection from Fusion computer.')

    def getPlatformTemperature(self):
        try:
            instruments.cryostat.send('03GPT'.encode())
            response = instruments.cryostat.recv(self.BUFFER_SIZE).decode()
            return response[2:]
        except AttributeError:
            QMessageBox.warning(self, 'Missing Instrument', 'Cannot get data because ' + 
                                 'cryostat is not yet connected')
        except:
            QMessageBox.warning(self, 'Error', 'Could not get data. Try to restart connection from ' +
                                'Fusion computer(may be timeout error)')
            
    def getPlatformStability(self):
        try:
            instruments.cryostat.send('03GPS'.encode())
            response = instruments.cryostat.recv(self.BUFFER_SIZE).decode()
            return str(round(float(response[2:]) * 1000, 2)) #multiply by 1000 to convert K to mK
        except AttributeError:
            QMessageBox.warning(self, 'Missing Instrument', 'Cannot get data because ' + 
                                 'cryostat is not yet connected')
        except:
            QMessageBox.warning(self, 'Error', 'Could not get data. Try to restart connection from ' +
                                'Fusion computer(may be timeout error)')

    def getTemperatureSetPoint(self):
        try:
            instruments.cryostat.send('04GTSP'.encode())
            response = instruments.cryostat.recv(self.BUFFER_SIZE).decode()
            return response[2:]
        except AttributeError:
            QMessageBox.warning(self, 'Missing Instrument', 'Cannot get data because ' + 
                                 'cryostat is not yet connected')
        except:
            QMessageBox.warning(self, 'Error', 'Could not get data. Try to restart connection from ' +
                                'Fusion computer(may be timeout error)')
    
    def getPlatformHeaterPower(self):
        try:
            instruments.cryostat.send('04GPHP'.encode())
            response = instruments.cryostat.recv(self.BUFFER_SIZE).decode()
            return response[2:]
        except AttributeError:
            QMessageBox.warning(self, 'Missing Instrument', 'Cannot get data because ' + 
                                 'cryostat is not yet connected')
        except:
            QMessageBox.warning(self, 'Error', 'Could not get data. Try to restart connection from ' +
                                'Fusion computer(may be timeout error)')

    def getSampleTemperature(self):
        try:
            instruments.cryostat.send('03GST'.encode())
            response = instruments.cryostat.recv(self.BUFFER_SIZE).decode()
            return response[2:]
        except AttributeError:
            QMessageBox.warning(self, 'Missing Instrument', 'Cannot get data because ' + 
                                 'cryostat is not yet connected')
        except:
            QMessageBox.warning(self, 'Error', 'Could not get data. Try to restart connection from ' +
                                'Fusion computer(may be timeout error)')
    
    def getSampleStability(self):
        try:
            instruments.cryostat.send('03GSS'.encode())
            response = instruments.cryostat.recv(self.BUFFER_SIZE).decode()
            return response[2:]
        except AttributeError:
            QMessageBox.warning(self, 'Missing Instrument', 'Cannot get data because ' + 
                                 'cryostat is not yet connected')
        except:
            QMessageBox.warning(self, 'Error', 'Could not get data. Try to restart connection from ' +
                                'Fusion computer(may be timeout error)')
    
    def getUserTemperature(self):
        try:
            instruments.cryostat.send('03GUT'.encode())
            response = instruments.cryostat.recv(self.BUFFER_SIZE).decode()
            return response[2:]
        except AttributeError:
            QMessageBox.warning(self, 'Missing Instrument', 'Cannot get data because ' + 
                                 'cryostat is not yet connected')
        except:
            QMessageBox.warning(self, 'Error', 'Could not get data. Try to restart connection from ' +
                                'Fusion computer(may be timeout error)')
    
    def getUserStability(self):
        try:
            instruments.cryostat.send('03GUS'.encode())
            response = instruments.cryostat.recv(self.BUFFER_SIZE).decode()
            return response[2:]
        except AttributeError:
            QMessageBox.warning(self, 'Missing Instrument', 'Cannot get data because ' + 
                                 'cryostat is not yet connected')
        except:
            QMessageBox.warning(self, 'Error', 'Could not get data. Try to restart connection from ' +
                                'Fusion computer(may be timeout error)')
    
    def displayData(self, empty=False):
        '''Updates table to display correct data'''
        try:
            if not empty:
                platform_dat = (self.getPlatformTemperature(), self.getPlatformStability(),
                                self.getTemperatureSetPoint(), self.getPlatformHeaterPower())
                sample_dat = (self.getSampleTemperature(), self.getSampleStability())
                user_dat = (self.getUserTemperature(), self.getUserStability())
            else:
                platform_dat = ('', '', '', '')
                sample_dat = ('', '')
                user_dat = ('', '')
        except:
            QMessageBox.warning(self, 'Data retrieval error', 'Could not retrieve data for the table.')
            return
        
        #make table string using rich text/html (string formatting does not work in QLabel)
        table = '<style>th,td{padding:0px 10px}td{text-align:right}</style>'
        table += '<table><thead><tr><th>{}</th><th>{}</th><th>{}</th><th>{}</th><th>{}</th></tr></thead>'.format('',
                                   'Temperature', 'Stability', 'Set Point', 'Heater Power')
        table += '<tbody><tr><td style="text-align:left"><b>{}</b></td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format('Platform',
                                 platform_dat[0]+'K',platform_dat[1]+'mK',platform_dat[2]+'K',platform_dat[3]+'W')
        table += '<tr><td style="text-align:left"><b>{}</b></td><td>{}</td><td>{}</td></tr>'.format('Sample',sample_dat[0]+'K',sample_dat[1]+'mK')
        table += '<tr><td style="text-align:left"><b>{}</b></td><td>{}</td><td>{}</td></tr></tbody></table>'.format('User',user_dat[0]+'K',user_dat[1]+'mK')
        
        #update table
        self.data_table.setText(table)
        
    def plotData(self):
        '''Plots temperature vs. time'''
        #append time to time_data then update x axis end labels
        self.time_data.append(time.time() - self.start_time)
        
        #append temperature data to each list within the 2d temp_data list
        self.temp_data[0].append(float(self.getPlatformTemperature()))
        self.temp_data[1].append(float(self.getSampleTemperature()))
        self.temp_data[2].append(float(self.getUserTemperature()))
        
        #append stabity data to list
        self.stability_data.append(float(self.getPlatformStability()))
        
        #clear previous plot and replot the data from last 20000 data points (should be a little over 5 hours)
        self.ax.clear()
        self.ax.plot(self.time_data[-20000:], self.temp_data[0][-20000:], label="Platform")
        self.ax.plot(self.time_data[-20000:], self.temp_data[1][-20000:], label="Sample")
        self.ax.plot(self.time_data[-20000:], self.temp_data[2][-20000:], label="User")
        
        #change x and y labels, change x ticks to only show first and last one, and add legend
        self.ax.set_xlabel(r'Time ($s$)')
        self.ax.set_ylabel(r'Temperature ($K$)')
        self.ax.set_title('Temperature vs. Time')
        self.ax.legend()
        self.fig.tight_layout()
        self.canvas.draw()
    
    def recordData(self):
        '''Record data in a .txt file using a comma to separate values'''
        file_name = self.file_name_le.text().rstrip('.txt')
        if file_name == '':
            file_name, ok = QInputDialog.getText(self, 'File Name Input', 'File name empty, please enter:')
            
            if not ok: #if user pressed cancel, don't record the data
                return

        try:
            f = open(file_name + '.txt', 'w+')
        except:
            QMessageBox.warning(self, 'File Name Error', 'Invalid file name')
            return
        f.write('Time(s), Platform Temperature(K), Sample Temperature(K), User Temperature(K)\n')
        f.close()
        
        f = open(file_name + '.txt', 'a+')
        for data in zip(self.time_data, self.temp_data[0], self.temp_data[1], self.temp_data[2]):
            f.write(str(data)[1:-1] + '\n')
        f.close()
        
    def closeEvent(self, e):
        try:
            self.timer.timeout.disconnect()
            self.plotTimer.timeout.disconnect()
            instruments.cryostat.close()
        except AttributeError:
            pass
        except Exception as e:
            QMessageBox.warning(self, 'Connection Error', 'There was an error closing the ' + 
                                'connection with the Fusion computer')
            print(str(e))
        
        if self.record_data.isChecked(): #if user wants to record data before closing
            self.recordData()
        
        self.main_window.close()
        


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())
        