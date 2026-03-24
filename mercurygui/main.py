# -*- coding: utf-8 -*-
"""
@author: Sam Schott  (ss2151@cam.ac.uk)

(c) Sam Schott; This work is licensed under a Creative Commons
Attribution-NonCommercial-NoDerivs 2.0 UK: England & Wales License.

"""

import inspect

# system imports
import sys
import os
import platform
import subprocess
import pkg_resources as pkgr
import time
import numpy as np
import logging
from pathlib import Path
from PyQt5 import QtCore, QtWidgets, uic
from mercuryitc.mercury_driver import MercuryITC_TEMP, MercuryITC_HTR, MercuryITC_AUX
from pymeasure.instruments.srs.sr830 import *
from pymeasure.instruments.srs.sr860 import *
import pyvisa
from QCL_interface import *
from mercurygui.pyqtplot_canvas import VoltageHistoryPlot, VoltageTemperaturePlot, VoltageVoltagePlot

# local imports
from mercurygui.feed import MercuryFeed
from .pyqt_labutils import LedIndicator, ConnectionDialog
from .pyqtplot_canvas import TemperatureHistoryPlot
from .config.main import CONF
import os
from get_project_path import cwd_path

MAIN_UI_PATH = r"{}\mercurygui\main.ui".format(cwd_path) # pkgr.resource_filename("mercurygui", "main.ui")
PANEL_UI_PATH = r"{}\mercurygui\panel.ui".format(cwd_path) #pkgr.resource_filename("mercurygui", "panel.ui")
MODULE_DIALOG_UI_PATH = r"{}\mercurygui\module_dialog.ui".format(cwd_path) #pkgr.resource_filename("mercurygui", "module_dialog.ui")

logger = logging.getLogger(__name__)


