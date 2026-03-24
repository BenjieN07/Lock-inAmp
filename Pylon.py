# from pypylon import pylon
from QCL_interface import *
import cv2
import numpy as np
from ctypes import *
from PyQt5.QtTest import *
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)
import scipy.misc
import os
from get_project_path import cwd_path

"""
Please be alert that this program cannot run alone, but work as a supplement for worklist.py
You can use the offset function without pylon camera function enabled
To enable the pylon camera function, install pypylon 1.8.0 with pip, comment on the first line, and change 
turn_on_Pylon to True (line 231)
"""

class GraphicsView(QGraphicsView):
    rectChanged = pyqtSignal(QRect)

    def __init__(self, *args, **kwargs):
        QGraphicsView.__init__(self, *args, **kwargs)
        self.rubberBand = QRubberBand(QRubberBand.Rectangle, self)
        self.setMouseTracking(True)
        self.origin = QPoint()
        self.changeRubberBand = False

    def mousePressEvent(self, event):
        self.origin = event.pos()
        self.rubberBand.setGeometry(QRect(self.origin, QSize()))
        self.rectChanged.emit(self.rubberBand.geometry())
        self.rubberBand.show()
        self.changeRubberBand = True
        QGraphicsView.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.changeRubberBand:
            self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())
            self.rectChanged.emit(self.rubberBand.geometry())
        QGraphicsView.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        self.changeRubberBand = False
        QGraphicsView.mouseReleaseEvent(self, event)

