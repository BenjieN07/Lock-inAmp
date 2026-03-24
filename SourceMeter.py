import numpy as np
from pymeasure.instruments.keithley.keithley2450 import *
from pymeasure.instruments.keithley.keithley2400 import *
import pyvisa
from QCL_interface import *
from PyQt5.QtTest import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

class SourceMeter(QFrame):
    def __init__(self):
        super().__init__()
        self.setGeometry(300, 50, 1000, 900)  # X, Y, Width, Height, in reference to Top Left of screen
        self.show()
        self.initUI()
        self.setWindowTitle("Keithley")
        self.enabled1 = False
        self.connected1 = False
        self.enabled2 = False
        self.connected2 = False
        self.in_voltage_ramping = False
        self.in_current_ramping = False

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
            if resource[i] == "GPIB0::24::INSTR":
                resource[i] += " (default)"

        device_lb1 = QLabel("Device 1")
        device_lb1.setFont(QFont("Times", 15, QFont.Bold))
        main_grid.addWidget(device_lb1, 0, 0, 1, 2, Qt.AlignCenter)
        device_lb2 = QLabel("Device 2")
        device_lb2.setFont(QFont("Times", 15, QFont.Bold))
        main_grid.addWidget(device_lb2, 0, 2, 1, 2, Qt.AlignCenter)

        self.keitheley_selection_box1 = QComboBox()
        self.keitheley_selection_box1.addItem("Keithley 2450")
        self.keitheley_selection_box1.addItem("Keithley 2400")
        main_grid.addWidget(self.keitheley_selection_box1, 1, 0, 1, 1, Qt.AlignCenter)

        connection_hbox1 = QHBoxLayout()
        # create a combo box to allow the user to connect with a given instrument then add all resources
        self.connection_box1 = QComboBox()
        self.connection_box1.addItem('Connect to keithley...')
        self.connection_box1.addItems(resource)
        self.connection_box1.currentIndexChanged.connect(self.connectInstrument1)
        connection_hbox1.addWidget(self.connection_box1)
        # create a label to show connection of the instrument with check or cross mark
        self.connection_indicator1 = QLabel(u'\u274c ')  # cross mark by default because not connected yet
        connection_hbox1.addWidget(self.connection_indicator1)
        main_grid.addLayout(connection_hbox1, 1, 1, 1, 1, Qt.AlignCenter)

        self.keitheley_selection_box2 = QComboBox()
        self.keitheley_selection_box2.addItem("Keithley 2450")
        self.keitheley_selection_box2.addItem("Keithley 2400")
        main_grid.addWidget(self.keitheley_selection_box2, 1, 2, 1, 1, Qt.AlignCenter)

        connection_hbox2 = QHBoxLayout()
        # create a combo box to allow the user to connect with a given instrument then add all resources
        self.connection_box2 = QComboBox()
        self.connection_box2.addItem('Connect to keithley...')
        self.connection_box2.addItems(resource)
        self.connection_box2.currentIndexChanged.connect(self.connectInstrument2)
        connection_hbox2.addWidget(self.connection_box2)
        # create a label to show connection of the instrument with check or cross mark
        self.connection_indicator2 = QLabel(u'\u274c ')  # cross mark by default because not connected yet
        connection_hbox2.addWidget(self.connection_indicator2)
        main_grid.addLayout(connection_hbox2, 1, 3, 1, 1, Qt.AlignCenter)

        V_lb1 = QLabel("Voltage")
        I_lb1 = QLabel("Current")
        main_grid.addWidget(V_lb1, 2, 0, 1, 1, Qt.AlignCenter)
        main_grid.addWidget(I_lb1, 2, 1, 1, 1, Qt.AlignCenter)

        self.V_value_lb1 = QLabel("")
        self.I_value_lb1 = QLabel("")
        main_grid.addWidget(self.V_value_lb1, 3, 0, 1, 1, Qt.AlignCenter)
        main_grid.addWidget(self.I_value_lb1, 3, 1, 1, 1, Qt.AlignCenter)

        V_lb2 = QLabel("Voltage")
        I_lb2 = QLabel("Current")
        main_grid.addWidget(V_lb2, 2, 2, 1, 1, Qt.AlignCenter)
        main_grid.addWidget(I_lb2, 2, 3, 1, 1, Qt.AlignCenter)

        self.V_value_lb2 = QLabel("")
        self.I_value_lb2 = QLabel("")
        main_grid.addWidget(self.V_value_lb2, 3, 2, 1, 1, Qt.AlignCenter)
        main_grid.addWidget(self.I_value_lb2, 3, 3, 1, 1, Qt.AlignCenter)

        self.tabs = QTabWidget()
        self.V_tab = QWidget()
        self.I_tab = QWidget()
        self.tabs.addTab(self.V_tab,"Voltage")
        self.tabs.addTab(self.I_tab,"Current")
        self.tabs.setFixedWidth(1000)  # width of the tab
        main_grid.addWidget(self.tabs, 4, 0, 3, 4, Qt.AlignCenter)

        voltage_grid = QGridLayout()
        voltage_grid.setSpacing(10)
        self.V_tab.setLayout(voltage_grid)

        source_voltage_hbox1 = QHBoxLayout()
        source_voltage_lb1 = QLabel("Source voltage 1 ")
        self.source_voltage_sb1 = QDoubleSpinBox()
        self.source_voltage_sb1.setDecimals(3)
        self.source_voltage_sb1.setRange(-100, 100)
        source_voltage_unit_lb1 = QLabel("V")
        source_voltage_hbox1.addWidget(source_voltage_lb1)
        source_voltage_hbox1.addWidget(self.source_voltage_sb1)
        source_voltage_hbox1.addWidget(source_voltage_unit_lb1)
        voltage_grid.addLayout(source_voltage_hbox1, 0, 0, 1, 2, Qt.AlignCenter)

        compliance_current_hbox1 = QHBoxLayout()
        compliance_current_lb1 = QLabel("Compliance current 1 ")
        self.compliance_current_sb1 = QDoubleSpinBox()
        self.compliance_current_sb1.setDecimals(1)
        self.compliance_current_sb1.setRange(0, 1e8)
        self.compliance_current_sb1.setValue(1000)
        compliance_current_unit_lb1 = QLabel("nA")
        compliance_current_hbox1.addWidget(compliance_current_lb1)
        compliance_current_hbox1.addWidget(self.compliance_current_sb1)
        compliance_current_hbox1.addWidget(compliance_current_unit_lb1)
        voltage_grid.addLayout(compliance_current_hbox1, 1, 0, 1, 2, Qt.AlignCenter)

        source_voltage_range_hbox1 = QHBoxLayout()
        source_voltage_range_lb1 = QLabel("Source voltage range 1 ")
        self.source_voltage_range_sb1 = QDoubleSpinBox()
        self.source_voltage_range_sb1.setDecimals(3)
        self.source_voltage_range_sb1.setRange(0, 210)
        self.source_voltage_range_sb1.setValue(10)
        source_voltage_range_unit_lb1 = QLabel("V")
        source_voltage_range_hbox1.addWidget(source_voltage_range_lb1)
        source_voltage_range_hbox1.addWidget(self.source_voltage_range_sb1)
        source_voltage_range_hbox1.addWidget(source_voltage_range_unit_lb1)
        voltage_grid.addLayout(source_voltage_range_hbox1, 2, 0, 1, 2, Qt.AlignCenter)

        source_voltage_hbox2 = QHBoxLayout()
        source_voltage_lb2 = QLabel("Source voltage 2 ")
        self.source_voltage_sb2 = QDoubleSpinBox()
        self.source_voltage_sb2.setDecimals(3)
        self.source_voltage_sb2.setRange(-100, 100)
        source_voltage_unit_lb2 = QLabel("V")
        source_voltage_hbox2.addWidget(source_voltage_lb2)
        source_voltage_hbox2.addWidget(self.source_voltage_sb2)
        source_voltage_hbox2.addWidget(source_voltage_unit_lb2)
        voltage_grid.addLayout(source_voltage_hbox2, 0, 2, 1, 2, Qt.AlignCenter)

        compliance_current_hbox2 = QHBoxLayout()
        compliance_current_lb2 = QLabel("Compliance current 2 ")
        self.compliance_current_sb2 = QDoubleSpinBox()
        self.compliance_current_sb2.setDecimals(1)
        self.compliance_current_sb2.setRange(0, 1e8)
        self.compliance_current_sb2.setValue(1000)
        compliance_current_unit_lb2 = QLabel("nA")
        compliance_current_hbox2.addWidget(compliance_current_lb2)
        compliance_current_hbox2.addWidget(self.compliance_current_sb2)
        compliance_current_hbox2.addWidget(compliance_current_unit_lb2)
        voltage_grid.addLayout(compliance_current_hbox2, 1, 2, 1, 2, Qt.AlignCenter)

        source_voltage_range_hbox2 = QHBoxLayout()
        source_voltage_range_lb2 = QLabel("Source voltage range 2 ")
        self.source_voltage_range_sb2 = QDoubleSpinBox()
        self.source_voltage_range_sb2.setDecimals(3)
        self.source_voltage_range_sb2.setRange(0, 210)
        self.source_voltage_range_sb2.setValue(10)
        source_voltage_range_unit_lb2 = QLabel("V")
        source_voltage_range_hbox2.addWidget(source_voltage_range_lb2)
        source_voltage_range_hbox2.addWidget(self.source_voltage_range_sb2)
        source_voltage_range_hbox2.addWidget(source_voltage_range_unit_lb2)
        voltage_grid.addLayout(source_voltage_range_hbox2, 2, 2, 1, 2, Qt.AlignCenter)

        current_grid = QGridLayout()
        current_grid.setSpacing(10)
        self.I_tab.setLayout(current_grid)

        source_current_hbox1 = QHBoxLayout()
        source_current_lb1 = QLabel("Source current 1 ")
        self.source_current_sb1 = QDoubleSpinBox()
        self.source_current_sb1.setDecimals(3)
        source_current_unit_lb1 = QLabel("A")
        source_current_hbox1.addWidget(source_current_lb1)
        source_current_hbox1.addWidget(self.source_current_sb1)
        source_current_hbox1.addWidget(source_current_unit_lb1)
        current_grid.addLayout(source_current_hbox1, 0, 0, 1, 2, Qt.AlignCenter)

        compliance_voltage_hbox1 = QHBoxLayout()
        compliance_voltage_lb1 = QLabel("Compliance voltage 1 ")
        self.compliance_voltage_sb1 = QDoubleSpinBox()
        self.compliance_voltage_sb1.setDecimals(3)
        compliance_voltage_unit_lb1 = QLabel("V")
        compliance_voltage_hbox1.addWidget(compliance_voltage_lb1)
        compliance_voltage_hbox1.addWidget(self.compliance_voltage_sb1)
        compliance_voltage_hbox1.addWidget(compliance_voltage_unit_lb1)
        current_grid.addLayout(compliance_voltage_hbox1, 1, 0, 1, 2, Qt.AlignCenter)

        source_current_range_hbox1 = QHBoxLayout()
        source_current_range_lb1 = QLabel("Source current range 1 ")
        self.source_current_range_sb1 = QDoubleSpinBox()
        self.source_current_range_sb1.setDecimals(3)
        self.source_current_range_sb1.setRange(0, 1.05)
        self.source_current_range_sb1.setValue(1)
        source_current_range_unit_lb1 = QLabel("A")
        source_current_range_hbox1.addWidget(source_current_range_lb1)
        source_current_range_hbox1.addWidget(self.source_current_range_sb1)
        source_current_range_hbox1.addWidget(source_current_range_unit_lb1)
        current_grid.addLayout(source_current_range_hbox1, 2, 0, 1, 2, Qt.AlignCenter)

        source_current_hbox2 = QHBoxLayout()
        source_current_lb2 = QLabel("Source current 2 ")
        self.source_current_sb2 = QDoubleSpinBox()
        self.source_current_sb2.setDecimals(3)
        source_current_unit_lb2 = QLabel("A")
        source_current_hbox2.addWidget(source_current_lb2)
        source_current_hbox2.addWidget(self.source_current_sb2)
        source_current_hbox2.addWidget(source_current_unit_lb2)
        current_grid.addLayout(source_current_hbox2, 0, 2, 1, 2, Qt.AlignCenter)

        compliance_voltage_hbox2 = QHBoxLayout()
        compliance_voltage_lb2 = QLabel("Compliance voltage 2 ")
        self.compliance_voltage_sb2 = QDoubleSpinBox()
        self.compliance_voltage_sb2.setDecimals(3)
        compliance_voltage_unit_lb2 = QLabel("V")
        compliance_voltage_hbox2.addWidget(compliance_voltage_lb2)
        compliance_voltage_hbox2.addWidget(self.compliance_voltage_sb2)
        compliance_voltage_hbox2.addWidget(compliance_voltage_unit_lb2)
        current_grid.addLayout(compliance_voltage_hbox2, 1, 2, 1, 2, Qt.AlignCenter)

        source_current_range_hbox2 = QHBoxLayout()
        source_current_range_lb2 = QLabel("Source current range 2 ")
        self.source_current_range_sb2 = QDoubleSpinBox()
        self.source_current_range_sb2.setDecimals(3)
        self.source_current_range_sb2.setRange(0, 1.05)
        self.source_current_range_sb2.setValue(1)
        source_current_range_unit_lb2 = QLabel("A")
        source_current_range_hbox2.addWidget(source_current_range_lb2)
        source_current_range_hbox2.addWidget(self.source_current_range_sb2)
        source_current_range_hbox2.addWidget(source_current_range_unit_lb2)
        current_grid.addLayout(source_current_range_hbox2, 2, 2, 1, 2, Qt.AlignCenter)

        enable_hbox1 = QHBoxLayout()
        self.enable_btn1 = QPushButton('Enable/Disable source 1')
        self.enable_btn1.setEnabled(False)
        self.enable_btn1.clicked.connect(self.toggleEnabled1)
        enable_hbox1.addWidget(self.enable_btn1)
        self.enable_ind1 = QLedIndicator('orange')
        enable_hbox1.addWidget(self.enable_ind1)
        main_grid.addLayout(enable_hbox1, 7, 0, 1, 2, Qt.AlignCenter)

        enable_hbox2 = QHBoxLayout()
        self.enable_btn2 = QPushButton('Enable/Disable source 2')
        self.enable_btn2.setEnabled(False)
        self.enable_btn2.clicked.connect(self.toggleEnabled2)
        enable_hbox2.addWidget(self.enable_btn2)
        self.enable_ind2 = QLedIndicator('orange')
        enable_hbox2.addWidget(self.enable_ind2)
        main_grid.addLayout(enable_hbox2, 7, 2, 1, 2, Qt.AlignCenter)

        ramp_lb = QLabel("Ramp")
        ramp_lb.setFont(QFont('Times', 15))
        main_grid.addWidget(ramp_lb, 8, 0, 2, 1, Qt.AlignCenter)

        self.action_cb = QComboBox()
        self.action_cb.addItem("Fixed")
        self.action_cb.addItem("Ramp up")
        self.action_cb.addItem("Ramp down")
        self.action_cb.addItem("Cycle up")
        self.action_cb.addItem("Cycle down")
        self.action_cb.setEnabled(False)
        self.action_cb.setFixedWidth(150)
        self.action_cb.setFixedHeight(40)
        self.action_cb.setFont(QFont('Times', 15))
        self.action_cb.currentIndexChanged.connect(self.ramping)
        main_grid.addWidget(self.action_cb, 8, 1, 2, 2, Qt.AlignCenter)

        cycle_times_hb = QHBoxLayout()
        cycle_times_lb = QLabel("Cycle times")
        self.cycle_times_sb = QSpinBox()
        self.cycle_times_sb.setMinimum(0)
        self.cycle_times_sb.setValue(1)
        self.cycle_times_sb.setFixedWidth(40)
        cycle_times_hb.addWidget(cycle_times_lb)
        cycle_times_hb.addWidget(self.cycle_times_sb)
        main_grid.addLayout(cycle_times_hb, 8, 3, 2, 1, Qt.AlignCenter)

        self.ramp_tabs = QTabWidget()
        self.V_ramp_tab = QWidget()
        self.I_ramp_tab = QWidget()
        self.ramp_tabs.addTab(self.V_ramp_tab,"Voltage")
        self.ramp_tabs.addTab(self.I_ramp_tab,"Current")
        #self.ramp_tabs.setFixedWidth(1000)  # width of the tab
        main_grid.addWidget(self.ramp_tabs, 10, 0, 8, 4, Qt.AlignCenter)

        voltage_ramp_grid = QGridLayout()
        voltage_ramp_grid.setSpacing(10)
        self.V_ramp_tab.setLayout(voltage_ramp_grid)

        voltage_up_lim_hbox1 = QHBoxLayout()
        voltage_up_lim_lb1 = QLabel("Up limit 1 (V)")
        self.voltage_up_lim_sb1 = QDoubleSpinBox()
        self.voltage_up_lim_sb1.setRange(0.01, 210)
        self.voltage_up_lim_sb1.setValue(10)
        self.voltage_up_lim_sb1.editingFinished.connect(lambda: self.voltage_lim_balance(1))
        voltage_up_lim_hbox1.addWidget(voltage_up_lim_lb1)
        voltage_up_lim_hbox1.addWidget(self.voltage_up_lim_sb1)
        voltage_ramp_grid.addLayout(voltage_up_lim_hbox1, 0, 0, 1, 1, Qt.AlignCenter)

        voltage_down_lim_hbox1 = QHBoxLayout()
        voltage_down_lim_lb1 = QLabel("Down limit 1 (V)")
        self.voltage_down_lim_sb1 = QDoubleSpinBox()
        self.voltage_down_lim_sb1.setRange(-210, 9.99)
        self.voltage_down_lim_sb1.editingFinished.connect(lambda: self.voltage_lim_balance(1))
        voltage_down_lim_hbox1.addWidget(voltage_down_lim_lb1)
        voltage_down_lim_hbox1.addWidget(self.voltage_down_lim_sb1)
        voltage_ramp_grid.addLayout(voltage_down_lim_hbox1, 0, 1, 1, 1, Qt.AlignCenter)

        voltage_up_speed_hbox1 = QHBoxLayout()
        voltage_up_speed_lb1 = QLabel("Up speed 1 (mV/s)")
        self.voltage_up_speed_sb1 = QDoubleSpinBox()
        self.voltage_up_speed_sb1.setRange(0, 210000)
        self.voltage_up_speed_sb1.setValue(100)
        self.voltage_up_speed_sb1.editingFinished.connect(lambda: self.voltage_speed_balance("up 1"))
        voltage_up_speed_hbox1.addWidget(voltage_up_speed_lb1)
        voltage_up_speed_hbox1.addWidget(self.voltage_up_speed_sb1)
        voltage_ramp_grid.addLayout(voltage_up_speed_hbox1, 1, 0, 1, 1, Qt.AlignCenter)

        voltage_down_speed_hbox1 = QHBoxLayout()
        voltage_down_speed_lb1 = QLabel("Down speed 1 (mV/s)")
        self.voltage_down_speed_sb1 = QDoubleSpinBox()
        self.voltage_down_speed_sb1.setRange(0, 210000)
        self.voltage_down_speed_sb1.setValue(100)
        self.voltage_down_speed_sb1.editingFinished.connect(lambda: self.voltage_speed_balance("down 1"))
        voltage_down_speed_hbox1.addWidget(voltage_down_speed_lb1)
        voltage_down_speed_hbox1.addWidget(self.voltage_down_speed_sb1)
        voltage_ramp_grid.addLayout(voltage_down_speed_hbox1, 1, 1, 1, 1, Qt.AlignCenter)

        voltage_up_step_size_vbox1 = QVBoxLayout()
        voltage_up_step_size_lb1 = QLabel("Up step size 1 (mV)")
        self.voltage_up_step_size_sb1 = QDoubleSpinBox()
        self.voltage_up_step_size_sb1.setRange(0, 1e4)
        self.voltage_up_step_size_sb1.setValue(100)
        self.voltage_up_step_size_sb1.editingFinished.connect(lambda: self.voltage_step_size_balance("up 1"))
        voltage_up_step_size_vbox1.addWidget(voltage_up_step_size_lb1)
        voltage_up_step_size_vbox1.addWidget(self.voltage_up_step_size_sb1)
        voltage_ramp_grid.addLayout(voltage_up_step_size_vbox1, 2, 0, 1, 1, Qt.AlignCenter)

        voltage_up_points_vbox1 = QVBoxLayout()
        voltage_up_points_lb1 = QLabel("Up points 1")
        self.voltage_up_points_sb1 = QSpinBox()
        self.voltage_up_points_sb1.setRange(1, int(1e4))
        self.voltage_up_points_sb1.setValue(100)
        self.voltage_up_points_sb1.editingFinished.connect(lambda: self.voltage_points_balance("up 1"))
        voltage_up_points_vbox1.addWidget(voltage_up_points_lb1)
        voltage_up_points_vbox1.addWidget(self.voltage_up_points_sb1)
        voltage_ramp_grid.addLayout(voltage_up_points_vbox1, 2, 1, 1, 1, Qt.AlignCenter)

        voltage_down_step_size_vbox1 = QVBoxLayout()
        voltage_down_step_size_lb1 = QLabel("Down step size 1 (mV)")
        self.voltage_down_step_size_sb1 = QDoubleSpinBox()
        self.voltage_down_step_size_sb1.setRange(0, 1e4)
        self.voltage_down_step_size_sb1.setValue(100)
        self.voltage_down_step_size_sb1.editingFinished.connect(lambda: self.voltage_step_size_balance("down 1"))
        voltage_down_step_size_vbox1.addWidget(voltage_down_step_size_lb1)
        voltage_down_step_size_vbox1.addWidget(self.voltage_down_step_size_sb1)
        voltage_ramp_grid.addLayout(voltage_down_step_size_vbox1, 3, 0, 1, 1, Qt.AlignCenter)

        voltage_down_points_vbox1 = QVBoxLayout()
        voltage_down_points_lb1 = QLabel("Down points 1")
        self.voltage_down_points_sb1 = QSpinBox()
        self.voltage_down_points_sb1.setRange(1, int(1e4))
        self.voltage_down_points_sb1.setValue(100)
        self.voltage_down_points_sb1.editingFinished.connect(lambda: self.voltage_points_balance("down 1"))
        voltage_down_points_vbox1.addWidget(voltage_down_points_lb1)
        voltage_down_points_vbox1.addWidget(self.voltage_down_points_sb1)
        voltage_ramp_grid.addLayout(voltage_down_points_vbox1, 3, 1, 1, 1, Qt.AlignCenter)

        voltage_up_lim_hbox2 = QHBoxLayout()
        voltage_up_lim_lb2 = QLabel("Up limit 2 (V)")
        self.voltage_up_lim_sb2 = QDoubleSpinBox()
        self.voltage_up_lim_sb2.setRange(0.01, 210)
        self.voltage_up_lim_sb2.setValue(10)
        self.voltage_up_lim_sb2.editingFinished.connect(lambda: self.voltage_lim_balance(2))
        voltage_up_lim_hbox2.addWidget(voltage_up_lim_lb2)
        voltage_up_lim_hbox2.addWidget(self.voltage_up_lim_sb2)
        voltage_ramp_grid.addLayout(voltage_up_lim_hbox2, 0, 2, 1, 1, Qt.AlignCenter)

        voltage_down_lim_hbox2 = QHBoxLayout()
        voltage_down_lim_lb2 = QLabel("Down limit 2 (V)")
        self.voltage_down_lim_sb2 = QDoubleSpinBox()
        self.voltage_down_lim_sb2.setRange(-210, 9.99)
        self.voltage_down_lim_sb2.editingFinished.connect(lambda: self.voltage_lim_balance(2))
        voltage_down_lim_hbox2.addWidget(voltage_down_lim_lb2)
        voltage_down_lim_hbox2.addWidget(self.voltage_down_lim_sb2)
        voltage_ramp_grid.addLayout(voltage_down_lim_hbox2, 0, 3, 1, 1, Qt.AlignCenter)

        voltage_up_speed_hbox2 = QHBoxLayout()
        voltage_up_speed_lb2 = QLabel("Up speed 2 (mV/s)")
        self.voltage_up_speed_sb2 = QDoubleSpinBox()
        self.voltage_up_speed_sb2.setRange(0, 210000)
        self.voltage_up_speed_sb2.setValue(100)
        self.voltage_up_speed_sb2.editingFinished.connect(lambda: self.voltage_speed_balance("up 2"))
        voltage_up_speed_hbox2.addWidget(voltage_up_speed_lb2)
        voltage_up_speed_hbox2.addWidget(self.voltage_up_speed_sb2)
        voltage_ramp_grid.addLayout(voltage_up_speed_hbox2, 1, 2, 1, 1, Qt.AlignCenter)

        voltage_down_speed_hbox2 = QHBoxLayout()
        voltage_down_speed_lb2 = QLabel("Down speed 2 (mV/s)")
        self.voltage_down_speed_sb2 = QDoubleSpinBox()
        self.voltage_down_speed_sb2.setRange(0, 210000)
        self.voltage_down_speed_sb2.setValue(100)
        self.voltage_down_speed_sb2.editingFinished.connect(lambda: self.voltage_speed_balance("down 2"))
        voltage_down_speed_hbox2.addWidget(voltage_down_speed_lb2)
        voltage_down_speed_hbox2.addWidget(self.voltage_down_speed_sb2)
        voltage_ramp_grid.addLayout(voltage_down_speed_hbox2, 1, 3, 1, 1, Qt.AlignCenter)

        voltage_up_step_size_vbox2 = QVBoxLayout()
        voltage_up_step_size_lb2 = QLabel("Up step size 2 (mV)")
        self.voltage_up_step_size_sb2 = QDoubleSpinBox()
        self.voltage_up_step_size_sb2.setRange(0, 1e4)
        self.voltage_up_step_size_sb2.setValue(100)
        self.voltage_up_step_size_sb2.editingFinished.connect(lambda: self.voltage_step_size_balance("up 2"))
        voltage_up_step_size_vbox2.addWidget(voltage_up_step_size_lb2)
        voltage_up_step_size_vbox2.addWidget(self.voltage_up_step_size_sb2)
        voltage_ramp_grid.addLayout(voltage_up_step_size_vbox2, 2, 2, 1, 1, Qt.AlignCenter)

        voltage_up_points_vbox2 = QVBoxLayout()
        voltage_up_points_lb2 = QLabel("Up points 2")
        self.voltage_up_points_sb2 = QSpinBox()
        self.voltage_up_points_sb2.setRange(1, int(1e4))
        self.voltage_up_points_sb2.setValue(100)
        self.voltage_up_points_sb2.editingFinished.connect(lambda: self.voltage_points_balance("up 2"))
        voltage_up_points_vbox2.addWidget(voltage_up_points_lb2)
        voltage_up_points_vbox2.addWidget(self.voltage_up_points_sb2)
        voltage_ramp_grid.addLayout(voltage_up_points_vbox2, 2, 3, 1, 1, Qt.AlignCenter)

        voltage_down_step_size_vbox2 = QVBoxLayout()
        voltage_down_step_size_lb2 = QLabel("Down step size 2 (mV)")
        self.voltage_down_step_size_sb2 = QDoubleSpinBox()
        self.voltage_down_step_size_sb2.setRange(0, 1e4)
        self.voltage_down_step_size_sb2.setValue(100)
        self.voltage_down_step_size_sb2.editingFinished.connect(lambda: self.voltage_step_size_balance("down 2"))
        voltage_down_step_size_vbox2.addWidget(voltage_down_step_size_lb2)
        voltage_down_step_size_vbox2.addWidget(self.voltage_down_step_size_sb2)
        voltage_ramp_grid.addLayout(voltage_down_step_size_vbox2, 3, 2, 1, 1, Qt.AlignCenter)

        voltage_down_points_vbox2 = QVBoxLayout()
        voltage_down_points_lb2 = QLabel("Down points 2")
        self.voltage_down_points_sb2 = QSpinBox()
        self.voltage_down_points_sb2.setRange(1, int(1e4))
        self.voltage_down_points_sb2.setValue(100)
        self.voltage_down_points_sb2.editingFinished.connect(lambda: self.voltage_points_balance("down 2"))
        voltage_down_points_vbox2.addWidget(voltage_down_points_lb2)
        voltage_down_points_vbox2.addWidget(self.voltage_down_points_sb2)
        voltage_ramp_grid.addLayout(voltage_down_points_vbox2, 3, 3, 1, 1, Qt.AlignCenter)

        self.voltage_figure = plt.figure()
        self.voltage_F = FigureCanvas(self.voltage_figure)
        self.voltage_axes = self.voltage_figure.add_subplot(111)
        self.voltage_F.figure.subplots_adjust(left=0.2,
                    bottom=0.15,
                    right=0.7,
                    top=0.9,
                    wspace=0.4,
                    hspace=0.4)
        self.voltage_axes.set_xlabel(r'Source 1 (V)')
        self.voltage_axes.set_ylabel(r'Source 2 (V)')
        self.voltage_axes.set_xlim([0, 10])
        self.voltage_axes.set_ylim([0, 10])
        self.voltage_axes.grid()
        self.voltage_sweep_curve, = self.voltage_axes.plot(np.linspace(self.voltage_down_lim_sb1.value(), self.voltage_up_lim_sb1.value(), 100, endpoint=True), np.linspace(self.voltage_down_lim_sb2.value(), self.voltage_up_lim_sb2.value(), 100, endpoint=True), color = 'b', linestyle = '-', label="Sweep")
        self.voltage_now_curve, = self.voltage_axes.plot([0], [0], marker="o", color = 'r', label="Now")
        self.voltage_axes.legend(bbox_to_anchor =(1.5, 1))
        voltage_ramp_grid.addWidget(self.voltage_F, 4, 0, 4, 4, Qt.AlignCenter)

        current_ramp_grid = QGridLayout()
        current_ramp_grid.setSpacing(10)
        self.I_ramp_tab.setLayout(current_ramp_grid)

        current_up_lim_hbox1 = QHBoxLayout()
        current_up_lim_lb1 = QLabel("Up limit 1 (A)")
        self.current_up_lim_sb1 = QDoubleSpinBox()
        self.current_up_lim_sb1.setRange(0, 1.05)
        self.current_up_lim_sb1.setValue(1)
        self.current_up_lim_sb1.editingFinished.connect(lambda: self.current_lim_balance(1))
        current_up_lim_hbox1.addWidget(current_up_lim_lb1)
        current_up_lim_hbox1.addWidget(self.current_up_lim_sb1)
        current_ramp_grid.addLayout(current_up_lim_hbox1, 0, 0, 1, 1, Qt.AlignCenter)

        current_down_lim_hbox1 = QHBoxLayout()
        current_down_lim_lb1 = QLabel("Down limit 1 (A)")
        self.current_down_lim_sb1 = QDoubleSpinBox()
        self.current_down_lim_sb1.setRange(0, 1.05)
        self.current_down_lim_sb1.editingFinished.connect(lambda: self.current_lim_balance(1))
        current_down_lim_hbox1.addWidget(current_down_lim_lb1)
        current_down_lim_hbox1.addWidget(self.current_down_lim_sb1)
        current_ramp_grid.addLayout(current_down_lim_hbox1, 0, 1, 1, 1, Qt.AlignCenter)

        current_up_speed_hbox1 = QHBoxLayout()
        current_up_speed_lb1 = QLabel("Up speed 1 (mA/s)")
        self.current_up_speed_sb1 = QDoubleSpinBox()
        self.current_up_speed_sb1.setRange(0, 1050)
        self.current_up_speed_sb1.setValue(10)
        self.current_up_speed_sb1.editingFinished.connect(lambda: self.current_speed_balance("up 1"))
        current_up_speed_hbox1.addWidget(current_up_speed_lb1)
        current_up_speed_hbox1.addWidget(self.current_up_speed_sb1)
        current_ramp_grid.addLayout(current_up_speed_hbox1, 1, 0, 1, 1, Qt.AlignCenter)

        current_down_speed_hbox1 = QHBoxLayout()
        current_down_speed_lb1 = QLabel("Down speed 1 (mA/s)")
        self.current_down_speed_sb1 = QDoubleSpinBox()
        self.current_down_speed_sb1.setRange(0, 1050)
        self.current_down_speed_sb1.setValue(10)
        self.current_down_speed_sb1.editingFinished.connect(lambda: self.current_speed_balance("down 1"))
        current_down_speed_hbox1.addWidget(current_down_speed_lb1)
        current_down_speed_hbox1.addWidget(self.current_down_speed_sb1)
        current_ramp_grid.addLayout(current_down_speed_hbox1, 1, 1, 1, 1, Qt.AlignCenter)

        current_up_step_size_vbox1 = QVBoxLayout()
        current_up_step_size_lb1 = QLabel("Up step size 1 (mA)")
        self.current_up_step_size_sb1 = QDoubleSpinBox()
        self.current_up_step_size_sb1.setRange(0, 1e4)
        self.current_up_step_size_sb1.setValue(10)
        self.current_up_step_size_sb1.editingFinished.connect(lambda: self.current_step_size_balance("up 1"))
        current_up_step_size_vbox1.addWidget(current_up_step_size_lb1)
        current_up_step_size_vbox1.addWidget(self.current_up_step_size_sb1)
        current_ramp_grid.addLayout(current_up_step_size_vbox1, 2, 0, 1, 1, Qt.AlignCenter)

        current_up_points_vbox1 = QVBoxLayout()
        current_up_points_lb1 = QLabel("Up points 1")
        self.current_up_points_sb1 = QSpinBox()
        self.current_up_points_sb1.setRange(1, int(1e4))
        self.current_up_points_sb1.setValue(100)
        self.current_up_points_sb1.editingFinished.connect(lambda: self.current_points_balance("up 1"))
        current_up_points_vbox1.addWidget(current_up_points_lb1)
        current_up_points_vbox1.addWidget(self.current_up_points_sb1)
        current_ramp_grid.addLayout(current_up_points_vbox1, 2, 1, 1, 1, Qt.AlignCenter)

        current_down_step_size_vbox1 = QVBoxLayout()
        current_down_step_size_lb1 = QLabel("Down step size 1 (mA)")
        self.current_down_step_size_sb1 = QDoubleSpinBox()
        self.current_down_step_size_sb1.setRange(0, 1e4)
        self.current_down_step_size_sb1.setValue(10)
        self.current_down_step_size_sb1.editingFinished.connect(lambda: self.current_step_size_balance("down 1"))
        current_down_step_size_vbox1.addWidget(current_down_step_size_lb1)
        current_down_step_size_vbox1.addWidget(self.current_down_step_size_sb1)
        current_ramp_grid.addLayout(current_down_step_size_vbox1, 3, 0, 1, 1, Qt.AlignCenter)

        current_down_points_vbox1 = QVBoxLayout()
        current_down_points_lb1 = QLabel("Down points 1")
        self.current_down_points_sb1 = QSpinBox()
        self.current_down_points_sb1.setRange(1, int(1e4))
        self.current_down_points_sb1.setValue(100)
        self.current_down_points_sb1.editingFinished.connect(lambda: self.current_points_balance("down 1"))
        current_down_points_vbox1.addWidget(current_down_points_lb1)
        current_down_points_vbox1.addWidget(self.current_down_points_sb1)
        current_ramp_grid.addLayout(current_down_points_vbox1, 3, 1, 1, 1, Qt.AlignCenter)

        current_up_lim_hbox2 = QHBoxLayout()
        current_up_lim_lb2 = QLabel("Up limit 2 (A)")
        self.current_up_lim_sb2 = QDoubleSpinBox()
        self.current_up_lim_sb2.setRange(0, 1)
        self.current_up_lim_sb2.setValue(10)
        self.current_up_lim_sb2.editingFinished.connect(lambda: self.current_lim_balance(2))
        current_up_lim_hbox2.addWidget(current_up_lim_lb2)
        current_up_lim_hbox2.addWidget(self.current_up_lim_sb2)
        current_ramp_grid.addLayout(current_up_lim_hbox2, 0, 2, 1, 1, Qt.AlignCenter)

        current_down_lim_hbox2 = QHBoxLayout()
        current_down_lim_lb2 = QLabel("Down limit 2 (A)")
        self.current_down_lim_sb2 = QDoubleSpinBox()
        self.current_down_lim_sb2.setRange(0, 1.05)
        self.current_down_lim_sb2.editingFinished.connect(lambda: self.current_lim_balance(2))
        current_down_lim_hbox2.addWidget(current_down_lim_lb2)
        current_down_lim_hbox2.addWidget(self.current_down_lim_sb2)
        current_ramp_grid.addLayout(current_down_lim_hbox2, 0, 3, 1, 1, Qt.AlignCenter)

        current_up_speed_hbox2 = QHBoxLayout()
        current_up_speed_lb2 = QLabel("Up speed 2 (mA/s)")
        self.current_up_speed_sb2 = QDoubleSpinBox()
        self.current_up_speed_sb2.setRange(0, 1050)
        self.current_up_speed_sb2.setValue(10)
        self.current_up_speed_sb2.editingFinished.connect(lambda: self.current_speed_balance("up 2"))
        current_up_speed_hbox2.addWidget(current_up_speed_lb2)
        current_up_speed_hbox2.addWidget(self.current_up_speed_sb2)
        current_ramp_grid.addLayout(current_up_speed_hbox2, 1, 2, 1, 1, Qt.AlignCenter)

        current_down_speed_hbox2 = QHBoxLayout()
        current_down_speed_lb2 = QLabel("Down speed 2 (mA/s)")
        self.current_down_speed_sb2 = QDoubleSpinBox()
        self.current_down_speed_sb2.setRange(0, 1050)
        self.current_down_speed_sb2.setValue(10)
        self.current_down_speed_sb2.editingFinished.connect(lambda: self.current_speed_balance("down 2"))
        current_down_speed_hbox2.addWidget(current_down_speed_lb2)
        current_down_speed_hbox2.addWidget(self.current_down_speed_sb2)
        current_ramp_grid.addLayout(current_down_speed_hbox2, 1, 3, 1, 1, Qt.AlignCenter)

        current_up_step_size_vbox2 = QVBoxLayout()
        current_up_step_size_lb2 = QLabel("Up step size 2 (mA)")
        self.current_up_step_size_sb2 = QDoubleSpinBox()
        self.current_up_step_size_sb2.setRange(0, 1e4)
        self.current_up_step_size_sb2.setValue(10)
        self.current_up_step_size_sb2.editingFinished.connect(lambda: self.current_step_size_balance("up 2"))
        current_up_step_size_vbox2.addWidget(current_up_step_size_lb2)
        current_up_step_size_vbox2.addWidget(self.current_up_step_size_sb2)
        current_ramp_grid.addLayout(current_up_step_size_vbox2, 2, 2, 1, 1, Qt.AlignCenter)

        current_up_points_vbox2 = QVBoxLayout()
        current_up_points_lb2 = QLabel("Up points 2")
        self.current_up_points_sb2 = QSpinBox()
        self.current_up_points_sb2.setRange(1, int(1e4))
        self.current_up_points_sb2.setValue(100)
        self.current_up_points_sb2.editingFinished.connect(lambda: self.current_points_balance("up 2"))
        current_up_points_vbox2.addWidget(current_up_points_lb2)
        current_up_points_vbox2.addWidget(self.current_up_points_sb2)
        current_ramp_grid.addLayout(current_up_points_vbox2, 2, 3, 1, 1, Qt.AlignCenter)

        current_down_step_size_vbox2 = QVBoxLayout()
        current_down_step_size_lb2 = QLabel("Down step size 2 (mA)")
        self.current_down_step_size_sb2 = QDoubleSpinBox()
        self.current_down_step_size_sb2.setRange(0, 1e4)
        self.current_down_step_size_sb2.setValue(10)
        self.current_down_step_size_sb2.editingFinished.connect(lambda: self.current_step_size_balance("down 2"))
        current_down_step_size_vbox2.addWidget(current_down_step_size_lb2)
        current_down_step_size_vbox2.addWidget(self.current_down_step_size_sb2)
        current_ramp_grid.addLayout(current_down_step_size_vbox2, 3, 2, 1, 1, Qt.AlignCenter)

        current_down_points_vbox2 = QVBoxLayout()
        current_down_points_lb2 = QLabel("Down points 2")
        self.current_down_points_sb2 = QSpinBox()
        self.current_down_points_sb2.setRange(1, int(1e4))
        self.current_down_points_sb2.setValue(100)
        self.current_down_points_sb2.editingFinished.connect(lambda: self.current_points_balance("down 2"))
        current_down_points_vbox2.addWidget(current_down_points_lb2)
        current_down_points_vbox2.addWidget(self.current_down_points_sb2)
        current_ramp_grid.addLayout(current_down_points_vbox2, 3, 3, 1, 1, Qt.AlignCenter)

        self.current_figure = plt.figure()
        self.current_F = FigureCanvas(self.current_figure)
        self.current_axes = self.current_figure.add_subplot(111)
        self.current_F.figure.subplots_adjust(left=0.2,
                    bottom=0.15,
                    right=0.7,
                    top=0.9,
                    wspace=0.4,
                    hspace=0.4)
        self.current_axes.set_xlabel(r'Source 1 (A)')
        self.current_axes.set_ylabel(r'Source 2 (A)')
        self.current_axes.set_xlim([0, 1])
        self.current_axes.set_ylim([0, 1])
        self.current_axes.grid()
        self.current_sweep_curve, = self.current_axes.plot(np.linspace(self.current_down_lim_sb1.value(), self.current_up_lim_sb1.value(), 100, endpoint=True), np.linspace(self.current_down_lim_sb2.value(), self.current_up_lim_sb2.value(), 100, endpoint=True), color = 'b', linestyle = '-', label="Sweep")
        self.current_now_curve, = self.current_axes.plot([0], [0], marker="o", color = 'r', label="Now")
        self.current_axes.legend(bbox_to_anchor =(1.5, 1))
        current_ramp_grid.addWidget(self.current_F, 4, 0, 4, 4, Qt.AlignCenter)

    def connectInstrument1(self):
        # if a selection is chosen that is not just the default prompt
        if (self.connection_box1.currentText() != 'Connect to keithley...'):
            # get the chopper name and connect the chopper
            if self.connection_box1.currentText()[-1] == ")":
                keithley_name = self.connection_box1.currentText()[:-10]
            else:
                keithley_name = self.connection_box1.currentText()

            try:
                if self.keitheley_selection_box1.currentText() == "Keithley 2450":
                    self.keithley1 = Keithley2450(keithley_name)
                elif self.keitheley_selection_box1.currentText() == "Keithley 2400":
                    self.keithley1 = Keithley2400(keithley_name)
                    self.keithley1.output_off_state = "HIMP"
                self.keithley1.apply_current()
                self.connected1 = True
            except:
                self.connection_indicator1.setText(u'\u274c ')
                self.connected1 = False
                #self.enable_ind.changeColor('orange')
                self.enable_btn1.setText('Enable/Disable source 1')
                self.enable_ind1.setChecked(False)
                self.enable_btn1.setEnabled(False)
                self.connected1 = False
                return

            # change connection indicator to a check mark from a cross mark
            self.connection_indicator1.setText(u'\u2705')
            self.connected1 = True

            self.enable_btn1.setText('Enable source 1')
            self.enable_ind1.setChecked(True)
            self.enable_btn1.setEnabled(True)
        else:
            self.connection_indicator1.setText(u'\u274c ')
            self.connected1 = False
             #self.enable_ind.changeColor('orange')
            self.enable_btn1.setText('Enable/Disable source 1')
            self.enable_ind1.setChecked(False)
            self.enable_btn1.setEnabled(False)
            self.connected1 = False

    def connectInstrument2(self):
        # if a selection is chosen that is not just the default prompt
        if (self.connection_box2.currentText() != 'Connect to keithley...'):
            # get the chopper name and connect the chopper
            if self.connection_box2.currentText()[-1] == ")":
                keithley_name = self.connection_box2.currentText()[:-10]
            else:
                keithley_name = self.connection_box2.currentText()

            try:
                if self.keitheley_selection_box2.currentText() == "Keithley 2450":
                    self.keithley2 = Keithley2450(keithley_name)
                elif self.keitheley_selection_box2.currentText() == "Keithley 2400":
                    self.keithley2 = Keithley2400(keithley_name)
                self.keithley2.apply_current()
                self.connected2 = True
            except:
                self.connection_indicator2.setText(u'\u274c ')
                self.connected2 = False
                #self.enable_ind.changeColor('orange')
                self.enable_btn2.setText('Enable/Disable source 1')
                self.enable_ind2.setChecked(False)
                self.enable_btn2.setEnabled(False)
                self.connected2 = False
                return

            # change connection indicator to a check mark from a cross mark
            self.connection_indicator2.setText(u'\u2705')
            self.connected2 = True

            self.enable_btn2.setText('Enable source 2')
            self.enable_ind2.setChecked(True)
            self.enable_btn2.setEnabled(True)

    def enable_source1(self):
        if self.tabs.currentIndex() == 0:
            if abs(self.source_voltage_sb1.value()) > self.source_voltage_range_sb1.value():
                QMessageBox.warning(self, "Voltage overflow", "Input voltage is out of range!")
                return
            self.keithley1.apply_voltage()
            self.keithley1.source_voltage_range = self.source_voltage_range_sb1.value()
            self.keithley1.source_voltage = self.source_voltage_sb1.value()
            self.keithley1.compliance_current = self.compliance_current_sb1.value()*1e-9
            self.voltage_sweep_curve.set_xdata(np.linspace(self.voltage_down_lim_sb1.value(), self.voltage_up_lim_sb1.value(), 100, endpoint=True))
            if not self.enabled2:
                self.voltage_sweep_curve.set_ydata(np.zeros(100))
                self.voltage_axes.set_ylim([-5, 5])
            self.voltage_now_curve.set_xdata([self.source_voltage_sb1.value()])
            self.voltage_axes.set_xlim([self.voltage_down_lim_sb1.value(), self.voltage_up_lim_sb1.value()])
            self.voltage_F.draw()
        else:
            if abs(self.source_current_sb1.value()) > self.source_current_range_sb1.value():
                QMessageBox.warning(self, "Current overflow", "Input current is out of range!")
                return
            self.keithley1.apply_current()
            self.keithley1.source_current_range = self.source_current_range_sb1.value()
            self.keithley1.source_current = self.source_current_sb1.value()
            self.keithley1.compliance_voltage = self.compliance_voltage_sb1.value()
            self.current_sweep_curve.set_xdata(np.linspace(self.current_down_lim_sb1.value(), self.current_up_lim_sb1.value(), 100, endpoint=True))
            if not self.enabled2:
                self.current_sweep_curve.set_ydata(np.zeros(100))
                self.current_axes.set_ylim([-0.5, 0.5])
            self.current_now_curve.set_xdata([self.source_current_sb1.value()])
            self.current_axes.set_xlim([self.current_down_lim_sb1.value(), self.current_up_lim_sb1.value()])
            self.current_F.draw()

        self.updateIVR1 = UpdateVIThread1(self)
        self.updateIVR1.start()

    def enable_source2(self):
        if self.tabs.currentIndex() == 0:
            if abs(self.source_voltage_sb2.value()) > self.source_voltage_range_sb2.value():
                QMessageBox.warning(self, "Voltage overflow", "Input voltage is out of range!")
                return
            self.keithley2.apply_voltage()
            self.keithley2.source_voltage_range = self.source_voltage_range_sb2.value()
            self.keithley2.source_voltage = self.source_voltage_sb2.value()
            self.keithley2.compliance_current = self.compliance_current_sb2.value()*1e-9
            self.voltage_sweep_curve.set_ydata(np.linspace(self.voltage_down_lim_sb2.value(), self.voltage_up_lim_sb2.value(), 100, endpoint=True))
            if not self.enabled1:
                self.voltage_sweep_curve.set_xdata(np.zeros(100))
                self.voltage_axes.set_xlim([-5, 5])
            self.voltage_now_curve.set_ydata([self.source_voltage_sb2.value()])
            self.voltage_axes.set_ylim([self.voltage_down_lim_sb2.value(), self.voltage_up_lim_sb2.value()])
            self.voltage_F.draw()
        else:
            if abs(self.source_current_sb2.value()) > self.source_current_range_sb2.value():
                QMessageBox.warning(self, "Current overflow", "Input current is out of range!")
                return
            self.keithley2.apply_current()
            self.keithley2.source_current_range = self.source_current_range_sb2.value()
            self.keithley2.source_current = self.source_current_sb2.value()
            self.keithley2.compliance_voltage = self.compliance_voltage_sb2.value()
            self.current_sweep_curve.set_ydata(np.linspace(self.current_down_lim_sb2.value(), self.current_up_lim_sb2.value(), 100, endpoint=True))
            if not self.enabled1:
                self.current_sweep_curve.set_xdata(np.zeros(100))
                self.current_axes.set_xlim([-0.5, 0.5])
            self.current_now_curve.set_ydata([self.source_current_sb2.value()])
            self.current_axes.set_ylim([self.current_down_lim_sb2.value(), self.current_up_lim_sb2.value()])
            self.current_F.draw()

        self.updateIVR2 = UpdateVIThread2(self)
        self.updateIVR2.start()

    def toggleEnabled1(self):
        if (self.enabled1 == True):  # disable, then change text to enable
            self.updateIVR1.terminate()
            self.keithley1.shutdown()
            self.enable_btn1.setText('Enable source 1')
            self.enable_ind1.changeColor('orange')
            self.enabled1 = False
            if not self.enabled2:
                self.action_cb.setEnabled(False)
        else:  # enable, then change text to disable
            self.enable_source1()
            self.keithley1.enable_source()
            self.enable_btn1.setText('Disable source 1')
            self.enable_ind1.changeColor('green')
            self.enabled1 = True
            self.action_cb.setEnabled(True)

    def toggleEnabled2(self):
        if (self.enabled2 == True):  # disable, then change text to enable
            self.updateIVR2.terminate()
            self.keithley2.shutdown()
            self.enable_btn2.setText('Enable source 2')
            self.enable_ind2.changeColor('orange')
            self.enabled2 = False
            if not self.enabled1:
                self.action_cb.setEnabled(False)
        else:  # enable, then change text to disable
            self.enable_source2()
            self.keithley2.enable_source()
            self.enable_btn2.setText('Disable source 2')
            self.enable_ind2.changeColor('green')
            self.enabled2 = True
            self.action_cb.setEnabled(True)

    def voltage_lim_balance(self, mode):
        if mode == 1:
            self.voltage_up_lim_sb1.setMinimum(self.voltage_down_lim_sb1.value()+0.01)
            self.voltage_down_lim_sb1.setMaximum(self.voltage_up_lim_sb1.value()-0.01)
        elif mode == 2:
            self.voltage_up_lim_sb2.setMinimum(self.voltage_down_lim_sb2.value())
            self.voltage_down_lim_sb2.setMaximum(self.voltage_up_lim_sb2.value())
        dV1 = self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()
        dV2 = self.voltage_up_lim_sb2.value() - self.voltage_down_lim_sb2.value()
        if self.enabled1 and self.enabled2:
            self.voltage_up_points_sb1.setValue(int(np.sqrt(dV1**2+dV2**2)/np.sqrt(2)*10))
            self.voltage_up_points_sb2.setValue(self.voltage_up_points_sb1.value())
            self.voltage_down_points_sb1.setValue(int(np.sqrt(dV1**2+dV2**2)/np.sqrt(2)*10))
            self.voltage_down_points_sb2.setValue(self.voltage_down_points_sb1.value())
            self.voltage_up_step_size_sb1.setValue(dV1/self.voltage_up_points_sb1.value()*1e3)
            self.voltage_up_step_size_sb2.setValue(dV2/self.voltage_up_points_sb2.value()*1e3)
            self.voltage_down_step_size_sb1.setValue(dV1/self.voltage_down_points_sb1.value()*1e3)
            self.voltage_down_step_size_sb2.setValue(dV2/self.voltage_down_points_sb2.value()*1e3)
            if mode == 1:
                self.voltage_up_speed_sb1.setValue(dV1/dV2*self.voltage_up_speed_sb2.value())
                self.voltage_down_speed_sb1.setValue(dV1/dV2*self.voltage_down_speed_sb2.value())
            elif mode == 2:
                self.voltage_up_speed_sb2.setValue(dV2/dV1*self.voltage_up_speed_sb1.value())
                self.voltage_down_speed_sb2.setValue(dV2/dV1*self.voltage_down_speed_sb1.value())
            self.voltage_sweep_curve.set_xdata(np.linspace(self.voltage_down_lim_sb1.value(), self.voltage_up_lim_sb1.value(), 100, endpoint=True))
            self.voltage_sweep_curve.set_ydata(np.linspace(self.voltage_down_lim_sb2.value(), self.voltage_up_lim_sb2.value(), 100, endpoint=True))
            self.voltage_axes.set_xlim([self.voltage_down_lim_sb1.value(), self.voltage_up_lim_sb1.value()])
            self.voltage_axes.set_ylim([self.voltage_down_lim_sb2.value(), self.voltage_up_lim_sb2.value()])
            self.voltage_F.draw()
        elif self.enabled1:
            self.voltage_up_points_sb1.setValue(int(dV1*1e3/self.voltage_up_step_size_sb1.value()))
            self.voltage_down_points_sb1.setValue(int(dV1*1e3/self.voltage_down_step_size_sb1.value()))
            self.voltage_up_step_size_sb1.setValue(dV1/self.voltage_up_points_sb1.value()*1e3)
            self.voltage_down_step_size_sb1.setValue(dV1/self.voltage_down_points_sb1.value()*1e3)
            self.voltage_sweep_curve.set_xdata(np.linspace(self.voltage_down_lim_sb1.value(), self.voltage_up_lim_sb1.value(), 100, endpoint=True))
            self.voltage_axes.set_xlim([self.voltage_down_lim_sb1.value(), self.voltage_up_lim_sb1.value()])
            self.voltage_F.draw()
        elif self.enabled2:
            self.voltage_up_points_sb2.setValue(int(dV2*1e3/self.voltage_up_step_size_sb2.value()))
            self.voltage_down_points_sb2.setValue(int(dV2*1e3/self.voltage_down_step_size_sb2.value()))
            self.voltage_up_step_size_sb2.setValue(dV2/self.voltage_up_points_sb2.value()*1e3)
            self.voltage_down_step_size_sb2.setValue(dV2/self.voltage_down_points_sb2.value()*1e3)
            self.voltage_sweep_curve.set_ydata(np.linspace(self.voltage_down_lim_sb2.value(), self.voltage_up_lim_sb2.value(), 100, endpoint=True))
            self.voltage_axes.set_ylim([self.voltage_down_lim_sb2.value(), self.voltage_up_lim_sb2.value()])
            self.voltage_F.draw()

    def voltage_speed_balance(self, mode):
        if self.enabled1 and self.enabled2:
            dV1 = self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()
            dV2 = self.voltage_up_lim_sb2.value() - self.voltage_down_lim_sb2.value()
            if mode == "up 1":
                self.voltage_up_speed_sb2.setValue(dV2/dV1*self.voltage_up_speed_sb1.value())
            elif mode == "up 2":
                self.voltage_up_speed_sb1.setValue(dV1/dV2*self.voltage_up_speed_sb2.value())
            elif mode == "down 1":
                self.voltage_down_speed_sb2.setValue(dV2/dV1*self.voltage_down_speed_sb1.value())
            elif mode == "down 2":
                self.voltage_down_speed_sb1.setValue(dV1/dV2*self.voltage_down_speed_sb2.value())

    def voltage_step_size_balance(self, mode):
        dV1 = self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()
        dV2 = self.voltage_up_lim_sb2.value() - self.voltage_down_lim_sb2.value()
        if mode == "up 1":
            if self.enabled1:
                self.voltage_up_points_sb1.setValue(int(dV1*1e3/self.voltage_up_step_size_sb1.value()))
                self.voltage_up_step_size_sb1.setValue(dV1*1e3/self.voltage_up_points_sb1.value())
            if self.enabled2:
                self.voltage_up_points_sb2.setValue(self.voltage_up_points_sb1.value())
                self.voltage_up_step_size_sb2.setValue(dV2*1e3/self.voltage_up_points_sb2.value())
        elif mode == "up 2":
            if self.enabled2:
                self.voltage_up_points_sb2.setValue(int(dV2*1e3/self.voltage_up_step_size_sb2.value()))
                self.voltage_up_step_size_sb2.setValue(dV2*1e3/self.voltage_up_points_sb2.value())
            if self.enabled1:
                self.voltage_up_points_sb1.setValue(self.voltage_up_points_sb2.value())
                self.voltage_up_step_size_sb1.setValue(dV1*1e3/self.voltage_up_points_sb1.value())
        elif mode == "down 1":
            if self.enabled1:
                self.voltage_down_points_sb1.setValue(int(dV1*1e3/self.voltage_down_step_size_sb1.value()))
                self.voltage_down_step_size_sb1.setValue(dV1*1e3/self.voltage_down_points_sb1.value())
            if self.enabled2:
                self.voltage_down_points_sb2.setValue(self.voltage_down_points_sb1.value())
                self.voltage_down_step_size_sb2.setValue(dV2*1e3/self.voltage_down_points_sb2.value())
        elif mode == "down 2":
            if self.enabled2:
                self.voltage_down_points_sb2.setValue(int(dV2*1e3/self.voltage_down_step_size_sb2.value()))
                self.voltage_down_step_size_sb2.setValue(dV2*1e3/self.voltage_down_points_sb2.value())
            if self.enabled1:
                self.voltage_down_points_sb1.setValue(self.voltage_down_points_sb2.value())
                self.voltage_down_step_size_sb1.setValue(dV1*1e3/self.voltage_down_points_sb1.value())

    def voltage_points_balance(self, mode):
        dV1 = self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()
        dV2 = self.voltage_up_lim_sb2.value() - self.voltage_down_lim_sb2.value()
        if mode == "up 1":
            if self.enabled1:
                self.voltage_up_step_size_sb1.setValue(dV1*1e3/self.voltage_up_points_sb1.value())
            if self.enabled2:
                self.voltage_up_points_sb2.setValue(self.voltage_up_points_sb1.value())
                self.voltage_up_step_size_sb2.setValue(dV2*1e3/self.voltage_up_points_sb2.value())
        elif mode == "up 2":
            if self.enabled2:
                self.voltage_up_step_size_sb2.setValue(dV2*1e3/self.voltage_up_points_sb2.value())
            if self.enabled1:
                self.voltage_up_points_sb1.setValue(self.voltage_up_points_sb2.value())
                self.voltage_up_step_size_sb1.setValue(dV1*1e3/self.voltage_up_points_sb1.value())
        elif mode == "down 1":
            if self.enabled1:
                self.voltage_down_step_size_sb1.setValue(dV1*1e3/self.voltage_down_points_sb1.value())
            if self.enabled2:
                self.voltage_down_points_sb2.setValue(self.voltage_down_points_sb1.value())
                self.voltage_down_step_size_sb2.setValue(dV2*1e3/self.voltage_down_points_sb2.value())
        elif mode == "down 2":
            if self.enabled2:
                self.voltage_down_step_size_sb2.setValue(dV2*1e3/self.voltage_down_points_sb2.value())
            if self.enabled1:
                self.voltage_down_points_sb1.setValue(self.voltage_down_points_sb2.value())
                self.voltage_down_step_size_sb1.setValue(dV1*1e3/self.voltage_down_points_sb1.value())

    def current_lim_balance(self, mode):
        dI1 = self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()
        dI2 = self.current_up_lim_sb2.value() - self.current_down_lim_sb2.value()
        if self.enabled1 and self.enabled2:
            self.current_up_points_sb1.setValue(int(np.sqrt(dI1**2+dI2**2)/np.sqrt(2)*100))
            self.current_up_points_sb2.setValue(self.current_up_points_sb1.value())
            self.current_down_points_sb1.setValue(int(np.sqrt(dI1**2+dI2**2)/np.sqrt(2)*100))
            self.current_down_points_sb2.setValue(self.current_down_points_sb1.value())
            self.current_up_step_size_sb1.setValue(dI1/self.current_up_points_sb1.value()*1e3)
            self.current_up_step_size_sb2.setValue(dI2/self.current_up_points_sb2.value()*1e3)
            self.current_down_step_size_sb1.setValue(dI1/self.current_down_points_sb1.value()*1e3)
            self.current_down_step_size_sb2.setValue(dI2/self.current_down_points_sb2.value()*1e3)
            if mode == 1:
                self.current_up_speed_sb1.setValue(dI1/dI2*self.current_up_speed_sb2.value())
                self.current_down_speed_sb1.setValue(dI1/dI2*self.current_down_speed_sb2.value())
            elif mode == 2:
                self.current_up_speed_sb2.setValue(dI2/dI1*self.current_up_speed_sb1.value())
                self.current_down_speed_sb2.setValue(dI2/dI1*self.current_down_speed_sb1.value())
            self.current_sweep_curve.set_xdata(np.linspace(self.current_down_lim_sb1.value(), self.current_up_lim_sb1.value(), 100, endpoint=True))
            self.current_sweep_curve.set_ydata(np.linspace(self.current_down_lim_sb2.value(), self.current_up_lim_sb2.value(), 100, endpoint=True))
            self.current_axes.set_xlim([self.current_down_lim_sb1.value(), self.current_up_lim_sb1.value()])
            self.current_axes.set_ylim([self.current_down_lim_sb2.value(), self.current_up_lim_sb2.value()])
            self.current_F.draw()
        elif self.enabled1:
            self.current_up_points_sb1.setValue(int(dI1*1e3/self.current_up_step_size_sb1.value()))
            self.current_down_points_sb1.setValue(int(dI1*1e3/self.current_down_step_size_sb1.value()))
            self.current_up_step_size_sb1.setValue(dI1/self.current_up_points_sb1.value()*1e3)
            self.current_down_step_size_sb1.setValue(dI1/self.current_down_points_sb1.value()*1e3)
            self.current_sweep_curve.set_xdata(np.linspace(self.current_down_lim_sb1.value(), self.current_up_lim_sb1.value(), 100, endpoint=True))
            self.current_axes.set_xlim([self.current_down_lim_sb1.value(), self.current_up_lim_sb1.value()])
            self.current_F.draw()
        elif self.enabled2:
            self.current_up_points_sb2.setValue(int(dI2*1e3/self.current_up_step_size_sb2.value()))
            self.current_down_points_sb2.setValue(int(dI2*1e3/self.current_down_step_size_sb2.value()))
            self.current_up_step_size_sb2.setValue(dI2/self.current_up_points_sb2.value()*1e3)
            self.current_down_step_size_sb2.setValue(dI2/self.current_down_points_sb2.value()*1e3)
            self.current_sweep_curve.set_ydata(np.linspace(self.current_down_lim_sb2.value(), self.current_up_lim_sb2.value(), 100, endpoint=True))
            self.current_axes.set_ylim([self.current_down_lim_sb2.value(), self.current_up_lim_sb2.value()])
            self.current_F.draw()

    def current_speed_balance(self, mode):
        if self.enabled1 and self.enabled2:
            dI1 = self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()
            dI2 = self.current_up_lim_sb2.value() - self.current_down_lim_sb2.value()
            if mode == "up 1":
                self.current_up_speed_sb2.setValue(dI2/dI1*self.current_up_speed_sb1.value())
            elif mode == "up 2":
                self.current_up_speed_sb1.setValue(dI1/dI2*self.current_up_speed_sb2.value())
            elif mode == "down 1":
                self.current_down_speed_sb2.setValue(dI2/dI1*self.current_down_speed_sb1.value())
            elif mode == "down 2":
                self.current_down_speed_sb1.setValue(dI1/dI2*self.current_down_speed_sb2.value())

    def current_step_size_balance(self, mode):
        dI1 = self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()
        dI2 = self.current_up_lim_sb2.value() - self.current_down_lim_sb2.value()
        if mode == "up 1":
            if self.enabled1:
                self.current_up_points_sb1.setValue(int(dI1*1e3/self.current_up_step_size_sb1.value()))
                self.current_up_step_size_sb1.setValue(dI1*1e3/self.current_up_points_sb1.value())
            if self.enabled2:
                self.current_up_points_sb2.setValue(self.current_up_points_sb1.value())
                self.current_up_step_size_sb2.setValue(dI2*1e3/self.current_up_points_sb2.value())
        elif mode == "up 2":
            if self.enabled2:
                self.current_up_points_sb2.setValue(int(dI2*1e3/self.current_up_step_size_sb2.value()))
                self.current_up_step_size_sb2.setValue(dI2*1e3/self.current_up_points_sb2.value())
            if self.enabled1:
                self.current_up_points_sb1.setValue(self.current_up_points_sb2.value())
                self.current_up_step_size_sb1.setValue(dI1*1e3/self.current_up_points_sb1.value())
        elif mode == "down 1":
            if self.enabled1:
                self.current_down_points_sb1.setValue(int(dI1*1e3/self.current_down_step_size_sb1.value()))
                self.current_down_step_size_sb1.setValue(dI1*1e3/self.current_down_points_sb1.value())
            if self.enabled2:
                self.current_down_points_sb2.setValue(self.current_down_points_sb1.value())
                self.current_down_step_size_sb2.setValue(dI2*1e3/self.current_down_points_sb2.value())
        elif mode == "down 2":
            if self.enabled2:
                self.current_down_points_sb2.setValue(int(dI2*1e3/self.current_down_step_size_sb2.value()))
                self.current_down_step_size_sb2.setValue(dI2*1e3/self.current_down_points_sb2.value())
            if self.enabled1:
                self.current_down_points_sb1.setValue(self.current_down_points_sb2.value())
                self.current_down_step_size_sb1.setValue(dI1*1e3/self.current_down_points_sb1.value())

    def current_points_balance(self, mode):
        dI1 = self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()
        dI2 = self.current_up_lim_sb2.value() - self.current_down_lim_sb2.value()
        if mode == "up 1":
            if self.enabled1:
                self.current_up_step_size_sb1.setValue(dI1*1e3/self.current_up_points_sb1.value())
            if self.enabled2:
                self.current_up_points_sb2.setValue(self.current_up_points_sb1.value())
                self.current_up_step_size_sb2.setValue(dI2*1e3/self.current_up_points_sb2.value())
        elif mode == "up 2":
            if self.enabled2:
                self.current_up_step_size_sb2.setValue(dI2*1e3/self.current_up_points_sb2.value())
            if self.enabled1:
                self.current_up_points_sb1.setValue(self.current_up_points_sb2.value())
                self.current_up_step_size_sb1.setValue(dI1*1e3/self.current_up_points_sb1.value())
        elif mode == "down 1":
            if self.enabled1:
                self.current_down_step_size_sb1.setValue(dI1*1e3/self.current_down_points_sb1.value())
            if self.enabled2:
                self.current_down_points_sb2.setValue(self.current_down_points_sb1.value())
                self.current_down_step_size_sb2.setValue(dI2*1e3/self.current_down_points_sb2.value())
        elif mode == "down 2":
            if self.enabled2:
                self.current_down_step_size_sb2.setValue(dI2*1e3/self.current_down_points_sb2.value())
            if self.enabled1:
                self.current_down_points_sb1.setValue(self.current_down_points_sb2.value())
                self.current_down_step_size_sb1.setValue(dI1*1e3/self.current_down_points_sb1.value())

    def ramping(self):
        if self.ramp_tabs.currentIndex() == 0: # voltage ramp
            if self.enabled1:
                self.keithley1.measure_voltage()
                V1_now = self.keithley1.source_voltage
            if self.enabled2:
                self.keithley2.measure_voltage()
                V2_now = self.keithley2.source_voltage
            if self.action_cb.currentText() == "Ramp up":
                if self.in_voltage_ramping:
                    self.voltage_ramp_thread.stop_command = True
                self.in_voltage_ramping = True
                if self.enabled1 and self.enabled2:
                    dV1 = self.voltage_up_lim_sb1.value() - V1_now
                    dV2 = self.voltage_up_lim_sb2.value() - V2_now
                    num_of_steps = round(self.voltage_up_points_sb1.value()*dV1/(self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()))
                    pause = dV1*1e3/self.voltage_up_speed_sb1.value()/num_of_steps
                    self.voltage_ramp_thread = RampingThread("V", "up", self.keithley1, self.keithley2, V1_now, V2_now, dV1, dV2, num_of_steps, pause)
                elif self.enabled1:
                    dV1 = self.voltage_up_lim_sb1.value() - V1_now
                    num_of_steps = round(self.voltage_up_points_sb1.value()*dV1/(self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()))
                    pause = dV1*1e3/self.voltage_up_speed_sb1.value()/num_of_steps
                    self.voltage_ramp_thread = RampingThread("V", "up", self.keithley1, None, V1_now, None, dV1, None, num_of_steps, pause)
                elif self.enabled2:
                    dV2 = self.voltage_up_lim_sb2.value() - V2_now
                    num_of_steps = round(self.voltage_up_points_sb2.value()*dV2/(self.voltage_up_lim_sb2.value() - self.voltage_down_lim_sb2.value()))
                    pause = dV2*1e3/self.voltage_up_speed_sb2.value()/num_of_steps
                    self.voltage_ramp_thread = RampingThread("V", "up", None, self.keithley2, None, V2_now, None, dV2, num_of_steps, pause)
                self.voltage_ramp_thread.graphSignal.connect(self.update_voltage_graph)
                self.voltage_ramp_thread.finalSignal.connect(self.ramping_finished)
                self.voltage_ramp_thread.start()
            elif self.action_cb.currentText() == "Ramp down":
                if self.in_voltage_ramping:
                    self.voltage_ramp_thread.stop_command = True
                self.in_voltage_ramping = True
                if self.enabled1 and self.enabled2:
                    dV1 = V1_now - self.voltage_down_lim_sb1.value()
                    dV2 = V2_now - self.voltage_down_lim_sb2.value()
                    num_of_steps = round(self.voltage_down_points_sb1.value()*dV1/(self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()))
                    pause = dV1*1e3/self.voltage_down_speed_sb1.value()/num_of_steps
                    self.voltage_ramp_thread = RampingThread("V", "down", self.keithley1, self.keithley2, V1_now, V2_now, dV1, dV2, num_of_steps, pause)
                elif self.enabled1:
                    dV1 = V1_now - self.voltage_down_lim_sb1.value()
                    num_of_steps = round(self.voltage_down_points_sb1.value()*dV1/(self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()))
                    pause = dV1*1e3/self.voltage_down_speed_sb1.value()/num_of_steps
                    self.voltage_ramp_thread = RampingThread("V", "down", self.keithley1, None, V1_now, None, dV1, None, num_of_steps, pause)
                elif self.enabled2:
                    dV2 = V2_now - self.voltage_down_lim_sb2.value()
                    num_of_steps = round(self.voltage_down_points_sb2.value()*dV2/(self.voltage_up_lim_sb2.value() - self.voltage_down_lim_sb2.value()))
                    pause = dV2*1e3/self.voltage_down_speed_sb2.value()/num_of_steps
                    self.voltage_ramp_thread = RampingThread("V", "down", None, self.keithley2, None, V2_now, None, dV2, num_of_steps, pause)
                self.voltage_ramp_thread.graphSignal.connect(self.update_voltage_graph)
                self.voltage_ramp_thread.finalSignal.connect(self.ramping_finished)
                self.voltage_ramp_thread.start()
            elif self.action_cb.currentText() == "Cycle up":
                if self.in_voltage_ramping:
                    self.voltage_ramp_thread.stop_command = True
                self.in_voltage_ramping = True
                if self.enabled1 and self.enabled2:
                    dV1 = self.voltage_up_lim_sb1.value() - V1_now
                    dV1_down = self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()
                    dV1_up = V1_now - self.voltage_down_lim_sb1.value()
                    dV2 = self.voltage_up_lim_sb2.value() - V2_now
                    dV2_down = self.voltage_down_lim_sb2.value() - self.voltage_up_lim_sb2.value()
                    dV2_up = V2_now - self.voltage_down_lim_sb2.value()
                    num_of_steps = round(self.voltage_up_points_sb1.value()*dV1/(self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()))
                    num_of_steps_down = round(self.voltage_down_points_sb1.value()*dV1_down/(self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()))
                    num_of_steps_up = round(self.voltage_up_points_sb1.value()*dV1_up/(self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()))
                    if num_of_steps > 0:
                        pause = dV1*1e3/self.voltage_up_speed_sb1.value()/num_of_steps
                    else:
                        pause = 0
                    if num_of_steps_down > 0:
                        pause_down = dV1_down*1e3/self.voltage_down_speed_sb1.value()/num_of_steps_down
                    else:
                        pause_down = 0
                    if num_of_steps_up > 0:
                        pause_up = dV1_up*1e3/self.voltage_up_speed_sb1.value()/num_of_steps_up
                    else:
                        pause_up = 0
                    self.voltage_ramp_thread = CyclingThread("V", "up", self.cycle_times_sb.value(), self.keithley1, self.keithley2, V1_now, V2_now, dV1, dV1_down, dV1_up, dV2, dV2_down, dV2_up,
                                                             num_of_steps, num_of_steps_down, num_of_steps_up, pause, pause_down, pause_up)
                elif self.enabled1:
                    dV1 = self.voltage_up_lim_sb1.value() - V1_now
                    dV1_down = self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()
                    dV1_up = V1_now - self.voltage_down_lim_sb1.value()
                    num_of_steps = round(self.voltage_up_points_sb1.value()*dV1/(self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()))
                    num_of_steps_down = round(self.voltage_down_points_sb1.value()*dV1_down/(self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()))
                    num_of_steps_up = round(self.voltage_up_points_sb1.value()*dV1_up/(self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()))
                    if num_of_steps > 0:
                        pause = dV1*1e3/self.voltage_up_speed_sb1.value()/num_of_steps
                    else:
                        pause = 0
                    if num_of_steps_down > 0:
                        pause_down = dV1_down*1e3/self.voltage_down_speed_sb1.value()/num_of_steps_down
                    else:
                        pause_down = 0
                    if num_of_steps_up > 0:
                        pause_up = dV1_up*1e3/self.voltage_up_speed_sb1.value()/num_of_steps_up
                    else:
                        pause_up = 0
                    self.voltage_ramp_thread = CyclingThread("V", "up", self.cycle_times_sb.value(), self.keithley1, None, V1_now, None, dV1, dV1_down, dV1_up, None, None, None,
                                                             num_of_steps, num_of_steps_down, num_of_steps_up, pause, pause_down, pause_up)
                elif self.enabled2:
                    dV2 = self.voltage_up_lim_sb2.value() - V2_now
                    dV2_down = self.voltage_up_lim_sb2.value() - self.voltage_down_lim_sb2.value()
                    dV2_up = V2_now - self.voltage_down_lim_sb2.value()
                    num_of_steps = round(self.voltage_up_points_sb2.value()*dV2/(self.voltage_up_lim_sb2.value() - self.voltage_down_lim_sb2.value()))
                    num_of_steps_down = round(self.voltage_down_points_sb2.value()*dV2_down/(self.voltage_up_lim_sb2.value() - self.voltage_down_lim_sb2.value()))
                    num_of_steps_up = round(self.voltage_up_points_sb2.value()*dV2_up/(self.voltage_up_lim_sb2.value() - self.voltage_down_lim_sb2.value()))
                    if num_of_steps > 0:
                        pause = dV2*1e3/self.voltage_up_speed_sb2.value()/num_of_steps
                    else:
                        pause = 0
                    if num_of_steps_down > 0:
                        pause_down = dV2_down*1e3/self.voltage_down_speed_sb2.value()/num_of_steps_down
                    else:
                        pause_down = 0
                    if num_of_steps_up > 0:
                        pause_up = dV2_up*1e3/self.voltage_up_speed_sb2.value()/num_of_steps_up
                    else:
                        pause_up = 0
                    self.voltage_ramp_thread = CyclingThread("V", "up", self.cycle_times_sb.value(), None, self.keithley2, None, V2_now, None, None, None, dV2, dV2_down, dV2_up,
                                                             num_of_steps, num_of_steps_down, num_of_steps_up, pause, pause_down, pause_up)
                self.voltage_ramp_thread.graphSignal.connect(self.update_voltage_graph)
                self.voltage_ramp_thread.finalSignal.connect(self.ramping_finished)
                self.voltage_ramp_thread.start()
            elif self.action_cb.currentText() == "Cycle down":
                if self.in_voltage_ramping:
                    self.voltage_ramp_thread.stop_command = True
                self.in_voltage_ramping = True
                if self.enabled1 and self.enabled2:
                    dV1 = V1_now - self.voltage_down_lim_sb1.value()
                    dV1_down = self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()
                    dV1_up = self.voltage_up_lim_sb1.value() - V1_now
                    dV2 = V2_now - self.voltage_down_lim_sb2.value()
                    dV2_down = self.voltage_up_lim_sb2.value() - self.voltage_down_lim_sb2.value()
                    dV2_up = self.voltage_up_lim_sb2.value() - V2_now
                    num_of_steps = round(self.voltage_down_points_sb1.value()*dV1/(self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()))
                    num_of_steps_down = round(self.voltage_up_points_sb1.value()*dV1_down/(self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()))
                    num_of_steps_up = round(self.voltage_down_points_sb1.value()*dV1_up/(self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()))
                    if num_of_steps > 0:
                        pause = dV1*1e3/self.voltage_down_speed_sb1.value()/num_of_steps
                    else:
                        pause = 0
                    if num_of_steps_down > 0:
                        pause_down = dV1_down*1e3/self.voltage_up_speed_sb1.value()/num_of_steps_down
                    else:
                        pause_down = 0
                    if num_of_steps_up > 0:
                        pause_up = dV1_up*1e3/self.voltage_down_speed_sb1.value()/num_of_steps_up
                    else:
                        pause_up = 0
                    self.voltage_ramp_thread = CyclingThread("V", "down", self.cycle_times_sb.value(), self.keithley1, self.keithley2, V1_now, V2_now, dV1, dV1_down, dV1_up, dV2, dV2_down, dV2_up,
                                                             num_of_steps, num_of_steps_down, num_of_steps_up, pause, pause_down, pause_up)
                elif self.enabled1:
                    dV1 = V1_now - self.voltage_down_lim_sb1.value()
                    dV1_down = self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()
                    dV1_up = self.voltage_up_lim_sb1.value() - V1_now
                    num_of_steps = round(self.voltage_down_points_sb1.value()*dV1/(self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()))
                    num_of_steps_down = round(self.voltage_up_points_sb1.value()*dV1_down/(self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()))
                    num_of_steps_up = round(self.voltage_down_points_sb1.value()*dV1_up/(self.voltage_up_lim_sb1.value() - self.voltage_down_lim_sb1.value()))
                    if num_of_steps > 0:
                        pause = dV1*1e3/self.voltage_down_speed_sb1.value()/num_of_steps
                    else:
                        pause = 0
                    if num_of_steps_down > 0:
                        pause_down = dV1_down*1e3/self.voltage_up_speed_sb1.value()/num_of_steps_down
                    else:
                        pause_down = 0
                    if num_of_steps_up > 0:
                        pause_up = dV1_up*1e3/self.voltage_down_speed_sb1.value()/num_of_steps_up
                    else:
                        pause_up = 0
                    self.voltage_ramp_thread = CyclingThread("V", "down", self.cycle_times_sb.value(), self.keithley1, None, V1_now, None, dV1, dV1_down, dV1_up, None, None, None,
                                                             num_of_steps, num_of_steps_down, num_of_steps_up, pause, pause_down, pause_up)
                elif self.enabled2:
                    dV2 = V2_now - self.voltage_down_lim_sb2.value()
                    dV2_down = self.voltage_up_lim_sb2.value() - self.voltage_down_lim_sb2.value()
                    dV2_up = self.voltage_up_lim_sb2.value() - V2_now
                    num_of_steps = round(self.voltage_down_points_sb2.value()*dV2/(self.voltage_up_lim_sb2.value() - self.voltage_down_lim_sb2.value()))
                    num_of_steps_down = round(self.voltage_up_points_sb2.value()*dV2_down/(self.voltage_up_lim_sb2.value() - self.voltage_down_lim_sb2.value()))
                    num_of_steps_up = round(self.voltage_down_points_sb2.value()*dV2_up/(self.voltage_up_lim_sb2.value() - self.voltage_down_lim_sb2.value()))
                    if num_of_steps > 0:
                        pause = dV2*1e3/self.voltage_down_speed_sb2.value()/num_of_steps
                    else:
                        pause = 0
                    if num_of_steps_down > 0:
                        pause_down = dV2_down*1e3/self.voltage_up_speed_sb2.value()/num_of_steps_down
                    else:
                        pause_down = 0
                    if num_of_steps_up > 0:
                        pause_up = dV2_up*1e3/self.voltage_down_speed_sb2.value()/num_of_steps_up
                    else:
                        pause_up = 0
                    self.voltage_ramp_thread = CyclingThread("V", "down", self.cycle_times_sb.value(), None, self.keithley2, None, V2_now, None, None, None, dV2, dV2_down, dV2_up,
                                                             num_of_steps, num_of_steps_down, num_of_steps_up, pause, pause_down, pause_up)
                self.voltage_ramp_thread.graphSignal.connect(self.update_voltage_graph)
                self.voltage_ramp_thread.finalSignal.connect(self.ramping_finished)
                self.voltage_ramp_thread.start()
            elif self.action_cb.currentText() == "Fixed":
                if self.in_voltage_ramping:
                    self.voltage_ramp_thread.stop_command = True
                self.in_voltage_ramping = False
        else:
            if self.enabled1:
                self.keithley1.measure_current()
                I1_now = self.keithley1.source_current
            if self.enabled2:
                self.keithley2.measure_current()
                I2_now = self.keithley2.source_current
            if self.action_cb.currentText() == "Ramp up":
                if self.in_current_ramping:
                    self.current_ramp_thread.stop_command = True
                self.in_current_ramping = True
                if self.enabled1 and self.enabled2:
                    dI1 = self.current_up_lim_sb1.value() - I1_now
                    dI2 = self.current_up_lim_sb2.value() - I2_now
                    num_of_steps = round(self.current_up_points_sb1.value()*dI1/(self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()))
                    pause = dI1*1e3/self.current_up_speed_sb1.value()/num_of_steps
                    self.current_ramp_thread = RampingThread("I", "up", self.keithley1, self.keithley2, I1_now, I2_now, dI1, dI2, num_of_steps, pause)
                elif self.enabled1:
                    dI1 = self.current_up_lim_sb1.value() - I1_now
                    num_of_steps = round(self.current_up_points_sb1.value()*dI1/(self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()))
                    pause = dI1*1e3/self.current_up_speed_sb1.value()/num_of_steps
                    self.current_ramp_thread = RampingThread("I", "up", self.keithley1, None, I1_now, None, dI1, None, num_of_steps, pause)
                elif self.enabled2:
                    dI2 = self.current_up_lim_sb2.value() - I2_now
                    num_of_steps = round(self.current_up_points_sb2.value()*dI2/(self.current_up_lim_sb2.value() - self.current_down_lim_sb2.value()))
                    pause = dI2*1e3/self.current_up_speed_sb2.value()/num_of_steps
                    self.current_ramp_thread = RampingThread("I", "up", None, self.keithley2, None, I2_now, None, dI2, num_of_steps, pause)
                self.current_ramp_thread.graphSignal.connect(self.update_current_graph)
                self.current_ramp_thread.finalSignal.connect(self.ramping_finished)
                self.current_ramp_thread.start()
            elif self.action_cb.currentText() == "Ramp down":
                if self.in_current_ramping:
                    self.current_ramp_thread.stop_command = True
                self.in_current_ramping = True
                if self.enabled1 and self.enabled2:
                    dI1 = I1_now - self.current_down_lim_sb1.value()
                    dI2 = I2_now - self.current_down_lim_sb2.value()
                    num_of_steps = round(self.current_down_points_sb1.value()*dI1/(self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()))
                    pause = dI1*1e3/self.current_down_speed_sb1.value()/num_of_steps
                    self.current_ramp_thread = RampingThread("I", "down", self.keithley1, self.keithley2, I1_now, I2_now, dI1, dI2, num_of_steps, pause)
                elif self.enabled1:
                    dI1 = I1_now - self.current_down_lim_sb1.value()
                    num_of_steps = round(self.current_down_points_sb1.value()*dI1/(self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()))
                    pause = dI1*1e3/self.current_down_speed_sb1.value()/num_of_steps
                    self.current_ramp_thread = RampingThread("I", "down", self.keithley1, None, I1_now, None, dI1, None, num_of_steps, pause)
                elif self.enabled2:
                    dI2 = I2_now - self.current_down_lim_sb2.value()
                    num_of_steps = round(self.current_down_points_sb2.value()*dI2/(self.current_up_lim_sb2.value() - self.current_down_lim_sb2.value()))
                    pause = dI2*1e3/self.current_down_speed_sb2.value()/num_of_steps
                    self.current_ramp_thread = RampingThread("I", "down", None, self.keithley2, None, I2_now, None, dI2, num_of_steps, pause)
                self.current_ramp_thread.graphSignal.connect(self.update_current_graph)
                self.current_ramp_thread.finalSignal.connect(self.ramping_finished)
                self.current_ramp_thread.start()
            elif self.action_cb.currentText() == "Cycle up":
                if self.in_current_ramping:
                    self.current_ramp_thread.stop_command = True
                self.in_current_ramping = True
                if self.enabled1 and self.enabled2:
                    dI1 = self.current_up_lim_sb1.value() - I1_now
                    dI1_down = self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()
                    dI1_up = I1_now - self.current_down_lim_sb1.value()
                    dI2 = self.current_up_lim_sb2.value() - I2_now
                    dI2_down = self.current_down_lim_sb2.value() - self.current_up_lim_sb2.value()
                    dI2_up = I2_now - self.current_down_lim_sb2.value()
                    num_of_steps = round(self.current_up_points_sb1.value()*dI1/(self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()))
                    num_of_steps_down = round(self.current_down_points_sb1.value()*dI1_down/(self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()))
                    num_of_steps_up = round(self.current_up_points_sb1.value()*dI1_up/(self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()))
                    if num_of_steps > 0:
                        pause = dI1*1e3/self.current_up_speed_sb1.value()/num_of_steps
                    else:
                        pause = 0
                    if num_of_steps_down > 0:
                        pause_down = dI1_down*1e3/self.current_down_speed_sb1.value()/num_of_steps_down
                    else:
                        pause_down = 0
                    if num_of_steps_up > 0:
                        pause_up = dI1_up*1e3/self.current_up_speed_sb1.value()/num_of_steps_up
                    else:
                        pause_up = 0
                    self.current_ramp_thread = CyclingThread("I", "up", self.cycle_times_sb.value(), self.keithley1, self.keithley2, I1_now, I2_now, dI1, dI1_down, dI1_up, dI2, dI2_down, dI2_up,
                                                             num_of_steps, num_of_steps_down, num_of_steps_up, pause, pause_down, pause_up)
                elif self.enabled1:
                    dI1 = self.current_up_lim_sb1.value() - I1_now
                    dI1_down = self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()
                    dI1_up = I1_now - self.current_down_lim_sb1.value()
                    num_of_steps = round(self.current_up_points_sb1.value()*dI1/(self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()))
                    num_of_steps_down = round(self.current_down_points_sb1.value()*dI1_down/(self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()))
                    num_of_steps_up = round(self.current_up_points_sb1.value()*dI1_up/(self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()))
                    if num_of_steps > 0:
                        pause = dI1*1e3/self.current_up_speed_sb1.value()/num_of_steps
                    else:
                        pause = 0
                    if num_of_steps_down > 0:
                        pause_down = dI1_down*1e3/self.current_down_speed_sb1.value()/num_of_steps_down
                    else:
                        pause_down = 0
                    if num_of_steps_up > 0:
                        pause_up = dI1_up*1e3/self.current_up_speed_sb1.value()/num_of_steps_up
                    else:
                        pause_up = 0
                    self.current_ramp_thread = CyclingThread("V", "up", self.cycle_times_sb.value(), self.keithley1, None, I1_now, None, dI1, dI1_down, dI1_up, None, None, None,
                                                             num_of_steps, num_of_steps_down, num_of_steps_up, pause, pause_down, pause_up)
                elif self.enabled2:
                    dI2 = self.current_up_lim_sb2.value() - I2_now
                    dI2_down = self.current_down_lim_sb2.value() - self.current_up_lim_sb2.value()
                    dI2_up = I2_now - self.current_down_lim_sb2.value()
                    num_of_steps = round(self.current_up_points_sb2.value()*dI2/(self.current_up_lim_sb2.value() - self.current_down_lim_sb2.value()))
                    num_of_steps_down = round(self.current_down_points_sb2.value()*dI2_down/(self.current_up_lim_sb2.value() - self.current_down_lim_sb2.value()))
                    num_of_steps_up = round(self.current_up_points_sb2.value()*dI2_up/(self.current_up_lim_sb2.value() - self.current_down_lim_sb2.value()))
                    if num_of_steps > 0:
                        pause = dI2*1e3/self.current_up_speed_sb2.value()/num_of_steps
                    else:
                        pause = 0
                    if num_of_steps_down > 0:
                        pause_down = dI2_down*1e3/self.current_down_speed_sb2.value()/num_of_steps_down
                    else:
                        pause_down = 0
                    if num_of_steps_up > 0:
                        pause_up = dI2_up*1e3/self.current_up_speed_sb2.value()/num_of_steps_up
                    else:
                        pause_up = 0
                    self.current_ramp_thread = CyclingThread("I", "up", self.cycle_times_sb.value(), None, self.keithley2, None, I2_now, None, None, None, dI2, dI2_down, dI2_up,
                                                             num_of_steps, num_of_steps_down, num_of_steps_up, pause, pause_down, pause_up)
                self.voltage_ramp_thread.graphSignal.connect(self.update_voltage_graph)
                self.voltage_ramp_thread.finalSignal.connect(self.ramping_finished)
                self.voltage_ramp_thread.start()
            elif self.action_cb.currentText() == "Cycle down":
                if self.in_voltage_ramping:
                    self.voltage_ramp_thread.stop_command = True
                self.in_voltage_ramping = True
                if self.enabled1 and self.enabled2:
                    dI1 = I1_now - self.current_down_lim_sb1.value()
                    dI1_down = self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()
                    dI1_up = self.current_up_lim_sb1.value() - I1_now
                    dI2 = I2_now - self.current_down_lim_sb2.value()
                    dI2_down = self.current_up_lim_sb2.value() - self.current_down_lim_sb2.value()
                    dI2_up = self.current_up_lim_sb2.value() - I2_now
                    num_of_steps = round(self.current_down_points_sb1.value()*dI1/(self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()))
                    num_of_steps_down = round(self.current_up_points_sb1.value()*dI1_down/(self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()))
                    num_of_steps_up = round(self.current_down_points_sb1.value()*dI1_up/(self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()))
                    if num_of_steps > 0:
                        pause = dI1*1e3/self.current_down_speed_sb1.value()/num_of_steps
                    else:
                        pause  = 0
                    if num_of_steps_down > 0:
                        pause_down = dI1_down*1e3/self.current_up_speed_sb1.value()/num_of_steps_down
                    else:
                        pause_down = 0
                    if num_of_steps_up > 0:
                        pause_up = dI1_up*1e3/self.current_down_speed_sb1.value()/num_of_steps_up
                    else:
                        pause_up = 0
                    self.current_ramp_thread = CyclingThread("I", "down", self.cycle_times_sb.value(), self.keithley1, self.keithley2, I1_now, I2_now, dI1, dI1_down, dI1_up, dI2, dI2_down, dI2_up,
                                                             num_of_steps, num_of_steps_down, num_of_steps_up, pause, pause_down, pause_up)
                elif self.enabled1:
                    dI1 = I1_now - self.current_down_lim_sb1.value()
                    dI1_down = self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()
                    dI1_up = self.current_up_lim_sb1.value() - I1_now
                    num_of_steps = round(self.current_down_points_sb1.value()*dI1/(self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()))
                    num_of_steps_down = round(self.current_up_points_sb1.value()*dI1_down/(self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()))
                    num_of_steps_up = round(self.current_down_points_sb1.value()*dI1_up/(self.current_up_lim_sb1.value() - self.current_down_lim_sb1.value()))
                    if num_of_steps > 0:
                        pause = dI1*1e3/self.current_down_speed_sb1.value()/num_of_steps
                    else:
                        pause  = 0
                    if num_of_steps_down > 0:
                        pause_down = dI1_down*1e3/self.current_up_speed_sb1.value()/num_of_steps_down
                    else:
                        pause_down = 0
                    if num_of_steps_up > 0:
                        pause_up = dI1_up*1e3/self.current_down_speed_sb1.value()/num_of_steps_up
                    else:
                        pause_up = 0
                    self.current_ramp_thread = CyclingThread("I", "down", self.cycle_times_sb.value(), self.keithley1, None, I1_now, None, dI1, dI1_down, dI1_up, None, None, None,
                                                             num_of_steps, num_of_steps_down, num_of_steps_up, pause, pause_down, pause_up)
                elif self.enabled2:
                    dI2 = I2_now - self.current_down_lim_sb2.value()
                    dI2_down = self.current_up_lim_sb2.value() - self.current_down_lim_sb2.value()
                    dI2_up = self.current_up_lim_sb2.value() - I2_now
                    num_of_steps = round(self.current_down_points_sb2.value()*dI2/(self.current_up_lim_sb2.value() - self.current_down_lim_sb2.value()))
                    num_of_steps_down = round(self.current_up_points_sb2.value()*dI2_down/(self.current_up_lim_sb2.value() - self.current_down_lim_sb2.value()))
                    num_of_steps_up = round(self.current_down_points_sb2.value()*dI2_up/(self.current_up_lim_sb2.value() - self.current_down_lim_sb2.value()))
                    if num_of_steps > 0:
                        pause = dI2*1e3/self.current_down_speed_sb2.value()/num_of_steps
                    else:
                        pause = 0
                    if num_of_steps_down > 0:
                        pause_down = dI2_down*1e3/self.current_up_speed_sb2.value()/num_of_steps_down
                    else:
                        pause_down = 0
                    if num_of_steps_up > 0:
                        pause_up = dI2_up*1e3/self.current_down_speed_sb2.value()/num_of_steps_up
                    else:
                        pause_up = 0
                    self.current_ramp_thread = CyclingThread("I", "down", self.cycle_times_sb.value(), None, self.keithley2, None, I2_now, None, None, None, dI2, dI2_down, dI2_up,
                                                             num_of_steps, num_of_steps_down, num_of_steps_up, pause, pause_down, pause_up)
                self.current_ramp_thread.graphSignal.connect(self.update_current_graph)
                self.current_ramp_thread.finalSignal.connect(self.ramping_finished)
                self.current_ramp_thread.start()
            elif self.action_cb.currentText() == "Fixed":
                if self.in_current_ramping:
                    self.current_ramp_thread.stop_command = True
                self.in_current_ramping = False

    def update_voltage_graph(self, x, y):
        if x is not None:
            self.voltage_now_curve.set_xdata([x])
        if y is not None:
            self.voltage_now_curve.set_ydata([y])
        self.voltage_F.draw()


    def update_current_graph(self, x, y):
        if x is not None:
            self.current_now_curve.set_xdata([x])
        if y is not None:
            self.current_now_curve.set_ydata([y])
        self.current_F.draw()

    def ramping_finished(self):
        self.action_cb.setCurrentText("Fixed")
        self.in_voltage_ramping = False
        self.in_current_ramping = False

