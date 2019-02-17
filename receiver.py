import gi
gi.require_version('Gst','1.0')
from gi.repository import Gst
import logging

from common import *

RTP_PORT = 5000
HOST = '127.0.0.1'

class StreamReceiver(object):
    def __init__(self, video = VIDEO_H264, onFrameCallback = None):
        self._host = HOST
        self._port = RTP_PORT
        self._onFrameCallback = None
        if (not onFrameCallback is None) and callable(onFrameCallback):
            self._onFrameCallback = onFrameCallback #обработчик события получен кадр
        #инициализация Gstreamer
        Gst.init(None)
        #создаем pipeline
        self.make_pipeline(video)

        #подключаем обработчик сообщений
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message', self._onMessage)

        #запускаем pipeline
        self.ready_pipeline()
        
    def make_pipeline(self, video):
        # Создание GStreamer pipeline
        self.pipeline = Gst.Pipeline()

        #rtpbin
        self.rtpbin = Gst.ElementFactory.make('rtpbin')
        #rtpbin.set_property('autoremove', True)
        self.rtpbin.set_property('latency', 200)        
        self.rtpbin.set_property('drop-on-latency', True) #отбрасывать устаревшие кадры
        self.rtpbin.set_property('buffer-mode', 4)
        #self.rtpbin.set_property('ntp-time-source', 3)
        #self.rtpbin.set_property('ntp-sync', True)
        #self.rtpbin.set_property('rtcp-sync-send-time', False)
        
        #RTP Video
        formatStr = 'H264'
        payloadType = 96
        if video:
            videoStr = 'JPEG'
            payloadType = 26
        
        self.udpsrc_rtpin = Gst.ElementFactory.make('udpsrc', 'udpsrc_rtpin')
        #self.udpsrc_rtpin.set_property('port', RTP_PORT)
        srcCaps = Gst.Caps.from_string('application/x-rtp, media=video, clock-rate=90000, encoding-name=%s, payload=%d' % (formatStr, payloadType))
        self.udpsrc_rtpin.set_property('caps', srcCaps)

        self.udpsrc_rtcpin = Gst.ElementFactory.make('udpsrc', 'udpsrc_rtcpin')
        #self.udpsrc_rtcpin.set_property('port', RTP_PORT + 1)
        srcCaps = Gst.Caps.from_string('application/x-rtcp')
        self.udpsrc_rtcpin.set_property('caps', srcCaps)

        self.udpsink_rtcpout = Gst.ElementFactory.make('udpsink', 'udpsink_rtcpout')
        #self.udpsink_rtcpout.set_property('host', HOST)
        #self.udpsink_rtcpout.set_property('port', RTP_PORT + 5)
        self.udpsink_rtcpout.set_property('sync', True)
        self.udpsink_rtcpout.set_property('async', False)

        #Задаем IP адресс и порт
        self.setHost(self._host)
        self.setPort(self._port)

        depayName = 'rtph264depay'
        decoderName = 'avdec_h264' #хреново работает загрузка ЦП 120% 
        #decoder = Gst.ElementFactory.make('avdec_h264_mmal') #не заработал
        if video:
            depayName = 'rtpjpegdepay'
            #decoderName = 'avdec_mjpeg' #
            decoderName = 'jpegdec' #

        #depayloader
        self.depay = Gst.ElementFactory.make(depayName)

        #decoder
        self.decoder = Gst.ElementFactory.make(decoderName)
        self.videorate = Gst.ElementFactory.make('videorate')

        #sink
        if not self._onFrameCallback is None:
            self.videoconvert = Gst.ElementFactory.make('videoconvert')
            
            self.sink = Gst.ElementFactory.make('appsink')
            sinkCaps = Gst.caps_from_string('video/x-raw, format=RGB') # формат принимаемых данных
            self.sink.set_property('caps', sinkCaps)
            self.sink.set_property('sync', False)
            #self.sink.set_property('async', False)
            self.sink.set_property('drop', True)
            self.sink.set_property('max-buffers', 5)
            self.sink.set_property('emit-signals', True)
            self.sink.connect('new-sample', self._newSample)
        else:
            #sink = Gst.ElementFactory.make('autovideosink')
            self.sink = Gst.ElementFactory.make('fpsdisplaysink')        
            self.sink.set_property('sync', False)

        # добавляем все элементы в pipeline
        elemList = [self.rtpbin, self.depay, self.decoder, self.videorate, self.sink, self.udpsrc_rtpin,
                    self.udpsrc_rtcpin, self.udpsink_rtcpout]

        if not self._onFrameCallback is None:
             elemList.extend([self.videoconvert]) # добавляем videoconvert в pipeline
            
        for elem in elemList:
            if elem is None:
                logging.critical('GST elements could not be null')
                sys.exit(1)
            self.pipeline.add(elem)

        #соединяем элементы
        ret = self.depay.link(self.decoder)
        ret = ret and self.decoder.link(self.videorate)
        
        if not self._onFrameCallback is None:
            ret = ret and self.videorate.link(self.videoconvert)
            ret = ret and self.videoconvert.link(self.sink)           
        else:
            ret = ret and self.videorate.link(self.sink)
        
        #соединяем элементы rtpbin

        def PadAdded(rtpbin, new_pad, gstElem):
            sinkPad = Gst.Element.get_static_pad(gstElem, 'sink')
            res = (Gst.Pad.link(new_pad, sinkPad) == Gst.PadLinkReturn.OK)
            #if res:
                #print('SrcPad: %s linked SinkPad: %s' % (new_pad, sinkPad))

        def PadLink(src, name):
            srcPad = Gst.Element.get_static_pad(src, 'src')
            sinkPad = Gst.Element.get_request_pad(rtpbin, name)
            return (Gst.Pad.link(srcPad, sinkPad) == Gst.PadLinkReturn.OK)            
                
        # get an RTP sinkpad in session 0
        #srcPad = Gst.Element.get_static_pad(udpsrc_rtpin, 'src')
        #sinkPad = Gst.Element.get_request_pad(rtpbin, 'recv_rtp_sink_0')
        #ret = ret and (Gst.Pad.link(srcPad, sinkPad) == Gst.PadLinkReturn.OK)
        #ret = ret and PadLink(udpsrc_rtpin, 'recv_rtp_sink_0')
        ret = ret and self.udpsrc_rtpin.link_pads('src', self.rtpbin, 'recv_rtp_sink_0')
        
        # get an RTCP sinkpad in session 0
        #srcPad = Gst.Element.get_static_pad(udpsrc_rtcpin, 'src')
        #sinkPad = Gst.Element.get_request_pad(rtpbin, 'recv_rtcp_sink_0')
        #ret = ret and (Gst.Pad.link(srcPad, sinkPad) == Gst.PadLinkReturn.OK)
        #ret = ret and PadLink(udpsrc_rtcpin, 'recv_rtcp_sink_0')
        ret = ret and self.udpsrc_rtcpin.link_pads('src', self.rtpbin, 'recv_rtcp_sink_0')

        # get an RTCP srcpad for sending RTCP back to the sender
        #srcPad = Gst.Element.get_request_pad(rtpbin, 'send_rtcp_src_0')
        #sinkPad = Gst.Element.get_static_pad(udpsink_rtcpout, 'sink')
        #ret = ret and (Gst.Pad.link(srcPad, sinkPad) == Gst.PadLinkReturn.OK)
        ret = ret and self.rtpbin.link_pads('send_rtcp_src_0', self.udpsink_rtcpout, 'sink')
        
        if not ret:
            logging.critical('GST elements could not be linked')
            sys.exit(1)

        self.rtpbin.connect('pad-added', PadAdded, self.depay) #динамическое подключение rtpbin->depay

    def setHost(self, host):
        self._host = host
        self.udpsink_rtcpout.set_property('host', host)

    def setPort(self, port):
        self._port = port
        self.udpsrc_rtpin.set_property('port', port)
        self.udpsrc_rtcpin.set_property('port', port + 1)
        self.udpsink_rtcpout.set_property('port', port + 5)
        
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

    def getStatePipeline(self):
        state = self.pipeline.get_state(Gst.CLOCK_TIME_NONE).state
        print('GST pipeline', state)

    def play_pipeline(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        #self.getStatePipeline()
        logging.info('GST pipeline PLAYING')

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

    def _newSample(self, sink):     # callback функция, вызываемая при каждом приходящем кадре
        sample = sink.emit('pull-sample')
        sampleBuff = sample.get_buffer()  # get the buffer
        
        data = sampleBuff.extract_dup(0, sampleBuff.get_size()) # extract data stream as string
               
        caps = sample.get_caps()

        widthFrame = caps.get_structure(0).get_value('width')
        heightFrame = caps.get_structure(0).get_value('height')
        #formatFrame = caps.get_structure(0).get_value('format')
        
        ''' 
        #создаем массив cvFrame в формате opencv
        cvFrame = np.ndarray((heightFrame, widthFrame, 3), buffer = data, dtype = np.uint8)
        
        self._onFrameCallback(cvFrame) #вызываем обработчик в качестве параметра передаем cv2 кадр
        '''
        #вызываем обработчик в качестве параметра передаем массив данных, ширина и высота кадра
        #формат цвета RGB
        self._onFrameCallback(data, widthFrame, heightFrame) 
        return Gst.FlowReturn.OK

