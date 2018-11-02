import cv2
import threading

from common import *

class OpenCVRTPStreamer(object):
    def __init__(self, video = VIDEO_MJPEG, resolution = (640, 480), framerate = 30, host = ('localhost', 5000)):
        self._host = host
        self._resolution = resolution
        self._framerate = framerate
        self._video = video
        
        codecStr = 'jpegenc ! rtpjpegpay'
        if video == VIDEO_H264:
            codecStr = 'x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! rtph264pay'
            
        self._pipeline = 'rtpbin name=rtpbin latency=200 drop-on-latency=true buffer-mode=4 ntp-time-source=3 ntp-sync=true rtcp-sync-send-time=false ' \
            ' appsrc ! video/x-raw,format=BGR ! videoconvert ! video/x-raw,format=I420 ! %s ! queue ! rtpbin.send_rtp_sink_0 ' \
            ' rtpbin.send_rtp_src_0 ! udpsink port=%d host=%s sync=true async=false' \
            ' rtpbin.send_rtcp_src_0 ! udpsink port=%d host=%s sync=false async=false ' \
            ' udpsrc port=%d caps="application/x-rtcp" ! rtpbin.recv_rtcp_sink_0' % (codecStr, host[1], host[0], host[1]+1, host[0], host[1]+5)
        self._streamer = cv2.VideoWriter()

    def start(self):
        if self._streamer.open(self._pipeline, cv2.CAP_GSTREAMER, 0, self._framerate, self._resolution, True):
            print('RTP streamer started...')
            return True
        else:
            print('Error start pipeline...')
            return False
            
    def stop(self):
        self._streamer.release()
        print('RTP streamer stopped...')
        
    def sendFrame(self, frame):
        if (self._streamer.isOpened()):
            self._streamer.write(frame)

class OpenCVRTPReciver(threading.Thread):
    def __init__(self, video = VIDEO_MJPEG, host = ('localhost', 5000), onFrameCallback = None):
        super(OpenCVRTPReciver, self).__init__()
        if (not onFrameCallback is None) and callable(onFrameCallback):
            self._onFrameCallback = onFrameCallback #обработчик события OpenCV кадр готов
            
        decodeStr = 'rtpjpegdepay ! jpegdec'
        encodingName = 'JPEG'
        if video == VIDEO_H264:
            decodeStr = 'rtph264depay ! avdec_h264'
            encodingName = 'H264'
        self._pipeline = 'rtpbin name=rtpbin latency=200 drop-on-latency=true buffer-mode=4 ntp-time-source=3 ntp-sync=true ' \
            'udpsrc caps="application/x-rtp,media=(string)video,clock-rate=(int)90000,encoding-name=(string)%s" port=%d ! rtpbin.recv_rtp_sink_0 ' \
            'rtpbin. ! %s ! videoconvert ! video/x-raw, format=BGR ! appsink ' \
            'udpsrc caps="application/x-rtcp" port=%d ! rtpbin.recv_rtcp_sink_0 ' \
            'rtpbin.send_rtcp_src_0 ! udpsink port=%d host=%s sync=false async=false' % (encodingName, host[1], decodeStr, host[1]+1, host[1]+5, host[0])
        self._receiver = cv2.VideoCapture()
        self._stopped = threading.Event() #событие для остановки потока
        
    def run(self):
        if self._receiver.open(self._pipeline, cv2.CAP_GSTREAMER):
            print('RTP receiver started...')
            while not self._stopped.is_set():

                ret, frame = self._receiver.read()

                if ret:
                    if not (self._onFrameCallback is None):
                        self._onFrameCallback(frame)
                else:
                    break
            print('RTP receiver stopped...')
        else:
            print('Error start pipeline...')
            
        self._receiver.release()
                    
    def stop(self): #остановка потока
        self._stopped.set()
        self.join()