class RampingThread(QThread):
    graphSignal = pyqtSignal(object, object)
    finalSignal = pyqtSignal()
    def __init__(self, V_I, mode, keithley1, keithley2, V1_now, V2_now, dV1, dV2, num_of_steps, pause, parent=None):
        super(RampingThread, self).__init__(parent)
        self.V_I = V_I
        self.mode = mode
        self.keithley1 = keithley1
        self.keithley2 = keithley2
        self.V1_now = V1_now
        self.V2_now = V2_now
        self.dV1 = dV1
        self.dV2 = dV2
        self.num_of_steps = num_of_steps
        self.pause = pause
        self.stop_command = False

    # def run(self):
    #     for i in range(self.num_of_steps):
    #         if self.stop_command:
    #             break
    #         if self.keithley1 is not None:
    #             if self.mode == "up":
    #                 target1 = self.dV1/self.num_of_steps*(i+1)+self.V1_now
    #             else:
    #                 target1 = self.V1_now - self.dV1/self.num_of_steps*(i+1)
    #             print(target1)
    #             if self.V_I == "V":
    #                 self.keithley1.ramp_to_voltage(target1)
    #             else:
    #                 self.keithley1.ramp_to_current(target1)
    #         if self.keithley2 is not None:
    #             if self.mode == "up":
    #                 target2 = self.dV2/self.num_of_steps*(i+1)+self.V2_now
    #             else:
    #                 target2 = self.V2_now - self.dV2/self.num_of_steps*(i+1)
    #             if self.V_I == "V":
    #                 self.keithley2.ramp_to_voltage(target2)
    #             else:
    #                 self.keithley2.ramp_to_current(target2)
    #         QTest.qWait(self.pause * 1000)
    #         if self.keithley1 is not None and self.keithley2 is not None:
    #             self.graphSignal.emit(target1, target2)
    #         elif self.keithley1 is not None:
    #             self.graphSignal.emit(target1, None)
    #         elif self.keithley2 is not None:
    #             self.graphSignal.emit(None, target2)
    #     if not self.stop_command:
    #         self.finalSignal.emit()
    def run(self):
        for i in range(self.num_of_steps):
            if self.stop_command:
                break
            if self.keithley1 is not None:
                if self.mode == "up":
                    target1 = self.dV1/self.num_of_steps*(i+1)+self.V1_now
                else:
                    target1 = self.V1_now - self.dV1/self.num_of_steps*(i+1)
                print(target1)
                if self.V_I == "V":
                    self.keithley1.source_voltage = target1
                    time.sleep(self.pause)
                else:
                    self.keithley1.source_current = target1
                    time.sleep(self.pause)
            if self.keithley2 is not None:
                if self.mode == "up":
                    target2 = self.dV2/self.num_of_steps*(i+1)+self.V2_now
                else:
                    target2 = self.V2_now - self.dV2/self.num_of_steps*(i+1)
                if self.V_I == "V":
                    self.keithley2.source_voltage = target2
                    time.sleep(self.pause)
                else:
                    self.keithley2.source_current = target2
                    time.sleep(self.pause)
            if self.keithley1 is not None and self.keithley2 is not None:
                self.graphSignal.emit(target1, target2)
            elif self.keithley1 is not None:
                self.graphSignal.emit(target1, None)
            elif self.keithley2 is not None:
                self.graphSignal.emit(None, target2)
        if not self.stop_command:
            self.finalSignal.emit()

