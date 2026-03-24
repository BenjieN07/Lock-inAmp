#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 10 13:42:35 2018

@author: Sivan
"""

import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import instruments
import zhinst.ziPython as ziPython
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import (NavigationToolbar2QT as NavigationToolbar)
import matplotlib.pyplot as plt
import numpy as np


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        #set the size and title of the window
        self.setGeometry(300, 300, 700, 600)
        self.setWindowTitle('Zurich')
        self.show()
        
        instruments.zi_widget = ZIWidget()
        self.setCentralWidget(instruments.zi_widget)
  

      
class ZIWidget(QFrame):
    def __init__(self):
        super().__init__()
        
        self.initUI()
        
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
        self.fig = plt.Figure()
        ax1 = self.fig.add_subplot(221)
        ax1.tick_params(axis='x',which='both',bottom=False,top=False,labelbottom=False)
        ax1.get_xaxis().set_visible(False)
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Frequency')
        ax1.set_title('Demodulator 1')
        ax2 = self.fig.add_subplot(222)
        ax2.tick_params(axis='x',which='both',bottom=False,top=False,labelbottom=False)
        ax2.get_xaxis().set_visible(False)
        ax2.set_xlabel('Time')
        ax2.set_ylabel('Frequency')
        ax2.set_title('Demodulator 2')
        ax3 = self.fig.add_subplot(223)
        ax3.tick_params(axis='x',which='both',bottom=False,top=False,labelbottom=False)
        ax3.get_xaxis().set_visible(False)
        ax3.set_xlabel('Time')
        ax3.set_ylabel('Frequency')
        ax3.set_title('Demodulator 3')
        ax4 = self.fig.add_subplot(224)
        ax4.tick_params(axis='x',which='both',bottom=False,top=False,labelbottom=False)
        ax4.get_xaxis().set_visible(False)
        ax4.set_xlabel('Time')
        ax4.set_ylabel('Frequency')
        ax4.set_title('Demodulator 4')
        self.axes = [ax1, ax2, ax3, ax4]
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.fig.tight_layout()
        
        main_grid.addWidget(self.toolbar,4,0,1,4)
        main_grid.addWidget(self.canvas,5,0,1,4)
        
        
        
    def connectDAQ(self):
        if (self.host_le.text() == '' or self.port_le.text() == ''):
            QMessageBox.warning(self, 'Data Server Settings Error',
                                'Do not leave host or port blank')
            return
        
        host = self.host_le.text()
        api_level = 5
        
        try:
            port = int(self.port_le.text())
        except ValueError:
            QMessageBox.warning(self, 'Port Value Error', 'Port must be a number')
            return
        
        try:
            instruments.daq = ziPython.ziDAQServer(host, port, api_level)
            self.daq_lbl.setText(u'Data Server Connection: \u2705')
        except RuntimeError as e:
            QMessageBox.warning(self, 'Connection Error', str(e))
            
    def startPlot(self):
        demod_path = self.demodulator_le.text()
        
        try:
            for i in range(4):
                instruments.daq.subscribe(demod_path + '/{}/sample'.format(i))
        except RuntimeError as e:
            QMessageBox.warning(self, 'Path Error', 'Incorrect path:\n' + str(e))
            return
        except AttributeError:
            QMessageBox.warning(self, 'Data Server Connection Error',
                                'Must connect to data server before plotting instrument data')
            return
        
        self.time_data = [None,]*4
        self.freq_data = [None,]*4
        instruments.daq.sync()
        data = instruments.daq.poll(0.1, 500, 0, True)
        
        for i, ax in enumerate(self.axes):
            try:
                self.time_data[i] = data['{}/{}/sample'.format(demod_path, i)]['timestamp']
                self.freq_data[i] = data['{}/{}/sample'.format(demod_path, i)]['frequency']
                ax.plot(self.time_data[i], self.freq_data[i])
            except:
                QMessageBox.warning(self, 'Data Error', 'The path {}/{}/sample may be incorrect or disconnected'.format(demod_path, i))
        self.canvas.draw()
        
        #call plot function every 0.1 seconds
        self.timer = QTimer()
        self.timer.timeout.connect(self.plot)
        self.timer.start(100)
        
    def stopPlot(self):
        self.timer.stop()
        for ax in self.axes:
            ax.clear()
        
        self.time_data = [[],[],[]]
        self.volt_data = [[],[],[]]
    
    def plot(self):
        demod_path = self.demodulator_le.text()
        
        #collect data for 0.1 seconds, then append to existing data
        data = instruments.daq.poll(0.1, 500, 0, True)
        
        for i in range(4):
            try:
                self.time_data[i] = np.append(self.time_data[i], data['{}/{}/sample'.format(demod_path, i)]['timestamp'])
                self.freq_data[i] = np.append(self.freq_data[i], data['{}/{}/sample'.format(demod_path, i)]['frequency'])
            except:
                pass
        #clear existing plot, then plot the last 10000 points
        for i, ax in enumerate(self.axes):
            ax.clear()
            ax.set_ylabel('Frequency')
            ax.set_title('Demodulator {}'.format(i+1))
            try:
                ax.plot(self.time_data[i][-10000:], self.freq_data[i][-10000:])
            except:
                pass
        self.fig.tight_layout()
        self.canvas.draw()
    
        
        




if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()    
    sys.exit(app.exec_())
        