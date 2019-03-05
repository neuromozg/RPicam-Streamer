#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import pygame

import receiver

IP_ROBOT = '127.0.0.1'
RTP_PORT = 5000
FPS = 30  # количество кадров в секунду у окна Pygame


def onFrameCallback(data, width, height):
    #преобразуем массив байт в изображение
    frame = pygame.image.frombuffer(data, (width, height), 'RGB')
    screen.blit(frame, (0,0)) #отрисовываем картинку на экране
  
pygame.init()
pygame.mixer.quit()

screen = pygame.display.set_mode((640, 480))  #Создаем окно вывода программы
clock = pygame.time.Clock() #для формирования задержки

#создаем приемник видеопотока
recv = receiver.StreamReceiver(receiver.VIDEO_MJPEG, onFrameCallback)
#recv = receiver.StreamReceiver(receiver.VIDEO_MJPEG)
#задаем IP адрес и порт
recv.setHost(IP_ROBOT)
recv.setPort(RTP_PORT)

#запускаем прием видепотока
recv.play_pipeline()

running = True

#главный цикл программы
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:  # The user pressed the close button in the top corner of the window.
            running = False

    #перерисовываем экран screen        
    pygame.display.update()
    clock.tick(FPS)

#останавливаем прием видеопотока
recv.stop_pipeline()
recv.null_pipeline()

pygame.quit()
