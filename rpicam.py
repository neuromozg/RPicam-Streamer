import gi
gi.require_version('Gst','1.0')
from gi.repository import Gst

import picamera
import numpy as np
import sys
import psutil
import threading

from common import *

RTP_PORT = 5000

class AppSrcStreamer(object):
    def __init__(self, video = VIDEO_MJPEG, resolution = (640, 480), framerate = 30, host = ('localhost', RTP_PORT),
                 onFrameCallback = None, useOMX = True, scale = 1):        
        self._host = host
        self._width = resolution[0]
        self._height = resolution[1]
        self._scaleWidth = int(self._width*scale)
        self._scaleHeight = int(self._height*scale)        
        self._needFrame = threading.Event() #флаг, необходимо сформировать OpenCV кадр
        self.playing = False
        self.paused = False
        self._onFrameCallback = None
        if (not onFrameCallback is None) and callable(onFrameCallback):
            self._onFrameCallback = onFrameCallback #обработчик события OpenCV кадр готов
        #инициализация Gstreamer
        Gst.init(None)
        #создаем pipeline
        self._make_pipeline(video, self._width, self._height, framerate, host, useOMX, scale)

        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message', self._onMessage)
        
        self.pipeline.set_state(Gst.State.READY)
        print('GST pipeline READY')
        
    def _make_pipeline(self, video, width, height, framerate, host, useOMX, scale):     
        # Создание GStreamer pipeline
        self.pipeline = Gst.Pipeline()
        rtpbin = Gst.ElementFactory.make('rtpbin')
        rtpbin.set_property('latency', 200)
        rtpbin.set_property('drop-on-latency', True) #отбрасывать устаревшие кадры
        rtpbin.set_property('buffer-mode', 4)
        rtpbin.set_property('ntp-time-source', 3) #источник времени clock-time
        rtpbin.set_property('ntp-sync', True)
        rtpbin.set_property('rtcp-sync-send-time', False) 
                
        #настраиваем appsrc
        self.appsrc = Gst.ElementFactory.make('appsrc')
        self.appsrc.set_property('is-live', True)
        if video == VIDEO_H264:
            videoStr = 'video/x-h264'
        elif video == VIDEO_MJPEG:
            videoStr = 'image/jpeg'
        elif video == VIDEO_RAW:
            videoStr = 'video/x-raw,format=BGR'
        capstring = videoStr + ',width=' + str(width) \
            + ',height=' + str(height) + ',framerate=' \
            + str(framerate)+'/1'   
        srccaps = Gst.Caps.from_string(capstring)
        self.appsrc.set_property('caps', srccaps)
        #print('RPi camera GST caps: %s' % capstring)
            
        if video == VIDEO_H264:
            parserName = 'h264parse'
        else:
            parserName = 'jpegparse'
            
        parser = Gst.ElementFactory.make(parserName)
        
        if video == VIDEO_H264:
            payloaderName = 'rtph264pay'
            #rtph264pay.set_property('config-interval', 10)
            #payloadType = 96
        else:
            payloaderName = 'rtpjpegpay'
            #payloadType = 26
            
        payloader = Gst.ElementFactory.make(payloaderName)
        #payloader.set_property('pt', payloadType)

        #For RTP Video
        udpsink_rtpout = Gst.ElementFactory.make('udpsink', 'udpsink_rtpout')
        udpsink_rtpout.set_property('host', host[0])
        udpsink_rtpout.set_property('port', host[1])
        udpsink_rtpout.set_property('sync', True)
        udpsink_rtpout.set_property('async', False)

        udpsink_rtcpout = Gst.ElementFactory.make('udpsink', 'udpsink_rtcpout')
        udpsink_rtcpout.set_property('host', host[0])
        udpsink_rtcpout.set_property('port', host[1] + 1)
        udpsink_rtcpout.set_property('sync', False)
        udpsink_rtcpout.set_property('async', False)

        srcCaps = Gst.Caps.from_string('application/x-rtcp')
        udpsrc_rtcpin = Gst.ElementFactory.make('udpsrc', 'udpsrc_rtcpin')
        udpsrc_rtcpin.set_property('port', host[1] + 5)
        udpsrc_rtcpin.set_property('caps', srcCaps)
        

        if not self._onFrameCallback is None:
            tee = Gst.ElementFactory.make('tee')
            rtpQueue = Gst.ElementFactory.make('queue', 'rtp_queue')
            frameQueue = Gst.ElementFactory.make('queue', 'frame_queue')
        
            if video == VIDEO_H264: 
                if useOMX:
                    decoderName = 'omxh264dec' #отлично работает загрузка ЦП 200%
                else:
                    decoderName = 'avdec_h264' #хреново работает загрузка ЦП 120% 
                    #decoder = Gst.ElementFactory.make('avdec_h264_mmal') #не заработал
            else:
                if useOMX:
                    decoderName = 'omxmjpegdec' #
                else:
                    decoderName = 'avdec_mjpeg' #
                    #decoder = Gst.ElementFactory.make('jpegdec') #
            decoder = Gst.ElementFactory.make(decoderName)
            
            videoconvert = Gst.ElementFactory.make('videoconvert')
            
            if scale != 1:
                videoscale = Gst.ElementFactory.make('videoscale')
                videoscaleFilter = Gst.ElementFactory.make('capsfilter', 'scalefilter')
                videoscaleCaps = Gst.caps_from_string('video/x-raw, width=%d, height=%d' % (self._scaleWidth, self._scaleHeight)) # формат данных после изменения размера
                videoscaleFilter.set_property('caps', videoscaleCaps)       
        
            ### создаем свой sink для перевода из GST в CV
            appsink = Gst.ElementFactory.make('appsink')

            cvCaps = Gst.caps_from_string('video/x-raw, format=BGR') # формат принимаемых данных
            appsink.set_property('caps', cvCaps)
            appsink.set_property('sync', True)
            #appsink.set_property('async', False)
            appsink.set_property('drop', True)
            appsink.set_property('max-buffers', 5)
            appsink.set_property('emit-signals', True)
            appsink.connect('new-sample', self._newSample, appsink)

        # добавляем все элементы в pipeline
        elemList = [self.appsrc, rtpbin, parser, payloader, udpsink_rtpout,
                    udpsink_rtcpout, udpsrc_rtcpin]
        if not self._onFrameCallback is None:
            elemList.extend([tee, rtpQueue, frameQueue, decoder, videoconvert, appsink])
            if scale != 1:
                elemList.extend([videoscale, videoscaleFilter])
            
        for elem in elemList:
            self.pipeline.add(elem)

        #соединяем элементы
        ret = self.appsrc.link(parser)

        #соединяем элементы rtpbin
        ret = ret and payloader.link_pads('src', rtpbin, 'send_rtp_sink_0')
        ret = ret and rtpbin.link_pads('send_rtp_src_0', udpsink_rtpout, 'sink')
        ret = ret and rtpbin.link_pads('send_rtcp_src_0', udpsink_rtcpout, 'sink')
        ret = ret and udpsrc_rtcpin.link_pads('src', rtpbin, 'recv_rtcp_sink_0')

        if self._onFrameCallback is None: #трансляция без onFrameCallback, т.е. создаем одну ветку
            ret = ret and parser.link(payloader)
            
        else: #трансляция с передачей кадров в onFrameCallback, создаем две ветки
            ret = ret and parser.link(tee)
            
            #1-я ветка RTP
            ret = ret and rtpQueue.link(payloader)

            #2-я ветка onFrame
            ret = ret and frameQueue.link(decoder)
            if scale != 1:        
                ret = ret and decoder.link(videoscale)
                ret = ret and videoscale.link(videoscaleFilter)
                ret = ret and videoscaleFilter.link(videoconvert)
            else:
                ret = ret and decoder.link(videoconvert)

            ret = ret and videoconvert.link(appsink)
            
            # подключаем tee к rtpQueue
            teeSrcPadTemplate = tee.get_pad_template('src_%u')
        
            rtpTeePad = tee.request_pad(teeSrcPadTemplate, None, None)
            rtpQueuePad = rtpQueue.get_static_pad('sink')
            ret = ret and (rtpTeePad.link(rtpQueuePad) == Gst.PadLinkReturn.OK)

            # подключаем tee к frameQueue
            frameTeePad = tee.request_pad(teeSrcPadTemplate, None, None)
            frameQueuePad = frameQueue.get_static_pad('sink')        
            ret = ret and (frameTeePad.link(frameQueuePad) == Gst.PadLinkReturn.OK)

        if not ret:
            print('ERROR: Elements could not be linked')
            sys.exit(1)

    def _newSample(self, sink, data):     # callback функция, вызываемая при каждом приходящем кадре
        if self._needFrame.is_set(): #если выставлен флаг нужен кадр
            self._needFrame.clear() #сбрасываем флаг
            sample = sink.emit('pull-sample')
            sampleBuff = sample.get_buffer()

            #создаем массив cvFrame в формате opencv
            cvFrame = np.ndarray(
                (self._scaleHeight, self._scaleWidth, 3),
                buffer = sampleBuff.extract_dup(0, sampleBuff.get_size()), dtype = np.uint8)
            
            self._onFrameCallback(cvFrame) #вызываем обработчик в качестве параметра передаем cv2 кадр

        return Gst.FlowReturn.OK
            
    def _onMessage(self, bus, message):
        #print('Message: %s' % str(message.type))
        t = message.type
        if t == Gst.MessageType.EOS:
            print('Received EOS-Signal')
            self.stop_pipeline()
        elif t == Gst.MessageType.ERROR:
            print('Received Error-Signal')
            error, debug = message.parse_error()
            print('Error-Details: #%u: %s' % (error.code, debug))
            self.null_pipeline()
        #else:
        #    print('Message: %s' % str(t))

    def play_pipeline(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        print('GST pipeline PLAYING')
        print('Streaming RTP on %s:%d' % (self._host[0], self._host[1]))

    def stop_pipeline(self):
        self.pause_pipeline()
        self.ready_pipeline()
        
    def ready_pipeline(self):
        self.pipeline.set_state(Gst.State.READY)
        print('GST pipeline READY')

    def pause_pipeline(self):
        self.pipeline.set_state(Gst.State.PAUSED)
        print('GST pipeline PAUSED')
        
    def null_pipeline(self):
        print('GST pipeline NULL')
        self.pipeline.set_state(Gst.State.NULL)

    def write(self, s):
        gstBuff = Gst.Buffer.new_wrapped(s)
        if not (gstBuff is None):
            self.appsrc.emit('push-buffer', gstBuff)

    def flush(self):
        self.stop_pipeline()

    def frameRequest(self): #выставляем флаг запрос кадра, возвращает True, если запрос кадра удался
        if not self._needFrame.is_set():
            self._needFrame.set()
            return True
        return False

class RPiCamStreamer(object):
    def __init__(self, video = VIDEO_MJPEG, resolution = (640, 480), framerate = 30, host = ('localhost', RTP_PORT),
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
        self._stream = AppSrcStreamer(video, resolution,
            framerate, host, onFrameCallback, True, scale)
        
    def init(self):
        pass

    def start(self):
        print('Start RPi camera recording: %s:%dx%d, framerate=%d, bitrate=%d, quality=%d'
              % (self._videoFormat, self.camera.resolution[0], self.camera.resolution[1],
                 self.camera.framerate, self._bitrate, self._quality))
        self._stream.play_pipeline() #запускаем RTP трансляцию
        #запускаем захват пока с камеры
        self.camera.start_recording(self._stream, self._videoFormat, bitrate=self._bitrate, quality=self._quality)

    def stop(self):
        print('Stop RPi camera recording')
        self.camera.stop_recording()

    def close(self):
        self._stream.null_pipeline() #закрываем трансляцию
        self.camera.close()

    def frameRequest(self): #выставляем флаг запрос кадра, возвращает True, если флаг выставлен
        return self._stream.frameRequest()

    def setFlip(self, hflip, vflip):
        self.camera.hflip = hflip
        self.camera.vflip = vflip
        
    def setRotation(self, rotation):
        self.camera.rotation = rotation
