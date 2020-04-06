import sys

from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget,  QFileDialog, QPushButton
from PyQt5.QtGui import QPixmap, QImage # , QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtCore import pyqtSignal, QEvent, pyqtSlot, QTimer, Qt
from PyQt5 import uic#, QtCore

sys.path.append('../AmScope')
import toupcam

import cv2
import drill_lib
import pycnc
import numpy as np
from time import time, sleep
from settingsfile_lib import LoadSettings, SaveSettings
import copy
import glob
# import imageprocessinglib


def grab_frame(cam):
    im = cam.get_cv2_image()
    return cv2.flip(cv2.cvtColor(im, cv2.COLOR_BGRA2BGR),1)

def clickable(widget):
    class Filter(QWidget):

        clicked = pyqtSignal(int,int)

        def eventFilter(self, obj, event):

            if obj == widget:
                if event.type() == QEvent.MouseButtonRelease:
                    if obj.rect().contains(event.pos()):
                        pos = event.pos()
                        self.clicked.emit(pos.x(), pos.y())
                        return True

            return False

    filter = Filter(widget)
    widget.installEventFilter(filter)
    return filter.clicked


def displayImage(img, label):
    height, width, channel = img.shape
    bytesPerLine = 3 * width
    qimg = QImage(img.data, width, height, bytesPerLine, QImage.Format_RGB888)
    qpm = QPixmap.fromImage(qimg)
    label.setPixmap(qpm)


