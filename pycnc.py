import serial
from time import sleep
import glob

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
        self.drillSpeed = 250
        self.vG0 = 2000
        self.vG1 = 600
        self.PLaser = 0.02
        # Find valid serial ports with Smoothies connected:
        self.get_serial_ports(keyword = "usbmodem", query = "\n", response = "ok")
        self.set_serial_port(serial_port)

    def set_serial_port(self, serport):
        try:
            self.ser = serial.Serial('/dev/tty.' + serport, 9600)
            if self.ser.is_open and self.query_response("\n","ok"):
                self.is_valid = True
                self.set_units_mm()
                self.set_G0_speed()
                self.set_G1_speed()
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

    def set_G0_speed(self,v=None):
        if v is None:
            v = self.vG0
        if self.is_valid:
            self.ser.write(b'G0 F%f\n' % (v))

    def set_G1_speed(self,v=None):
        if v is None:
            v = self.vG1
        if self.is_valid:
            self.ser.write(b'G1 F%f\n' % (v))

    def set_laser_power(self,P=None):
        if P is None:
            P = self.PLaser
        if self.is_valid:
            self.ser.write(b'G0 S%f\n' % (P))

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