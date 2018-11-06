#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gi
gi.require_version('Gst','1.0')
from gi.repository import Gst

from common import *

RTP_PORT = 5000
HOST = '127.0.0.1'

class StreamReceiver(object):
    def __init__(self, video = VIDEO_H264, host = (HOST, RTP_PORT)):
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
        #rtpbin.set_property('autoremove', True)
        rtpbin.set_property('latency', 200)        
        rtpbin.set_property('drop-on-latency', True) #отбрасывать устаревшие кадры
        rtpbin.set_property('buffer-mode', 4)
        #rtpbin.set_property('ntp-time-source', 3)
        #rtpbin.set_property('ntp-sync', True)
        #rtpbin.set_property('rtcp-sync-send-time', False)
        
        #RTP Video
        formatStr = 'H264'
        payloadType = 96
        if video:
            videoStr = 'JPEG'
            payloadType = 26
        srcCaps = Gst.Caps.from_string('application/x-rtp, media=video, clock-rate=90000, encoding-name=%s, payload=%d' % (formatStr, payloadType))
        
        udpsrc_rtpin = Gst.ElementFactory.make('udpsrc', 'udpsrc_rtpin')
        udpsrc_rtpin.set_property('port', host[1])
        udpsrc_rtpin.set_property('caps', srcCaps)

        srcCaps = Gst.Caps.from_string('application/x-rtcp')
        udpsrc_rtcpin = Gst.ElementFactory.make('udpsrc', 'udpsrc_rtcpin')
        udpsrc_rtcpin.set_property('port', host[1] + 1)
        udpsrc_rtcpin.set_property('caps', srcCaps)

        udpsink_rtcpout = Gst.ElementFactory.make('udpsink', 'udpsink_rtcpout')
        udpsink_rtcpout.set_property('host', host[0])
        udpsink_rtcpout.set_property('port', host[1] + 5)
        udpsink_rtcpout.set_property('sync', True)
        udpsink_rtcpout.set_property('async', False)

        depayName = 'rtph264depay'
        decoderName = 'avdec_h264' #хреново работает загрузка ЦП 120% 
        #decoder = Gst.ElementFactory.make('avdec_h264_mmal') #не заработал
        if video:
            depayName = 'rtpjpegdepay'
            #decoderName = 'avdec_mjpeg' #
            decoderName = 'jpegdec' #

        #depayloader
        depay = Gst.ElementFactory.make(depayName)

        #decoder
        decoder = Gst.ElementFactory.make(decoderName)
        videorate = Gst.ElementFactory.make('videorate')

        #sink
        #sink = Gst.ElementFactory.make('autovideosink')
        sink = Gst.ElementFactory.make('fpsdisplaysink')        
        sink.set_property('sync', False)

        # добавляем все элементы в pipeline
        elemList = [rtpbin, depay, decoder, videorate, sink, udpsrc_rtpin,
                    udpsrc_rtcpin, udpsink_rtcpout]
            
        for elem in elemList:
            self.pipeline.add(elem)

        #соединяем элементы
        ret = depay.link(decoder)
        ret = ret and decoder.link(videorate)
        ret = ret and videorate.link(sink)
        #print(ret)
        
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
        ret = ret and udpsrc_rtpin.link_pads('src', rtpbin, 'recv_rtp_sink_0')
        
        # get an RTCP sinkpad in session 0
        #srcPad = Gst.Element.get_static_pad(udpsrc_rtcpin, 'src')
        #sinkPad = Gst.Element.get_request_pad(rtpbin, 'recv_rtcp_sink_0')
        #ret = ret and (Gst.Pad.link(srcPad, sinkPad) == Gst.PadLinkReturn.OK)
        #ret = ret and PadLink(udpsrc_rtcpin, 'recv_rtcp_sink_0')
        ret = ret and udpsrc_rtcpin.link_pads('src', rtpbin, 'recv_rtcp_sink_0')

        # get an RTCP srcpad for sending RTCP back to the sender
        #srcPad = Gst.Element.get_request_pad(rtpbin, 'send_rtcp_src_0')
        #sinkPad = Gst.Element.get_static_pad(udpsink_rtcpout, 'sink')
        #ret = ret and (Gst.Pad.link(srcPad, sinkPad) == Gst.PadLinkReturn.OK)
        ret = ret and rtpbin.link_pads('send_rtcp_src_0', udpsink_rtcpout, 'sink')
        
        if not ret:
            print('ERROR: Elements could not be linked')
            sys.exit(1)

        rtpbin.connect('pad-added', PadAdded, depay) #динамическое подключение rtpbin->depay
        
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

    def getStatePipeline(self):
        state = self.pipeline.get_state(Gst.CLOCK_TIME_NONE).state
        print('GST pipeline', state)

    def play_pipeline(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        #self.getStatePipeline()
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

