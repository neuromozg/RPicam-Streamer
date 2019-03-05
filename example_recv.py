#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import receiver

IP_ROBOT = '127.0.0.1'
RTP_PORT = 5000

def onFrameCallback(frame):
    print(frame)

recv = receiver.StreamReceiver(receiver.VIDEO_MJPEG, onFrameCallback)
recv.setPort(RTP_PORT)
recv.setHost(IP_ROBOT)
recv.play_pipeline()

#recvCV = receiver.StreamReceiver(receiver.VIDEO_MJPEG, (IP_ROBOT, RTP_PORT+50))
#recvCV.play_pipeline()

#главный цикл программы    
try:
    while True:
        time.sleep(0.1)
except (KeyboardInterrupt, SystemExit):
    print('Ctrl+C pressed')

recv.stop_pipeline()
recv.null_pipeline()
