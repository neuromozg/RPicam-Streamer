#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import cv2
import numpy as np
import psutil
import threading

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

#поток обработки кадров
#параметр 
class FrameHandler(threading.Thread):
    
    def __init__(self, stream):
        super(FrameHandler, self).__init__()
        self.daemon = True
        self.rpiCamStream = stream
        self._frame = None
        self._frameCount = 0
        self._stopped = threading.Event() #событие для остановки потока
        self._newFrameEvent = threading.Event() #событие для контроля поступления кадров
        
    def run(self):
        print('Frame handler started')
        while not self._stopped.is_set():
            self.rpiCamStream.frameRequest() #отправил запрос на новый кадр
            self._newFrameEvent.wait() #ждем появления нового кадра
            if not (self._frame is None): #если кадр есть
                
                #--------------------------------------
                # тут у нас обрабока кадра self._frame средствами OpenCV
                time.sleep(2) #имитируем обработку кадра
                imgFleName = 'frame%d.jpg' % self._frameCount
                #cv2.imwrite(imgFleName, self._frame) #сохраняем полученный кадр в файл
                print('Write image file: %s' % imgFleName)
                self._frameCount += 1
                #--------------------------------------
                
            self._newFrameEvent.clear() #сбрасываем событие
            
        print('Frame handler stopped')

    def stop(self): #остановка потока
        self._stopped.set()
        if not self._newFrameEvent.is_set(): #если кадр не обрабатывается
            self._frame = None
            self._newFrameEvent.set() 
        self.join()

    def setFrame(self, frame): #задание нового кадра для обработки
        if not self._newFrameEvent.is_set(): #если обработчик готов принять новый кадр
            self._frame = frame
            self._newFrameEvent.set() #задали событие
        return self._newFrameEvent.is_set()

                
def onFrameCallback(frame): #обработчик события 'получен кадр'
    #print('New frame')
    frameHandler.setFrame(frame) #задали новый кадр

print('Start program')

#проверка наличия камеры в системе  
assert rpicam.checkCamera(), 'Raspberry Pi camera not found'
print('Raspberry Pi camera found')

print('OpenCV version: %s' % cv2.__version__)

#создаем трансляцию с камеры (тип потока h264/mjpeg, разрешение, частота кадров, хост куда шлем, функция обрабтчик кадров)
rpiCamStreamer = rpicam.RPiCamStreamer(FORMAT, RESOLUTION, FRAMERATE, (IP, RTP_PORT), onFrameCallback)
#robotCamStreamer.setFlip(False, True) #отражаем кадр (вертикальное отражение, горизонтальное отражение)
rpiCamStreamer.setRotation(180) #поворачиваем кадр на 180 град, доступные значения 90, 180, 270
rpiCamStreamer.start() #запускаем трансляцию

#обработчик кадров    
frameHandler = FrameHandler(rpiCamStreamer)
frameHandler.start()

#главный цикл программы
try:
    rpiCamStreamer.frameRequest() #отправил запрос на новый кадр, для инициализации работы обработчика кадров   
    while True:
        print ('CPU temp: %.2f°C. CPU use: %.2f%%' % (rpicam.getCPUtemperature(), psutil.cpu_percent()))
        time.sleep(1)
except (KeyboardInterrupt, SystemExit):
    print('Ctrl+C pressed')

#останавливаем обработчик кадров
frameHandler.stop()

#останов трансляции c камеры
rpiCamStreamer.stop()    
rpiCamStreamer.close()
   
print('End program')
