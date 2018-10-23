#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import time
from cv_stream import OpenCVRTPStreamer, OpenCVRTPReciver

RTP_PORT = 5000
HOST = '127.0.0.1'
FRAMERATE = 30.0
RESOLUTION = (640, 480)

running = True
        
def showFrame(frame):

    global running
    
    cv2.imshow("Frame", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        running = False
        
print(cv2.__version__)
print(cv2.getBuildInformation())

cap = cv2.VideoCapture(0)

streamer = OpenCVRTPStreamer()
streamer.start()

receiver = OpenCVRTPReciver(onFrameCallback = showFrame)
receiver.start()

while running:

    ret, frame = cap.read()
    
    if ret:
        time.sleep(0.1) # имитация обработки
        streamer.sendFrame(frame)
    else:
        break

# Release everything if job is finished
receiver.stop()
streamer.stop()
cap.release()
cv2.destroyAllWindows()