class App(QMainWindow):

    def __init__(self):

        super(App, self).__init__()
        uic.loadUi("UI_DrillMaster.ui", self)
        self.title = "DrillMaster V2.0"
        self.setWindowTitle(self.title)

        self.webcam_w = self.webcam_image_label.geometry().width()
        self.webcam_h = self.webcam_image_label.geometry().height()
        self.webcam_cx = int(self.webcam_w / 2)
        self.webcam_cy = int(self.webcam_h / 2)
        self.excellon_w = self.excellon_image_label.geometry().width()
        self.excellon_h = self.excellon_image_label.geometry().height()

        self.cam = toupcam.camera(resolution_number=2)
        self.cam.open()
        self.cam.set_auto_exposure(0)
        self.cam.set_exposure_time(50000)

        self.cnc = pycnc.cnc()
        self.serial_port_combobox.addItems([""] + self.cnc.serial_ports)
        # Load settings from cfg file
        for key, value in LoadSettings('DrillMaster.cfg', 'cnc').items():
            setattr(self.cnc, key, value)
        for key, value in LoadSettings('DrillMaster.cfg', 'Excellon').items():
            if key=='Ts':
                if self.Excellon.Ts==None:
                    self.Excellon.Ts = None
                else:
                    self.Excellon.Ts = [np.matrix(x) for x in X]
        self.init_ui()

    def init_ui(self):

        # Set callback for serial port combobox:
        self.serial_port_combobox.activated.connect(self.on_serial_port_combobox)

        # Set callbacks for buttons:
        for pb in self.findChildren(QPushButton):
            pb.clicked.connect(getattr(self, "on_"+pb.objectName()))

        # Set initial webcam image
        img = grab_frame(self.cam)
        displayImage(img, self.webcam_image_label)
        print("w=%d" % (self.webcam_image_label.geometry().width()))
        clickable(self.webcam_image_label).connect(self.on_webcam_image_label)

        # Create Excellon file label
        self.excellon_image = np.zeros((480,640,3), np.uint8)
        displayImage(self.excellon_image, self.excellon_image_label)
        clickable(self.excellon_image_label).connect(self.on_excellon_image_label)

        self.drill_depth_textbox.setText(str(self.cnc.zDrillDepth))
        self.drill_depth_textbox.textChanged.connect(self.on_drill_depth_textbox)

        # Drill type list
        # self.model = QStandardItemModel()
        # self.view = QListView()
        # self.view.setModel(self.model)


        # Timer for webcam image update
        self.webcam_timer = QTimer()
        self.webcam_timer.timeout.connect(self.on_webcam_timeout)
        self.webcam_timer.start(100)

        self.pos_timer = QTimer()
        self.pos_timer.timeout.connect(self.on_pos_timeout)
        self.pos_timer.start(300)

        self.show()

    def get_step_size(self):
        return float(self.speed_combobox.currentText())

    def closeEvent(self,event):
        print("Ending this misery ...!")
        self.cam.close()
        if self.cnc.is_valid:
            self.cnc.drill_off()
            self.cnc.motors_off()
        self.webcam_timer.stop()
        self.pos_timer.stop()
        # Save settings:
        SaveSettings('DrillMaster.cfg', 'cnc',
                     {attr:getattr(self.cnc,attr) for attr in
                     ['cameraOffset', 'zCamera', 'zContact', 'zDrillDepth', 'zSeparation',
                      'zFastMargin', 'DrillFeedRate']})
        event.accept()

    @pyqtSlot()
    def on_serial_port_combobox(self):
        print("serial_port_combobox")
        serial_port = str(self.serial_port_combobox.currentText())
        serial_port_index = self.serial_port_combobox.currentIndex()
        print("%d: %s\n" % (serial_port_index, serial_port))
        self.cnc.set_serial_port(serial_port)
        print(self.cnc.is_valid)

    @pyqtSlot()
    def on_left_button(self):
        print("left")
        self.cnc.move_rel_mm(-self.get_step_size(), 0)
        self.cnc.motors_off()

    @pyqtSlot()
    def on_right_button(self):
        print("right")
        self.cnc.move_rel_mm(self.get_step_size(), 0)
        self.cnc.motors_off()

    @pyqtSlot()
    def on_up_button(self):
        print("up")
        self.cnc.move_rel_mm(0, self.get_step_size())
        self.cnc.motors_off()

    @pyqtSlot()
    def on_down_button(self):
        print("down")
        self.cnc.move_rel_mm(0, -self.get_step_size())
        self.cnc.motors_off()

    @pyqtSlot()
    def on_zup_button(self):
        print("up")
        self.cnc.move_rel_z_mm(self.get_step_size())
        self.cnc.motors_off()

    @pyqtSlot()
    def on_zdown_button(self):
        print("down")
        self.cnc.move_rel_z_mm(-self.get_step_size())
        self.cnc.motors_off()

    @pyqtSlot()
    def on_motor_off_button(self):
        print("motors off")
        self.cnc.motors_off()

    @pyqtSlot()
    def on_set_zcam_button(self):
        x, y, z = self.cnc.get_pos_mm()
        self.cnc.zCamera = z
        SaveSettings('DrillMaster.cfg', 'cnc', {'zCamera': self.cnc.zCamera})
        print("Camera z-position stored.")

    @pyqtSlot()
    def on_goto_zcam_button(self):
        if hasattr(self.cnc, 'zCamera') and self.cnc.zCamera is not None:
            print("Moving z-position to camera focus.")
            self.cnc.move_abs_z_mm(self.cnc.zCamera)
            self.cnc.motors_off()
        else:
            print("Z-position for camera focus not set.")

    @pyqtSlot()
    def on_set_zcontact_button(self):
        x, y, z = self.cnc.get_pos_mm()
        self.cnc.zContact = z
        SaveSettings('DrillMaster.cfg', 'cnc', {'zContact': self.cnc.zContact})
        print("Contact z-position stored.")

    @pyqtSlot()
    def on_home_button(self):
        self.cnc.home_z()
        self.cnc.motors_off()

    @pyqtSlot()
    def on_spindle_on_button(self):
        self.cnc.drill_on(250)

    @pyqtSlot()
    def on_spindle_off_button(self):
        self.cnc.drill_off()

    @pyqtSlot()
    def on_set_P1_button(self):
        self.Excellon.v[0][0], self.Excellon.v[1][0], z = self.cnc.get_pos_mm()
        self.Excellon.u[0][0] = self.Excellon.Pxref
        self.Excellon.u[1][0] = self.Excellon.Pyref
        self.set_P2_button.setEnabled(True)
        print('u = ' + str(self.Excellon.u))
        print('v = ' + str(self.Excellon.v))

    @pyqtSlot()
    def on_set_P2_button(self):
        self.Excellon.v[0][1], self.Excellon.v[1][1], z = self.cnc.get_pos_mm()
        self.Excellon.u[0][1] = self.Excellon.Pxref
        self.Excellon.u[1][1] = self.Excellon.Pyref
        self.set_P3_button.setEnabled(True)
        print('u = ' + str(self.Excellon.u))
        print('v = ' + str(self.Excellon.v))

    @pyqtSlot()
    def on_set_P3_button(self):
        self.Excellon.v[0][2], self.Excellon.v[1][2], z = self.cnc.get_pos_mm()
        self.Excellon.u[0][2] = self.Excellon.Pxref
        self.Excellon.u[1][2] = self.Excellon.Pyref
        self.calc_xform_button.setEnabled(True)
        print('u = '+str(self.Excellon.u))
        print('v = '+str(self.Excellon.v))

    @pyqtSlot()
    def on_calc_xform_button(self):
        self.Excellon.TransformDrillData()
        self.calc_xform_button.setEnabled(False)
        self.clear_xform_button.setEnabled(True)
        self.set_P3_button.setEnabled(False)
        self.set_P2_button.setEnabled(False)
        self.set_P1_button.setEnabled(False)
        # SaveSettings('DrillMaster.cfg', 'Excellon', {'Ts': [ts.tolist() for ts in self.Excellon.Ts]})
        print('Transform done.')

    @pyqtSlot()
    def on_clear_xform_button(self):
        self.Excellon.Ts = None
        # SaveSettings('DrillMaster.cfg', 'Excellon', {'Ts': self.Excellon.Ts})
        self.calc_xform_button.setEnabled(False)
        self.clear_xform_button.setEnabled(False)
        self.set_P3_button.setEnabled(False)
        self.set_P2_button.setEnabled(False)
        self.set_P1_button.setEnabled(True)
        print('Transform cleared.')

    @pyqtSlot()
    def on_drill_depth_textbox(self):
        print("on_drill_depth_textbox")
        try:
            drilldepth = float(self.drill_depth_textbox.text())
            if drilldepth is not float('nan'):
                print('DrillDepth = %f' % drilldepth)
                self.cnc.zDrillDepth = drilldepth
        except:
            pass

    @pyqtSlot()
    def on_set_drill_ref_button(self):
        x,y,z=self.cnc.get_pos_mm()
        self.camera_offset_reference = [x,y]
        print('Camera offset reference: (%f, %f)' % (x,y))

    @pyqtSlot()
    def on_set_cam_ref_button(self):
        if hasattr(self, 'camera_offset_reference') and self.camera_offset_reference is not None:
            x, y, z = self.cnc.get_pos_mm()
            print('Camera position: (%f, %f)' % (x, y))
            self.cnc.cameraOffset = [x-self.camera_offset_reference[0], y-self.camera_offset_reference[1]]
            self.camera_offset_reference=None
            SaveSettings('DrillMaster.cfg', 'cnc', {'cameraOffset': self.cnc.cameraOffset})
            print('Camera offset: (%f, %f)' % (self.cnc.cameraOffset[0], self.cnc.cameraOffset[1]))

    @pyqtSlot()
    def on_camdrill_button(self):
        if hasattr(self.cnc,'cameraOffset') and self.cnc.cameraOffset is not None:
            self.pos_timer.stop()
            self.cnc.drill_hole_at_cam()
            self.pos_timer.start(300)

    @pyqtSlot()
    def on_file_dialog_button(self):
        efile = QFileDialog.getOpenFileName(self, 'Open file', '/Users/gfattinger/Documents/','*.xln *.drl')[0]
        if not efile=="":
            self.Excellon = drill_lib.excellon(efile)
            import ntpath
            efname=ntpath.basename(efile)
            print(efname)
            self.file_label.setText(efname)
            self.set_P1_button.setEnabled(True)
            self.Excellon.setZoom(0.9)
            self.Excellon.PlotDrillData(self.excellon_image)
            displayImage(self.excellon_image,self.excellon_image_label)
