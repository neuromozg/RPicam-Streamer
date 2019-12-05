#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import cv2
import numpy as np
import psutil
import threading

import rpicam

#настройки видеопотока
#FORMAT = rpicam.VIDEO_H264 #поток H264
FORMAT = rpicam.VIDEO_MJPEG #поток MJPEG
WIDTH, HEIGHT = 640, 360
RESOLUTION = (WIDTH, HEIGHT)
FRAMERATE = 30

#сетевые параметры
IP = '10.1.0.95' #IP адрес куда отправляем видео
RTP_PORT = 5000 #порт отправки RTP видео

#поток для обработки кадров
#параметр 
class FrameHandlerThread(threading.Thread):
    
    def __init__(self, stream):
        super(FrameHandlerThread, self).__init__()
        self.daemon = True
        self.rpiCamStream = stream
        self._frame = None
        self._frameCount = 0
        self._stopped = threading.Event() #событие для остановки потока
        self._newFrameEvent = threading.Event() #событие для контроля поступления кадров
        self.sensivity = 60 #чувствительность алгоритма
        
    def run(self):
        print('Frame handler started')
        while not self._stopped.is_set():
            if self.rpiCamStream.frameRequest(): #отправил запрос на новый кадр
                self._newFrameEvent.wait() #если запрос отправлен успешно, ждем появления нового кадра
                if not (self._frame is None): #если получен кадр
                
                    #--------------------------------------
                    #ищем линнию
                    lineFound, direction = self.lineDetect(self._frame)
                    if lineFound:
                        print('direction: %.2f' % direction)
                    
                    #--------------------------------------
                    
                self._newFrameEvent.clear() #сбрасываем событие

        print('Frame handler stopped')

    def stop(self): #остановка потока
        self._stopped.set()
        if not self._newFrameEvent.is_set(): #если кадр не обрабатывается
            self._frame = None
            self._newFrameEvent.set() 
        self.join() #ждем завершения работы потока

    def setFrame(self, frame): #задание нового кадра для обработки
        if not self._newFrameEvent.is_set(): #если обработчик готов принять новый кадр
            self._frame = frame
            self._newFrameEvent.set() #задали событие
            return True
        return False
    
    def lineDetect(self, frame): #следование по линии

        height, width = frame.shape[:2]
        
        # Crop the image
        #crop_img = frame[60:120, 0:160] #обрезаем по вертикали
 
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
     
        # Gaussian blur
        blur = cv2.GaussianBlur(gray, (5,5), 0)
     
        # Color thresholding
        ret, thresh = cv2.threshold(blur, self.sensivity, 255, cv2.THRESH_BINARY_INV)

        # Erode and dilate to remove accidental line detections
        mask = cv2.erode(thresh, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
     
        # Find the contours of the frame
        contours, _ = cv2.findContours(mask.copy(), 1, cv2.CHAIN_APPROX_NONE)

        direction = 0.0
        lineFound = False
        
        # Find the biggest contour (if detected)
        if len(contours) > 0:
            c = max(contours, key=cv2.contourArea)
            M = cv2.moments(c)
     
            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])
     
            cv2.line(frame, (cx,0), (cx,720), (255,0,0), 1)
            cv2.line(frame, (0,cy), (1280,cy), (255,0,0), 1)
     
            cv2.drawContours(frame, contours, -1, (0,255,0), 1)
     
            direction = cx/(width/2)-1  # преобразуем координаты от 0 до ширина кадра -> от -1 до 1
            lineFound = True
            
        return lineFound, direction
         
def onFrameCallback(data, width, height): #обработчик события 'получен кадр'
    #создаем массив cvFrame в формате opencv
    rgbFrame = np.ndarray((height, width, 3), buffer = data, dtype = np.uint8)
    # Converts to BGR format for OpenCV
    bgrFrame = cv2.cvtColor(rgbFrame, cv2.COLOR_RGB2BGR)
    frameHandlerThread.setFrame(bgrFrame) #задали новый кадр

print('Start program')

#проверка наличия камеры в системе  
assert rpicam.checkCamera(), 'Raspberry Pi camera not found'
print('Raspberry Pi camera found')

print('OpenCV version: %s' % cv2.__version__)

#создаем трансляцию с камеры (тип потока h264/mjpeg, разрешение, частота кадров, функция обрабтчик кадров)
rpiCamStreamer = rpicam.RPiCamStreamer(FORMAT, RESOLUTION, FRAMERATE, onFrameCallback)
#задаем порт и хост куда шлем видео
rpiCamStreamer.setPort(RTP_PORT)
rpiCamStreamer.setHost(IP)
#robotCamStreamer.setFlip(False, True) #отражаем кадр (вертикальное отражение, горизонтальное отражение)
rpiCamStreamer.setRotation(180) #поворачиваем кадр на 180 град, доступные значения 90, 180, 270
rpiCamStreamer.start() #запускаем трансляцию

#поток обработки кадров    
frameHandlerThread = FrameHandlerThread(rpiCamStreamer)
frameHandlerThread.start() #запускаем обработку

#главный цикл программы
try:
    while True:
        print ('CPU temp: %.2f°C. CPU use: %.2f%%' % (rpicam.getCPUtemperature(), psutil.cpu_percent()))
        time.sleep(1)
except (KeyboardInterrupt, SystemExit):
    print('Ctrl+C pressed')

#останавливаем обработку кадров
frameHandlerThread.stop()

#останов трансляции c камеры
rpiCamStreamer.stop()    
rpiCamStreamer.close()
   
print('End program')
