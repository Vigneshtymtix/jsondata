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

video_x_size = 1920
video_y_size = 1080

flip_image = 0
rotate_image = 0
masks = []

farmewin = 30
frameNo = 0
ftimes = []
for i in range(farmewin):
	ftimes.append(time.time()-(farmewin-i))
	

############################################################################
def readcamerasettings():	
	global still_time, still_interval,motion_area,motion_threshold,flip_image,masks
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
			
			
	print "Motion Area: ",motion_area
	print "Motion Threshold: ",motion_threshold
	print "Motion Stop Time: ",motion_stop_time
	print "Still Interval: ",still_interval
	print "Flip Image: ",flip_image
	print "Rotate Image: ",rotate_image
	
	
	if os.path.isfile("cammask.txt"):
		with open("cammask.txt") as myfile:
			for line in myfile:
				print line								#For Debugging
				temp1 = line.split("|")
				for m in temp1:
					mask = np.fromstring(m,dtype=int,sep=',')
					mask = mask.reshape((-1,2))
					masks.append(mask)
				print masks								#For Debugging				
				
############################################################################
	

readcamerasettings()

camera = cv2.VideoCapture(0)
#camera = picamera.PiCamera()
#camera.framerate = 30
#camera.rotation = rotate_image

#if camera.rotation == 90 or camera.rotation == 270 :
#	camera.resolution = (video_y_size,video_x_size)
#else:
#	camera.resolution = (video_x_size,video_y_size)

#if flip_image == 1:
#	print "########################### Setting Flip Image ON #############################"
#	camera.vflip = False
#	camera.hflip = False
#else:
#	print "########################### Setting Flip Image OFF ############################"
#	camera.vflip = True
#	camera.hflip = True

frame = PiRGBArray(camera)
lastgrey = None


############################################################################
mac = getHwAddr('eth0')
print "Mac: ", mac
############################################################################

lasttime = time.time();

def saveImage(saveimage):
	global frameNo, ftimes
	alert = 0;
	
	# RGB -> BGR
#	saveimage = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
	
	####################################################################
	## Alert Detection
##	s = cv2.resize(saveimage,(1,1))
##	print 
##	rt = (s[0,0,0] + s[0,0,1])*2;
##	if( s[0,0,2] > rt ):
##		print "Alert: ",s
##		alert = 1
	
	t = time.time()
	
	####################################################################
	## Noise Detection
	avg = 0
	frameNo += 1
	ftimes.append(t);
	for i in range(farmewin):
##		print "Frame",ftimes[i]
		avg += (ftimes[i+1] - ftimes[i])
	avg = avg/farmewin;
##	print "####### Average Frame Time: ",avg
	ftimes.pop(0)
	
	if avg > .5 :
		filename = '/home/pi/Desktop/CamManager/clips_new/0x{}L-{}-{}.jpg'.format(mac,t,alert)
		cv2.imwrite(filename,saveimage)
		print "Saving Still: ",filename
	else:
		print "Frames Too Fast"

############################################################################
def T(l):
	global lasttime
	
	tt = time.time();
	print "Position: ",l,"  Time: ",(tt-lasttime);
	lasttime = tt;
	
############################################################################
while True:

	motion = False
	
	## Capture a frame
	
#	T("####### S ########")
#	camera.capture(frame, format='rgb', use_video_port=True)
	res, image = camera.read()
	if( rotate_image == 90 ):
		image=cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
	if( rotate_image == 180 ):
		image=cv2.rotate(image, cv2.ROTATE_180_CLOCKWISE)
	if( rotate_image == 270 ):
		image=cv2.rotate(image, cv2.ROTATE_270_CLOCKWISE)

		
	if not res:
		sys.exit()
#	T("C")
#	image = frame.array
#	T("M")
	####################################################################
	## Motion Detection
	gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#	gray = cv2.GaussianBlur(gray, (5,5), 0)
#	T("M1")
	
	# User Motion Masks ################################################
	for i in range(0,len(masks)):
		cv2.fillPoly(gray,[masks[i]],(0,0,0))
	####################################################################
	if lastgrey is None:
		lastgrey = gray
		motion = True
		
	frameDelta = cv2.absdiff(lastgrey, gray)
	thresh = cv2.threshold(frameDelta, motion_threshold, 255, cv2.THRESH_BINARY)[1]	
	thresh = cv2.dilate(thresh, None, iterations=1)
	(cnts,_) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#	T("M2")

	# loop over the contours
	for c in cnts:
		# if the contour is large enough
		if cv2.contourArea(c) > motion_area:
			motion = True
			break
		
#	motion = 1
	## Save still if there was motion
	if motion:
		savethread = threading.Thread(target=saveImage, args = (image,))
		savethread.daemon = True
		savethread.start()
		time.sleep(.25)
		
#	T("SF")


	## Delte the frame
	frame.truncate(0)
	lastgrey = gray;
#	T("DF")