#             # listitems=list(['Test', 'Whatever', 'Super'])
#             self.drill_items=list()
#             for data_drill in self.Excellon.data:
#                 self.drill_items.append(QStandardItem('%s: %1.2fmm (%d)' % (data_drill[0],data_drill[1],len(data_drill[2]))))
#                 self.drill_items[-1].setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
#                 self.drill_items[-1].setData(QVariant(Qt.Checked), Qt.CheckStateRole)
#                 self.model.appendRow(self.drill_items[-1])
#
    @pyqtSlot()
    def on_pcb_image_button(self):
        print('PCB Image Load')
        # self.pcb_image=cv2.imread('bottom.png')
        # self.pcb_image_scaled=cv2.resize(self.pcb_image,(640,480))
        # displayImage(self.pcb_image_scaled,self.excellon_image_label)

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
                        sleep(0.2)
                        while self.cnc.is_running():
                            sleep(0.1)
            self.cnc.drill_off()
        else:
            print('Invalid transform - aborting.')


    @pyqtSlot()
    def on_webcam_timeout(self):
        img = grab_frame(self.cam)
        # img=imageprocessinglib.processPCBimage(img)
        cv2.line(img,(self.webcam_cx,0),(self.webcam_cx,self.webcam_h),(255,255,255),3)
        cv2.line(img,(0,self.webcam_cy),(self.webcam_w,self.webcam_cy),(255,255,255),3)
        cv2.circle(img,(self.webcam_cx,self.webcam_cy), 50, (255,255,255), 3)
        cv2.line(img,(self.webcam_cx,0),(self.webcam_cx,self.webcam_h),(0,0,0),1)
        cv2.line(img,(0,self.webcam_cy),(self.webcam_w,self.webcam_cy),(0,0,0),1)
        cv2.circle(img,(self.webcam_cx,self.webcam_cy), 50, (0,0,0), 1)
        displayImage(img, self.webcam_image_label)