class Pylon(QFrame):
    def __init__(self, parent):
        super().__init__()
        self.setGeometry(700, 400, 950, 700)
        self.parent = parent
        # self.show()
        self.initUI()
        self.setWindowTitle("Camera")
        self.x_reference = None
        self.y_reference = None
        self.z_reference = None
        self.x_offset = 0
        self.y_offset = 0
        self.z_offset = 0
        self.left_lim = 0
        self.right_lim = 1294
        self.up_lim = 0
        self.down_lim = 972
        self.img_record = None
        self.continuous_shot = False
        self.connected = False

    def initUI(self):
        # create main grid to organize layout
        main_grid = QGridLayout()
        main_grid.setSpacing(10)
        self.setLayout(main_grid)

        top_hbox = QHBoxLayout()
        self.image_type_indicator = QLabel("")
        self.image_type_indicator.setFixedWidth(200)
        top_hbox.addWidget(self.image_type_indicator)

        self.mode_cb = QComboBox()
        self.mode_cb.addItem("Single Shot")
        self.mode_cb.addItem("Continuous Shot")
        self.mode_cb.setFixedHeight(30)
        self.mode_cb.setFixedWidth(200)
        self.mode_cb.setEnabled(False)
        top_hbox.addWidget(self.mode_cb)

        self.objective = QComboBox()
        self.objective.addItem("No crosshair")
        self.objective.addItem("15 X IR")
        self.objective.addItem("36 X IR")
        self.objective.addItem("Visible")
        # self.objective.currentIndexChanged.connect(self.display_crosshair)
        top_hbox.addWidget(self.objective)

        main_grid.addLayout(top_hbox, 0, 0, 1, 2, Qt.AlignCenter)

        self.view = GraphicsView()
        self.view.rectChanged.connect(self.onRectChanged)
        self.figure = QGraphicsScene()
        self.view.setScene(self.figure)

        # self.figure = QLabel()
        self.view.setFixedWidth(649)
        self.view.setFixedHeight(490)
        main_grid.addWidget(self.view, 1, 0, 10, 2, Qt.AlignCenter)

        btn_vbox = QVBoxLayout()

        reference_lb = QLabel(f"Reference ({chr(956)}m)")
        x_reference_lb = QLabel("x")
        y_reference_lb = QLabel("y")
        z_reference_lb = QLabel("z")
        self.x_reference_sb = QDoubleSpinBox()
        self.x_reference_sb.setDecimals(2)
        self.x_reference_sb.setMinimum(-1e8)
        self.x_reference_sb.setMaximum(1e8)
        self.y_reference_sb = QDoubleSpinBox()
        self.y_reference_sb.setDecimals(2)
        self.y_reference_sb.setMinimum(-1e8)
        self.y_reference_sb.setMaximum(1e8)
        self.z_reference_sb = QDoubleSpinBox()
        self.z_reference_sb.setDecimals(2)
        self.z_reference_sb.setMinimum(-1e8)
        self.z_reference_sb.setMaximum(1e8)

        x_offset_lb = QLabel("x offset")
        y_offset_lb = QLabel("y offset")
        z_offset_lb = QLabel("z offset")
        self.x_offset_sb = QDoubleSpinBox()
        self.x_offset_sb.setDecimals(2)
        self.x_offset_sb.setMinimum(-1e8)
        self.x_offset_sb.setMaximum(1e8)
        # self.x_offset_sb.setEnabled(False)
        self.y_offset_sb = QDoubleSpinBox()
        self.y_offset_sb.setDecimals(2)
        self.y_offset_sb.setMinimum(-1e8)
        self.y_offset_sb.setMaximum(1e8)
        # self.y_offset_sb.setEnabled(False)
        self.z_offset_sb = QDoubleSpinBox()
        self.z_offset_sb.setDecimals(2)
        self.z_offset_sb.setMinimum(-1e8)
        self.z_offset_sb.setMaximum(1e8)
        # self.z_offset_sb.setEnabled(False)

        x_hbox = QHBoxLayout()
        x_hbox.addWidget(x_reference_lb)
        x_hbox.addWidget(self.x_reference_sb)
        x_hbox.addWidget(x_offset_lb)
        x_hbox.addWidget(self.x_offset_sb)
        y_hbox = QHBoxLayout()
        y_hbox.addWidget(y_reference_lb)
        y_hbox.addWidget(self.y_reference_sb)
        y_hbox.addWidget(y_offset_lb)
        y_hbox.addWidget(self.y_offset_sb)
        z_hbox = QHBoxLayout()
        z_hbox.addWidget(z_reference_lb)
        z_hbox.addWidget(self.z_reference_sb)
        z_hbox.addWidget(z_offset_lb)
        z_hbox.addWidget(self.z_offset_sb)

        pos_vbox = QVBoxLayout()
        pos_vbox.addWidget(reference_lb)
        pos_vbox.addLayout(x_hbox)
        pos_vbox.addLayout(y_hbox)
        pos_vbox.addLayout(z_hbox)

        self.move_to_reference_with_offset_btn = QPushButton("Move to reference point with offset")
        self.move_to_reference_with_offset_btn.clicked.connect(self.move_to_reference_with_offset)
        pos_vbox.addWidget(self.move_to_reference_with_offset_btn)

        self.save_btn = QPushButton("Save the current reference and offset input")
        self.save_btn.clicked.connect(self.save)
        pos_vbox.addWidget(self.save_btn)

        connection_hbox = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connection_indicator = QLabel(u'\u274c ')  # cross mark by default because not connected yet
        connection_hbox.addWidget(self.connection_indicator)
        connection_hbox.addWidget(self.connect_btn)

        self.snippet_btn = QPushButton("Camera view")
        self.snippet_btn.setEnabled(False)

        self.save_snippet_btn = QPushButton("Camera view and set \n as reference point")
        self.save_snippet_btn.setEnabled(False)

        self.set_as_offset_btn = QPushButton("Camera view and set \n as offset")
        self.set_as_offset_btn.setEnabled(False)

        self.show_snippet_btn = QPushButton("Show the camera view \n of reference point")
        self.show_snippet_btn.setEnabled(False)

        self.save_snippet_as_png_btn = QPushButton("Save reference point as .png")
        self.save_snippet_as_png_btn.setEnabled(False)

        self.load_snippet_as_reference_btn = QPushButton("Load .png as reference point")
        self.load_snippet_as_reference_btn.setEnabled(False)

        self.select_aperture_cropping_btn = QPushButton("Select the region for tracking")
        self.select_aperture_cropping_btn.setEnabled(False)

        self.aperture_lim_lb = QLabel("Aperture: ({}, {}) x ({}, {})".format(0, 0, 1294, 972))

        self.auto_focus_btn = QPushButton("Auto focus")
        self.auto_focus_btn.setEnabled(False)

        self.auto_xyz_btn = QPushButton("Auto xyz")
        self.auto_xyz_btn.setEnabled(False)

        self.state_lb = QLabel("")

        btn_vbox.addLayout(pos_vbox)
        btn_vbox.addLayout(connection_hbox)
        btn_vbox.addWidget(self.snippet_btn)
        btn_vbox.addWidget(self.save_snippet_btn)
        btn_vbox.addWidget(self.set_as_offset_btn)
        btn_vbox.addWidget(self.show_snippet_btn)
        btn_vbox.addWidget(self.save_snippet_as_png_btn)
        btn_vbox.addWidget(self.load_snippet_as_reference_btn)
        btn_vbox.addWidget(self.select_aperture_cropping_btn)
        btn_vbox.addWidget(self.aperture_lim_lb)
        btn_vbox.addWidget(self.auto_focus_btn)
        btn_vbox.addWidget(self.auto_xyz_btn)
        btn_vbox.addWidget(self.state_lb)
        main_grid.addLayout(btn_vbox, 0, 3, 11, 1, Qt.AlignCenter)

        turn_on_Pylon = False
        if turn_on_Pylon:
            self.mode_cb.currentIndexChanged.connect(self.switch_mode)
            self.connect_btn.clicked.connect(self.connect_disconnect)
            self.snippet_btn.clicked.connect(self.take_snippet)
            self.save_snippet_btn.clicked.connect(self.save_snippet)
            self.set_as_offset_btn.clicked.connect(self.save_snippet_as_offset)
            self.show_snippet_btn.clicked.connect(self.show_snippet)
            self.save_snippet_as_png_btn.clicked.connect(self.save_snippet_as_png)
            self.load_snippet_as_reference_btn.clicked.connect(self.load_snippet_as_reference)
            self.select_aperture_cropping_btn.clicked.connect(self.select_aperture_cropping)
            self.auto_focus_btn.clicked.connect(self.auto_focus)
            self.auto_xyz_btn.clicked.connect(self.auto_xyz)

    def connect_disconnect(self):
        if self.connect_btn.text() == "Connect":
            try:
                self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
                self.camera.Open()
                self.connection_indicator.setText(u'\u2705 ')
                self.connect_btn.setText("Disconnect")
                self.connected = True
                self.mode_cb.setEnabled(True)
                self.select_aperture_cropping_btn.setEnabled(True)
                self.snippet_btn.setEnabled(True)
                self.save_snippet_btn.setEnabled(True)
                self.set_as_offset_btn.setEnabled(True)
                self.save_snippet_as_png_btn.setEnabled(True)
                self.load_snippet_as_reference_btn.setEnabled(True)
                self.show_snippet_btn.setEnabled(True)
                self.auto_focus_btn.setEnabled(True)
                self.auto_xyz_btn.setEnabled(True)
            except:
                QMessageBox.warning(self, "Connection", "Connection failed! Please turn off the Video Wizard in OPUS!")
                return
        else:
            try:
                self.camera.Close()
                self.connection_indicator.setText(u'\u274c ')
                self.connect_btn.setText("Connect")
                self.connected = False
                self.mode_cb.setEnabled(False)
                self.snippet_btn.setEnabled(False)
                self.save_snippet_btn.setEnabled(False)
                self.set_as_offset_btn.setEnabled(False)
                self.auto_focus_btn.setEnabled(False)
                self.auto_xyz_btn.setEnabled(False)
            except:
                QMessageBox.warning(self, "Disconnection", "Disconnection failed!")
                return

    def display_crosshair(self):
        if self.objective.currentText() == "15 X IR":
            crosshair = QPixmap(r"{}\yellow_crosshair.png".format(cwd_path)).scaled(360, 360)
            item = self.figure.addPixmap(crosshair)
            item.setPos(140, 65)
            scalebar50 = QPixmap(r"{]\scalebar50.png".format(cwd_path)).scaled(360, 360).copy(0, 100, 360, 110)
            item = self.figure.addPixmap(scalebar50)
            item.setPos(40, 370)
        elif self.objective.currentText() == "36 X IR":
            crosshair = QPixmap(r"{]\yellow_crosshair.png".format(cwd_path)).scaled(360, 360)
            item = self.figure.addPixmap(crosshair)
            item.setPos(140, 65)
            scalebar10 = QPixmap(r"{]\scalebar10.png".format(cwd_path)).scaled(360, 360).copy(0, 100, 360, 110)
            item = self.figure.addPixmap(scalebar10)
            item.setPos(40, 370)
        elif self.objective.currentText() == "Visible":
            crosshair = QPixmap(r"{}\yellow_crosshair.png".format(cwd_path)).scaled(360, 360)
            item = self.figure.addPixmap(crosshair)
            item.setPos(140, 65)
            scalebar100 = QPixmap(r"{]\scalebar100.png".format(cwd_path)).scaled(360, 360).copy(0, 100, 360, 110)
            item = self.figure.addPixmap(scalebar100)
            item.setPos(40, 370)

    def switch_mode(self):
        if self.mode_cb.currentText() == "Continuous Shot":
            self.continuous_thread = ContinuousShotThread(self)
            self.continuous_thread.start()
        else:
            self.continuous_thread.terminate()

    def onRectChanged(self, r):
        topLeft = r.topLeft()
        bottomRight = r.bottomRight()
        if self.select_aperture_cropping_btn.text() == "Done":
            if topLeft.x()*2 >= 0 and topLeft.y()*2 >= 0 and bottomRight.x()*2 <= 1294 and bottomRight.y()*2 <= 972:
                self.aperture_lim_lb.setText("Aperture: ({}, {}) x ({}, {})".format(topLeft.x()*2, topLeft.y()*2, bottomRight.x()*2, bottomRight.y()*2))
                self.left_lim = topLeft.x()*2
                self.right_lim = bottomRight.x()*2
                self.up_lim = topLeft.y()*2
                self.down_lim = bottomRight.y()*2

    def import_reference_pos(self):
        path = QFileDialog.getOpenFileName(self, "Select a file", r"C:\Users\Public\Documents\Bruker\OPUS_8.5.29\instruments\VERTEX_80v\Positions", "TXT Files (*.txt)")[0]
        if path == "":
            return
        file = open(path, 'r')
        for line_index, line_str in enumerate(file):
            if line_index == 0:
                self.x_reference = float(self.split_string_to_data(line_str))
                self.x_reference_sb.setValue(self.x_reference)
            elif line_index == 1:
                self.y_reference = float(self.split_string_to_data(line_str))
                self.y_reference_sb.setValue(self.y_reference)
            else:
                self.z_reference = float(self.split_string_to_data(line_str))
                self.z_reference_sb.setValue(self.z_reference)
        file.close()
        self.x_offset = 0
        self.y_offset = 0
        self.z_offset = 0
        self.x_offset_sb.setValue(self.x_offset)
        self.y_offset_sb.setValue(self.y_offset)
        self.z_offset_sb.setValue(self.z_offset)

    def import_offset(self):
        path = QFileDialog.getOpenFileName(self, "Select a file", r"C:\Users\Public\Documents\Bruker\OPUS_8.5.29\instruments\VERTEX_80v\Positions", "TXT Files (*.txt)")[0]
        if path == "":
            return
        file = open(path, 'r')
        for line_index, line_str in enumerate(file):
            if line_index == 0:
                self.x_offset = float(self.split_string_to_data(line_str))
                self.x_offset_sb.setValue(self.x_offset)
            elif line_index == 1:
                self.y_offset = float(self.split_string_to_data(line_str))
                self.y_offset_sb.setValue(self.y_offset)
            else:
                self.z_offset = float(self.split_string_to_data(line_str))
                self.z_offset_sb.setValue(self.z_offset)
        file.close()

    def save_reference_pos(self):
        path = QFileDialog.getSaveFileName(self, "Select a file", r"C:\Users\Public\Documents\Bruker\OPUS_8.5.29\instruments\VERTEX_80v\Positions", "TXT Files (*.txt)")[0]
        if path == "":
            return
        file = open(path, 'w')
        file.write(f"{self.x_reference_sb.value()}\n")
        file.write(f"{self.y_reference_sb.value()}\n")
        file.write(f"{self.z_reference_sb.value()}")
        file.close()
        QMessageBox.information(self, "Save", "Reference position is saved to .txt successfully!")

    def save_offset(self):
        path = QFileDialog.getSaveFileName(self, "Select a file", r"C:\Users\Public\Documents\Bruker\OPUS_8.5.29\instruments\VERTEX_80v\Positions", "TXT Files (*.txt)")[0]
        if path == "":
            return
        file = open(path, 'w')
        file.write(f"{self.x_offset_sb.value()}\n")
        file.write(f"{self.y_offset_sb.value()}\n")
        file.write(f"{self.z_offset_sb.value()}")
        file.close()
        QMessageBox.information(self, "Save", "Offset is saved to .txt successfully!")

    def move_to_reference(self):
        if self.x_reference is None or self.y_reference is None or self.z_reference is None:
            QMessageBox.warning(self, "Reference error", "The reference position is not saved yet!")
            return
        elif not self.parent.connected:
            QMessageBox.warning(self, "Tango", "Tango is not connected!")
            return
        elif not (self.parent.x-2000 < self.x_referenc < self.parent.x+2000 and self.parent.y-2000 < self.y_reference < self.parent.y+2000 and self.parent.z-2000 < self.z_reference < self.parent.z+2000):
            buttonReply = QMessageBox.question(self, 'Reintialize', "Are you sure to reinitialize everything?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if buttonReply == QMessageBox.No:
                return
        self.parent.Tango.LSX_MoveAbs(self.parent.LSID, c_double(self.x_reference), c_double(self.y_reference), c_double(self.z_reference), c_double(0), c_bool(True))

    def move_to_reference_with_offset(self):
        if self.x_reference is None or self.y_reference is None or self.z_reference is None:
            QMessageBox.warning(self, "Reference error", "The reference position is not saved yet!")
            return
        elif not self.parent.connected:
            QMessageBox.warning(self, "Tango", "Tango is not connected!")
            return
        elif not (self.parent.x-2000 < self.x_reference+self.x_offset < self.parent.x+2000 and self.parent.y-2000 < self.y_reference+self.y_offset < self.parent.y+2000 and self.parent.z-2000 < self.z_reference+self.z_offset < self.parent.z+2000):
            buttonReply = QMessageBox.question(self, 'Reintialize', "Are you sure to reinitialize everything?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if buttonReply == QMessageBox.No:
                return
        self.parent.Tango.LSX_MoveAbs(self.parent.LSID, c_double(self.x_reference+self.x_offset), c_double(self.y_reference+self.y_offset), c_double(self.z_reference+self.z_offset), c_double(0), c_bool(True))

    def save(self):
        self.x_reference = self.x_reference_sb.value()
        self.y_reference = self.y_reference_sb.value()
        self.z_reference = self.z_reference_sb.value()
        self.x_offset = self.x_offset_sb.value()
        self.y_offset = self.y_offset_sb.value()
        self.z_offset = self.z_offset_sb.value()
        QMessageBox.information(self, "Save", "Directories are saved successfully!")

    def select_aperture_cropping(self):
        if self.select_aperture_cropping_btn.text() == "Select the region for tracking":
            self.select_aperture_cropping_btn.setText("Done")
            self.view.rubberBand.setGeometry(QRect(int(self.left_lim/2), int(self.up_lim/2), int((self.right_lim-self.left_lim)/2), int((self.down_lim-self.up_lim)/2)))
            self.view.rubberBand.show()
        else:
            self.select_aperture_cropping_btn.setText("Select the region for tracking")

    def take_img(self):
        img = pylon.PylonImage()
        converter = pylon.ImageFormatConverter()

        # converting to opencv bgr format
        converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
        self.camera.StartGrabbing()

        grabResult = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

        if grabResult.GrabSucceeded():
            # Access the image data
            image = converter.Convert(grabResult)
            img = image.GetArray()
        grabResult.Release()

        self.camera.StopGrabbing()

        return img

    def take_snippet(self):
        img = self.take_img()
        height, width, channel = img.shape
        bytesPerLine = 3 * width
        qImg = QImage(img.data, width, height, bytesPerLine, QImage.Format_RGB888).rgbSwapped()
        self.figure.clear()
        self.figure.addPixmap(QPixmap.fromImage(qImg).scaled(647, 486))
        self.image_type_indicator.setText("Camera view")
        self.display_crosshair()

    def save_snippet(self):
        if not self.parent.connected:
            QMessageBox.warning(self, "Tango", "Tango is not connected!")
            return
        self.x_reference = self.parent.x
        self.y_reference = self.parent.y
        self.z_reference = self.parent.z
        self.x_offset = 0
        self.y_offset = 0
        self.z_offset = 0
        self.x_offset_sb.setValue(self.x_offset)
        self.y_offset_sb.setValue(self.y_offset)
        self.z_offset_sb.setValue(self.z_offset)
        self.x_reference_sb.setValue(self.x_reference)
        self.y_reference_sb.setValue(self.y_reference)
        self.z_reference_sb.setValue(self.z_reference)
        self.img_record = self.take_img()
        height, width, channel = self.img_record.shape
        bytesPerLine = 3 * width
        qImg = QImage(self.img_record.data, width, height, bytesPerLine, QImage.Format_RGB888).rgbSwapped()
        self.figure.addPixmap(QPixmap.fromImage(qImg).scaled(647, 486))
        self.image_type_indicator.setText("Reference point")
        self.display_crosshair()

    def save_snippet_as_offset(self):
        if not self.parent.connected:
            QMessageBox.warning(self, "Tango", "Tango is not connected!")
            return
        self.x_offset = self.parent.x - self.x_reference
        self.y_offset = self.parent.y - self.y_reference
        self.z_offset = self.parent.z - self.z_reference
        self.x_offset_sb.setValue(self.x_offset)
        self.y_offset_sb.setValue(self.y_offset)
        self.z_offset_sb.setValue(self.z_offset)

        self.take_snippet()

    def save_snippet_as_png(self):
        if self.img_record is not None:
            path = QFileDialog.getSaveFileName(self, "Select a file", "C:/Users/Public/Documents/Bruker/OPUS_8.5.29/instruments/VERTEX_80v/Images/x={}, y={}, z={}, x_offset={}, y_offset={}, z_offset={}".format(self.x_reference, self.y_reference, self.z_reference, self.x_offset, self.y_offset, self.z_offset), "PNG Files (*.png)")[0]
            if path != "":
                cv2.imwrite(path, self.img_record)
        else:
            QMessageBox.warning(self, "Show snippet error", "No reference point snippet found!")

    def load_snippet_as_reference(self):
        path = QFileDialog.getOpenFileName(self, "Select a file", r"C:\Users\Public\Documents\Bruker\OPUS_8.5.29\instruments\VERTEX_80v\Images", "PNG Files (*.png)")[0]
        if path != "":
            self.img_record = cv2.imread(path)
            val_list = self.split_string_to_data(path)
            for val in val_list:
                if val[0:2] == "x=":
                    self.x_reference_sb.setValue(float(val[2:]))
                elif val[0:2] == "y=":
                    self.y_reference_sb.setValue(float(val[2:]))
                elif val[0:2] == "z=":
                    self.z_reference_sb.setValue(float(val[2:]))
                elif val[0:9] == "x_offset=":
                    self.x_offset_sb.setValue(float(val[9:]))
                elif val[0:9] == "y_offset=":
                    self.y_offset_sb.setValue(float(val[9:]))
                elif val[0:9] == "z_offset=":
                    self.z_offset_sb.setValue(float(val[9:]))
            self.save()
            self.show_snippet()

    def show_snippet(self):
        if self.img_record is not None:
            height, width, channel = self.img_record.shape
            bytesPerLine = 3 * width
            qImg = QImage(self.img_record.data, width, height, bytesPerLine, QImage.Format_RGB888).rgbSwapped()
            self.figure.addPixmap(QPixmap.fromImage(qImg).scaled(647, 486))
            self.image_type_indicator.setText("Reference point")
            self.display_crosshair()
        else:
            QMessageBox.warning(self, "Show snippet error", "No snippet found!")

    def auto_focus(self):
        if not self.parent.connected:
            QMessageBox.warning(self, "Tango", "Tango is not connected!")
            return
        self.state_lb.setText("Auto focus started")
        QTest.qWait(100)
        range = 50
        step = 2
        z0 = self.parent.z
        z_test = np.arange(z0-range, z0+range+step, step)
        blur_estimation = []
        try:
            for z in z_test:
                self.parent.Tango.LSX_MoveAbs(self.parent.LSID, c_double(self.parent.x), c_double(self.parent.y), c_double(z), c_double(0), c_bool(True))
                img = self.take_img()[self.up_lim:self.down_lim, self.left_lim:self.right_lim, :]
                blur_estimation.append(cv2.Laplacian(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()*1000)
                # cv2.imwrite("blur_estimation/{}_blur_estimation={}.png".format(z_test.tolist().index(z), round(blur_estimation[-1], 2)), img)
            max_index = blur_estimation.index(max(blur_estimation))
            self.parent.Tango.LSX_MoveAbs(self.parent.LSID, c_double(self.parent.x), c_double(self.parent.y), c_double(z_test[max_index]), c_double(0), c_bool(True))
            self.take_snippet()
            # if max_index <= (len(z_test) - 1)*0.1 or max_index >= (len(z_test) - 1)*0.9:
            #     self.auto_focus()
            self.z_offset = self.parent.get_z_pos() - self.z_reference
            self.z_offset_sb.setValue(self.z_offset)

            self.state_lb.setText("Auto focus finished")
        except:
            self.parent.Tango.LSX_MoveAbs(self.parent.LSID, c_double(self.parent.x), c_double(self.parent.y), c_double(z0), c_double(0), c_bool(True))
            QMessageBox.warning(self, "Auto focus", "Auto focus fails! The stage has returned to the original position.")

    def auto_xyz(self):
        if self.img_record is not None:

            self.auto_focus()

            self.state_lb.setText("Auto xyz tracking started")
            QTest.qWait(100)

            img = self.take_img()

            cv2_img1 = cv2.cvtColor(self.img_record[self.up_lim:self.down_lim, self.left_lim:self.right_lim, :], cv2.COLOR_BGR2GRAY)
            cv2_img2 = cv2.cvtColor(img[self.up_lim:self.down_lim, self.left_lim:self.right_lim, :], cv2.COLOR_BGR2GRAY)

            # auto-correlation method to optimize the xy position
            image1FFT = np.fft.fft2(cv2_img1)
            image2FFT = np.conjugate(np.fft.fft2(cv2_img2))
            imageCCor = np.real(np.fft.ifft2(image1FFT*image2FFT))
            imageCCorShift = np.fft.fftshift(imageCCor)
            row, col = cv2_img1.shape
            yShift, xShift = np.unravel_index(np.argmax(imageCCorShift), (row, col))
            yShift -= int(row/2)
            xShift -= int(col/2)

            # pixel to micron
            xShift /= 4.67
            yShift /= 4.67

            self.parent.Tango.LSX_MoveRel(self.parent.LSID, c_double(-xShift), c_double(-yShift), c_double(0), c_double(0), c_bool(True))

            self.take_snippet()

            self.x_offset = self.parent.get_x_pos() - self.x_reference
            self.y_offset = self.parent.get_y_pos() - self.y_reference

            self.x_offset_sb.setValue(self.x_offset)
            self.y_offset_sb.setValue(self.y_offset)

            self.state_lb.setText("Auto xyz tracking finished")

        else:
            QMessageBox.warning(self, "Auto xyz error", "No reference found!")

    def split_string_to_data(self, str):
        str = str.replace("\t", "")
        str = str.replace("\n", "")
        str = str.replace("<fX>", "")
        str = str.replace("<fY>", "")
        str = str.replace("<fZ>", "")
        str = str.replace(r"</fX>", "")
        str = str.replace(r"</fY>", "")
        str = str.replace(r"</fZ>", "")
        return str

class ContinuousShotThread(QThread):
    def __init__(self, pylon, parent=None):
        super(ContinuousShotThread, self).__init__(parent)
        self.pylon = pylon
        self.count = 0

    def run(self):
        self.snippetTimer = QTimer()
        self.snippetTimer.timeout.connect(self.pylon.take_snippet)
        self.snippetTimer.start(500)
        loop = QEventLoop()
        loop.exec_()

    def streaming(self):
        img = pylon.PylonImage()
        converter = pylon.ImageFormatConverter()

        # converting to opencv bgr format
        converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
        # if self.count % 100 == 0:
        self.pylon.camera.StartGrabbing()

        grabResult = self.pylon.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

        if grabResult.GrabSucceeded():
            # Access the image data
            image = converter.Convert(grabResult)
            img = image.GetArray()
        grabResult.Release()

        #if self.count % 100 == 99:
        self.pylon.camera.StopGrabbing()

        height, width, channel = img.shape
        bytesPerLine = 3 * width
        qImg = QImage(img.data, width, height, bytesPerLine, QImage.Format_RGB888).rgbSwapped()
        self.pylon.figure.addPixmap(QPixmap.fromImage(qImg).scaled(647, 486))

        self.count += 1

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # tran_widget = Translator()
    window = Pylon()
    sys.exit(app.exec_())
