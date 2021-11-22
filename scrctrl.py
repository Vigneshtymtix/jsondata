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
import copy

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
show_mask = 0

farmewin = 30
frameNo = 0
ftimes = []

cameraType = 0;

for i in range(farmewin):
	ftimes.append(time.time()-(farmewin-i))
	

############################################################################
def readcamerasettings():	
	global still_time, still_interval,motion_area,motion_threshold,flip_image,masks,rotate_image,show_mask
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
			show_mask = 4*myvars['SHOWMASK']
			
			
	print "Motion Area: ",motion_area
	print "Motion Threshold: ",motion_threshold
	print "Motion Stop Time: ",motion_stop_time
	print "Still Interval: ",still_interval
	print "Flip Image: ",flip_image
	print "Rotate Image: ",rotate_image
	print "Show Mask: ",show_mask
	
	
	if os.path.isfile("campmask.txt"):
		with open("campmask.txt") as myfile:
			for line in myfile: 
				print line								#For Debugging
				temp1 = line.split("|")
				for m in temp1:
					mask = np.fromstring(m,dtype=float,sep=',')
					mask = mask.reshape((-1,2))
					masks.append(mask)
				print masks								#For Debugging
				for i in range(0,len(masks)):				
					print masks[i]				
						
				
############################################################################
readcamerasettings()

	
camera = cv2.VideoCapture(0)
cameraType = 1
print "Camera Is Type #1"

#if camera.rotation == 90 or camera.rotation == 270 :
#	camera.resolution = (video_y_size,video_x_size)
#else:
#	camera.resolution = (video_x_size,video_y_size)

#if( cameraType == 2 ):
#	if flip_image == 1:
#		print "########################### Setting Flip Image ON #############################"
#		camera.vflip = False
#		camera.hflip = False
#	else:
#		print "########################### Setting Flip Image OFF ############################"
#		camera.vflip = True
#		camera.hflip = True

frame = PiRGBArray(camera)
lastgrey = None

############################################################################
mac = getHwAddr('eth0')
print "Mac: ", mac
############################################################################

lasttime = time.time();

def rotateImage(mat, angle):
		floatAngle = float(angle)
		#Rotates an image (angle in degrees) and expands image to avoid cropping

		height, width = mat.shape[:2] # image shape has 3 dimensions
		image_center = (width/2, height/2) # getRotationMatrix2D needs coordinates in reverse order (width, height) compared t$

		rotation_mat = cv2.getRotationMatrix2D(image_center, floatAngle, 1.)

		# rotation calculates the cos and sin, taking absolutes of those.
		abs_cos = abs(rotation_mat[0,0])
		abs_sin = abs(rotation_mat[0,1])

		# find the new width and height bounds
		bound_w = int(height * abs_sin + width * abs_cos)
		bound_h = int(height * abs_cos + width * abs_sin)

		# subtract old image center (bringing image back to origo) and adding the new image center coordinates
		rotation_mat[0, 2] += bound_w/2 - image_center[0]
		rotation_mat[1, 2] += bound_h/2 - image_center[1]

		# rotate image with the new bounds and translated rotation matrix
		rotated_mat = cv2.warpAffine(mat, rotation_mat, (bound_w, bound_h))
		return rotated_mat


def saveImage(saveimage):
	global frameNo, ftimes, rotate_image
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

	res, pimage = camera.read()
#	if( rotate_image == 90 ):
#		image=cv2.rotate(pimage, cv2.ROTATE_90_CLOCKWISE)
#	if( rotate_image == 180 ):
#		image=cv2.rotate(pimage, cv2.ROTATE_180_CLOCKWISE)
#	if( rotate_image == 270 ):
#		image=cv2.rotate(pimage, cv2.ROTATE_270_CLOCKWISE)
#	else:
	image = pimage
			
	if not res:
		print "No Image: Quitting"
		sys.exit()
			

#	T("C")
#	image = frame.array
#	T("M")
	if rotate_image != 0:
			image = rotateImage(image,rotate_image)
			
	####################################################################
	## Motion Detection
	gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#	gray = cv2.GaussianBlur(gray, (5,5), 0)
#	T("M1")
	
	# User Motion Masks ################################################
#	print "Apply Mask"
	h, w, c = image.shape
#	print "Image Res:",w,"x",h
	pmasks = copy.deepcopy(masks)
	for i in range(0,len(pmasks)):				
		for j in range(0,len(pmasks[i])):
			pmasks[i][j][0] = int(masks[i][j][0]*w)		#For Debugging	
			pmasks[i][j][1] = int(masks[i][j][1]*h)		#For Debugging
#			print "Scaled Mask:",pmasks[i][j][0],pmasks[i][j][1]
	for i in range(0,len(pmasks)):
#		print " Aply Mask:",np.int32([pmasks[i]])
		cv2.fillPoly(gray,np.int32([pmasks[i]]),(0,0,0))
		
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

#	T("MF")

	# User Motion Masks ################################################
	if( show_mask == 2 ):
		print "************************ Sending Masked Image ***********************"
		savethread = threading.Thread(target=saveImage, args = (gray,))
		savethread.daemon = True
		savethread.start()
		time.sleep(.25)
	else:
		if( motion or show_mask == 1 ):
			savethread = threading.Thread(target=saveImage, args = (image,))
			savethread.daemon = True
			savethread.start()
			time.sleep(.25)
			
	if( show_mask > 0 ):
		show_mask = show_mask-1
	
#	T("SF")


	## Delte the frame
	frame.truncate(0)
	lastgrey = gray;
#	T("DF")
