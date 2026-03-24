from PEM_interface import *
import sys
import win32com.client
from get_project_path import cwd_path

class BrukerControlPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setGeometry(700, 400, 550, 150)
        self.show()
        self.initUI()
        self.setWindowTitle("Bruker Control")
        self.directCommand = None  # No directCommand when the PC is not connected to Bruker
        #self.directCommand = win32com.client.Dispatch("{}/OpusCMD334.DirectCommand".format(cwd_path))  # replace the line above if the PC is connected to Bruker
        # self.initialize_state()

    def initUI(self):
        # create main grid to organize layout
        main_grid = QGridLayout()
        main_grid.setSpacing(10)
        self.setLayout(main_grid)

        self.temp_sensor_cb = QComboBox()
        self.temp_sensor_cb.addItem("MercuryITC")
        self.temp_sensor_cb.addItem("Lakeshore")
        self.temp_sensor_cb.addItem("None")
        self.temp_sensor_cb.setFixedWidth(150)
        self.temp_sensor_cb.setFixedHeight(40)
        main_grid.addWidget(self.temp_sensor_cb, 0, 0, 2, 2, Qt.AlignBottom)

        print("{}/BrukerIcon/illumination.png".format(cwd_path))

        self.illumination_label = QLabel()
        self.pixmap = QPixmap("{}\BrukerIcon\illumination.png".format(cwd_path)).scaled(350, 60)
        self.illumination_label.setPixmap(self.pixmap)
        main_grid.addWidget(self.illumination_label, 0, 2, 1, 3, Qt.AlignCenter)

        self.illumination_slider = QSlider(Qt.Horizontal)
        self.illumination_slider.setRange(100, 200)
        self.illumination_slider.setSingleStep(1)
        self.illumination_slider.setTickInterval(10)
        self.illumination_slider.setFixedWidth(250)
        self.illumination_slider.sliderReleased.connect(self.set_illumination)
        main_grid.addWidget(self.illumination_slider, 1, 2, 1, 2, Qt.AlignRight)

        self.illumination_sb = QSpinBox()
        self.illumination_sb.setRange(0, 100)
        self.illumination_sb.editingFinished.connect(self.set_illumination2)
        main_grid.addWidget(self.illumination_sb, 1, 4, 1, 1, Qt.AlignCenter)

        refl_hbox = QHBoxLayout()
        self.refl_btn = QPushButton()
        self.refl_btn.setIcon(QIcon('{}/BrukerIcon/refl.png'.format(cwd_path)))
        self.refl_btn.setIconSize(QSize(50, 30))
        self.refl_btn.setFixedWidth(50)
        self.refl_btn.setFixedHeight(30)
        self.refl_btn.clicked.connect(self.set_refl)
        refl_hbox.addWidget(self.refl_btn)

        self.refl_Led = QLedIndicator('green')
        refl_hbox.addWidget(self.refl_Led)
        main_grid.addLayout(refl_hbox, 0, 5, 1, 1, Qt.AlignCenter)

        trans_hbox = QHBoxLayout()
        self.trans_btn = QPushButton()
        self.trans_btn.setIcon(QIcon('{}/BrukerIcon/trans.png'.format(cwd_path)))
        self.trans_btn.setIconSize(QSize(50, 30))
        self.trans_btn.setFixedWidth(50)
        self.trans_btn.setFixedHeight(30)
        self.trans_btn.clicked.connect(self.set_trans)
        trans_hbox.addWidget(self.trans_btn)

        self.trans_Led = QLedIndicator('green')
        trans_hbox.addWidget(self.trans_Led)
        main_grid.addLayout(trans_hbox, 0, 6, 1, 1, Qt.AlignCenter)

        IR_hbox = QHBoxLayout()
        self.IR_btn = QPushButton()
        self.IR_btn.setIcon(QIcon('{}/BrukerIcon/IR.png'.format(cwd_path)))
        self.IR_btn.setIconSize(QSize(50, 30))
        self.IR_btn.setFixedWidth(50)
        self.IR_btn.setFixedHeight(30)
        self.IR_btn.clicked.connect(self.set_IR)
        IR_hbox.addWidget(self.IR_btn)

        self.IR_Led = QLedIndicator('green')
        IR_hbox.addWidget(self.IR_Led)
        main_grid.addLayout(IR_hbox, 2, 2, 1, 1, Qt.AlignCenter)

        Visible_hbox = QHBoxLayout()
        self.Visible_btn = QPushButton()
        self.Visible_btn.setIcon(QIcon('{}/BrukerIcon/Visable.png'.format(cwd_path)))
        self.Visible_btn.setIconSize(QSize(50, 30))
        self.Visible_btn.setFixedWidth(50)
        self.Visible_btn.setFixedHeight(30)
        self.Visible_btn.clicked.connect(self.set_Visable)
        Visible_hbox.addWidget(self.Visible_btn)

        self.Visible_Led = QLedIndicator('green')
        Visible_hbox.addWidget(self.Visible_Led)
        main_grid.addLayout(Visible_hbox, 2, 3, 1, 1, Qt.AlignCenter)

        IR_Visible_hbox = QHBoxLayout()
        self.IR_Visible_btn = QPushButton()
        self.IR_Visible_btn.setIcon(QIcon('{}/BrukerIcon/IR_Visable.png'.format(cwd_path)))
        self.IR_Visible_btn.setIconSize(QSize(50, 30))
        self.IR_Visible_btn.setFixedWidth(70)
        self.IR_Visible_btn.setFixedHeight(30)
        self.IR_Visible_btn.clicked.connect(self.set_IR_Visable)
        IR_Visible_hbox.addWidget(self.IR_Visible_btn)

        self.IR_Visible_Led = QLedIndicator("green")
        IR_Visible_hbox.addWidget(self.IR_Visible_Led)
        main_grid.addLayout(IR_Visible_hbox, 2, 4, 1, 1, Qt.AlignCenter)

        name_lb = QLabel("Hyperion Status")
        main_grid.addWidget(name_lb, 1, 5, 2, 2, Qt.AlignCenter)

    """
    def initialize_state(self):
        self.directCommand.SendDirect("MOT56 =105", False)
        self.directCommand.SendDirect("MOT56 =4", False)
        self.directCommand.SendDirect("MOT56 =1", False)
        self.illumination_slider.setValue(105)
        self.illumination_sb.setValue(5)
        self.refl_Led.setChecked(True)
        self.IR_Led.setChecked(True)
    """

    def set_illumination(self):
        self.directCommand.SendDirect("MOT56 ={}".format(self.illumination_slider.value()), True)
        self.illumination_sb.setValue(self.illumination_slider.value()-100)

    def set_illumination2(self):
        self.directCommand.SendDirect("MOT56 ={}".format(self.illumination_sb.value()+100), True)
        self.illumination_slider.setValue(self.illumination_sb.value()+100)

    def set_refl(self):
        self.directCommand.SendDirect("MOT56 =4", True)
        self.refl_Led.setChecked(True)
        self.trans_Led.setChecked(False)

    def set_trans(self):
        self.directCommand.SendDirect("MOT56 =5", True)
        self.refl_Led.setChecked(False)
        self.trans_Led.setChecked(True)

    def set_IR(self):
        self.directCommand.SendDirect("MOT56 =1", True)
        self.IR_Led.setChecked(True)
        self.Visible_Led.setChecked(False)
        self.IR_Visible_Led.setChecked(False)

    def set_Visable(self):
        self.directCommand.SendDirect("MOT56 =2", True)
        self.IR_Led.setChecked(False)
        self.Visible_Led.setChecked(True)
        self.IR_Visible_Led.setChecked(False)

    def set_IR_Visable(self):
        self.directCommand.SendDirect("MOT56 =3", True)
        self.IR_Led.setChecked(False)
        self.Visible_Led.setChecked(False)
        self.IR_Visible_Led.setChecked(True)


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

class PicButton(QAbstractButton):
    def __init__(self, pixmap, parent=None):
        super(PicButton, self).__init__(parent)
        self.pixmap = pixmap

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(event.rect(), self.pixmap)

    def sizeHint(self):
        return self.pixmap.size()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = BrukerControlPanel()
    sys.exit(app.exec_())
