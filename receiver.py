#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gi
gi.require_version('Gst','1.0')
from gi.repository import Gst

FORMAT_H264 = 0
FORMAT_MJPEG = 1

RTP_PORT = 5000

class StreamReceiver(object):
    def __init__(self, video = FORMAT_H264, host = ('127.0.0.1', RTP_PORT)):
        self._host = host
        #инициализация Gstreamer
        Gst.init(None)
        #создаем pipeline
        self.make_pipeline(video, host)

        #подключаем обработчик сообщений
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message', self.onMessage)

        #запускаем pipeline
        self.ready_pipeline()
        
    def make_pipeline(self, video, host):
        # Создание GStreamer pipeline
        self.pipeline = Gst.Pipeline()

        #rtpbin
        rtpbin = Gst.ElementFactory.make('rtpbin')
        rtpbin.set_property('drop-on-latency', True) #отбрасывать устаревшие кадры
        rtpbin.set_property('buffer-mode', 0)
        
        #RTP Video
        formatStr = 'H264'
        payloadType = 96
        if video:
            videoStr = 'JPEG'
            payloadType = 26
        srcCaps = Gst.Caps.from_string('application/x-rtp,media=(string)video,clock-rate=(int)90000,encoding-name=(string)%s,payload=%d' % (formatStr, payloadType))
        
        udpsrc_rtpin = Gst.ElementFactory.make('udpsrc', 'udpsrc_rtpin')
        udpsrc_rtpin.set_property('port', host[1])
        udpsrc_rtpin.set_property('caps', srcCaps)

        udpsrc_rtcpin = Gst.ElementFactory.make('udpsrc', 'udpsrc_rtcpin')
        udpsrc_rtcpin.set_property('port', host[1] + 1)

        udpsink_rtcpout = Gst.ElementFactory.make('udpsink', 'udpsink_rtcpout')
        udpsink_rtcpout.set_property('host', host[0])
        udpsink_rtcpout.set_property('port', host[1] + 5)
        udpsink_rtcpout.set_property('sync', False)
        udpsink_rtcpout.set_property('async', False)

        if video == FORMAT_H264:
            depayName = 'rtph264depay'
            decoderName = 'avdec_h264' #хреново работает загрузка ЦП 120% 
            #decoder = Gst.ElementFactory.make('avdec_h264_mmal') #не заработал
        else:
            depayName = 'rtpjpegdepay'
            decoderName = 'avdec_mjpeg' #
            #decoder = Gst.ElementFactory.make('jpegdec') #

        #depayloader
        depay = Gst.ElementFactory.make(depayName)

        #decoder
        decoder = Gst.ElementFactory.make(decoderName)
        videorate = Gst.ElementFactory.make('videorate')
        sink = Gst.ElementFactory.make('autovideosink')

        # добавляем все элементы в pipeline
        elemList = [rtpbin, depay, decoder, videorate, sink, udpsrc_rtpin,
                    udpsrc_rtcpin, udpsink_rtcpout]
            
        for elem in elemList:
            self.pipeline.add(elem)

        #соединяем элементы
        ret = depay.link(decoder)
        ret = ret and decoder.link(videorate)
        ret = ret and videorate.link(sink)
        
        #соединяем элементы rtpbin

        def pad_added_cb(rtpbin, new_pad, gstElem):
            sinkPad = Gst.Element.get_static_pad(gstElem, 'sink')
            res = Gst.Pad.link(new_pad, sinkPad)
            if res:
                print('Pad linked')
        
        # get an RTP sinkpad in session 0
        srcPad = Gst.Element.get_static_pad(udpsrc_rtpin, 'src')
        sinkPad = Gst.Element.get_request_pad(rtpbin, 'recv_rtp_sink_0')
        ret = ret and Gst.Pad.link(srcPad, sinkPad)

        # get an RTCP sinkpad in session 0
        srcPad = Gst.Element.get_static_pad(udpsrc_rtcpin, 'src')
        sinkPad = Gst.Element.get_request_pad(rtpbin, 'recv_rtcp_sink_0')
        ret = ret and Gst.Pad.link(srcPad, sinkPad)

        # get an RTCP srcpad for sending RTCP back to the sender
        srcPad = Gst.Element.get_request_pad(rtpbin, 'send_rtcp_src_0')
        sinkPad = Gst.Element.get_static_pad(udpsink_rtcpout, 'sink')
        ret = ret and Gst.Pad.link(srcPad, sinkPad)

        rtpbin.connect('pad-added', pad_added_cb, depay)
        
    def onMessage(self, bus, message):
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

#-------------------------------------------------------------------------------------------------

import time

recv = StreamReceiver(FORMAT_MJPEG)
recv.play_pipeline()

#главный цикл программы    
try:
    while True:
        time.sleep(0.1)
except (KeyboardInterrupt, SystemExit):
    print('Ctrl+C pressed')

recv.null_pipeline()