class LockinAmplifier(QFrame):
    def __init__(self, parent):
        super().__init__()
        # self.setGeometry(700, 400, 500, 450)
        self.setWindowTitle("Lock-in Amplifier")
        self.parent = parent
        self.MAX_DISPLAY = 3*24*60*60
        self.magnitude = []
        self.connected = False
        self.trigger_logging = False
        self.keithley = None
        self.show()
        self.initUI()

    def initUI(self):
        # create main grid to organize layout
        main_grid = QGridLayout()
        main_grid.setSpacing(10)
        self.setLayout(main_grid)

        # create resource manager to connect to the instrument and store resources in a list
        instruments.rm = visa.ResourceManager()
        resources = instruments.rm.list_resources()
        resource = []
        for i in range(len(resources)):
            resource.append(resources[i])
            if resource[i] == "GPIB0::8::INSTR":
                resource[i] += " (default)"

        # create a combo box to allow the user to connect with a given instrument then add all resources
        self.connection_box = QComboBox()
        self.connection_box.addItem('Connect to lock-in amplifier...')
        self.connection_box.addItems(resource)
        self.connection_box.currentIndexChanged.connect(self.connectInstrument)
        main_grid.addWidget(self.connection_box, 0, 1, 1, 2, Qt.AlignCenter)

        # create a label to show connection of the instrument with check or cross mark
        self.connection_indicator = QLabel(u'\u274c ')  # cross mark by default because not connected yet
        main_grid.addWidget(self.connection_indicator, 0, 3, 1, 1, Qt.AlignLeft)

        self.lockin_selection_box = QComboBox()
        self.lockin_selection_box.addItem("SR830")
        self.lockin_selection_box.addItem("SR860")
        main_grid.addWidget(self.lockin_selection_box, 0, 0, 1, 1, Qt.AlignCenter)

        self.magnitude_lb = QLabel("Magnitude")
        self.magnitude_reading_lb = QLabel("")
        self.magnitude_reading_lb.setStyleSheet("color: red")
        self.magnitude_reading_lb.setFixedWidth(100)
        self.magnitude_reading_lb.setFixedHeight(40)
        self.phase_lb = QLabel("Phase")
        self.phase_reading_lb = QLabel("")
        self.phase_reading_lb.setStyleSheet("color: red")
        self.phase_reading_lb.setFixedWidth(100)
        self.phase_reading_lb.setFixedHeight(40)
        self.reference_lb = QLabel("Reference")
        self.reference_reading_lb = QLabel("")
        self.reference_reading_lb.setFixedWidth(100)
        self.reference_reading_lb.setFixedHeight(40)
        self.real_lb = QLabel("Real")
        self.real_reading_lb = QLabel("")
        self.real_reading_lb.setStyleSheet("color: blue")
        self.real_reading_lb.setFixedWidth(100)
        self.real_reading_lb.setFixedHeight(40)
        self.imag_lb = QLabel("Imag")
        self.imag_reading_lb = QLabel("")
        self.imag_reading_lb.setStyleSheet("color: blue")
        self.imag_reading_lb.setFixedWidth(100)
        self.imag_reading_lb.setFixedHeight(40)
        self.reference_freq_lb = QLabel("Frequency")
        self.reference_freq_reading_lb = QLabel("")
        self.reference_freq_reading_lb.setFixedWidth(100)
        self.reference_freq_reading_lb.setFixedHeight(40)

        readings_grid = QGridLayout()
        readings_grid.addWidget(self.magnitude_lb, 0, 0, 1, 1, Qt.AlignCenter)
        readings_grid.addWidget(self.magnitude_reading_lb, 0, 1, 1, 1, Qt.AlignCenter)
        readings_grid.addWidget(self.phase_lb, 0, 2, 1, 1, Qt.AlignCenter)
        readings_grid.addWidget(self.phase_reading_lb, 0, 3, 1, 1, Qt.AlignCenter)
        readings_grid.addWidget(self.reference_lb, 0, 4, 1, 1, Qt.AlignCenter)
        readings_grid.addWidget(self.reference_reading_lb, 0, 5, 1, 1, Qt.AlignCenter)
        readings_grid.addWidget(self.real_lb, 1, 0, 1, 1, Qt.AlignCenter)
        readings_grid.addWidget(self.real_reading_lb, 1, 1, 1, 1, Qt.AlignCenter)
        readings_grid.addWidget(self.imag_lb, 1, 2, 1, 1, Qt.AlignCenter)
        readings_grid.addWidget(self.imag_reading_lb, 1, 3, 1, 1, Qt.AlignCenter)
        readings_grid.addWidget(self.reference_freq_lb, 1, 4, 1, 1, Qt.AlignCenter)
        readings_grid.addWidget(self.reference_freq_reading_lb, 1, 5, 1, 1, Qt.AlignCenter)
        main_grid.addLayout(readings_grid, 1, 0, 2, 4, Qt.AlignCenter)

        self.tabs = QTabWidget()
        # self.tabs.setFixedWidth(600)
        # self.tabs.setFixedHeight(500)
        self.voltage_temperature_tab = QWidget()
        self.voltage_voltage_tab = QWidget()
        self.voltage_time_tab = QWidget()

        # set the voltage-temperature plot
        vbox1 = QVBoxLayout()
        vbox1.setSpacing(10)
        self.voltage_temperature_tab.setLayout(vbox1)

        self.voltage_temperature_canvas = VoltageTemperaturePlot()
        self.temp_xdata = np.array([])
        self.temp_ydata_magnitude = np.array([])

        vbox1.addWidget(self.voltage_temperature_canvas)

        # set the voltage-voltage plot
        vbox3 = QVBoxLayout()
        vbox3.setSpacing(10)
        self.voltage_voltage_tab.setLayout(vbox3)

        self.voltage_voltage_canvas = VoltageVoltagePlot()
        self.voltage_xdata = np.array([])
        self.voltage_xdata2 = np.array([])
        self.voltage_ydata_magnitude = np.array([])

        vbox3.addWidget(self.voltage_voltage_canvas)

        # set the voltage-time plot
        vbox2 = QVBoxLayout()
        vbox2.setSpacing(10)
        self.voltage_time_tab.setLayout(vbox2)

        self.voltage_time_canvas = VoltageHistoryPlot()

        # set up data vectors for plot
        self.xdata = np.array([])
        self.xdata_min_zero = np.array([])
        self.rel_time = np.array([])
        self.ydata_magnitude = np.array([])

        self.timeLabel = QLabel("Show last 1 min")
        self.horizontalSlider = QSlider(Qt.Horizontal)
        self.horizontalSlider.setTickPosition(QSlider.TicksBelow)
        self.horizontalSlider.setTickInterval(60)
        self.horizontalSlider.setMinimum(1)
        self.horizontalSlider.setMaximum(self.MAX_DISPLAY / 60)
        # self.horizontalSlider.setFixedWidth(600)

        # connect slider to plot
        self.horizontalSlider.valueChanged.connect(self.on_slider_changed)

        vbox2.addWidget(self.voltage_time_canvas)
        vbox2.addWidget(self.timeLabel)
        vbox2.addWidget(self.horizontalSlider)

        self.tabs.addTab(self.voltage_time_tab, "Voltage-Time")
        self.tabs.addTab(self.voltage_temperature_tab, "Voltage-Temperature")
        self.tabs.addTab(self.voltage_voltage_tab, "Voltage-Voltage")
        main_grid.addWidget(self.tabs, 3, 0, 6, 4, Qt.AlignCenter)

        hbox1 = QHBoxLayout()

        self.trigger_lb = QLabel("Trigger")
        self.trigger_lb.setFixedHeight(50)
        self.trigger_cb = QComboBox()
        self.trigger_cb.addItems(["No trigger", "Temperature", "Voltage"])
        self.spacer_lb = QLabel("")
        self.spacer_lb.setFixedWidth(50)
        self.threshold_lb = QLabel("Threshold")
        self.threshold_sb = QDoubleSpinBox()
        self.threshold_sb.setDecimals(3)
        self.threshold_sb.setValue(1)
        hbox1.addWidget(self.trigger_lb)
        hbox1.addWidget(self.trigger_cb)
        hbox1.addWidget(self.spacer_lb)
        hbox1.addWidget(self.threshold_lb)
        hbox1.addWidget(self.threshold_sb)
        main_grid.addLayout(hbox1, 9, 0, 1, 4, Qt.AlignCenter)

        self.filepath_btn = QPushButton("Save to path")
        self.filepath_btn.setFixedHeight(30)
        self.filepath_btn.clicked.connect(self.set_filepath)
        self.filepath_dispaly_lb = QLabel("")
        main_grid.addWidget(self.filepath_btn, 10, 0, 1, 1, Qt.AlignCenter)
        main_grid.addWidget(self.filepath_dispaly_lb, 10, 1, 1, 3, Qt.AlignCenter)

        self.filename_lb = QLabel("Filename")
        self.filename_le = QLineEdit("Log")
        self.comment_lb = QLabel("Comment")
        self.comment_te = QTextEdit()
        self.comment_te.setFixedHeight(100)
        main_grid.addWidget(self.comment_lb, 11, 0, 1, 1, Qt.AlignCenter)
        main_grid.addWidget(self.filename_lb, 11, 2, 1, 1, Qt.AlignRight)
        main_grid.addWidget(self.filename_le, 11, 3, 1, 1, Qt.AlignLeft)
        main_grid.addWidget(self.comment_te, 12, 0, 1, 2, Qt.AlignCenter)

        self.start_logging_btn = QPushButton("Start\nLogging")
        self.start_logging_btn.setFixedWidth(80)
        self.start_logging_btn.setFixedHeight(80)
        self.start_logging_btn.clicked.connect(self.setup_trigger_logging)
        self.logging_ind = QLedIndicator('orange')
        self.logging_ind.setChecked(True)
        self.logging_ind.setFixedWidth(40)
        self.logging_ind.setFixedHeight(40)
        main_grid.addWidget(self.logging_ind, 12, 2, 1, 1, Qt.AlignRight)
        main_grid.addWidget(self.start_logging_btn, 12, 3, 1, 1, Qt.AlignCenter)

        self.setup_time_logging()

    def connectInstrument(self):
        # if a selection is chosen that is not just the default prompt
        if (self.connection_box.currentText() != 'Connect to lock-in amplifier...'):
            # get the chopper name and connect the chopper
            if self.connection_box.currentText()[-1] == ")":
                lockin_name = self.connection_box.currentText()[:-10]
            else:
                lockin_name = self.connection_box.currentText()

            try:
                if self.lockin_selection_box.currentText() == "SR830":
                    self.lockin = SR830(lockin_name)
                elif self.lockin_selection_box.currentText() == "SR860":
                    self.lockin = SR860(lockin_name)
                self.connected = True
            except:
                self.connection_indicator.setText(u'\u274c ')
                self.connected = False
                return

            # change connection indicator to a check mark from a cross mark
            self.connection_indicator.setText(u'\u2705')
            self.connected = True

            print(self.lockin.magnitude, self.lockin.theta, self.lockin.sine_voltage, self.lockin.frequency)

            # update magnitude, phase, reference every second (1000 ms)
            self.timer = QTimer()
            self.timer.timeout.connect(self.updateMPR)
            self.timer.start(1500)

            # declare the trigger log timer

            t_save = 1 # set the interval of trigger based logging to 1s

            self.trigger_log_timer = QtCore.QTimer()
            self.trigger_log_timer.setInterval(t_save * 1000)
            self.trigger_log_timer.setSingleShot(False)  # set to reoccur
            self.trigger_log_timer.timeout.connect(self.log_trigger_voltage_data)

    def updateMPR(self):
        magnitude = self.lockin.magnitude
        phase = self.lockin.theta
        reference = self.lockin.sine_voltage
        real = self.lockin.x
        imag = self.lockin.y
        frequency = self.lockin.frequency
        if abs(magnitude) < 1e-7:
            self.magnitude_reading_lb.setText("{:.3f} nV".format(magnitude*1e9))
        elif abs(magnitude) < 1e-4:
            self.magnitude_reading_lb.setText(u"{:.3f} \u03bcV".format(magnitude*1e6))
        elif abs(magnitude) < 0.1:
            self.magnitude_reading_lb.setText(u"{:.3f} mV".format(magnitude*1e3))
        else:
            self.magnitude_reading_lb.setText(u"{:.3f} V".format(magnitude))
        self.phase_reading_lb.setText("{:.3f} deg".format(phase))
        if abs(reference) < 1e-7:
            self.reference_reading_lb.setText("{:.3f} nV".format(reference*1e9))
        elif abs(reference) < 1e-4:
            self.reference_reading_lb.setText(u"{:.3f} \u03bcV".format(reference*1e6))
        elif abs(reference) < 0.1:
            self.reference_reading_lb.setText(u"{:.3f} mV".format(reference*1e3))
        else:
            self.reference_reading_lb.setText(u"{:.3f} V".format(reference))
        if abs(real) < 1e-7:
            self.real_reading_lb.setText("{:.3f} nV".format(real*1e9))
        elif abs(real) < 1e-4:
            self.real_reading_lb.setText(u"{:.3f} \u03bcV".format(real*1e6))
        elif abs(real) < 0.1:
            self.real_reading_lb.setText(u"{:.3f} mV".format(real*1e3))
        else:
            self.real_reading_lb.setText(u"{:.3f} V".format(real))
        if abs(imag) < 1e-7:
            self.imag_reading_lb.setText("{:.3f} nV".format(imag*1e9))
        elif abs(imag) < 1e-4:
            self.imag_reading_lb.setText(u"{:.3f} \u03bcV".format(imag*1e6))
        elif abs(imag) < 0.1:
            self.imag_reading_lb.setText(u"{:.3f} mV".format(imag*1e3))
        else:
            self.imag_reading_lb.setText(u"{:.3f} V".format(imag))
        self.reference_freq_reading_lb.setText("{:.3f} Hz".format(frequency))

        self.xdata = np.append(self.xdata, time.time())
        self.rel_time = np.append(self.rel_time, time.time())
        self.rel_time[-1] -= self.xdata[0]
        self.ydata_magnitude = np.append(self.ydata_magnitude, magnitude)

        # prevent data vector from exceeding MAX_DISPLAY
        self.xdata = self.xdata[-self.MAX_DISPLAY :]
        self.ydata_magnitude = self.ydata_magnitude[-self.MAX_DISPLAY :]

        # convert xData to minutes and set current time to t = 0
        self.xdata_min_zero = (self.xdata - self.xdata[-1]) / 60

        # update plot
        self.voltage_time_canvas.update_data(
            self.xdata_min_zero, self.ydata_magnitude
        )

        if self.parent.mercury.connected:
            # if not self.trigger_logging:
            #     self.temp_xdata = np.append(self.temp_xdata, float(list(self.parent.panels.values())[0].t1_reading.text()[:-2]))
            #     self.temp_ydata_magnitude = np.append(self.temp_ydata_magnitude, magnitude)
            # else:
            if self.trigger_cb.currentText() == "Temperature":
                if len(self.temp_xdata) == 0:
                    self.temp_xdata = np.append(self.temp_xdata, float(list(self.parent.panels.values())[0].t1_reading.text()[:-2]))
                    self.temp_ydata_magnitude = np.append(self.temp_ydata_magnitude, magnitude)
                else:
                    if abs(float(list(self.parent.panels.values())[0].t1_reading.text()[:-2]) - self.temp_xdata[-1]) >= self.threshold_sb.value():
                        self.temp_xdata = np.append(self.temp_xdata, float(list(self.parent.panels.values())[0].t1_reading.text()[:-2]))
                        self.temp_ydata_magnitude = np.append(self.temp_ydata_magnitude, magnitude)
            self.voltage_temperature_canvas.update_data(
                self.temp_xdata, self.temp_ydata_magnitude
            )

        if self.keithley is not None and self.keithley.connected1 and self.keithley.enabled1:
            # if not self.trigger_logging:
            #     self.voltage_xdata = np.append(self.voltage_xdata, self.keithley.keithley1.voltage)
            #     self.voltage_ydata_magnitude = np.append(self.voltage_ydata_magnitude, magnitude)
            # else:
            if self.trigger_cb.currentText() == "Voltage":
                if len(self.voltage_xdata) == 0:
                    self.voltage_xdata = np.append(self.voltage_xdata, self.keithley.voltage_now_curve.get_xdata()[0])
                    self.voltage_ydata_magnitude = np.append(self.voltage_ydata_magnitude, magnitude)
                else:
                    if abs(self.keithley.voltage_now_curve.get_xdata()[0] - self.voltage_xdata[-1]) >= self.threshold_sb.value():
                        self.voltage_xdata = np.append(self.voltage_xdata, self.keithley.voltage_now_curve.get_xdata()[0])
                        self.voltage_ydata_magnitude = np.append(self.voltage_ydata_magnitude, magnitude)
            self.voltage_voltage_canvas.update_data(
                self.voltage_xdata, self.voltage_ydata_magnitude
            )

        if self.keithley is not None and self.keithley.connected2 and self.keithley.enabled2:
            # if not self.trigger_logging:
            #     self.voltage_xdata = np.append(self.voltage_xdata, self.keithley.keithley1.voltage)
            #     self.voltage_ydata_magnitude = np.append(self.voltage_ydata_magnitude, magnitude)
            # else:
            if self.trigger_cb.currentText() == "Voltage":
                if len(self.voltage_xdata2) == 0:
                    self.voltage_xdata2 = np.append(self.voltage_xdata2, self.keithley.voltage_now_curve.get_ydata()[0])
                    if not self.keithley.connected1 and not self.keithley.enabled1:
                        self.voltage_ydata_magnitude = np.append(self.voltage_ydata_magnitude, magnitude)
                else:
                    if abs(self.keithley.voltage_now_curve.get_ydata()[0] - self.voltage_xdata2[-1]) >= self.threshold_sb.value():
                        self.voltage_xdata2 = np.append(self.voltage_xdata2, self.keithley.voltage_now_curve.get_ydata()[0])
                        if not self.keithley.connected1 and not self.keithley.enabled1:
                            self.voltage_ydata_magnitude = np.append(self.voltage_ydata_magnitude, magnitude)
                if not self.keithley.connected1 and not self.keithley.enabled1:
                    self.voltage_voltage_canvas.update_data(
                        self.voltage_xdata2, self.voltage_ydata_magnitude
                    )

    def on_slider_changed(self):
        # determine first plotted data point
        sv = self.horizontalSlider.value()

        self.timeLabel.setText("Show last %s min" % sv)
        self.voltage_time_canvas.set_xmin(-sv)
        self.voltage_time_canvas.p0.setXRange(-sv, 0)
        self.voltage_time_canvas.p0.enableAutoRange(x=False, y=True)

    # =================== TRIGGER-BASED LOGGING DATA ============================================

    def setup_trigger_logging(self):
        if not self.trigger_logging:

            if self.filepath_dispaly_lb.text() == "" or self.filename_le.text() == "":
                QMessageBox.warning(self, "Log path and filename", "Invalid file path or filename!")
                return
            if self.trigger_cb.currentText() == "No trigger" or self.threshold_sb.value() <= 0:
                QMessageBox.warning(self, "Trigger and threshold", "No trigger or threshold declared!")
                return

            self.start_logging_btn.setText("Stop\nLogging")
            self.logging_ind.changeColor("green")

            os.makedirs(self.filepath_dispaly_lb.text(), exist_ok=True)
            time_str = time.strftime("%Y-%m-%d_%H-%M-%S")
            self.trigger_log_file = self.filepath_dispaly_lb.text() + "//" + f"{self.filename_le.text()}_{time_str}.txt"

            self.trigger_logging = True

            if self.trigger_cb.currentText() == "Temperature":
                self.temp_xdata = np.array([])
                self.temp_ydata_magnitude = np.array([])
            elif self.trigger_cb.currentText() == "Voltage":
                self.voltage_xdata = np.array([])
                self.voltage_xdata2 = np.array([])
                self.voltage_ydata_magnitude = np.array([])

            self.trigger_cb.setEnabled(False)
            self.threshold_sb.setEnabled(False)

            self.trigger_log_timer.start()

        else:

            self.trigger_log_timer.stop()

            self.start_logging_btn.setText("Start\nLogging")
            self.logging_ind.changeColor("orange")

            self.trigger_cb.setEnabled(True)
            self.threshold_sb.setEnabled(True)

            # if self.trigger_cb.currentText() == "Temperature":
            #     self.temp_xdata = np.array([])
            #     self.temp_ydata_magnitude = np.array([])
            # elif self.trigger_cb.currentText() == "Voltage":
            #     self.voltage_xdata = np.array([])
            #     self.voltage_ydata_magnitude = np.array([])

            self.trigger_logging = False

    def log_trigger_voltage_data(self):

        if self.trigger_cb.currentText() == "Temperature":
            if self.connected and self.parent.mercury.connected:
                self.save_trigger_voltage_data(self.trigger_log_file)
        elif self.trigger_cb.currentText() == "Voltage":
            if self.connected and (self.keithley.connected1 or self.keithley.connected2):
                self.save_trigger_voltage_data(self.trigger_log_file)

    def save_trigger_voltage_data(self, path=None):
        # prompt user for file path if not given
        if path is None:
            text = "Select path for temperature data file:"
            path = QtWidgets.QFileDialog.getSaveFileName(caption=text)
            path = path[0]

        if self.trigger_cb.currentText() == "Temperature":
            if self.comment_te.toPlainText() == "":
                header = "\t".join(
                    ["Temperature (K)", "Voltage (uV)\nStart from {}".format(time.strftime("%Y-%m-%d_%H-%M-%S"))]
                )
            else:
                header = "\t".join(
                    ["{}\nTemperature (K)".format(self.comment_te.toPlainText()), "Voltage (uV)\nStart from {}".format(time.strftime("%Y-%m-%d_%H-%M-%S"))]
                )

            data_matrix = np.concatenate(
                (
                    self.temp_xdata[:, np.newaxis],
                    self.temp_ydata_magnitude[:, np.newaxis]*1e6
                ),
                axis=1,
            )
        elif self.trigger_cb.currentText() == "Voltage":
            if self.keithley.connected1 and self.keithley.connected2:
                if self.comment_te.toPlainText() == "":
                    header = "\t".join(
                        ["Source Voltage 1 (V)", "Source Voltage 2 (V)", "Voltage (uV)\nStart from {}".format(time.strftime("%Y-%m-%d_%H-%M-%S"))]
                    )
                else:
                    header = "\t".join(
                        ["{}\nSource Voltage 1 (V)".format(self.comment_te.toPlainText()), "Source Voltage 2 (V)", "Voltage (uV)\nStart from {}".format(time.strftime("%Y-%m-%d_%H-%M-%S"))]
                    )

                data_matrix = np.concatenate(
                    (
                        self.voltage_xdata[:, np.newaxis],
                        self.voltage_xdata2[:, np.newaxis],
                        self.voltage_ydata_magnitude[:, np.newaxis]*1e6
                    ),
                    axis=1,
                )
            elif self.keithley.connected1:
                if self.comment_te.toPlainText() == "":
                    header = "\t".join(
                        ["Source Voltage (V)", "Voltage (uV)\nStart from {}".format(time.strftime("%Y-%m-%d_%H-%M-%S"))]
                    )
                else:
                    header = "\t".join(
                        ["{}\nSource Voltage (V)".format(self.comment_te.toPlainText()), "Voltage (uV)\nStart from {}".format(time.strftime("%Y-%m-%d_%H-%M-%S"))]
                    )

                data_matrix = np.concatenate(
                    (
                        self.voltage_xdata[:, np.newaxis],
                        self.voltage_ydata_magnitude[:, np.newaxis]*1e6
                    ),
                    axis=1,
                )
            elif self.keithley.connected2:
                if self.comment_te.toPlainText() == "":
                    header = "\t".join(
                        ["Source Voltage (V)", "Voltage (uV)\nStart from {}".format(time.strftime("%Y-%m-%d_%H-%M-%S"))]
                    )
                else:
                    header = "\t".join(
                        ["{}\nSource Voltage (V)".format(self.comment_te.toPlainText()), "Voltage (uV)\nStart from {}".format(time.strftime("%Y-%m-%d_%H-%M-%S"))]
                    )

                data_matrix = np.concatenate(
                    (
                        self.voltage_xdata2[:, np.newaxis],
                        self.voltage_ydata_magnitude[:, np.newaxis]*1e6
                    ),
                    axis=1,
                )

        # noinspection PyTypeChecker
        np.savetxt(path, data_matrix, delimiter="\t", header=header, fmt="%f")
        screenshot = self.grab()
        screenshot.save(path, 'jpg')

    # =================== LOGGING DATA ============================================

    def setup_time_logging(self):
        """
        Save temperature history to log file at '~/.CustomXepr/LOG_FILES/' every 10 min.
        """

        os.makedirs(self.parent.log_path, exist_ok=True)

        # set logging file path
        time_str = time.strftime("%Y-%m-%d_%H-%M-%S")
        self.time_log_file = self.parent.log_path / f"Lock_in_amplifier_{time_str}.txt"

        # delete old log files
        now = time.time()
        days_to_keep = 7

        for file in os.scandir(self.parent.log_path):
            if file.stat().st_mtime < now - days_to_keep * 24 * 60 * 60:
                if file.is_file():
                    os.remove(file.path)

        # set up periodic logging
        t_save = 5 # t_save is the time interval to save temperature data (min)

        self.time_log_timer = QtCore.QTimer()
        self.time_log_timer.setInterval(t_save * 60 * 1000)
        self.time_log_timer.setSingleShot(False)  # set to reoccur
        self.time_log_timer.timeout.connect(self.log_time_voltage_data)
        self.time_log_timer.start()

    def save_time_voltage_data(self, path=None):
        # prompt user for file path if not given
        if path is None:
            text = "Select path for temperature data file:"
            path = QtWidgets.QFileDialog.getSaveFileName(caption=text)
            path = path[0]

        header = "\t".join(
            ["Time (sec)", "Voltage (uV)\nStart from {}".format(time.strftime("%Y-%m-%d_%H-%M-%S"))]
        )

        data_matrix = np.concatenate(
            (
                self.rel_time[:, np.newaxis],
                self.ydata_magnitude[:, np.newaxis]*1e6
            ),
            axis=1,
        )

        # noinspection PyTypeChecker
        np.savetxt(path, data_matrix, delimiter="\t", header=header, fmt="%f")

    def log_time_voltage_data(self):
        # save temperature data to log file
        if self.connected:
            self.save_time_voltage_data(self.time_log_file)

    def set_filepath(self):
        path = QFileDialog.getExistingDirectory(self, "Select a folder", r"D:\Data")
        self.filepath_dispaly_lb.setText(path)
        self.filepath = path