#
    @pyqtSlot()
    def on_pos_timeout(self):
        x,y,z = self.cnc.get_pos_mm()
        self.posdisp_label.setText('x:%3.2f  y:%3.2f  z:%3.2f' % (x,y,z))

    def on_webcam_image_label(self,x,y):
        print('Webcam image clicked (%d %d).' % (x,y))
        # cam2xy = float(self.cam2xy_textbox.text())/1000
        # dx = (x-320) * cam2xy
        # dy = -(y-240) * cam2xy
        # self.cnc.move_rel_mm(dx,dy)

    def on_excellon_image_label(self, x, y):
        print('Excellon image clicked (%d %d).' % (x, y))
        # if not hasattr(self,'Excellon'):
        #     return
        # px,py,ndrill,nhole = self.Excellon.drillfile_mouse_event(x, y)
        # if self.Excellon.Ts == None:
        #     excellon_image_marked = copy.copy(self.excellon_image)
        #     cv2.circle(excellon_image_marked, (px, py), 4, (0, 255, 255), 1)
        #     displayImage(excellon_image_marked, self.excellon_image_label)
        #     self.Excellon.Pxref = self.Excellon.data[ndrill][2][nhole]
        #     self.Excellon.Pyref = self.Excellon.data[ndrill][3][nhole]
        # else:
        #     print('x='+str(self.Excellon.datanew[ndrill][2][nhole]))
        #     print('y=' + str(self.Excellon.datanew[ndrill][3][nhole]))
        #     excellon_image_marked = copy.copy(self.excellon_image)
        #     cv2.circle(excellon_image_marked, (px, py), 4, (255, 0, 0), 1)
        #     displayImage(excellon_image_marked, self.excellon_image_label)
        #     self.cnc.move_abs_mm(self.Excellon.datanew[ndrill][2][nhole],self.Excellon.datanew[ndrill][3][nhole])



app = QApplication(sys.argv)
ex = App()
app.exec_()
