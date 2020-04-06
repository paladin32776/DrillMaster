import serial
from time import sleep
import glob

import copy
import cv2
import numpy as np
from math import isnan

class cnc:

    def __init__(self, serial_port = None):
        # Default values in case not set by user:
        self.cameraOffset=[55.05,-3.64]
        self.zCamera=None
        self.zContact=None
        self.zDrillDepth=0
        self.zSeparation = 5
        self.zFastMargin=0.5
        self.DrillFeedRate=100
        self.fastRate = 2000
        self.slowRate = 300
        self.drillSpeed = 250
        # Find valid serial ports with Smoothies connected:
        self.get_serial_ports(keyword = "usbmodem", query = "\n", response = "ok")
        self.set_serial_port(serial_port)

    def set_serial_port(self, serport):
        try:
            self.ser = serial.Serial('/dev/tty.' + serport, 9600)
            if self.ser.is_open and self.query_response("\n","ok"):
                self.is_valid = True
                self.set_units_mm()
                self.set_fastRate()
                self.set_slowRate()
        except:
            self.is_valid = False

    def get_serial_ports(self, keyword = "", query = None, response = None):
        serial_ports = [s.split('.')[1] for s in glob.glob('/dev/tty.*') if keyword in s]
        self.serial_ports = []
        for serial_port in serial_ports:
            try:
                self.ser = serial.Serial('/dev/tty.' + serial_port, 9600)
                if self.ser.is_open:
                    if self.query_response(query, response):
                        self.serial_ports = self.serial_ports + [serial_port]
                    self.ser.close()
            except:
                pass

    def query_response(self, query = None, response = None):
        if query is None or response is None:
            return True
        self.ser.read_all()
        self.ser.write(bytes(query,'utf-8'))
        s = self.ser.readline().decode('utf-8')
        if s.__contains__(response):
            return True
        else:
            return False

    def set_units_mm(self):
        self.ser.write(b'G21\n')

    def motors_off(self):
        self.ser.write(b'M18\n')

    def move_rel_mm(self, x=None, y=None, z=None):
        coords = " ".join(
            [axis + str(offset) for axis, offset in zip(["X", "Y", "Z"], [x, y, z]) if offset is not None])
        print("Moving by %s ..." % (coords))
        self.ser.write(("G91\nG0 " + coords + "\nG90\n").encode('UTF-8'))

    def move_rel_z_mm(self, z):
        self.move_rel_mm(z=z)

    def move_abs_mm(self, x=None, y=None, z=None):
        coords = " ".join(
            [axis + str(offset) for axis, offset in zip(["X", "Y", "Z"], [x, y, z]) if offset is not None])
        print("Moving to %s ..." % (coords))
        self.ser.write(("G90\nG0 " + coords + "\n").encode('UTF-8'))

    def move_abs_z_mm(self, z):
        self.move_abs_mm(z=z)

    def move_abs_z_feed_mm(self,z,f=None):
        print('move to %f with rate %f' % (z,f))
        self.ser.write(b'G90\nG1 Z%f F%f\n' % (z,f))
        self.set_slowRate()

    def set_fastRate(self, rate=None):
        if rate is None:
            rate = self.fastRate
        self.ser.write(b'G0 F%f\n' % (rate))

    def set_slowRate(self, rate=None):
        if rate is None:
            rate = self.slowRate
        self.ser.write(b'G1 F%f\n' % (rate))

    def get_state(self):
        try:
            self.ser.read_all()
            self.ser.write(b'?')
            s=self.ser.readline().decode('utf-8')
            if s.__contains__('|'):
                vs = s.strip('<>\n').split('|')
                result = {v.split(':')[0]:[float(d) for d in v.split(':')[1].split(',')] for v in vs[1:]}
                result['Status'] = vs[0]
            elif s.__contains__('<') and s.__contains__('>'):
                vs = s.strip('<>\n\r').replace('MPos:', '').replace('WPos:', '').split(',')
                result = {'Status': vs[0], 'MPos': [float(v) for v in vs[1:4]], 'WPos': [float(v) for v in vs[4:7]], 'F':[float('nan')]*2}
            else:
                result = {'Status': 'undefined', 'MPos': [float('nan')] * 3, 'WPos': [float('nan')] * 3, 'F': [float('nan')] * 2}
        except:
            result = {'Status':'undefined', 'MPos':[float('nan')]*3, 'WPos':[float('nan')]*3, 'F':[float('nan')]*2}
        return result

    def get_pos_mm(self):
        return self.get_state()['WPos']

    def get_progress(self):
        try:
            self.ser.read_all()
            self.ser.write(b'progress\n')
            s = self.ser.readline().decode('utf-8')
            percent = int(s.split(", ")[1].split(" % ")[0])
            elapsed = s.split(", ")[2].split(": ")[-1].rstrip()
            remaining = s.split(", ")[3].split(": ")[-1].rstrip()
            return percent, elapsed, remaining
        except:
            return 0, "na", "na"

    def set_zContact(self):
        x0,y0,z0=self.get_pos_mm()
        self.zContact=z0
        print('zContact set to %fmm' % (self.zContact))

    def set_zCamera(self):
        x0,y0,z0=self.get_pos_mm()
        self.zCamera=z0
        print('zCamera set to %fmm' % (self.zCamera))

    def home_z(self):
        print('Homing z-axis ... ')
        self.ser.write(b'G28 Z\n')
        while (not self.is_idle()):
            sleep(0.05)
        print('done. ')

    def home(self):
        print('Homing all axes ... ')
        self.ser.write(b'G28\n')
        while (not self.is_idle()):
            sleep(0.05)
        self.motors_off()
        print('done. ')

    def set_coordinates(self,x=None, y=None, z=None):
        coords = " ".join([axis+str(offset) for axis,offset in zip(["X","Y","Z"],[x,y,z]) if offset is not None])
        print("Setting %s ..." % (coords))
        self.ser.write(("G92 " + coords + "\n").encode('UTF-8'))

    def drill_on(self,speed=50):
        print('Turn drill on (speed %f)' % (speed))
        ramp_template = list(range(5,30,5))+list(range(50,255,50))
        ramp = [s for s in ramp_template if s<speed]+list([speed])
        for s in ramp:
            self.ser.write(b'M3 S%f\n' % (s))
            sleep(0.2)

    def drill_off(self):
        print('Turn drill off')
        self.ser.write(b'M5\n')


    def drill_hole(self,x,y):
        self.move_abs_z_mm(self.zContact+self.zSeparation)
        self.move_abs_mm(x-self.cameraOffset[0],y-self.cameraOffset[1])
        self.move_abs_z_mm(self.zContact+self.zFastMargin)
        self.move_abs_z_feed_mm(self.zContact-self.zDrillDepth,self.DrillFeedRate)
        self.move_abs_z_mm(self.zContact+self.zSeparation)


    def drill_hole_at_cam(self):
        x0,y0,z0=self.get_pos_mm()
        self.drill_on(self.drillSpeed)
        self.drill_hole(x0,y0)
        self.drill_off()
        self.move_abs_z_mm(self.zCamera)
        self.move_abs_mm(x0,y0)
        while self.is_running():
            sleep(0.1)
            pass

    def laser_on(self, power):
        print('Turn laser on (power %d)' % (power))
        self.ser.write(b'fire %d\n' % (power))

    def laser_off(self):
        print('Turn laser off')
        self.ser.write(b'fire off\n')

    def play(self, filename):
        print("Playing %s ...\n" % (filename))
        self.ser.write(('cd /sd\nplay %s\n' % (filename.lower())).encode('UTF-8'))

    def abort(self):
        print("Aborting.\n")
        self.ser.write(b'abort\n')
        self.motors_off()

    def is_running(self):
        if self.get_state()['Status']=='Run':
            return 1
        else:
            return 0

    def is_idle(self):
        if self.get_state()['Status']=='Idle':
            return True
        else:
            return False

    def  __del__(self):
        self.ser.close()


