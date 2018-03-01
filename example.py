#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import cv2
import numpy as np
import psutil

import rpicam

#настройки видеопотока
FORMAT = rpicam.FORMAT_H264 #поток H264
#FORMAT = rpicam.FORMAT_MJPG #поток MJPG
WIDTH, HEIGHT = 640, 360
RESOLUTION = (WIDTH, HEIGHT)
FRAMERATE = 30

#сетевые параметры
IP = '173.1.0.95' #IP адрес куда отправляем видео
RTP_PORT = 5000 #порт отправки RTP видео

frameCount = 0 #счетчик кадров
                
def onFrameCallback(frame): #обработчик события 'получен кадр'
    #--------------------------------------
    # тут у нас обрабока кадра средствами OpenCV
    time.sleep(1) #имитируем обработку кадра
    #--------------------------------------
    imgFleName = 'frame%d.jpg' % frameCount
    cv2.imwrite(imgFleName, frame)
    print('Write image file: %s' % imgFleName)
    
    rpiCamStreamer.frameRequest() #отправил запрос на новый кадр

print('Start program')
  
assert rpicam.checkCamera(), 'Raspberry Pi camera not found'
print('Raspberry Pi camera found')

print('OpenCV version: %s' % cv2.__version__)

#видеопоток с камеры
rpiCamStreamer = rpicam.RPiCamStreamer(FORMAT, RESOLUTION, FRAMERATE, (IP, RTP_PORT), onFrameCallback)
#robotCamStreamer.setFlip(False, True) #отражаем кадр (вертикальное отражение, горизонтальное отражение)
rpiCamStreamer.setRotation(180) #поворачиваем кадр на 180 град
rpiCamStreamer.start()

#главный цикл программы
try
    rpiCamStreamer.frameRequest() #отправил запрос на новый кадр, для инициализации работы обработчика кадров   
    while True:
        print ('CPU temp: %.2f°C. CPU use: %.2f%%' % (rpicam.getCPUtemperature(), psutil.cpu_percent()))
        time.sleep(1)
except (KeyboardInterrupt, SystemExit):
    print('Ctrl+C pressed')

#останов трансляции c камеры
robotCamStreamer.stop()    
robotCamStreamer.close()
   
print('End program')
