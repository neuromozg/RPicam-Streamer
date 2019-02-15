#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import pygame

import receiver

IP_ROBOT = '127.0.0.1'
RTP_PORT = 5000
FPS = 30  # количество кадров в секунду у окна Pygame


def onFrameCallback(data, width, height):
    frame = pygame.image.frombuffer(data, (width, height), 'RGB') #преобразуем массив байт в изображение
    screen.blit(frame, (0,0)) #отрисовываем картинку на экране
  
pygame.init()
pygame.mixer.quit()

screen = pygame.display.set_mode((640, 480))  #Создаем окно вывода программы
clock = pygame.time.Clock() #для формирования задержки

recv = receiver.StreamReceiver(receiver.VIDEO_MJPEG, (IP_ROBOT, RTP_PORT), onFrameCallback)
#recv = receiver.StreamReceiver(receiver.VIDEO_MJPEG, (IP_ROBOT, RTP_PORT))
recv.play_pipeline()

running = True

#главный цикл программы
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:  # The user pressed the close button in the top corner of the window.
            running = False
            
    pygame.display.update()
    clock.tick(FPS)

recv.stop_pipeline()
recv.null_pipeline()

pygame.quit()