class CyclingThread(QThread):
    graphSignal = pyqtSignal(object, object)
    finalSignal = pyqtSignal()
    def __init__(self, V_I, mode, times, keithley1, keithley2, V1_now, V2_now, dV1, dV1_down, dV1_up, dV2, dV2_down, dV2_up,
                                                             num_of_steps, num_of_steps_down, num_of_steps_up, pause, pause_down, pause_up, parent=None):
        super(CyclingThread, self).__init__(parent)
        self.V_I = V_I
        self.mode = mode
        self.times = times
        self.keithley1 = keithley1
        self.keithley2 = keithley2
        self.V1_now = V1_now
        self.V2_now = V2_now
        self.dV1 = dV1
        self.dV1_down = dV1_down
        self.dV1_up = dV1_up
        self.dV2 = dV2
        self.dV2_down = dV2_down
        self.dV2_up = dV2_up
        self.num_of_steps = num_of_steps
        self.num_of_steps_down = num_of_steps_down
        self.num_of_steps_up = num_of_steps_up
        self.pause = pause
        self.pause_down = pause_down
        self.pause_up = pause_up
        self.stop_command = False

    def run(self):
        for t in range(self.times):
            for i in range(self.num_of_steps):
                if self.stop_command:
                    break
                if self.keithley1 is not None:
                    if self.mode == "up":
                        target1 = self.dV1/self.num_of_steps*(i+1)+self.V1_now
                    else:
                        target1 = self.V1_now - self.dV1/self.num_of_steps*(i+1)
                    print(target1)
                    if self.V_I == "V":
                        self.keithley1.source_voltage = target1
                        time.sleep(self.pause)
                    else:
                        self.keithley1.source_current = target1
                        time.sleep(self.pause)
                if self.keithley2 is not None:
                    if self.mode == "up":
                        target2 = self.dV2/self.num_of_steps*(i+1)+self.V2_now
                    else:
                        target2 = self.V2_now - self.dV2/self.num_of_steps*(i+1)
                    if self.V_I == "V":
                        self.keithley2.source_voltage = target2
                        time.sleep(self.pause)
                    else:
                        self.keithley2.source_current = target2
                        time.sleep(self.pause)
                if self.keithley1 is not None and self.keithley2 is not None:
                    self.graphSignal.emit(target1, target2)
                elif self.keithley1 is not None:
                    self.graphSignal.emit(target1, None)
                elif self.keithley2 is not None:
                    self.graphSignal.emit(None, target2)
            for i in range(self.num_of_steps_down):
                if self.stop_command:
                    break
                if self.keithley1 is not None:
                    if self.mode == "up":
                        target1 = self.V1_now + self.dV1 - self.dV1_down/self.num_of_steps_down*(i+1)
                    else:
                        target1 = self.V1_now - self.dV1 + self.dV1_down/self.num_of_steps_down*(i+1)
                    print(target1)
                    if self.V_I == "V":
                        self.keithley1.source_voltage = target1
                        time.sleep(self.pause)
                    else:
                        self.keithley1.source_current = target1
                        time.sleep(self.pause)
                if self.keithley2 is not None:
                    if self.mode == "up":
                        target2 = self.V2_now + self.dV2 - self.dV2_down/self.num_of_steps_down*(i+1)
                    else:
                        target2 = self.V2_now - self.dV2 + self.dV2_down/self.num_of_steps_down*(i+1)
                    if self.V_I == "V":
                        self.keithley2.source_voltage = target2
                        time.sleep(self.pause)
                    else:
                        self.keithley2.source_current = target2
                        time.sleep(self.pause)
                if self.keithley1 is not None and self.keithley2 is not None:
                    self.graphSignal.emit(target1, target2)
                elif self.keithley1 is not None:
                    self.graphSignal.emit(target1, None)
                elif self.keithley2 is not None:
                    self.graphSignal.emit(None, target2)
            for i in range(self.num_of_steps_up):
                if self.stop_command:
                    break
                if self.keithley1 is not None:
                    if self.mode == "up":
                        target1 = self.V1_now + self.dV1 - self.dV1_down + self.dV1_up/self.num_of_steps_up*(i+1)
                    else:
                        target1 = self.V1_now - self.dV1 + self.dV1_down - self.dV1_up/self.num_of_steps_up*(i+1)
                    print(target1)
                    if self.V_I == "V":
                        self.keithley1.source_voltage = target1
                        time.sleep(self.pause)
                    else:
                        self.keithley1.source_current = target1
                        time.sleep(self.pause)
                if self.keithley2 is not None:
                    if self.mode == "up":
                        target2 = self.V2_now + self.dV2 - self.dV2_down + self.dV2_up/self.num_of_steps_up*(i+1)
                    else:
                        target2 = self.V2_now - self.dV2 + self.dV2_down - self.dV2_up/self.num_of_steps_up*(i+1)
                    if self.V_I == "V":
                        self.keithley2.source_voltage = target2
                        time.sleep(self.pause)
                    else:
                        self.keithley2.source_current = target2
                        time.sleep(self.pause)
                if self.keithley1 is not None and self.keithley2 is not None:
                    self.graphSignal.emit(target1, target2)
                elif self.keithley1 is not None:
                    self.graphSignal.emit(target1, None)
                elif self.keithley2 is not None:
                    self.graphSignal.emit(None, target2)

        if not self.stop_command:
            self.finalSignal.emit()

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

