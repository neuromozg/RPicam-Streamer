#HOST=192.168.1.183
HOST=173.1.0.86
RTPBIN_PARAMS="drop-on-latency=1 buffer-mode=0"

gst-launch-1.0 -v rtpbin name=rtpbin $RTPBIN_PARAMS                                          \
    udpsrc caps="application/x-rtp,media=(string)video,clock-rate=(int)90000,encoding-name=(string)H264" \
            port=5000 ! rtpbin.recv_rtp_sink_0                                \
        rtpbin. ! rtph264depay ! avdec_h264 ! videorate ! fpsdisplaysink sync=false                    \
     udpsrc port=5001 ! rtpbin.recv_rtcp_sink_0                               \
     rtpbin.send_rtcp_src_0 ! udpsink host=$HOST port=5005 sync=false async=false
