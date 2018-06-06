import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QLineEdit, QComboBox, QGridLayout, QHBoxLayout, \
    QVBoxLayout, QSizePolicy, QFileDialog, QListView
from PyQt5.QtGui import QIcon, QPixmap, QImage, QStandardItemModel, QStandardItem
from PyQt5.QtCore import pyqtSlot,QTimer, pyqtSignal,QEvent,Qt, QVariant
import cv2
import drill_lib
import numpy as np
from time import time, sleep
import settingsfile_lib
import copy
import imageprocessinglib


def set_res(cap, x,y):
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(x))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(y))
    return str(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),str(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))


def grab_frame(cap):
    ret,frame = cap.read()
    return cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)


def clickable(widget):
    class Filter(QWidget):

        clicked = pyqtSignal(int,int)

        def eventFilter(self, obj, event):

            if obj == widget:
                if event.type() == QEvent.MouseButtonRelease:
                    if obj.rect().contains(event.pos()):
                        pos=event.pos()
                        self.clicked.emit(pos.x(), pos.y())
                        return True

            return False

    filter = Filter(widget)
    widget.installEventFilter(filter)
    return filter.clicked

def displayImage(img,label):
    height, width, channel = img.shape
    bytesPerLine = 3 * width
    qimg = QImage(img.data, width, height, bytesPerLine, QImage.Format_RGB888)
    qpm = QPixmap.fromImage(qimg)
    label.setPixmap(qpm)