class UpdateVIThread1(QThread):
    def __init__(self, widget, parent=None):
        super(UpdateVIThread1, self).__init__(parent)
        self.widget = widget

    def run(self):
        self.Timer = QTimer()
        self.Timer.timeout.connect(self.updateIVR)
        self.Timer.start(2000)
        loop = QEventLoop()
        loop.exec_()

    def updateIVR(self):
        try:
            if not self.widget.in_voltage_ramping and not self.widget.in_current_ramping:
                if self.widget.keithley1.source_current < 1e-7:
                    self.widget.I_value_lb1.setText(str(round(self.widget.keithley1.source_current*1e9, 4)) + " nA")
                elif self.widget.keithley1.source_current < 1e-4:
                    self.widget.I_value_lb1.setText(str(round(self.widget.keithley1.source_current*1e6, 4)) + " uA")
                elif self.widget.keithley1.source_current < 1e-1:
                    self.widget.I_value_lb1.setText(str(round(self.widget.keithley1.source_current*1e3, 4)) + " mA")
                else:
                    self.widget.I_value_lb1.setText(str(round(self.widget.keithley1.source_current, 4)) + " A")
                if self.widget.keithley1.source_voltage < 1e-7:
                    self.widget.V_value_lb1.setText(str(round(self.widget.keithley1.source_voltage*1e9, 4)) + " nV")
                elif self.widget.keithley1.source_voltage < 1e-4:
                    self.widget.V_value_lb1.setText(str(round(self.widget.keithley1.source_voltage*1e6, 4)) + " uV")
                elif self.widget.keithley1.source_voltage < 1e-1:
                    self.widget.V_value_lb1.setText(str(round(self.widget.keithley1.source_voltage*1e3, 4)) + " mV")
                else:
                    self.widget.V_value_lb1.setText(str(round(self.widget.keithley1.source_voltage, 4)) + " V")
                self.widget.voltage_now_curve.set_xdata([round(self.widget.keithley1.source_voltage, 4)])
                self.widget.voltage_F.draw()
        except:
            return