class excellon:
    def __init__(self,filename):
        self.data=None
        self.minmax=None
        #self.u = [[0, 0, 0], [0, 0, 0]]
        #self.v = [[0, 0, 0], [0, 0, 0]]
        self.u = [[82.55, 80.5688, 17.0688], [10.7061, 71.9455, 71.9455]]
        self.v = [[-86.3714, -84.4706, -20.8226], [-56.2333, 5.0563, 5.0947]]
        self.Ts=None
        self.datanew=None
        self.read(filename)

    def read(self, filename):
        import re
        unit_factor = 25.4 / 100000
        drills = list()
        diameters = list()
        coords = list()
        print(filename)
        file = open(filename, 'r')
        s = file.readline().rstrip('\n')
        while len(s) > 0:
            if (not s.strip()[0]==";"):
                # Checking for METRIC/INCH tag:
                d =re.findall('METRIC|INCH',s)
                if len(d)>0:
                    d = s.split(',')
                    unit = d[0].upper()
                    if len(d)>1:
                        zeromode = d[1]
                        numberformat = d[2]
                        numberdigits = numberformat.count('0')
                        digitsaftercomma = re.findall('[.][0]+',numberformat)[0].count('0')
                        mag_factor = pow(10, -digitsaftercomma)
                    else:
                        zeromode = 'DECIMAL'
                        mag_factor = 1.0
                    if unit=="METRIC":
                        unit_factor = 1 # 1 mm
                    elif unit=="INCH":
                        unit_factor = 25.4 # 1 inch (25.4 mm)

                # TxxCy.yyyyy sections:
                d = re.findall('T[0-9]*[C][+-]?[0-9]+[0-9]*[.][0-9]*', s)
                if len(d) > 0:
                    d = d[0].split('C')
                    drills.append(d[0].strip('\n'))
                    if d[1].count('.')>0:
                        diameters.append(float(d[1]) * unit_factor)
                    else:
                        if zeromode == 'TZ':
                            diameters.append(float(d[1].rjust(numberdigits, '0')) * unit_factor * mag_factor)
                        elif zeromode == 'LZ':
                            diameters.append(float(d[1].ljust(numberdigits, '0')) * unit_factor * mag_factor)
                    coords.append(list())

                # Txx sections:
                d = re.findall('T[0-9]+$', s)
                if len(d) > 0:
                    drill = d[0].strip('\n')
                    if drills.__contains__(drill):
                        ndrill = drills.index(drill)
                        coords[ndrill].append(drills[ndrill])
                        coords[ndrill].append(diameters[ndrill])
                        coords[ndrill].append(list())
                        coords[ndrill].append(list())

                # X...Y... sections:
                d = re.findall('X[+-]?[0-9]+[0-9]*[.]?[0-9]*Y[+-]?[0-9]+[0-9]*[.]?[0-9]*', s)
                if len(d) > 0:
                    s_xy = s.split('X')[1].split('Y')
                    if zeromode=='TZ':
                        # coords[ndrill][2].append(float(s_xy[0].rjust(numberdigits, '0')) * unit_factor * mag_factor)
                        # coords[ndrill][3].append(float(s_xy[1].rjust(numberdigits, '0')) * unit_factor * mag_factor)
                        coords[ndrill][2].append(float(s_xy[0]) * unit_factor * mag_factor)
                        coords[ndrill][3].append(float(s_xy[1]) * unit_factor * mag_factor)
                    elif zeromode=='LZ':
                        coords[ndrill][2].append(float(s_xy[0].ljust(numberdigits, '0')) * unit_factor * mag_factor)
                        coords[ndrill][3].append(float(s_xy[1].ljust(numberdigits, '0')) * unit_factor * mag_factor)
                    elif zeromode=='DECIMAL':
                        coords[ndrill][2].append(float(s_xy[0]) * unit_factor)
                        coords[ndrill][3].append(float(s_xy[1]) * unit_factor)

            s = file.readline().rstrip('\n')

        file.close()

        minmax = [min(coords[0][2]), max(coords[0][2]), min(coords[0][3]), max(coords[0][3])]
        for n in range(0, len(coords)):
            minmax = [min(coords[n][2] + [minmax[0]]), max(coords[n][2] + [minmax[1]]),
                      min(coords[n][3] + [minmax[2]]), max(coords[n][3] + [minmax[3]])]
        print(minmax)
        self.data = coords
        self.minmax = minmax
        self.view = minmax

    def GetTransform3P(self):
        u = np.matrix(self.u)
        v = np.matrix(self.v)
        uu = u - u[0:2, 0]
        vv = v - v[0:2, 0]
        U = np.matrix([[uu[0, 1], uu[1, 1], 0, 0], [0, 0, uu[0, 1], uu[1, 1]], [uu[0, 2], uu[1, 2], 0, 0],
                       [0, 0, uu[0, 2], uu[1, 2]]])
        vvv = vv[0:2, 1:3].T.reshape([4, 1])
        t = U.I * vvv
        T = t.reshape([2, 2])
        u0 = u[0:2, 0]
        v0 = v[0:2, 0]
        self.Ts = [T, u0, v0]

    # Apply Transform information to corrdinate vectors:
    def Transform(self,u):
        u = np.matrix(u)
        unew = self.Ts[0] * (u - self.Ts[1]) + self.Ts[2]
        return unew.tolist()

    # Transform drill data set:
    def TransformDrillData(self):
        self.GetTransform3P()
        self.datanew = copy.deepcopy(self.data)
        for ndrill in range(0, len(self.datanew)):
            self.datanew[ndrill][2:4] = self.Transform(self.data[ndrill][2:4])

    # Visualize drill data set:
    def PlotDrillData(self,img):
        global view
        for ndrill in range(0, len(self.data)):
            x = ((np.matrix(self.data[ndrill][2]) - self.view[0]) / (self.view[1] - self.view[0]) * 640).astype(int).tolist()[0]
            y = ((np.matrix(self.data[ndrill][3]) - self.view[2]) / (self.view[3] - self.view[2]) * 480).astype(int).tolist()[0]
            d = self.data[ndrill][1]
            for nhole in range(0, len(x)):
                cv2.circle(img, (x[nhole], y[nhole]), 2, (255, 255, 255), 1)

    def setZoom(self,factor):
        marginx=(self.minmax[1]-self.minmax[0])*(1-factor)/2
        marginy=(self.minmax[3]-self.minmax[2])*(1-factor)/2
        self.view = [self.minmax[0]-marginx,self.minmax[1]+marginx,self.minmax[2]-marginy,self.minmax[3]+marginy]

    def drillfile_mouse_event(self, px, py):
        #global data, view, xyRef, datanew
        print('click:  px=%d  py=%d' % (px, py))
        for ndrill in range(0, len(self.data)):
            x = ((np.matrix(self.data[ndrill][2]) - self.view[0]) / (self.view[1] - self.view[0]) * 640).astype(int) #.tolist()[0]
            y = ((np.matrix(self.data[ndrill][3]) - self.view[2]) / (self.view[3] - self.view[2]) * 480).astype(int) #.tolist()[0]
            dxy = np.square(x - px) + np.square(y - py)
            if ndrill == 0:
                dxy_min = np.min(dxy)
                nhole_min = np.argmin(dxy)
                ndrill_min = ndrill
            else:
                if dxy_min > np.min(dxy):
                    dxy_min = np.min(dxy)
                    nhole_min = np.argmin(dxy)
                    ndrill_min = ndrill
        d = self.data[ndrill_min][1]
        x = ((np.matrix(self.data[ndrill_min][2][nhole_min]) - self.view[0]) / (self.view[1] - self.view[0]) * 640).astype(int).tolist()[0][0]
        y = ((np.matrix(self.data[ndrill_min][3][nhole_min]) - self.view[2]) / (self.view[3] - self.view[2]) * 480).astype(int).tolist()[0][0]
        return x,y,ndrill_min,nhole_min

        #return x,y,drill_image_marked
        #     cv2.imshow('drillfile', drill_image_marked)
        # if False: #isT == 0:
        #     xyRef = [data[ndrill_min][2][nhole_min], data[ndrill_min][3][nhole_min]]
        # else:
        #     x = datanew[ndrill_min][2][nhole_min]
        #     y = datanew[ndrill_min][3][nhole_min]
        #     print('GOTO: %f  %f' % (x, y))