# noinspection PyArgumentList
class MercuryMonitorApp(QtWidgets.QMainWindow):

    QUIT_ON_CLOSE = True

    MAX_DISPLAY = 24 * 60 * 60
    UPDATE_FREQ = 1
    TITLE_TEMPLATE = "MercuryiTC Control"
    log_path = Path.home() / ".mercurygui" / "LOG_FILES"

    def __init__(self, mercury):
        super(self.__class__, self).__init__()
        uic.loadUi(MAIN_UI_PATH, self)

        self.mercury = mercury
        self._cached_connection_status = False

        # create popup Widgets
        self.connectionDialog = ConnectionDialog(self, self.mercury, CONF)
        self.readingsDialog = ReadingsOverview(self.mercury)
        self.modulesDialog = ModulesDialog(self.mercury)
        self.PIDDialog = PIDDialog(self.mercury)

        # create LED indicator
        self.led = LedIndicator(self)
        self.statusbar.addPermanentWidget(self.led)
        self.led.setChecked(False)

        # restore previous window geometry
        self.restore_geometry()

        # connect to callbacks
        self.modulesAction.triggered.connect(self.on_module_selection_clicked)
        self.PIDAction.triggered.connect(self.on_PID_clicked)
        self.showLogAction.triggered.connect(self.on_log_clicked)
        self.exitAction.triggered.connect(self.exit_)
        self.readingsAction.triggered.connect(self.on_readings_clicked)
        self.updateAddressAction.triggered.connect(self.connectionDialog.open)
        self.connectionDialog.accepted.connect(self.build_tabs)

        self.actionUpdateVeryOften.triggered.connect(lambda: self.set_update_freq(0.5))
        self.actionUpdateOften.triggered.connect(lambda: self.set_update_freq(1))
        self.actionUpdateNormally.triggered.connect(lambda: self.set_update_freq(2))

        action_group = QtWidgets.QActionGroup(self)
        action_group.addAction(self.actionUpdateVeryOften)
        action_group.addAction(self.actionUpdateOften)
        action_group.addAction(self.actionUpdateNormally)

        self.actionUpdatePeriodVeryOften.triggered.connect(lambda: self.set_update_period(5))
        self.actionUpdatePeriodOften.triggered.connect(lambda: self.set_update_period(10))
        self.actionUpdatePeriodNormally.triggered.connect(lambda: self.set_update_period(30))
        self.actionUpdatePeriodSlowly.triggered.connect(lambda: self.set_update_period(60))

        action_group2 = QtWidgets.QActionGroup(self)
        action_group2.addAction(self.actionUpdatePeriodVeryOften)
        action_group2.addAction(self.actionUpdatePeriodOften)
        action_group2.addAction(self.actionUpdatePeriodNormally)
        action_group2.addAction(self.actionUpdatePeriodSlowly)

        # initially disable menu bar items, will be enabled later individually
        self.modulesAction.setEnabled(False)
        self.readingsAction.setEnabled(False)
        self.PIDAction.setEnabled(False)

        # check if mercury is connected, connect slots
        self.display_message(f"Looking for Mercury at {self.mercury.visa_address}...")

        # populate panels for temperature modules
        self.panels = {}
        self.build_tabs()

        self.update_gui()

        """
        self.update_timer = QtCore.QTimer()
        self.update_timer.setInterval(self.UPDATE_FREQ * 1000)
        self.update_timer.setSingleShot(False)  # set to reoccur
        self.update_timer.timeout.connect(self.update_gui)
        self.update_timer.start()
        """

    def set_update_freq(self, seconds):
        self.update_timer.setInterval(seconds * 1000)

        for panel in self.panels.values():
            panel.feed.refresh = seconds

    def set_update_period(self, minutes):
        for panel in self.panels.values():
            panel.log_timer.setInterval(minutes * 60 * 1000)

    def build_tabs(self):
        self.tabWidget.clear()

        sensor_names = self._get_nicks(MercuryITC_TEMP)

        if len(sensor_names) == 0:
            sensor_names.append("...")

        for sensor_name in sensor_names:
            panel = ControlPanel(self.mercury, self, sensor_name)
            self.panels[sensor_name] = panel
            self.tabWidget.addTab(panel, sensor_name)

        # Lock-in is added here for now
        self.lockin = LockinAmplifier(self)
        self.tabWidget.addTab(self.lockin, "Lock-in Amplifier")

    def update_gui(self):
        if not self.mercury.connected:
            self.mercury.connect()

        connected = self.mercury.connected

        if connected is not self._cached_connection_status:
            # update gui to reflect changed connection status
            self.update_gui_connection(connected)
            for panel in self.panels.values():
                panel.update_gui_connection(connected)

            if connected:
                self.build_tabs()
                self.readingsDialog.build_tabs()

        self._cached_connection_status = self.mercury.connected

    # =================== BASIC UI SETUP ==========================================

    def restore_geometry(self):
        x = CONF.get("Window", "x")
        y = CONF.get("Window", "y")
        w = CONF.get("Window", "width")
        h = CONF.get("Window", "height")

        self.setGeometry(x, y, w, h)

    def save_geometry(self):
        geo = self.geometry()
        CONF.set("Window", "height", geo.height())
        CONF.set("Window", "width", geo.width())
        CONF.set("Window", "x", geo.x())
        CONF.set("Window", "y", geo.y())

    def exit_(self):
        self.save_geometry()
        self.deleteLater()

    def closeEvent(self, event):
        if self.QUIT_ON_CLOSE:
            self.exit_()
        else:
            self.hide()

    def update_gui_connection(self, connected):

        if connected:
            self.led.setChecked(True)

            # enable / disable menu bar items
            self.connectAction.setEnabled(False)
            self.disconnectAction.setEnabled(True)
            self.modulesAction.setEnabled(True)
            self.readingsAction.setEnabled(True)
            self.sensorAction.setEnabled(True)
            self.PIDAction.setEnabled(True)

        elif not connected:
            self.led.setChecked(False)

            # enable / disable menu bar items
            self.connectAction.setEnabled(True)
            self.disconnectAction.setEnabled(False)
            self.modulesAction.setEnabled(False)
            self.readingsAction.setEnabled(False)
            self.PIDAction.setEnabled(False)

    def display_message(self, text):
        self.statusbar.showMessage(str(text), 5000)

    def display_error(self, text):
        self.statusbar.showMessage(str(text))

    # ========================== CALLBACKS FOR MENU BAR ===========================

    @QtCore.pyqtSlot()
    def on_readings_clicked(self):
        self.readingsDialog.show()

    @QtCore.pyqtSlot()
    def on_module_selection_clicked(self):
        self.modulesDialog.update_gui()
        self.modulesDialog.open()

    def on_PID_clicked(self):
        self.PIDDialog.get_reading()
        self.PIDDialog.open()

    @QtCore.pyqtSlot()
    def on_log_clicked(self):
        """
        Opens directory with log files with current log file selected.
        """

        if platform.system() == "Windows":
            os.startfile(self.log_path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", str(self.log_path)])
        else:
            subprocess.Popen(["xdg-open", str(self.log_path)])

    def _get_nicks(self, sensor_type):
        if self.mercury.connected:
            return list(m.nick for m in self.mercury.modules if type(m) == sensor_type)
        else:
            return []


# noinspection PyArgumentList
class ControlPanel(QtWidgets.QMainWindow):

    MAX_DISPLAY = 3 * 24 * 60 * 60

    def __init__(self, mercury, parent, sensor_name=""):
        super(self.__class__, self).__init__()
        uic.loadUi(PANEL_UI_PATH, self)

        self.mercury = mercury
        self.parent = parent
        connected = self.mercury.connected

        self.sensor_name = sensor_name
        self.temperature = self.get_temperature_module(sensor_name)
        if self.temperature:
            self.feed = MercuryFeed(self.mercury, self.temperature, self.parent.UPDATE_FREQ)
            self.feed.readings_signal.connect(self.update_gui)
            self.feed.readings_signal.connect(self.update_plot)
            self.feed.connected_signal.connect(self.update_gui_connection)
        else:
            self.feed = None

        # set up temperature plot, adjust window margins accordingly
        self.canvas = TemperatureHistoryPlot()
        self.gridLayoutCanvas.addWidget(self.canvas)
        self.horizontalSlider.setMaximum(self.MAX_DISPLAY / 60)

        # connect slider to plot
        self.horizontalSlider.valueChanged.connect(self.on_slider_changed)

        # adapt text edit colors to graph colors
        self.t1_reading.setStyleSheet("color:rgb%s" % str(self.canvas.GREEN))
        self.gf1_edit.setStyleSheet("color:rgb%s" % str(self.canvas.BLUE))
        self.h1_edit.setStyleSheet("color:rgb%s" % str(self.canvas.RED))
        self.gf1_edit.setMinimalStep(0.1)
        self.h1_edit.setMinimalStep(0.1)

        # set up data vectors for plot
        self.xdata = np.array([])
        self.xdata_min_zero = np.array([])
        self.rel_time = np.array([])
        self.ydata_tmpr = np.array([])
        self.ydata_gflw = np.array([])
        self.ydata_htr = np.array([])

        # connect to callbacks
        self.t2_edit.returnPressed.connect(self.change_t_setpoint)
        self.r1_edit.returnPressed.connect(self.change_ramp)
        self.r2_checkbox.clicked.connect(self.change_ramp_auto)
        self.gf1_edit.returnPressed.connect(self.change_flow)
        self.gf2_checkbox.clicked.connect(self.change_flow_auto)
        self.gf3_edit.returnPressed.connect(self.change_flow_min)
        self.h1_edit.returnPressed.connect(self.change_heater)
        self.h2_checkbox.clicked.connect(self.change_heater_auto)

        # enable or disable controls
        self.update_gui_connection(connected)

        # set up logging to file
        self.setup_logging()

    def get_temperature_module(self, sensor_name):
        """
        Updates module list after the new modules have been selected.
        """
        # find all temperature modules
        tmp_modules = [m for m in self.mercury.modules if type(m) is MercuryITC_TEMP]

        # find match for given nick
        match = next((m for m in tmp_modules if m.nick == sensor_name), None)

        if match:
            temperature = match
        elif tmp_modules:
            logger.warning(f'Sensor "{sensor_name}" not found, choosing first module')
            temperature = tmp_modules[0]
            self.sensor_name = tmp_modules[0].nick
        else:
            temperature = None
            logger.warning('No temperature sensors found')

        return temperature

    # =================== BASIC UI SETUP ==========================================

    def on_slider_changed(self):
        # determine first plotted data point
        sv = self.horizontalSlider.value()

        self.timeLabel.setText("Show last %s min" % sv)
        self.canvas.set_xmin(-sv)
        self.canvas.p0.setXRange(-sv, 0)
        self.canvas.p0.enableAutoRange(x=False, y=True)

    def update_gui_connection(self, connected):
        #print(inspect.stack())
        if connected:

            # enable controls
            self.t2_edit.setEnabled(True)
            self.r1_edit.setEnabled(True)
            self.r2_checkbox.setEnabled(True)
            self.gf1_edit.setEnabled(True)
            self.gf2_checkbox.setEnabled(True)
            self.gf3_edit.setEnabled(True)
            self.h1_edit.setEnabled(True)
            self.h2_checkbox.setEnabled(True)

        elif not connected:
            # disable controls
            self.t2_edit.setEnabled(False)
            self.r1_edit.setEnabled(False)
            self.r2_checkbox.setEnabled(False)
            self.gf1_edit.setEnabled(False)
            self.gf2_checkbox.setEnabled(False)
            self.gf3_edit.setEnabled(False)
            self.h1_edit.setEnabled(False)
            self.h2_checkbox.setEnabled(False)

            if self.feed:
                self.feed.worker.terminate = True

    def update_gui(self, readings):
        """
        Parses readings for the MercuryMonitorApp and updates UI accordingly
        """
        # heater signals
        self.h1_label.setText("Heater, %s V:" % readings["HeaterVolt"])
        self.h1_edit.updateValue(readings["HeaterPercent"])

        if self.feed.heater:
            is_heater_auto = readings["HeaterAuto"] == "ON"
            self.h1_edit.setReadOnly(is_heater_auto)
            self.h1_edit.setEnabled(not is_heater_auto)
            self.h2_checkbox.setChecked(is_heater_auto)
            self.h2_checkbox.setEnabled(True)
        else:
            self.h1_edit.setReadOnly(True)
            self.h1_edit.setEnabled(False)
            self.h2_checkbox.setEnabled(False)

        # gas flow signals
        self.gf1_edit.updateValue(readings["FlowPercent"])
        self.gf3_edit.updateValue(readings["FlowMin"])

        if self.feed.gasflow:
            is_gf_auto = readings["FlowAuto"] == "ON"
            self.gf1_edit.setReadOnly(is_gf_auto)
            self.gf1_edit.setEnabled(not is_gf_auto)
            self.gf2_checkbox.setChecked(is_gf_auto)
            self.gf2_checkbox.setEnabled(True)
            self.gf3_edit.setEnabled(True)
        else:
            self.gf1_edit.setEnabled(False)
            self.gf2_checkbox.setEnabled(False)
            self.gf3_edit.setEnabled(False)

        # temperature signals
        self.t1_reading.setText("%s K" % round(readings["Temp"], 3))
        self.t2_edit.updateValue(readings["TempSetpoint"])
        self.r1_edit.updateValue(readings["TempRamp"])

        is_ramp_enable = readings["TempRampEnable"] == "ON"
        self.r2_checkbox.setChecked(is_ramp_enable)

        # alarms
        alarm_str = ""
        for k, v in readings["Alarms"].items():
            alarm_str += "{}: {} ".format(k, v)

        self.alarm_label.setText(alarm_str)

        if alarm_str:
            self.alarm_label.show()
        else:
            self.alarm_label.hide()

    def update_plot(self, readings):
        # append data for plotting
        self.xdata = np.append(self.xdata, time.time())
        self.rel_time = np.append(self.rel_time, time.time())
        self.rel_time[-1] -= self.xdata[0]
        self.ydata_tmpr = np.append(self.ydata_tmpr, readings["Temp"])
        self.ydata_gflw = np.append(self.ydata_gflw, readings["FlowPercent"] / 100)
        self.ydata_htr = np.append(self.ydata_htr, readings["HeaterPercent"] / 100)

        # prevent data vector from exceeding MAX_DISPLAY
        self.xdata = self.xdata[-self.MAX_DISPLAY :]
        self.ydata_tmpr = self.ydata_tmpr[-self.MAX_DISPLAY :]
        self.ydata_gflw = self.ydata_gflw[-self.MAX_DISPLAY :]
        self.ydata_htr = self.ydata_htr[-self.MAX_DISPLAY :]

        # convert xData to minutes and set current time to t = 0
        self.xdata_min_zero = (self.xdata - self.xdata[-1]) / 60

        # update plot
        self.canvas.update_data(
            self.xdata_min_zero, self.ydata_tmpr, self.ydata_gflw, self.ydata_htr
        )

    def clear_plot(self):
        # append data for plotting
        self.xdata = np.array([])
        self.xdata_min_zero = np.array([])
        self.ydata_tmpr = np.array([])
        self.ydata_gflw = np.array([])
        self.ydata_htr = np.array([])

        # update plot
        self.canvas.update_data(
            self.xdata, self.ydata_tmpr, self.ydata_gflw, self.ydata_htr
        )

    def display_message(self, text):
        self.parent.display_message(text)

    def display_error(self, text):
        self.parent.display_error(text)

    # =================== LOGGING DATA ============================================

    def setup_logging(self):
        """
        Save temperature history to log file at '~/.CustomXepr/LOG_FILES/' every 10 min.
        """

        os.makedirs(self.parent.log_path, exist_ok=True)

        # set logging file path
        time_str = time.strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = self.parent.log_path / f"{self.sensor_name}_{time_str}.txt"

        # delete old log files
        now = time.time()
        days_to_keep = 7

        for file in os.scandir(self.parent.log_path):
            if file.stat().st_mtime < now - days_to_keep * 24 * 60 * 60:
                if file.is_file():
                    os.remove(file.path)

        # set up periodic logging
        t_save = 10 # t_save is the time interval to save temperature data (min)

        self.log_timer = QtCore.QTimer()
        self.log_timer.setInterval(t_save * 60 * 1000)
        self.log_timer.setSingleShot(False)  # set to reoccur
        self.log_timer.timeout.connect(self.log_temperature_data)
        self.log_timer.start()

    def save_temperature_data(self, path=None):
        # prompt user for file path if not given
        if path is None:
            text = "Select path for temperature data file:"
            path = QtWidgets.QFileDialog.getSaveFileName(caption=text)
            path = path[0]

        header = "\t".join(
            ["Time (sec)", "Temperature (K)", "Heater (%)", "Gas flow (%)\nStart from {}".format(time.strftime("%Y-%m-%d_%H-%M-%S"))]
        )

        data_matrix = np.concatenate(
            (
                self.rel_time[:, np.newaxis],
                self.ydata_tmpr[:, np.newaxis],
                self.ydata_htr[:, np.newaxis],
                self.ydata_gflw[:, np.newaxis],
            ),
            axis=1,
        )

        # noinspection PyTypeChecker
        np.savetxt(path, data_matrix, delimiter="\t", header=header, fmt="%f")

    def log_temperature_data(self):
        # save temperature data to log file
        if self.mercury.connected:
            self.save_temperature_data(self.log_file)

    # =================== CALLBACKS FOR SETTING CHANGES ===========================

    def change_t_setpoint(self):
        new_t = self.t2_edit.value()

        if 3.5 < new_t < 350.5:
            self.temperature.loop_tset = new_t
            self.feed.worker.readings["TempSetpoint"] = new_t
            self.display_message(f"T_setpoint = {new_t} K")
            print("New temperature setpoint is updated succesfully!")
        else:
            self.display_error(
                "Error: Only temperature setpoints between 3.5 K and 350.5 K allowed."
            )

    def change_ramp(self):
        self.temperature.loop_rset = self.r1_edit.value()
        self.display_message(f"Ramp = {self.r1_edit.value()} K/min")

    def change_ramp_auto(self, checked):
        if checked:
            self.temperature.loop_rena = "ON"
            self.feed.worker.readings["TempRampEnable"] = "ON"
            self.display_message("Ramp is turned ON")
        else:
            self.temperature.loop_rena = "OFF"
            self.feed.worker.readings["TempRampEnable"] = "OFF"
            self.display_message("Ramp is turned OFF")

    def change_flow(self):
        flow_setpoint = self.gf1_edit.value()
        self.temperature.loop_fset = flow_setpoint
        self.feed.worker.readings["FlowSetpoint"] = flow_setpoint
        self.display_message(f"Gas flow = {flow_setpoint}%")

    def change_flow_min(self):
        gmin = self.gf3_edit.value()
        self.feed.gasflow.gmin = gmin
        self.feed.worker.readings["FlowMin"] = gmin
        self.display_message(f"Gas flow min = {gmin}%")

    def change_flow_auto(self, checked):
        if checked:
            self.temperature.loop_faut = "ON"
            self.feed.worker.readings["FlowAuto"] = "ON"
            self.display_message("Gas flow is automatically controlled.")
            self.gf1_edit.setReadOnly(True)
            self.gf1_edit.setEnabled(False)
        else:
            self.temperature.loop_faut = "OFF"
            self.feed.worker.readings["FlowAuto"] = "OFF"
            self.display_message("Gas flow is manually controlled.")
            self.gf1_edit.setReadOnly(False)
            self.gf1_edit.setEnabled(True)

    def change_heater(self):
        heater_setpoint = self.h1_edit.value()
        self.temperature.loop_hset = heater_setpoint
        self.feed.worker.readings["HeaterPercent"] = heater_setpoint
        self.display_message(f"Heater power  = {heater_setpoint}%")

    def change_heater_auto(self, checked):
        if checked:
            self.temperature.loop_enab = "ON"
            self.feed.worker.readings["HeaterAuto"] = "ON"
            self.display_message("Heater is automatically controlled.")
            self.h1_edit.setReadOnly(True)
            self.h1_edit.setEnabled(False)
        else:
            self.temperature.loop_enab = "OFF"
            self.feed.worker.readings["HeaterAuto"] = "OFF"
            self.display_message("Heater is manually controlled.")
            self.h1_edit.setReadOnly(False)
            self.h1_edit.setEnabled(True)

# noinspection PyUnresolvedReferences
class ReadingsTab(QtWidgets.QWidget):

    EXCEPT = ["read", "write", "query", "CAL_INT", "EXCT_TYPES", "TYPES", "clear_cache"]

    def __init__(self, mercury, module):
        super(self.__class__, self).__init__()

        self.module = module
        self.mercury = mercury

        self.name = module.nick
        self.attr = dir(module)

        self.gridLayout = QtWidgets.QGridLayout(self)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout_%s" % self.name)

        self.label = QtWidgets.QLabel(self)
        self.label.setObjectName("label_%s" % self.name)
        self.gridLayout.addWidget(self.label, 0, 0, 1, 2)

        self.comboBox = QtWidgets.QComboBox(self)
        self.comboBox.setObjectName("comboBox_%s" % self.name)
        self.gridLayout.addWidget(self.comboBox, 1, 0, 1, 1)

        self.lineEdit = QtWidgets.QLineEdit(self)
        self.lineEdit.setObjectName("lineEdit_%s" % self.name)
        self.gridLayout.addWidget(self.lineEdit, 1, 1, 1, 1)

        readings = [x for x in self.attr if not (x.startswith("_") or x in self.EXCEPT)]
        self.comboBox.addItems(readings)

        self.comboBox.currentIndexChanged.connect(self.get_reading)
        self.comboBox.currentIndexChanged.connect(self.get_alarms)

    def get_reading(self):
        """Gets readings of selected variable in combobox."""

        reading = getattr(self.module, self.comboBox.currentText())
        if isinstance(reading, tuple):
            reading = "".join(map(str, reading))
        reading = str(reading)
        self.lineEdit.setText(reading)

    def get_alarms(self):
        """Gets alarms of associated module."""

        # get alarms for all modules
        try:
            alarm = self.mercury.alarms[self.module.uid]
        except KeyError:
            alarm = "--"

        self.label.setText("Alarms: %s" % alarm)

class ReadingsOverview(QtWidgets.QWidget):
    def __init__(self, mercury, parent=None):
        super(self.__class__, self).__init__(parent=parent)
        self.setWindowTitle("Readings Overview")
        self.resize(500, 142)
        self.masterGrid = QtWidgets.QGridLayout(self)
        self.masterGrid.setObjectName("gridLayout")

        self.mercury = mercury

        # create main tab widget
        self.tabWidget = QtWidgets.QTabWidget(self)
        self.masterGrid.addWidget(self.tabWidget, 0, 0, 1, 1)

        self.build_tabs()

        # refresh readings every 3 sec
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.get_readings)
        self.timer.start(3000)

    def build_tabs(self):

        # create a tab with combobox and text box for each module
        self.readings_tabs = []
        self.tabWidget.clear()

        for module in self.mercury.modules:
            new_tab = ReadingsTab(self.mercury, module)
            self.readings_tabs.append(new_tab)
            if type(module) is MercuryITC_TEMP:
                self.tabWidget.addTab(new_tab, "Temperature Controller")
            elif type(module) is MercuryITC_HTR:
                self.tabWidget.addTab(new_tab, "Heater")
            else:
                self.tabWidget.addTab(new_tab, "Auxillary Device")

        self.tabWidget.setCurrentIndex(0)

    def get_readings(self):
        """
        Getting alarms of selected tab and update its selected reading, only
        if QWidget is not hidden.
        """
        if self.isVisible():
            self.tabWidget.currentWidget().get_reading()
            self.tabWidget.currentWidget().get_alarms()

    def show(self):
        self.get_readings()
        super().show()


