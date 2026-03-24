from pymeasure.instruments.srs.sr830 import *
from pymeasure.instruments.srs.sr860 import *
import pyvisa
from QCL_interface import *
from mercurygui.pyqtplot_canvas import VoltageHistoryPlot, VoltageTemperaturePlot

class LockinAmplifier(QFrame):
    def __init__(self):
        super().__init__()
        # self.setGeometry(700, 400, 500, 450)
        self.setWindowTitle("Lock-in Amplifier")
        self.MAX_DISPLAY = 3*24*60*60
        self.filename = "Log"
        self.filepath = ""
        self.magnitude = []
        self.connected = False
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

        self.reading_lb = QLabel("Readings")
        self.reading1_lb = QLabel("")
        self.reading2_lb = QLabel("")
        self.reading3_lb = QLabel("")
        main_grid.addWidget(self.reading_lb, 1, 0, 1, 1, Qt.AlignCenter)
        main_grid.addWidget(self.reading1_lb, 1, 1, 1, 1, Qt.AlignCenter)
        main_grid.addWidget(self.reading2_lb, 1, 2, 1, 1, Qt.AlignCenter)
        main_grid.addWidget(self.reading3_lb, 1, 3, 1, 1, Qt.AlignCenter)

        self.tabs = QTabWidget()
        self.tabs.setFixedWidth(600)
        self.tabs.setFixedHeight(500)
        self.voltage_temperature_tab = QWidget()
        self.voltage_time_tab = QWidget()

        # set the voltage-temperature plot
        vbox1 = QVBoxLayout()
        vbox1.setSpacing(10)
        self.voltage_temperature_tab.setLayout(vbox1)

        self.voltage_temperature_canvas = VoltageTemperaturePlot()

        vbox1.addWidget(self.voltage_temperature_canvas)

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
        self.horizontalSlider.setFixedWidth(500)

        # connect slider to plot
        self.horizontalSlider.valueChanged.connect(self.on_slider_changed)

        vbox2.addWidget(self.voltage_time_canvas)
        vbox2.addWidget(self.timeLabel)
        vbox2.addWidget(self.horizontalSlider)


        self.tabs.addTab(self.voltage_temperature_tab, "Voltage-Temperature")
        self.tabs.addTab(self.voltage_time_tab, "Voltage-Time")
        main_grid.addWidget(self.tabs, 2, 0, 6, 4, Qt.AlignCenter)

        self.trigger_lb = QLabel("Trigger")
        self.trigger_cb = QComboBox()
        self.trigger_cb.addItems(["No trigger", "Temperature", "Voltage"])
        self.threshold_lb = QLabel("Threshold")
        self.threshold_sb = QDoubleSpinBox()
        main_grid.addWidget(self.trigger_lb, 8, 0, 1, 1, Qt.AlignCenter)
        main_grid.addWidget(self.trigger_cb, 8, 1, 1, 1, Qt.AlignCenter)
        main_grid.addWidget(self.threshold_lb, 8, 2, 1, 1, Qt.AlignCenter)
        main_grid.addWidget(self.threshold_sb, 8, 3, 1, 1, Qt.AlignCenter)

        self.filename_lb = QLabel("Filename")
        self.filename_le = QLineEdit("Log")
        main_grid.addWidget(self.filename_lb, 9, 0, 1, 1, Qt.AlignCenter)
        main_grid.addWidget(self.filename_le, 9, 1, 1, 2, Qt.AlignCenter)

        self.filepath_btn = QPushButton("Save to path")
        self.filepath_btn.clicked.connect(self.set_filepath)
        self.filepath_dispaly_lb = QLabel("")
        main_grid.addWidget(self.filepath_btn, 10, 0, 1, 1, Qt.AlignCenter)
        main_grid.addWidget(self.filepath_dispaly_lb, 10, 1, 1, 3, Qt.AlignCenter)


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

            print(self.lockin.magnitude, self.lockin.theta, self.lockin.sine_voltage)

            # update magnitude, phase, reference every second (1000 ms)
            self.timer = QTimer()
            self.timer.timeout.connect(self.updateMPR)
            self.timer.start(1500)

    def updateMPR(self):
        magnitude = self.lockin.magnitude
        phase = self.lockin.theta
        reference = self.lockin.sine_voltage
        if magnitude < 1e-7:
            self.reading1_lb.setText("{:.3f} nV".format(magnitude*1e9))
        elif magnitude < 1e-4:
            self.reading1_lb.setText(u"{:.3f} \u03bcV".format(magnitude*1e6))
        elif magnitude < 0.1:
            self.reading1_lb.setText(u"{:.3f} mV".format(magnitude*1e3))
        else:
            self.reading1_lb.setText(u"{:.3f} V".format(magnitude))
        self.reading2_lb.setText("{:.3f} deg".format(phase))
        if reference < 1e-7:
            self.reading3_lb.setText("{:.3f} nV".format(reference*1e9))
        elif reference < 1e-4:
            self.reading3_lb.setText(u"{:.3f} \u03bcV".format(reference*1e6))
        elif reference < 0.1:
            self.reading3_lb.setText(u"{:.3f} mV".format(reference*1e3))
        else:
            self.reading3_lb.setText(u"{:.3f} V".format(reference))

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

    def on_slider_changed(self):
        # determine first plotted data point
        sv = self.horizontalSlider.value()

        self.timeLabel.setText("Show last %s min" % sv)
        self.voltage_time_canvas.set_xmin(-sv)
        self.voltage_time_canvas.p0.setXRange(-sv, 0)
        self.voltage_time_canvas.p0.enableAutoRange(x=False, y=True)

    def set_filepath(self):
        path = QFileDialog.getExistingDirectory(self, "Select a folder", r"D:\Data")
        self.filepath_dispaly_lb.setText(path)
        self.filepath = path

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LockinAmplifier()
    sys.exit(app.exec_())
