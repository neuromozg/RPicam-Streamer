import picamera
import logging
import app_streamer
from common import *

class RPiCamStreamer(object):
    def __init__(self, video = VIDEO_MJPEG, resolution = (640, 480), framerate = 30,
                 onFrameCallback = None, scale = 1):
        self._videoFormat = 'h264'
        self._quality = 20
        self._bitrate = 1000000
        if video:
            self._videoFormat = 'mjpeg'
            self._quality = 60
            self._bitrate = 8000000
        self.camera = picamera.PiCamera()
        self.camera.resolution = resolution
        self.camera.framerate = framerate
        self.camera.led = False #выключаем светодиод на камере
        self._stream = app_streamer.AppSrcStreamer(video, resolution,
            framerate, onFrameCallback, True, scale)
        
    def init(self):
        pass

    def start(self):
        logging.info('Start RPi camera recording: %s:%dx%d, framerate=%d, bitrate=%d, quality=%d', 
                self._videoFormat, self.camera.resolution[0], self.camera.resolution[1],
                self.camera.framerate, self._bitrate, self._quality)
        self._stream.play_pipeline() #запускаем RTP трансляцию
        #запускаем захват видеопотока с камеры
        self.camera.start_recording(self._stream, self._videoFormat, bitrate=self._bitrate, quality=self._quality)
        self.camera.led = True #включаем светодиод на камере

    def stop(self):
        if self.camera.recording:
            self.camera.stop_recording()
            self.camera.led = False #выключаем светодиод на камере
            logging.info('Stop RPi camera recording')

    def close(self):
        self._stream.null_pipeline() #закрываем трансляцию
        if not self.camera.closed:
            self.camera.close()

    def frameRequest(self): #выставляем флаг запрос кадра, возвращает True, если флаг выставлен
        return self._stream.frameRequest()

    def setFlip(self, hflip, vflip):
        self.camera.hflip = hflip
        self.camera.vflip = vflip
        
    def setRotation(self, rotation):
        self.camera.rotation = rotation
        
    def setHost(self, host):
        self._stream.setHost(host)

    def setPort(self, port):
        self._stream.setPort(port)