class _NoModule:
    nick = "None"


class ModulesDialog(QtWidgets.QDialog):
    """
    Provides a user dialog to select which gasflow and heater modules are associated
    with a temperature sensor.
    """

    accepted = QtCore.pyqtSignal(object)

    def __init__(self, mercury, parent=None):
        super(self.__class__, self).__init__(parent=parent)
        uic.loadUi(MODULE_DIALOG_UI_PATH, self)

        self.mercury = mercury
        self.update_gui()

    def update_gui(self):

        self.temp_modules = self._get_modules_for_type(MercuryITC_TEMP)
        self.htr_modules = self._get_modules_for_type(MercuryITC_HTR)
        self.aux_modules = self._get_modules_for_type(MercuryITC_AUX)

        self.htr_modules.append(_NoModule())
        self.aux_modules.append(_NoModule())

        self.comboBoxTEMP.clear()
        self.comboBoxHTR.clear()
        self.comboBoxAUX.clear()

        self.comboBoxTEMP.addItems([m.nick for m in self.temp_modules])
        self.comboBoxHTR.addItems([m.nick for m in self.htr_modules])
        self.comboBoxAUX.addItems([m.nick for m in self.aux_modules])

        # get current modules
        if len(self.temp_modules) > 0:
            self.comboBoxTEMP.setCurrentIndex(0)
            self.comboBoxHTR.setCurrentText(self.temp_modules[0].loop_htr)
            self.comboBoxAUX.setCurrentText(self.temp_modules[0].loop_aux)

        # connect callbacks
        self.comboBoxTEMP.currentIndexChanged.connect(self.on_temp_selected)
        self.buttonBox.accepted.connect(self.on_accept)

    def on_temp_selected(self, index):
        # update content of heater and gasflow combo boxes
        self.comboBoxHTR.setCurrentText(self.temp_modules[index].loop_htr)
        self.comboBoxAUX.setCurrentText(self.temp_modules[index].loop_aux)

    def on_accept(self):
        temp_index = self.comboBoxTEMP.currentIndex()
        htr_nick = self.comboBoxHTR.currentText()
        aux_nick = self.comboBoxAUX.currentText()

        # remove heater and gasflow modules from previous loop
        for module in self.temp_modules:
            if module is not self.temp_modules[temp_index]:
                if module.loop_htr == htr_nick:
                    module.loop_htr = "None"
                if module.loop_aux == aux_nick:
                    module.loop_aux = "None"

        # assign heater and gasflow modules to selected loop
        self.temp_modules[temp_index].loop_htr = htr_nick
        self.temp_modules[temp_index].loop_aux = aux_nick

    def _get_modules_for_type(self, sensor_type):
        return [m for m in self.mercury.modules if type(m) is sensor_type]

