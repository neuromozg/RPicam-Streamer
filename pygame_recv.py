#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import pygame
import numpy as np

import receiver

IP_ROBOT = '127.0.0.1'
RTP_PORT = 5000


def onFrameCallback(frame):
    frame = np.rot90(frame) #поворачиваем на 90 градусов
    #надо её еще отразить по вертикали
    framePygame = pygame.surfarray.make_surface(frame) #преобразуем в картинку формата Pygame
    screen.blit(framePygame, (0,0)) #отрисовываем картинку на экране
'''
def onFrameCallback(buffer):
    #img = pygame.image.frombuffer(bytearray(buffer.extract_dup(0, buffer.get_size())), 1024, "RGB")
    print(buffer)
'''    
pygame.init()
pygame.mixer.quit()

screen = pygame.display.set_mode((720, 480))  #Экран программы
clock = pygame.time.Clock()
FPS = 30  # This variable will define how many frames we update per second.

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
