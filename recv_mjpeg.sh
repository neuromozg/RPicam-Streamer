#HOST=192.168.42.162
HOST=10.1.0.78
#HOST=127.0.0.1
RTPBIN_PARAMS="drop-on-latency=true buffer-mode=1"

gst-launch-1.0 -v rtpbin name=rtpbin $RTPBIN_PARAMS                                          \
    udpsrc caps="application/x-rtp,media=(string)video,clock-rate=(int)90000,encoding-name=(string)JPEG,payload=(int)26" \
            port=5000 ! rtpbin.recv_rtp_sink_0                                \
        rtpbin. ! rtpjpegdepay ! jpegdec ! videorate ! fpsdisplaysink sync=false                    \
     udpsrc port=5001 ! rtpbin.recv_rtcp_sink_0                               \
     rtpbin.send_rtcp_src_0 ! udpsink host=$HOST port=5005 sync=false async=false
