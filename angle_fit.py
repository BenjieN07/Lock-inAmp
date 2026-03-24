import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from functools import partial
import sys
import matplotlib
matplotlib.use("Qt5Agg")  # 声明使用QT5
matplotlib.rcParams['savefig.dpi'] = 600
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from scipy import optimize
import os
import re
from scipy.interpolate import interp1d

"""
================
Title: Angle Analysis GUI
Author: Siyuan Qiu
Create Date: 2023/3/7
Institution: Columbia University, Department of Physics
=================
"""

class MainWindow(QFrame):
    def __init__(self):
        super().__init__()
        self.show()
        self.initUI()
        self.setGeometry(150, 200, 1200, 600)
        self.reflectance = []
        self.freq = []
        self.angles = []
        self.reflectance_loaded = False
        self.cbar_R = None
        self.line_r1 = None
        self.line_peaks = None
        self.fit_line = None

    def initUI(self):
        # create main grid to organize layout
        main_grid = QGridLayout()
        main_grid.setSpacing(10)
        self.setLayout(main_grid)
        self.setWindowTitle("Angle analysis")

        self.figure = plt.figure()
        self.F = FigureCanvas(self.figure)
        main_grid.addWidget(NavigationToolbar(self.F, self), 0, 0, 1, 6, Qt.AlignCenter)
        main_grid.addWidget(self.F, 1, 0, 1, 6)

        self.freq_sld = QSlider(Qt.Horizontal)
        self.freq_sld.setTickPosition(QSlider.TicksBelow)
        self.freq_sld.setMaximum(5000)
        self.freq_sld.setMinimum(0)
        self.freq_sld.setSingleStep(1)
        self.freq_sld.setTickInterval(100)
        self.freq_sld.setFixedWidth(350)
        self.freq_sld.setEnabled(False)
        self.freq_sld.valueChanged.connect(self.setFreqSb)
        main_grid.addWidget(self.freq_sld, 2, 0, 1, 2, Qt.AlignCenter)

        self.freq_sb = QDoubleSpinBox()
        self.freq_sb.setMaximum(20000)
        self.freq_sb.setEnabled(False)
        self.freq_sb.setFixedWidth(100)
        self.freq_sb.editingFinished.connect(self.setFreqSld)
        main_grid.addWidget(self.freq_sb, 2, 2, 1, 1, Qt.AlignCenter)

        self.load_reflectance_btn = QPushButton('Load Reflectance.txt')
        self.load_reflectance_btn.clicked.connect(self.load_reflectance)
        self.load_reflectance_btn.setFixedWidth(500)
        main_grid.addWidget(self.load_reflectance_btn, 3, 0, 1, 3, Qt.AlignCenter)

        hbox1 = QHBoxLayout()
        hbox2 = QHBoxLayout()
        hbox3 = QHBoxLayout()
        intensity_ratio_lb = QLabel("Intensity ratio")
        self.intensity_ratio_sb = QDoubleSpinBox()
        self.intensity_ratio_sb.setMaximum(1)
        self.intensity_ratio_sb.setMinimum(-1)
        self.intensity_ratio_sb.setFixedWidth(60)
        rotation_angle_lb = QLabel("Rotation angle")
        self.rotation_angle_sb = QDoubleSpinBox()
        self.rotation_angle_sb.setMaximum(360)
        self.rotation_angle_sb.setMinimum(-360)
        self.rotation_angle_sb.setFixedWidth(60)
        offset_lb = QLabel("Offset")
        self.offset_sb = QDoubleSpinBox()
        self.offset_sb.setMaximum(360)
        self.offset_sb.setMinimum(-360)
        self.offset_sb.setFixedWidth(60)
        hbox1.addWidget(intensity_ratio_lb)
        hbox1.addWidget(self.intensity_ratio_sb)
        hbox2.addWidget(rotation_angle_lb)
        hbox2.addWidget(self.rotation_angle_sb)
        hbox3.addWidget(offset_lb)
        hbox3.addWidget(self.offset_sb)
        main_grid.addLayout(hbox1, 2, 3, 1, 1, Qt.AlignCenter)
        main_grid.addLayout(hbox2, 2, 4, 1, 1, Qt.AlignCenter)
        main_grid.addLayout(hbox3, 2, 5, 1, 1, Qt.AlignCenter)

        self.cos_rb = QRadioButton("cos")
        self.cos_sqaure_rb = QRadioButton("cos square")
        self.cos_sqaure_rb.setChecked(True)
        vbox1 = QVBoxLayout()
        vbox1.addWidget(self.cos_rb)
        vbox1.addWidget(self.cos_sqaure_rb)
        main_grid.addLayout(vbox1, 3, 3, 1, 1, Qt.AlignCenter)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.remove_fit_line)
        main_grid.addWidget(self.clear_btn, 3, 4, 1, 1, Qt.AlignCenter)
        self.fit_btn = QPushButton("Fit")
        self.fit_btn.clicked.connect(self.fit_angles)
        main_grid.addWidget(self.fit_btn, 3, 5, 1, 1, Qt.AlignCenter)

    def load_reflectance(self):
        path = QFileDialog.getOpenFileName(self, "Select a file", r"D:\Data", "TXT Files (*.txt)")
        if path[0] != "":
            file = open(path[0], 'r')
        else:
            return
        num_of_frequencies = 0
        num_of_angles = 0
        angles = []
        try:
            for line_index, line_str in enumerate(file):
                if line_index == 0:
                    line_list = self.split_string_to_data(line_str)
                    num_of_angles += len(line_list) - 1
                    for angle in line_list[1:]:
                        angles.append(float(angle))
                else:
                    num_of_frequencies += 1
            file.close()
            reflectance = np.zeros((num_of_angles, num_of_frequencies))
            freq = []
            file = open(path[0], 'r')
            for line_index, line_str in enumerate(file):
                if line_index == 0:
                    continue
                line_list = self.split_string_to_data(line_str)
                for i in range(len(line_list)):
                    if i == 0:
                        freq.append(float(line_list[i]))
                    else:
                        reflectance[i-1,line_index-1] += float(line_list[i])
            file.close()
            self.reflectance = reflectance
            self.freq = freq
            self.angles = angles
            self.draw_reflectance()
            self.freq_sld.setEnabled(True)
            self.freq_sb.setEnabled(True)
            self.reflectance_loaded = True
            self.freq_sld.setMaximum(len(self.freq)-1)
            self.freq_sb.setMaximum(self.freq[-1])
            self.freq_sb.setMinimum(self.freq[0])

        except:
            QMessageBox.warning(self, "Load reflectance", "You are not selecting a correct file!")
            return

    def draw_reflectance(self):
        if self.cbar_R is not None:
            self.cbar_R.remove()
        self.axes_F1 = self.figure.add_subplot(121)
        self.axes_F2 = self.figure.add_subplot(122)
        # 2D color plot
        min_index = 0
        max_index = len(self.freq)
        freq = self.freq[min_index:max_index]
        arg = np.argsort(np.array(self.angles))
        angles = np.array(self.angles)[arg]
        reflectance = np.array(self.reflectance)[arg]
        ff, aa = np.meshgrid(freq,angles)
        img = self.axes_F1.pcolormesh(ff, aa, reflectance[:, min_index:max_index], vmin=0, vmax=1, shading='auto')
        self.axes_F1.set_title("Reflectance", fontsize=12)
        self.axes_F1.set_ylabel("Angle (deg)", fontsize=9)
        self.axes_F1.set_xlabel(r'Frequency (cm$^{-1}$)', fontsize=9)
        self.cbar_R = self.F.figure.colorbar(img, ax=self.axes_F1, shrink=0.6)
        self.F.figure.subplots_adjust(left=0.1,
                    bottom=0.15,
                    right=0.9,
                    top=0.9,
                    wspace=0.4,
                    hspace=0.4)
        self.F.draw()

    def setFreqSb(self):
        self.freq_sb.setValue(self.freq[self.freq_sld.value()])
        self.draw_peaks()

    def setFreqSld(self):
        freq = np.asarray(self.freq)
        i = (np.abs(freq - self.freq_sb.value())).argmin()
        self.freq_sb.setValue(self.freq[i])
        self.freq_sld.setValue(i)
        self.draw_peaks()

    def draw_peaks(self):
        if self.reflectance_loaded:
            if self.line_r1 is not None:
                self.line_r1.remove()
            self.line_r1 = self.axes_F1.axvline(x = self.freq_sb.value(), color = 'r', linestyle = '--')
            if self.line_peaks is not None:
                self.line_peaks.remove()
            self.line_peaks = self.axes_F2.scatter(self.angles, self.reflectance[:, self.freq_sld.value()], color="r")
            self.axes_F2.set_title("Peaks", fontsize=12)
            self.axes_F2.set_xlabel(r'Angle (deg)', fontsize=9)
            self.F.draw()

    def remove_fit_line(self):
        if self.fit_line is not None:
            self.fit_line.remove()
            self.fit_line = None
        self.F.draw()

    def fitfunc(self, p, x):
        """
        x = angle in degrees
        p = fitting parameters
        p[0]: Intensity ratio
        p[1]: Rotation angle, theta_F
        p[2]: offset from leaky polarizer
        """
        xrad = [i*np.pi/180 for i in x]
        if self.cos_rb.isChecked():
            return p[0]*np.cos(xrad-p[1]) + p[2]
        else:
            return p[0]*pow(np.cos(xrad-p[1]),2) + p[2]

    def resid(self, p, x, y):
        return ((y - self.fitfunc(p, x))**2)

    def fit(self, init, x, y):
        # initial guess for paras.
        res,flag = optimize.leastsq(self.resid, init, args=(x, y), maxfev=50000)
        [p0,p1,p2] = res
        print('p0 = %.3f, p1 = %.3f, rotation angle = %f degs' %(p0,p1,p1*180/np.pi))
        return [p0,p1,p2]

    def fit_angles(self):
        if self.reflectance_loaded:
            self.remove_fit_line()
        result = self.fit([self.intensity_ratio_sb.value(), self.rotation_angle_sb.value(), self.offset_sb.value()], self.angles, self.reflectance[:, self.freq_sld.value()])
        self.intensity_ratio_sb.setValue(result[0])
        self.rotation_angle_sb.setValue(result[1])
        self.offset_sb.setValue(result[2])
        self.fit_line, = self.axes_F2.plot(self.angles, self.fitfunc(result, self.angles), color="#000000")
        self.axes_F2.set_title('p0 = %.3f, p1 = %.3f, rotation angle = %f degs' %(result[0],result[1],result[1]*180/np.pi), fontsize=12)
        self.F.draw()

    def split_string_to_data(self, string):
        string = string.replace('\n', '') # delete tail '\n'
        string = string.replace(',', ' ') # replace ',' by ' '
        string = string.replace('\t', ' ') # replace '\t' by ' '
        string = string.replace(';', ' ') # replace ';' by ' '
        while '  ' in string:
            # replace multiple spaces by one space
            string = string.replace('  ', ' ')
        # split with delimiter ' ' and store them in a list
        var_list = string.split(' ')
        while '' in var_list:
            # remove empty strings from the list
            var_list.remove('')
        return var_list

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
        if type(value) != int:
            raise ValueError('Number of decimals must be an int')
        else:
            self.decimals = value

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())