class PIDDialog(QtWidgets.QDialog):
    """
    Provides a user dialog to select which gasflow and heater modules are associated
    with a temperature sensor.
    """

    def __init__(self, mercury, parent=None):
        super(self.__class__, self).__init__(parent=parent)

        self.mercury = mercury
        self.module = None
        self.initiate_gui()

    def initiate_gui(self):
        self.setWindowTitle("PID")
        self.resize(300, 142)

        main_grid = QtWidgets.QGridLayout()
        main_grid.setSpacing(10)
        self.setLayout(main_grid)

        self.comboBoxTEMP = QtWidgets.QComboBox()
        main_grid.addWidget(self.comboBoxTEMP, 0, 0)

        resources = ["P", "I", "D"]
        self.comboBox = QtWidgets.QComboBox(self)
        self.comboBox.addItems(resources)
        self.comboBox.currentIndexChanged.connect(self.get_reading)
        main_grid.addWidget(self.comboBox, 1, 0)

        self.value = QtWidgets.QDoubleSpinBox()
        self.value.editingFinished.connect(self.set_value)
        main_grid.addWidget(self.value, 1, 1)

        self.temp_modules = self._get_modules_for_type(MercuryITC_TEMP)

        self.comboBoxTEMP.clear()
        self.comboBoxTEMP.addItems([m.nick for m in self.temp_modules])

        # get current modules
        if len(self.temp_modules) > 0:
            self.comboBoxTEMP.setCurrentIndex(0)

        self.comboBoxTEMP.currentIndexChanged.connect(self.update_module)

        self.update_module()
        self.get_reading()

    def _get_modules_for_type(self, sensor_type):
        return [m for m in self.mercury.modules if type(m) is sensor_type]

    def update_module(self):
        if len(self.temp_modules) > 0:
            self.module = self.temp_modules[self.comboBoxTEMP.currentIndex()]

    def get_reading(self):
        if self.module is not None:
            """Gets readings of selected variable in combobox."""
            if self.comboBox.currentText() == "P":
                reading = getattr(self.module, "loop_p")
            elif self.comboBox.currentText() == "I":
                reading = getattr(self.module, "loop_i")
            else:
                reading = getattr(self.module, "loop_d")
            if isinstance(reading, tuple):
                reading = "".join(map(str, reading))
            if reading != "INVALID":
                reading = float(reading)
                self.value.setValue(reading)
                self.value.setEnabled(True)
            else:
                self.value.setEnabled(False)

    def set_value(self):
        if self.comboBox.currentText() == "P":
            self.module.loop_p = self.value.value()
        elif self.comboBox.currentText() == "I":
            self.module.loop_i = self.value.value()
        else:
            self.module.loop_d = self.value.value()

# from https://github.com/nlamprian/pyqt5-led-indicator-widget/blob/master/LedIndicatorWidget.py
class QLedIndicator(QAbstractButton):
    scaledSize = 1000.0

    def __init__(self, color='green', parent=None):  # added a color option to use red or orange
        QAbstractButton.__init__(self, parent)

        self.setMinimumSize(24, 24)
        self.setCheckable(True)

        # prevent user from changing indicator color by clicking
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
        else:  # default to green if user does not give valid option
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

def run():

    from mercuryitc import MercuryITC
    from mercurygui.config.main import CONF

    app = QtWidgets.QApplication(sys.argv)

    mercury_address = CONF.get("Connection", "VISA_ADDRESS")
    visa_library = CONF.get("Connection", "VISA_LIBRARY")

    mercury = MercuryITC(mercury_address, visa_library, open_timeout=1)

    mercury_gui = MercuryMonitorApp(mercury)
    mercury_gui.show()

    app.exec_()


if __name__ == "__main__":
    run()