class UpdateVIThread2(QThread):
    def __init__(self, widget, parent=None):
        super(UpdateVIThread2, self).__init__(parent)
        self.widget = widget

    def run(self):
        self.Timer = QTimer()
        self.Timer.timeout.connect(self.updateIVR)
        self.Timer.start(2000)
        loop = QEventLoop()
        loop.exec_()

    def updateIVR(self):
        try:
            if not self.widget.in_voltage_ramping and not self.widget.in_current_ramping:
                if self.widget.keithley2.source_current < 1e-7:
                    self.widget.I_value_lb2.setText(str(round(self.widget.keithley2.source_current*1e9, 4)) + " nA")
                elif self.widget.keithley2.source_current < 1e-4:
                    self.widget.I_value_lb2.setText(str(round(self.widget.keithley2.source_current*1e6, 4)) + " uA")
                elif self.widget.keithley2.source_current < 1e-1:
                    self.widget.I_value_lb2.setText(str(round(self.widget.keithley2.source_current*1e3, 4)) + " mA")
                else:
                    self.widget.I_value_lb2.setText(str(round(self.widget.keithley2.source_current, 4)) + " A")
                if self.widget.keithley2.source_voltage < 1e-7:
                    self.widget.V_value_lb2.setText(str(round(self.widget.keithley2.source_voltage*1e9, 4)) + " nV")
                elif self.widget.keithley2.source_voltage < 1e-4:
                    self.widget.V_value_lb2.setText(str(round(self.widget.keithley2.source_voltage*1e6, 4)) + " uV")
                elif self.widget.keithley2.source_voltage < 1e-1:
                    self.widget.V_value_lb2.setText(str(round(self.widget.keithley2.source_voltage*1e3, 4)) + " mV")
                else:
                    self.widget.V_value_lb2.setText(str(round(self.widget.keithley2.source_voltage, 4)) + " V")
                self.widget.voltage_now_curve.set_ydata([round(self.widget.keithley2.source_voltage, 4)])
                self.widget.voltage_F.draw()
        except:
            return

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SourceMeter()
    sys.exit(app.exec_())
