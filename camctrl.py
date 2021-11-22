#!/usr/bin/python
import time
import picamera
import cv2
import subprocess
import threading
from uuid import getnode as get_mac
from picamera.array import PiRGBArray
import os.path
import sys
import socket
import fcntl
import struct
import numpy as np
import json

############################################################################
def getHwAddr(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', ifname[:15]))
    return ''.join(['%02x' % ord(char) for char in info[18:24]])

############################################################################
index = 1
motion_threshold = 40
motion_area = 500
motion_stop_time = 5
still_interval = 5
still_time = time.time()
video_x_size = 512
video_y_size = 320
flip_image = 0
rotate_image = 0
masks = []
show_mask = 0

############################################################################
def readcamerasettings():
        global still_time, still_interval,motion_area,motion_threshold,flip_image,masks,show_mask
        myvars = {}
        if os.path.isfile("camsettings.txt"):
                with open("camsettings.txt") as myfile:
                        for line in myfile:
                                name, var = line.partition("=")[::2]
                                myvars[name.strip()] = int(var.strip())

                        motion_area = myvars['MOTION_AREA']
                        motion_threshold = myvars['MOTION_THRESHOLD']
                        motion_stop_time = myvars['MOTION_STOP_TIME']
                        still_interval = myvars['STILL_INTERVAL']
                        flip_image = myvars['FLIP_IMAGE']
                        rotate_image = myvars['ROTATE_IMAGE']
                        show_mask = myvars['SHOWMASK']


        print "Motion Area: ",motion_area
        print "Motion Threshold: ",motion_threshold
        print "Motion Stop Time: ",motion_stop_time
        print "Still Interval: ",still_interval
        print "Flip Image: ",flip_image
        print "Rotate Image: ",rotate_image
        print "Show Mask: ",show_mask


        if os.path.isfile("cammask.txt"):
                with open("cammask.txt") as myfile:
                        for line in myfile:
                                print line                                                              #For Debugging
                                temp1 = line.split("|")
                                for m in temp1:
                                        mask = np.fromstring(m,dtype=int,sep=',')
                                        mask = mask.reshape((-1,2))
                                        masks.append(mask)
                                print masks                                                             #For Debugging

############################################################################

readcamerasettings()

camera = picamera.PiCamera()
camera.framerate = 30
camera.rotation = rotate_image

if camera.rotation == 90 or camera.rotation == 270 :
        camera.resolution = (video_y_size,video_x_size)
else:
        camera.resolution = (video_x_size,video_y_size)

if flip_image == 1:
        print "########################### Setting Flip Image ON #############################"
        camera.vflip = False
        camera.hflip = False
else:
        print "########################### Setting Flip Image OFF ############################"
        camera.vflip = True
        camera.hflip = True

frame = PiRGBArray(camera)
videostream = picamera.PiCameraCircularIO(camera, seconds=1)
lastgrey = None

############################################################################
mac = getHwAddr('eth0')
print "Mac: ", mac
############################################################################
def detect_motion():
        global lastgrey,motion_area,motion_threshold,masks

        ret = False
        camera.capture(frame, format='bgr', use_video_port=True)
        image = frame.array

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # User Masks ########################################
        for i in range(0,len(masks)):
                cv2.fillPoly(gray,[masks[i]],(0,0,0))
        #####################################################

        if lastgrey is None:
                lastgrey = gray

        frameDelta = cv2.absdiff(lastgrey, gray)
        thresh = cv2.threshold(frameDelta, motion_threshold, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        (_, cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # loop over the contours
        for c in cnts:
                # if the contour is large enough
                if cv2.contourArea(c) > motion_area:
                        ret = True
                        # compute the bounding box for the contour, draw it on the frame,
                        # and update the text
#                       (x, y, w, h) = cv2.boundingRect(c)
#                       cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Save Change Example
#       if ret:
#               cv2.imwrite("grey.jpg",gray)
#               cv2.imwrite("delta.jpg",frameDelta)

#       cv2.imshow("OpenCV", image)
        frame.truncate(0)
        lastgrey = gray;
        return ret

############################################################################
## Trim A Video Clip and Move to the New Clips Directory
############################################################################
def finish_video( stime ):

        filein = './clips_raw/%d.h264' % stime
        fileout = './clips_raw/0x{}L-{:.2f}.mp4'.format(mac,stime)

        subprocess.call(["MP4Box","-add",filein,"-fps","32.33",fileout])
        subprocess.call(["rm",filein])
        time.sleep(1);

        print "FileOut:", fileout

        cmd = 'mediainfo %s | grep Duration | head -1 | awk \'{print (substr($3,length($3))=="n") ? $3*60+$4*1 : $3*1+$4/1000}\'' % fileout

        print "Cmd:", cmd

        rsl = subprocess.check_output(cmd,shell=True)
        print "Raw Source Length:", rsl
        srclen = float(rsl)
        print "Raw Source Length:", srclen

        filein = './clips_raw/0x{}L-{:.2f}.mp4'.format(mac,stime)
        fileout = './clips_new/0x{}L-{:.2f}-{:.2f}.mp4'.format(mac,stime,srclen)

        print "FileIn:", filein
        print "FileOut:", fileout

        subprocess.call(["mv",filein,fileout])

#       offset = srclen - float(length);
#       destlen = srclen - offset;
##      destlen = (int((etime - stime)*25)/25)+1.0
##      start = (int((float(srclen) - destlen)*25)/25)-1.0

#       print "############################################"
#       print "############################################"
#       print "Source Length:", float(srclen)
#       print "Source Start Offset:", float(offset)
#       print "Destination Length:", float(destlen)

#       if offset < 0:
#               quit()

#       subprocess.call(["rm",out])
#       if srclen > destlen and offset > 0:
#               print "Trimming";
#               print "############################################"
#               print "############################################"
#               subprocess.call(["ffmpeg","-i",temp,"-ss",str(offset),"-t",str(destlen),out])
#       else:
#               print "No Trimming";
#               print "############################################"
#               print "############################################"
#               subprocess.call(["mv",temp,out])


#       subprocess.call(["rm",temp])

#       destlen = subprocess.check_output("mediainfo "+out+" | grep Duration | head -1 | awk '{print $3*1+$4/1000}'",shell=True)
#       finalout = './newclips/0x{}L-{}-{:4.2f}.mp4'.format(mac,seconds,float(destlen))

#       subprocess.call(["mv",out,finalout])

########################################################################


#       put = "sftp -i 'RPWebServer.pem' ubuntu@ec2-54-187-207-201.us-west-2.compute.amazonaws.com:/var/www/html <<< 'put ./{}'".format(finalout)
#       print "Cmd: ", put

#       system('ls')

#   sftp -i "RPWebServer.pem" ubuntu@ec2-54-187-207-201.us-west-2.compute.amazonaws.com:/var/www/html <<< 'put ./out001.mp4'


#       file = open("info%03d.txt" % idx,"w")
#       file.write("time: %f\n" % (time) )
#       file.write("Length: %f\n" % (length) )
#       file.close()

############################################################################
## Start Recording On Slave Cams
############################################################################
def startsocket(addr,data):
        # Create a TCP/IP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Connect the socket to the port where the server is listening
        server_address = (addr,10000)
        print >>sys.stderr, 'connecting to %s port %s' % server_address
        sock.connect(server_address)

        try:
                # Send data
                print >>sys.stderr, 'sending "%s"' % data
                sock.sendall(data)

        finally:
                print >>sys.stderr, 'closing socket'
                sock.close()

def tellslaves(slaves,msg):
        for slave in slaves:
                print "Tell Slave: ",slave,msg
#               startsocket(slave,msg)

def startslaves():
        slaves = []
        if os.path.isfile("slaves.txt"):
                with open("slaves.txt") as f:
                        slaves = f.readlines()
                slaves = [x.strip() for x in slaves]

        slavethread = threading.Thread(target=tellslaves, args = (slaves,'start'))
        slavethread.daemon = True
        slavethread.start()

############################################################################
def StillTime():
        global still_time, still_interval,show_mask
        if still_interval > 0:
                if time.time() > still_time:
                        print "Old Still Time: ",still_time
                        print "Interval: ",still_interval
                        still_time = time.time()+(60*still_interval)
                        print "New Still Time: ",still_time
                        camera.capture(frame, format='bgr', use_video_port=True)
                        image = frame.array
						
                        if( show_mask == 1 ):
                            for i in range(0,len(masks)):
                                cv2.fillPoly(image,[masks[i]],(0,0,0))
                            show_mask = 0
						
                        filename = './still/0x{}L.jpg'.format(mac)
#                       cv2.imshow("OpenCV", image)
                        cv2.imwrite(filename,image)
                        print "Saving Still: ",filename
                        frame.truncate(0)

############################################################################
## Start of the Main Loop
############################################################################

subprocess.call(["rm","./clips_raw/*.*"])

minute_break = 60;

while True:
#       print('begin pre-record')
#       camera.start_recording(videostream, format='h264')
        detect_motion()
        detect_motion()

        motion_stopped = 0;

        StillTime()
        if minute_break > 0:
                while True:
                        StillTime()
                        if detect_motion():
        #                               startslaves()
                                print('motion detected...')
                                break

        try:
                minute_break = 60;
                stime = time.time()
                file = './clips_raw/%d.h264' % stime
                camera.start_recording(file, format='h264')
                while True:
                        print 'rcording body...(',motion_stop_time-motion_stopped,') breaking in (',minute_break,')'
                        camera.wait_recording(1)

                        if detect_motion() == False:
                                motion_stopped = motion_stopped + 1
                        else:
                                motion_stopped = 0

                        minute_break = minute_break - 1

                        if motion_stopped+1 > motion_stop_time:
                                print('no motion...')
                                break

                        if minute_break == 0:
                                print('minute break...')
                                break

        finally:
                camera.stop_recording()

        ####################################################################
        ## Process The Raw Video Into An mp4 and Add Time Info To Filename
        ####################################################################
        trimthread = threading.Thread(target=finish_video, args = (stime,))
        trimthread.daemon = True
        trimthread.start()
