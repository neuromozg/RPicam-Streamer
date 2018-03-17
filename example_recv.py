#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import receiver

recv = receiver.StreamReceiver(receiver.FORMAT_MJPEG)
recv.play_pipeline()

#главный цикл программы    
try:
    while True:
        time.sleep(0.1)
except (KeyboardInterrupt, SystemExit):
    print('Ctrl+C pressed')

recv.stop_pipeline()
recv.null_pipeline()
