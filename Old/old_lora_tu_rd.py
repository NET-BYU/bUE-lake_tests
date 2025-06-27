#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Not titled yet
# Author: admin
# GNU Radio version: 3.10.5.1

import time
from gnuradio import analog
from gnuradio import audio
from gnuradio import blocks
import pmt
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
import gnuradio.lora_sdr as lora_sdr
import RPi.GPIO as GPIO
import os



class lora_tu_rd(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "Not titled yet", catch_exceptions=True)

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 48000

        ##################################################
        # Blocks
        ##################################################

        self.lora_tx_0 = lora_sdr.lora_sdr_lora_tx(
            bw=8000,
            cr=1,
            has_crc=True,
            impl_head=False,
            samp_rate=samp_rate,
            sf=7,
            ldro_mode=2, frame_zero_padd=1280, sync_word=[0x12])
        self.lora_sdr_payload_id_inc_0 = lora_sdr.payload_id_inc(':')
        self.lora_rx_0 = lora_sdr.lora_sdr_lora_rx(
            bw=8000, cr=1, has_crc=True, impl_head=False, pay_len=255,
            samp_rate=samp_rate, sf=7, sync_word=[0x12], soft_decoding=True,
            ldro_mode=2, print_rx=[True, True])
        self.blocks_multiply_xx_0_0 = blocks.multiply_vcc(1)
        self.blocks_multiply_xx_0 = blocks.multiply_vcc(1)
        self.blocks_message_strobe_0 = blocks.message_strobe(pmt.intern("NETLab: 0"), 1000)
        self.blocks_float_to_complex_0 = blocks.float_to_complex(1)
        self.blocks_conjugate_cc_0 = blocks.conjugate_cc()
        self.blocks_complex_to_float_0 = blocks.complex_to_float(1)
        self.audio_source_0 = audio.source(48000, 'hw:3,0', True)
        self.audio_sink_1_0 = audio.sink(samp_rate, 'hw:3,0', True)
        self.analog_sig_source_x_0_0 = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, 30000, 1, 0, 0)
        self.analog_sig_source_x_0 = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, (-30000), 5, 0, 0)

        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.blocks_message_strobe_0, 'strobe'), (self.lora_sdr_payload_id_inc_0, 'msg_in'))
        self.msg_connect((self.blocks_message_strobe_0, 'strobe'), (self.lora_tx_0, 'in'))
        self.msg_connect((self.lora_sdr_payload_id_inc_0, 'msg_out'), (self.blocks_message_strobe_0, 'set_msg'))
        self.connect((self.analog_sig_source_x_0, 0), (self.blocks_multiply_xx_0, 1))
        self.connect((self.analog_sig_source_x_0_0, 0), (self.blocks_multiply_xx_0_0, 0))
        self.connect((self.audio_source_0, 0), (self.blocks_float_to_complex_0, 0))
        self.connect((self.blocks_complex_to_float_0, 0), (self.audio_sink_1_0, 0))
        self.connect((self.blocks_conjugate_cc_0, 0), (self.lora_rx_0, 0))
        self.connect((self.blocks_float_to_complex_0, 0), (self.blocks_multiply_xx_0, 0))
        self.connect((self.blocks_multiply_xx_0, 0), (self.blocks_conjugate_cc_0, 0))
        self.connect((self.blocks_multiply_xx_0_0, 0), (self.blocks_complex_to_float_0, 0))
        self.connect((self.lora_tx_0, 0), (self.blocks_multiply_xx_0_0, 1))


    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.analog_sig_source_x_0.set_sampling_freq(self.samp_rate)
        self.analog_sig_source_x_0_0.set_sampling_freq(self.samp_rate)

def main(top_block_cls=lora_tu_rd, options=None):
    tb = top_block_cls()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()

    timeout = 10  # seconds
    start_time = time.time()
    try:
        print('Running for up to 10 seconds. Press Ctrl+C to quit early.')
        while True:
            if time.time() - start_time > timeout:
                print('Timeout reached, stopping...')
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        print('Keyboard interrupt received, stopping...')
        pass
    tb.stop()
    tb.wait()


if __name__ == '__main__':
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(26, GPIO.OUT)

    GPIO.output(26, GPIO.HIGH)
    time.sleep(0.5)

    main()

    GPIO.cleanup()
    print("Audio device closed, GPIO cleaned up")