class App(QWidget):
 
    def __init__(self):
        super().__init__()
        self.cap = cv2.VideoCapture(2)
        set_res(self.cap, 640, 480)
        self.cnc=drill_lib.cnc()
        [self.cnc.cameraOffset, self.cnc.zCamera, self.cnc.zContact, self.cnc.zDrillDepth, self.cnc.zSeparation, self.cnc.zFastMargin, self.cnc.DrillFeedRate]=settingsfile_lib.File2Settings('test.cfg')
        self.initUI()
 
    def initUI(self):
        # Define some GUI dimensions
        # Application window
        self.title = ''
        self.left = 10
        self.top = 10
        self.width = 640+160
        self.height = 960+30
        # Camera view
        self.WCAM_WIDTH = 640
        self.WCAM_HEIGHT = 480
        self.WCAM_XPOS = 10
        self.WCAM_YPOS = 10

        # Position display
        self.POS_X = 10 + self.WCAM_WIDTH + self.WCAM_XPOS
        self.POS_Y = self.WCAM_YPOS
        self.POS_HEIGHT = 30

        # Button array
        self.B_X = 10 + self.WCAM_WIDTH + self.WCAM_XPOS
        self.B_Y = 0 + self.WCAM_YPOS + self.POS_HEIGHT +10
        self.B_WIDTH = 30
        self.B_HEIGHT = 30
        self.B_SX = 10
        self.B_SY = 10

        # Window properties
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        # Create image label
        self.webcam_image_label = QLabel(self)
        img = grab_frame(self.cap)
        displayImage(img, self.webcam_image_label)
        clickable(self.webcam_image_label).connect(self.on_webcam_image_label)

        # Create Excellon file label
        self.excellon_image_label = QLabel(self)
        self.excellon_image = np.zeros((480,640,3), np.uint8)
        displayImage(self.excellon_image, self.excellon_image_label)
        clickable(self.excellon_image_label).connect(self.on_excellon_image_label)

        # Create position display
        self.posdisp_label = QLabel()
        self.posdisp_label.setAlignment(Qt.AlignCenter)

        # Jog Controls
        left_button = QPushButton(u'\u2190')
        left_button.clicked.connect(self.on_left_button)

        right_button = QPushButton(u'\u2192')
        right_button.clicked.connect(self.on_right_button)

        up_button = QPushButton(u'\u2191')
        up_button.clicked.connect(self.on_up_button)

        down_button = QPushButton(u'\u2193')
        down_button.clicked.connect(self.on_down_button)

        zup_button = QPushButton(u'Z\u2191')
        zup_button.clicked.connect(self.on_zup_button)

        self.speed_combobox = QComboBox()
        self.speed_combobox.addItems(['0.01','0.1','1','10'])

        zdown_button = QPushButton(u'Z\u2193')
        zdown_button.clicked.connect(self.on_zdown_button)

        motor_off_button = QPushButton(u"\U0000233D")
        motor_off_button.clicked.connect(self.on_motor_off_button)

        # Z position storage/recall/home buttons
        store_zcam_button = QPushButton(u"\U0001F4F7\nM_Z")
        store_zcam_button.setStyleSheet('QPushButton {font-size: 8px; color: red;}')
        store_zcam_button.clicked.connect(self.on_store_zcam_button)

        move_zcam_button = QPushButton(u"\U0001F4F7")
        move_zcam_button.clicked.connect(self.on_move_zcam_button)

        store_zcontact_button = QPushButton(u"M\U0000261F")
        store_zcontact_button.clicked.connect(self.on_store_zcontact_button)

        zhome_button = QPushButton(u"Z\U0001F3E0")
        zhome_button.clicked.connect(self.on_zhome_button)

        # Spindle control
        spindle_on_button = QPushButton(u"\U000021BB")
        spindle_on_button.clicked.connect(self.on_spindle_on_button)

        spindle_off_button = QPushButton(u"\U00002715")
        spindle_off_button.clicked.connect(self.on_spindle_off_button)

        camera_offset_reference_button = QPushButton(u"\U0001F4F7\nM_XY")
        camera_offset_reference_button.setStyleSheet('QPushButton {font-size: 8px; color: red;}')
        camera_offset_reference_button.clicked.connect(self.on_camera_offset_reference_button)

        camera_offset_button = QPushButton(u"C")
        camera_offset_button.clicked.connect(self.on_camera_offset_button)

        camdrill_button = QPushButton(u'\U000021DF')
        camdrill_button.clicked.connect(self.on_camdrill_button)

        # Transform buttons
        self.store_P1_button = QPushButton(u"P1")
        self.store_P1_button.setEnabled(False)
        self.store_P1_button.clicked.connect(self.on_store_P1_button)
        self.store_P2_button = QPushButton(u"P2")
        self.store_P2_button.setEnabled(False)
        self.store_P2_button.clicked.connect(self.on_store_P2_button)
        self.store_P3_button = QPushButton(u"P3")
        self.store_P3_button.setEnabled(False)
        self.store_P3_button.clicked.connect(self.on_store_P3_button)
        self.transform_button = QPushButton(u"T")
        self.transform_button.setEnabled(True)
        self.transform_button.clicked.connect(self.on_transform_button)

        self.clear_transform_button = QPushButton(u"xT")
        self.clear_transform_button.setEnabled(True)
        self.clear_transform_button.clicked.connect(self.on_clear_transform_button)

        # Settings textboxes
        self.cam2xy_textbox = QLineEdit()
        self.cam2xy_textbox.move(self.B_X, self.B_Y + 6 * self.B_HEIGHT + 4*self.B_SY)
        self.cam2xy_textbox.resize(2*self.B_WIDTH, 20)
        self.cam2xy_textbox.setText("19.2")
        self.cam2xy_textbox.setDisabled(True)

        self.drilldepth_textbox = QLineEdit()
        self.drilldepth_textbox.move(self.B_X, self.B_Y + 6 * self.B_HEIGHT + 4 * self.B_SY + 30)
        self.drilldepth_textbox.resize(2 * self.B_WIDTH, 20)
        self.drilldepth_textbox.setText(str(self.cnc.zDrillDepth))
        self.drilldepth_textbox.textChanged.connect(self.on_drilldepth_textbox)

        # Excellon file controls
        file_dialog_button = QPushButton(u"Load ...")
        file_dialog_button.clicked.connect(self.on_file_dialog_button)
        self.file_label = QLabel('none')

        # PCB image file controls
        pcb_image_button = QPushButton(u"Load ...")
        pcb_image_button.clicked.connect(self.on_pcb_image_button)
        self.pcb_image_label = QLabel('none')

        # Drill type list
        self.model = QStandardItemModel()
        self.view = QListView()
        self.view.setModel(self.model)

        # Auto drill button
        auto_drill_button = QPushButton(u"Auto Drill")
        auto_drill_button.clicked.connect(self.on_auto_drill_button)

        # Level2 Grid for xy controls
        grid1 = QGridLayout()
        grid1.addWidget(up_button, 0, 1)
        grid1.addWidget(down_button, 2, 1)
        grid1.addWidget(left_button, 1, 0)
        grid1.addWidget(right_button, 1, 2)
        grid1.addWidget(motor_off_button, 1, 1)
        grid1.addWidget(zup_button,0,3)
        grid1.addWidget(self.speed_combobox,1,3)
        grid1.addWidget(zdown_button,2,3)
        grid1w = QWidget()
        grid1w.setLayout(grid1)
        grid1w.setFixedHeight(120)
        grid1w.setFixedWidth(160)

        # Level1 Grid for z position buttons
        grid2 = QGridLayout()
        grid2.addWidget(store_zcam_button,0,0)
        grid2.addWidget(move_zcam_button,0,1)
        grid2.addWidget(store_zcontact_button,0,2)
        grid2.addWidget(zhome_button,0,3)
        grid2.addWidget(camera_offset_reference_button, 1, 0)
        grid2.addWidget(camera_offset_button, 1, 1)
        grid2w = QWidget()
        grid2w.setLayout(grid2)
        grid2w.setFixedHeight(80)
        grid2w.setFixedWidth(160)

        # Level1 Grid for transform buttons
        grid3 = QGridLayout()
        grid3.addWidget(self.store_P1_button,0,0)
        grid3.addWidget(self.store_P2_button,0,1)
        grid3.addWidget(self.store_P3_button,0,2)
        grid3.addWidget(self.transform_button,0,3)
        grid3.addWidget(self.clear_transform_button, 1, 3)
        grid3w = QWidget()
        grid3w.setLayout(grid3)
        grid3w.setFixedHeight(90)
        grid3w.setFixedWidth(160)

        # Level1 Grid for spindle buttons
        grid4 = QGridLayout()
        grid4.addWidget(spindle_on_button, 0, 0)
        grid4.addWidget(spindle_off_button, 0, 1)
        grid4.addWidget(camdrill_button, 0, 2)
        grid4w = QWidget()
        grid4w.setLayout(grid4)
        grid4w.setFixedHeight(45)
        grid4w.setFixedWidth(120)

        # Level1 Grid for Excellon file handling
        grid5 = QGridLayout()
        grid5.addWidget(file_dialog_button, 0, 0, Qt.AlignLeft)
        grid5.addWidget(self.file_label, 0, 1, 1, 3, Qt.AlignRight)
        grid5w = QWidget()
        grid5w.setLayout(grid5)
        grid5w.setFixedHeight(45)
        grid5w.setFixedWidth(160)

        # Level1 Grid for PCB Image file handling
        grid6 = QGridLayout()
        grid6.addWidget(pcb_image_button, 0, 0, Qt.AlignLeft)
        grid6.addWidget(self.pcb_image_label, 0, 1, 1, 3, Qt.AlignRight)
        grid6w = QWidget()
        grid6w.setLayout(grid6)
        grid6w.setFixedHeight(45)
        grid6w.setFixedWidth(160)

        # Level1 HBox for extra settings
        hbox1 = QHBoxLayout()
        hbox1.addWidget(QLabel('Cam2XY:'))
        hbox1.addWidget(self.cam2xy_textbox)
        hbox1.addWidget(QLabel('Depth:'))
        hbox1.addWidget(self.drilldepth_textbox)

        # Level0 QVBoxLayout for toolbar
        vbox1 = QVBoxLayout()
        vbox1.setAlignment(Qt.AlignHCenter)
        vbox1.setSpacing(0)
        vbox1.addWidget(self.posdisp_label)  # Add position display
        vbox1.addWidget(grid1w)  # Add jog controls
        vbox1.addWidget(QLabel('Stored Positions/Offsets:'))
        vbox1.addWidget(grid2w)  # Add z position buttons
        vbox1.addWidget(QLabel('Spindle/Drill:'))
        vbox1.addWidget(grid4w)
        vbox1.addWidget(QLabel('Excellon File:'))
        vbox1.addWidget(grid5w)  # Add transform buttons
        vbox1.addWidget(QLabel('PBC Image File:'))
        vbox1.addWidget(grid6w)  # Add transform buttons
        vbox1.addWidget(QLabel('Coordinate Transform:'))
        vbox1.addWidget(grid3w)  # Add transform buttons
        vbox1.addWidget(QLabel('Settings:'))
        vbox1.addLayout(hbox1)
        vbox1.addSpacing(5)
        vbox1.addWidget(QLabel('Drills:'))
        vbox1.addSpacing(5)
        vbox1.addWidget(self.view)
        vbox1.addSpacing(5)
        vbox1.addWidget(auto_drill_button)
        vbox1.addStretch()

        # Vbox for images
        vbox0 = QVBoxLayout()
        vbox0.addWidget(self.webcam_image_label)
        vbox0.addWidget(self.excellon_image_label)
        vbox0.addStretch()

        # QHBoxLayout to separate camera image from controls area
        hbox0 = QHBoxLayout()
        hbox0.setSpacing(10)
        hbox0.addLayout(vbox0)
        #hbox0.addSpacing(640)
        hbox0.addLayout(vbox1)
        hbox0.addStretch()

        self.setLayout(hbox0)

        # Timer for webcam image update
        self.webcam_timer = QTimer()
        self.webcam_timer.timeout.connect(self.on_webcam_timeout)
        self.webcam_timer.start(100)

        self.pos_timer = QTimer()
        self.pos_timer.timeout.connect(self.on_pos_timeout)
        self.pos_timer.start(300)


        self.show()

    def getStepSize(self):
        return float(self.speed_combobox.currentText())

    def closeEvent(self,event):
        print("Ending this misery ...!")
        self.cnc.drill_off()
        self.cnc.motors_off()
        self.webcam_timer.stop()
        self.pos_timer.stop()
        # Save settings:

        settingsfile_lib.Settings2File('test.cfg',[self.cnc.cameraOffset, self.cnc.zCamera, self.cnc.zContact, self.cnc.zDrillDepth, self.cnc.zSeparation, self.cnc.zFastMargin, self.cnc.DrillFeedRate])
        event.accept()

    @pyqtSlot()
    def on_left_button(self):
        print("left")
        self.cnc.move_rel_mm(-self.getStepSize(),0)

    @pyqtSlot()
    def on_right_button(self):
        print("right")
        self.cnc.move_rel_mm(self.getStepSize(),0)

    @pyqtSlot()
    def on_up_button(self):
        print("up")
        self.cnc.move_rel_mm(0,self.getStepSize())

    @pyqtSlot()
    def on_down_button(self):
        print("down")
        self.cnc.move_rel_mm(0,-self.getStepSize())

    @pyqtSlot()
    def on_zup_button(self):
        print("up")
        self.cnc.move_rel_z_mm(self.getStepSize())

    @pyqtSlot()
    def on_zdown_button(self):
        print("down")
        self.cnc.move_rel_z_mm(-self.getStepSize())

    @pyqtSlot()
    def on_motor_off_button(self):
        print("motors off")
        self.cnc.motors_off()

    @pyqtSlot()
    def on_store_zcam_button(self):
        x, y, z = self.cnc.get_pos_mm()
        self.cnc.zCamera = z
        print("Camera z-position stored.")

    @pyqtSlot()
    def on_move_zcam_button(self):
        if hasattr(self.cnc, 'zCamera') and self.cnc.zCamera is not None:
            print("Moving z-position to camera focus.")
            self.cnc.move_abs_z_mm(self.cnc.zCamera)
        else:
            print("Z-position for camera focus not set.")

    @pyqtSlot()
    def on_store_zcontact_button(self):
        x, y, z = self.cnc.get_pos_mm()
        self.cnc.zContact = z
        print("Contact z-position stored.")

    @pyqtSlot()
    def on_zhome_button(self):
        self.cnc.home_z()

    @pyqtSlot()
    def on_spindle_on_button(self):
        self.cnc.drill_on(50)

    @pyqtSlot()
    def on_spindle_off_button(self):
        self.cnc.drill_off()

    @pyqtSlot()
    def on_store_P1_button(self):
        self.Excellon.v[0][0], self.Excellon.v[1][0], z = self.cnc.get_pos_mm()
        self.Excellon.u[0][0] = self.Excellon.Pxref
        self.Excellon.u[1][0] = self.Excellon.Pyref
        self.store_P1_button.setStyleSheet('QPushButton {color: green;}')
        self.store_P2_button.setEnabled(True)
        print('u = ' + str(self.Excellon.u))
        print('v = ' + str(self.Excellon.v))

    @pyqtSlot()
    def on_store_P2_button(self):
        self.Excellon.v[0][1], self.Excellon.v[1][1], z = self.cnc.get_pos_mm()
        self.Excellon.u[0][1] = self.Excellon.Pxref
        self.Excellon.u[1][1] = self.Excellon.Pyref
        self.store_P2_button.setStyleSheet('QPushButton {color: green;}')
        self.store_P3_button.setEnabled(True)
        print('u = ' + str(self.Excellon.u))
        print('v = ' + str(self.Excellon.v))

    @pyqtSlot()
    def on_store_P3_button(self):
        self.Excellon.v[0][2], self.Excellon.v[1][2], z = self.cnc.get_pos_mm()
        self.Excellon.u[0][2] = self.Excellon.Pxref
        self.Excellon.u[1][2] = self.Excellon.Pyref
        self.store_P3_button.setStyleSheet('QPushButton {color: green;}')
        self.transform_button.setEnabled(True)
        print('u = '+str(self.Excellon.u))
        print('v = '+str(self.Excellon.v))

    @pyqtSlot()
    def on_transform_button(self):
        self.Excellon.TransformDrillData()
        print('Transform done.')

    @pyqtSlot()
    def on_clear_transform_button(self):
        self.Excellon.Ts = None
        print('Transform cleared.')

    @pyqtSlot()
    def on_drilldepth_textbox(self):
        print("on_drilldepth_textbox")
        try:
            drilldepth = float(self.drilldepth_textbox.text())
            if drilldepth is not float('nan'):
                print('DrillDepth = %f' % drilldepth)
                self.cnc.zDrillDepth = drilldepth
        except:
            pass

    @pyqtSlot()
    def on_camera_offset_reference_button(self):
        x,y,z=self.cnc.get_pos_mm()
        self.camera_offset_reference = [x,y]
        print('Camera offset reference: (%f, %f)' % (x,y))

    @pyqtSlot()
    def on_camera_offset_button(self):
        if hasattr(self, 'camera_offset_reference') and self.camera_offset_reference is not None:
            x, y, z = self.cnc.get_pos_mm()
            print('Camera position: (%f, %f)' % (x, y))
            self.cnc.cameraOffset = [x-self.camera_offset_reference[0], y-self.camera_offset_reference[1]]
            self.camera_offset_reference=None
            print('Camera offset: (%f, %f)' % (self.cnc.cameraOffset[0], self.cnc.cameraOffset[1]))

    @pyqtSlot()
    def on_camdrill_button(self):
        if hasattr(self.cnc,'cameraOffset') and self.cnc.cameraOffset is not None:
            self.pos_timer.stop()
            self.cnc.drill_hole_at_cam()
            self.pos_timer.start(300)

    @pyqtSlot()
    def on_file_dialog_button(self):
        efile = QFileDialog.getOpenFileName(self, 'Open file', '/Users/gfattinger/Documents/eagle/#_GERBER_OUT/','*.xln')[0]
        if not efile=="":
            self.Excellon = drill_lib.excellon(efile)
            import ntpath
            efname=ntpath.basename(efile)
            print(efname)
            self.file_label.setText(efname)
            self.store_P1_button.setEnabled(True)
            self.Excellon.setZoom(0.9)
            self.Excellon.PlotDrillData(self.excellon_image)
            displayImage(self.excellon_image,self.excellon_image_label)
            # listitems=list(['Test', 'Whatever', 'Super'])
            self.drill_items=list()
            for data_drill in self.Excellon.data:
                self.drill_items.append(QStandardItem('%s: %1.2fmm (%d)' % (data_drill[0],data_drill[1],len(data_drill[2]))))
                self.drill_items[-1].setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                self.drill_items[-1].setData(QVariant(Qt.Checked), Qt.CheckStateRole)
                self.model.appendRow(self.drill_items[-1])

    @pyqtSlot()
    def on_pcb_image_button(self):
        print('PCB Image Load')
        self.pcb_image=cv2.imread('bottom.png')
        self.pcb_image_scaled=cv2.resize(self.pcb_image,(640,480))
        displayImage(self.pcb_image_scaled,self.excellon_image_label)

    @pyqtSlot()
    def on_auto_drill_button(self):
        if self.Excellon.Ts is not None:
            self.cnc.drill_on(50)
            for ndrill, drill_item in enumerate(self.drill_items):
                if drill_item.checkState()==Qt.Checked:
                    print(drill_item.text())
                    for nhole in range(0,len(self.Excellon.datanew[ndrill][2])):
                        x=self.Excellon.datanew[ndrill][2][nhole]
                        y=self.Excellon.datanew[ndrill][3][nhole]
                        print('%f, %f' %(x,y))
                        self.cnc.drill_hole(x,y)
                        while self.cnc.is_running():
                            sleep(0.05)
            self.cnc.drill_off()
        else:
            print('Invalid transform - aborting.')


    @pyqtSlot()
    def on_webcam_timeout(self):
        img = grab_frame(self.cap)

        # img=imageprocessinglib.processPCBimage(img)
        if hasattr(self, 'pcb_image_scaled'):
            print('OK')

        cv2.line(img,(320,0),(320,480),(255,255,255),3)
        cv2.line(img,(0,240),(640,240),(255,255,255),3)
        cv2.circle(img,(320,240), 50, (255,255,255), 3)
        cv2.line(img,(320,0),(320,480),(0,0,0),1)
        cv2.line(img,(0,240),(640,240),(0,0,0),1)
        cv2.circle(img,(320,240), 50, (0,0,0), 1)
        displayImage(img, self.webcam_image_label)

    @pyqtSlot()
    def on_pos_timeout(self):
        x,y,z = self.cnc.get_pos_mm()
        self.posdisp_label.setText('x:%3.2f  y:%3.2f  z:%3.2f' % (x,y,z))

    def on_webcam_image_label(self,x,y):
        print('Webcam image clicked (%d %d).' % (x,y))
        cam2xy = float(self.cam2xy_textbox.text())/1000
        dx = (x-320) * cam2xy
        dy = -(y-240) * cam2xy
        self.cnc.move_rel_mm(dx,dy)

    def on_excellon_image_label(self, x, y):
        print('Excellon image clicked (%d %d).' % (x, y))
        px,py,ndrill,nhole = self.Excellon.drillfile_mouse_event(x, y)
        if self.Excellon.Ts == None:
            excellon_image_marked = copy.copy(self.excellon_image)
            cv2.circle(excellon_image_marked, (px, py), 4, (0, 255, 255), 1)
            displayImage(excellon_image_marked, self.excellon_image_label)
            self.Excellon.Pxref = self.Excellon.data[ndrill][2][nhole]
            self.Excellon.Pyref = self.Excellon.data[ndrill][3][nhole]
        else:
            print('x='+str(self.Excellon.datanew[ndrill][2][nhole]))
            print('y=' + str(self.Excellon.datanew[ndrill][3][nhole]))
            excellon_image_marked = copy.copy(self.excellon_image)
            cv2.circle(excellon_image_marked, (px, py), 4, (255, 0, 0), 1)
            displayImage(excellon_image_marked, self.excellon_image_label)
            self.cnc.move_abs_mm(self.Excellon.datanew[ndrill][2][nhole],self.Excellon.datanew[ndrill][3][nhole])

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
