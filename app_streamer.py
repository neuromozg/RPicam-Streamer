import gi
gi.require_version('Gst','1.0')
from gi.repository import Gst

import sys
import threading
import logging

from common import *

HOST = '127.0.0.1'
RTP_PORT = 5000

class AppSrcStreamer(object):
    def __init__(self, video = VIDEO_MJPEG, resolution = (640, 480), framerate = 30,
                 onFrameCallback = None, useOMX = False, scale = 1):        
        self._host = HOST
        self._port = RTP_PORT
        self._width = resolution[0]
        self._height = resolution[1]
        self._scaleWidth = int(self._width*scale)
        self._scaleHeight = int(self._height*scale)        
        self._needFrame = threading.Event() #флаг, необходимо сформировать OpenCV кадр
        self.playing = False
        self.paused = False
        self._onFrameCallback = None
        if video != VIDEO_RAW:
            if (not onFrameCallback is None) and callable(onFrameCallback):
                self._onFrameCallback = onFrameCallback #обработчик события OpenCV кадр готов
        #инициализация Gstreamer
        Gst.init(None)
        #создаем pipeline
        self._make_pipeline(video, self._width, self._height, framerate, useOMX, scale)

        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message', self._onMessage)
        
        self.ready_pipeline()
        
    def _make_pipeline(self, video, width, height, framerate, useOMX, scale):     
        # Создание GStreamer pipeline
        self.pipeline = Gst.Pipeline()
        self.rtpbin = Gst.ElementFactory.make('rtpbin')
        self.rtpbin.set_property('latency', 200)
        self.rtpbin.set_property('drop-on-latency', True) #отбрасывать устаревшие кадры
        self.rtpbin.set_property('buffer-mode', 4)
        self.rtpbin.set_property('ntp-time-source', 3) #источник времени clock-time
        self.rtpbin.set_property('ntp-sync', True)
        self.rtpbin.set_property('rtcp-sync-send-time', False) 
                
        #настраиваем appsrc
        self.appsrc = Gst.ElementFactory.make('appsrc')
        self.appsrc.set_property('is-live', True)
        if video == VIDEO_H264:
            videoStr = 'video/x-h264'
        elif video == VIDEO_MJPEG:
            videoStr = 'image/jpeg'
        elif video == VIDEO_RAW:
            videoStr = 'video/x-raw,format=RGB'
        capstring = videoStr + ',width=' + str(width) \
            + ',height=' + str(height) + ',framerate=' \
            + str(framerate)+'/1'   
        srccaps = Gst.Caps.from_string(capstring)
        self.appsrc.set_property('caps', srccaps)
        #print('RPi camera GST caps: %s' % capstring)

        if video == VIDEO_RAW:
            self.videoconvertRAW =  Gst.ElementFactory.make('videoconvert')
            self.videoconvertRAWFilter = Gst.ElementFactory.make('capsfilter', 'videoconvertfilter')
            videoconvertCaps = Gst.caps_from_string('video/x-raw,format=I420') # формат данных для преобразования в JPEG
            self.videoconvertRAWFilter.set_property('caps', videoconvertCaps)     
            self.jpegenc = Gst.ElementFactory.make('jpegenc')
            #self.jpegenc = Gst.ElementFactory.make('vaapijpegenc')
            #self.jpegenc = Gst.ElementFactory.make('avenc_ljpeg')
            #jpegencCaps = Gst.Caps.from_string('video/x-raw,format=I420')
            #self.jpegenc.set_property('caps', jpegencCaps)
            
        if video == VIDEO_H264:
            parserName = 'h264parse'
        else:
            parserName = 'jpegparse'
            
        self.parser = Gst.ElementFactory.make(parserName)
        
        if video == VIDEO_H264:
            payloaderName = 'rtph264pay'
            #rtph264pay.set_property('config-interval', 10)
            #payloadType = 96
        else:
            payloaderName = 'rtpjpegpay'
            #payloadType = 26
            
        self.payloader = Gst.ElementFactory.make(payloaderName)
        #payloader.set_property('pt', payloadType)

        #For RTP Video
        self.udpsink_rtpout = Gst.ElementFactory.make('udpsink', 'udpsink_rtpout')
        #self.udpsink_rtpout.set_property('host', self._host)
        #self.udpsink_rtpout.set_property('port', self._port)
        self.udpsink_rtpout.set_property('sync', True)
        self.udpsink_rtpout.set_property('async', False)

        self.udpsink_rtcpout = Gst.ElementFactory.make('udpsink', 'udpsink_rtcpout')
        #self.udpsink_rtcpout.set_property('host', self._host)
        #self.udpsink_rtcpout.set_property('port', self._port + 1)
        self.udpsink_rtcpout.set_property('sync', False)
        self.udpsink_rtcpout.set_property('async', False)

        self.udpsrc_rtcpin = Gst.ElementFactory.make('udpsrc', 'udpsrc_rtcpin')
        srcCaps = Gst.Caps.from_string('application/x-rtcp')
        #self.udpsrc_rtcpin.set_property('port', self._port + 5)
        self.udpsrc_rtcpin.set_property('caps', srcCaps)

        #Задаем IP адресс и порт
        self.setHost(self._host)
        self.setPort(self._port)

        if not self._onFrameCallback is None:
            self.tee = Gst.ElementFactory.make('tee')
            self.rtpQueue = Gst.ElementFactory.make('queue', 'rtp_queue')
            self.frameQueue = Gst.ElementFactory.make('queue', 'frame_queue')
        
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
            self.decoder = Gst.ElementFactory.make(decoderName)
            
            self.videoconvert = Gst.ElementFactory.make('videoconvert')
            
            if scale != 1:
                self.videoscale = Gst.ElementFactory.make('videoscale')
                self.videoscaleFilter = Gst.ElementFactory.make('capsfilter', 'scalefilter')
                videoscaleCaps = Gst.caps_from_string('video/x-raw, width=%d, height=%d' % (self._scaleWidth, self._scaleHeight)) # формат данных после изменения размера
                self.videoscaleFilter.set_property('caps', videoscaleCaps)       
        
            ### создаем свой sink для перевода из GST в CV
            self.appsink = Gst.ElementFactory.make('appsink')

            cvCaps = Gst.caps_from_string('video/x-raw, format=RGB') # формат принимаемых данных
            self.appsink.set_property('caps', cvCaps)
            self.appsink.set_property('sync', False)
            #appsink.set_property('async', False)
            self.appsink.set_property('drop', True)
            self.appsink.set_property('max-buffers', 5)
            self.appsink.set_property('emit-signals', True)
            self.appsink.connect('new-sample', self._newSample)

        # добавляем все элементы в pipeline
        elemList = [self.appsrc, self.rtpbin, self.parser, self.payloader, self.udpsink_rtpout,
                    self.udpsink_rtcpout, self.udpsrc_rtcpin]

        if video == VIDEO_RAW:
            elemList.extend([self.videoconvertRAW, self.videoconvertRAWFilter, self.jpegenc])
        
        if not self._onFrameCallback is None:
            elemList.extend([self.tee, self.rtpQueue, self.frameQueue, self.decoder, self.videoconvert, self.appsink])
            if scale != 1:
                elemList.extend([self.videoscale, self.videoscaleFilter])
            
        for elem in elemList:
            if elem is None:
                logging.critical('GST elements could not be null')
                sys.exit(1)
            self.pipeline.add(elem)

        #соединяем элементы
        if video == VIDEO_RAW:
            ret = self.appsrc.link(self.videoconvertRAW)
            ret = ret and self.videoconvertRAW.link(self.videoconvertRAWFilter)
            ret = ret and self.videoconvertRAWFilter.link(self.jpegenc)
            ret = ret and self.jpegenc.link(self.parser)        
        else:
            ret = self.appsrc.link(self.parser)

        #соединяем элементы rtpbin
        ret = ret and self.payloader.link_pads('src', self.rtpbin, 'send_rtp_sink_0')
        ret = ret and self.rtpbin.link_pads('send_rtp_src_0', self.udpsink_rtpout, 'sink')
        ret = ret and self.rtpbin.link_pads('send_rtcp_src_0', self.udpsink_rtcpout, 'sink')
        ret = ret and self.udpsrc_rtcpin.link_pads('src', self.rtpbin, 'recv_rtcp_sink_0')

        if self._onFrameCallback is None: #трансляция без onFrameCallback, т.е. создаем одну ветку
            ret = ret and self.parser.link(self.payloader)
            
        else: #трансляция с передачей кадров в onFrameCallback, создаем две ветки
            ret = ret and self.parser.link(self.tee)
            
            #1-я ветка RTP
            ret = ret and self.rtpQueue.link(self.payloader)

            #2-я ветка onFrame
            ret = ret and self.frameQueue.link(self.decoder)
            if scale != 1:        
                ret = ret and self.decoder.link(self.videoscale)
                ret = ret and self.videoscale.link(self.videoscaleFilter)
                ret = ret and self.videoscaleFilter.link(self.videoconvert)
            else:
                ret = ret and self.decoder.link(self.videoconvert)

            ret = ret and self.videoconvert.link(self.appsink)
            
            # подключаем tee к rtpQueue
            teeSrcPadTemplate = self.tee.get_pad_template('src_%u')
        
            rtpTeePad = self.tee.request_pad(teeSrcPadTemplate, None, None)
            rtpQueuePad = self.rtpQueue.get_static_pad('sink')
            ret = ret and (rtpTeePad.link(rtpQueuePad) == Gst.PadLinkReturn.OK)

            # подключаем tee к frameQueue
            frameTeePad = self.tee.request_pad(teeSrcPadTemplate, None, None)
            frameQueuePad = self.frameQueue.get_static_pad('sink')        
            ret = ret and (frameTeePad.link(frameQueuePad) == Gst.PadLinkReturn.OK)

        if not ret:
            logging.critical('GST elements could not be linked')
            sys.exit(1)

    def setHost(self, host):
        self._host = host
        self.udpsink_rtpout.set_property('host', host)
        self.udpsink_rtcpout.set_property('host', host)

    def setPort(self, port):
        self._port = port
        self.udpsink_rtpout.set_property('port', port)
        self.udpsink_rtcpout.set_property('port', port + 1)
        self.udpsrc_rtcpin.set_property('port', port + 5)

    def _newSample(self, sink):     # callback функция, вызываемая при каждом приходящем кадре
        if self._needFrame.is_set(): #если выставлен флаг нужен кадр
            self._needFrame.clear() #сбрасываем флаг
            sample = sink.emit('pull-sample')
            sampleBuff = sample.get_buffer()

            data = sampleBuff.extract_dup(0, sampleBuff.get_size()) # extract data stream as string
                        
            #вызываем обработчик в качестве параметра передаем массив данных, ширина и высота кадра
            #формат цвета RGB
            self._onFrameCallback(data, self._scaleWidth, self._scaleHeight) 

        return Gst.FlowReturn.OK
            
    def _onMessage(self, bus, message):
        #print('Message: %s' % str(message.type))
        t = message.type
        if t == Gst.MessageType.EOS:
            logging.info('Received EOS-Signal')
            self.stop_pipeline()
        elif t == Gst.MessageType.ERROR:
            error, debug = message.parse_error()
            logging.error('Received Error-Signal #%u: %s', error.code, debug)
            self.null_pipeline()
        #else:
        #    print('Message: %s' % str(t))

    def play_pipeline(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        logging.info('GST pipeline PLAYING')
        logging.info('Streaming RTP on %s:%d', self._host, self._port)

    def stop_pipeline(self):
        self.pause_pipeline()
        self.ready_pipeline()
        
    def ready_pipeline(self):
        self.pipeline.set_state(Gst.State.READY)
        logging.info('GST pipeline READY')

    def pause_pipeline(self):
        self.pipeline.set_state(Gst.State.PAUSED)
        logging.info('GST pipeline PAUSED')
        
    def null_pipeline(self):
        self.pipeline.set_state(Gst.State.NULL)
        logging.info('GST pipeline NULL')

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
