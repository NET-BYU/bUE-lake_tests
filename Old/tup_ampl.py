#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Not titled yet
# Author: admin
# GNU Radio version: 3.10.9.2

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




class tup_rup(gr.top_block):

    def __init__(self, rx_bw=0, rx_cr=0, rx_pay_len=0, rx_sf=0, rx_sync_word=0, tx_bw=8000, tx_cr=1, tx_sf=7, tx_sync_word=[0x12]):
        gr.top_block.__init__(self, "Not titled yet", catch_exceptions=True)

        ##################################################
        # Parameters
        ##################################################
        self.rx_bw = rx_bw
        self.rx_cr = rx_cr
        self.rx_pay_len = rx_pay_len
        self.rx_sf = rx_sf
        self.rx_sync_word = rx_sync_word
        self.tx_bw = tx_bw
        self.tx_cr = tx_cr
        self.tx_sf = tx_sf
        self.tx_sync_word = tx_sync_word

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 48000

        ##################################################
        # Blocks
        ##################################################

        self.lora_tx_0 = lora_sdr.lora_sdr_lora_tx(
            bw=tx_bw,
            cr=tx_cr,
            has_crc=True,
            impl_head=False,
            samp_rate=samp_rate,
            sf=tx_sf,
         ldro_mode=2,frame_zero_padd=1280,sync_word=tx_sync_word )
        self.lora_sdr_payload_id_inc_0 = lora_sdr.payload_id_inc(':')
        self.lora_rx_0 = lora_sdr.lora_sdr_lora_rx( bw=8000, cr=1, has_crc=True, impl_head=False, pay_len=255, samp_rate=samp_rate, sf=7, sync_word=[0x12], soft_decoding=True, ldro_mode=2, print_rx=[True,True])
        self.blocks_multiply_xx_0_0 = blocks.multiply_vcc(1)
        self.blocks_multiply_xx_0 = blocks.multiply_vcc(1)
        self.blocks_multiply_const_vxx_0 = blocks.multiply_const_cc(0.2)
        self.blocks_message_strobe_0 = blocks.message_strobe(pmt.intern("TEST"), 1000)
        self.blocks_complex_to_float_0 = blocks.complex_to_float(1)
        self.audio_sink_0 = audio.sink(samp_rate, 'hw:3,0', True)
        self.analog_sig_source_x_0_0 = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, 5000, 1, 0, 0)
        self.analog_sig_source_x_0 = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, (-5000), 1, 0, 0)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.blocks_message_strobe_0, 'strobe'), (self.lora_sdr_payload_id_inc_0, 'msg_in'))
        self.msg_connect((self.blocks_message_strobe_0, 'strobe'), (self.lora_tx_0, 'in'))
        self.msg_connect((self.lora_sdr_payload_id_inc_0, 'msg_out'), (self.blocks_message_strobe_0, 'set_msg'))
        self.connect((self.analog_sig_source_x_0, 0), (self.blocks_multiply_xx_0, 1))
        self.connect((self.analog_sig_source_x_0_0, 0), (self.blocks_multiply_xx_0_0, 0))
        self.connect((self.blocks_complex_to_float_0, 0), (self.audio_sink_0, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.blocks_complex_to_float_0, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.blocks_multiply_xx_0, 0))
        self.connect((self.blocks_multiply_xx_0, 0), (self.lora_rx_0, 0))
        self.connect((self.blocks_multiply_xx_0_0, 0), (self.blocks_multiply_const_vxx_0, 0))
        self.connect((self.lora_tx_0, 0), (self.blocks_multiply_xx_0_0, 1))


    def get_rx_bw(self):
        return self.rx_bw

    def set_rx_bw(self, rx_bw):
        self.rx_bw = rx_bw

    def get_rx_cr(self):
        return self.rx_cr

    def set_rx_cr(self, rx_cr):
        self.rx_cr = rx_cr

    def get_rx_pay_len(self):
        return self.rx_pay_len

    def set_rx_pay_len(self, rx_pay_len):
        self.rx_pay_len = rx_pay_len

    def get_rx_sf(self):
        return self.rx_sf

    def set_rx_sf(self, rx_sf):
        self.rx_sf = rx_sf

    def get_rx_sync_word(self):
        return self.rx_sync_word

    def set_rx_sync_word(self, rx_sync_word):
        self.rx_sync_word = rx_sync_word

    def get_tx_bw(self):
        return self.tx_bw

    def set_tx_bw(self, tx_bw):
        self.tx_bw = tx_bw

    def get_tx_cr(self):
        return self.tx_cr

    def set_tx_cr(self, tx_cr):
        self.tx_cr = tx_cr
        self.lora_tx_0.set_cr(self.tx_cr)

    def get_tx_sf(self):
        return self.tx_sf

    def set_tx_sf(self, tx_sf):
        self.tx_sf = tx_sf
        self.lora_tx_0.set_sf(self.tx_sf)

    def get_tx_sync_word(self):
        return self.tx_sync_word

    def set_tx_sync_word(self, tx_sync_word):
        self.tx_sync_word = tx_sync_word

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.analog_sig_source_x_0.set_sampling_freq(self.samp_rate)
        self.analog_sig_source_x_0_0.set_sampling_freq(self.samp_rate)



def argument_parser():
    parser = ArgumentParser()
    parser.add_argument(
        "--tx-bw", dest="tx_bw", type=intx, default=8000,
        help="Set tx_bw [default=%(default)r]")
    parser.add_argument(
        "--tx-cr", dest="tx_cr", type=intx, default=1,
        help="Set tx_cr [default=%(default)r]")
    parser.add_argument(
        "--tx-sf", dest="tx_sf", type=intx, default=7,
        help="Set tx_sf [default=%(default)r]")
    return parser


def main(top_block_cls=tup_rup, options=None):
    if options is None:
        options = argument_parser().parse_args()
    tb = top_block_cls(tx_bw=options.tx_bw, tx_cr=options.tx_cr, tx_sf=options.tx_sf)

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()

    timeout = 60  # seconds
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
