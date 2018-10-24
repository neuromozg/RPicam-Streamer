#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import time
import cv_stream

RTP_PORT = 5000
HOST = '127.0.0.1'
FRAMERATE = 10.0
RESOLUTION = (800, 600)

running = True
        
def showFrame(frame):

    global running
    
    cv2.imshow("Frame", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        running = False
        
print(cv2.__version__)
print(cv2.getBuildInformation())

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUTION[0])
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUTION[1])
cap.set(cv2.CAP_PROP_FPS, FRAMERATE)

streamer = cv_stream.OpenCVRTPStreamer(resolution = RESOLUTION)
streamer.start()

receiver = cv_stream.OpenCVRTPReciver(onFrameCallback = showFrame)
receiver.start()

while running:

    ret, frame = cap.read()
    
    if ret:
        streamer.sendFrame(frame)
    else:
        break

# Release everything if job is finished
receiver.stop()
streamer.stop()
cap.release()
cv2.destroyAllWindows()
