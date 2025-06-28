#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Not titled yet
# Author: admin
# GNU Radio version: 3.10.9.2

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




class tup_rdo(gr.top_block):

    def __init__(self, message_str='TEST', mult_amp=0.5, tx_cr=1, tx_rx_bw=8000, tx_rx_mix_freq=1000, tx_rx_sf=7, tx_rx_sync_word=[0x12], wav_file_path=''):
        gr.top_block.__init__(self, "Not titled yet", catch_exceptions=True)

        ##################################################
        # Parameters
        ##################################################
        self.message_str = message_str
        self.mult_amp = mult_amp
        self.tx_cr = tx_cr
        self.tx_rx_bw = tx_rx_bw
        self.tx_rx_mix_freq = tx_rx_mix_freq
        self.tx_rx_sf = tx_rx_sf
        self.tx_rx_sync_word = tx_rx_sync_word
        self.wav_file_path = wav_file_path

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 48000

        ##################################################
        # Blocks
        ##################################################

        self.lora_tx_0 = lora_sdr.lora_sdr_lora_tx(
            bw=tx_rx_bw,
            cr=tx_cr,
            has_crc=True,
            impl_head=False,
            samp_rate=samp_rate,
            sf=tx_rx_sf,
         ldro_mode=2,frame_zero_padd=1280,sync_word=tx_rx_sync_word )
        self.lora_rx_0 = lora_sdr.lora_sdr_lora_rx( bw=tx_rx_bw, cr=1, has_crc=True, impl_head=False, pay_len=255, samp_rate=samp_rate, sf=tx_rx_sf, sync_word=tx_rx_sync_word, soft_decoding=True, ldro_mode=2, print_rx=[True,True])
        self.blocks_wavfile_sink_0 = blocks.wavfile_sink(
            wav_file_path,
            1,
            samp_rate,
            blocks.FORMAT_WAV,
            blocks.FORMAT_PCM_16,
            False
            )
        self.blocks_multiply_xx_0_0 = blocks.multiply_vcc(1)
        self.blocks_multiply_xx_0 = blocks.multiply_vcc(1)
        self.blocks_multiply_const_vxx_0 = blocks.multiply_const_cc(mult_amp)
        self.blocks_message_strobe_0 = blocks.message_strobe(pmt.intern(f"{message_str}"), 500)
        self.blocks_float_to_complex_0 = blocks.float_to_complex(1)
        self.blocks_conjugate_cc_0 = blocks.conjugate_cc()
        self.blocks_complex_to_float_0 = blocks.complex_to_float(1)
        self.audio_source_0 = audio.source(samp_rate, 'hw:3,0', True)
        self.audio_sink_0 = audio.sink(samp_rate, 'hw:3,0', True)
        self.analog_sig_source_x_0_0 = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, tx_rx_mix_freq, 1, 0, 0)
        self.analog_sig_source_x_0 = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, (-tx_rx_mix_freq), 1, 0, 0)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.blocks_message_strobe_0, 'strobe'), (self.lora_tx_0, 'in'))
        self.connect((self.analog_sig_source_x_0, 0), (self.blocks_multiply_xx_0, 1))
        self.connect((self.analog_sig_source_x_0_0, 0), (self.blocks_multiply_xx_0_0, 0))
        self.connect((self.audio_source_0, 0), (self.blocks_float_to_complex_0, 0))
        self.connect((self.blocks_complex_to_float_0, 0), (self.audio_sink_0, 0))
        self.connect((self.blocks_complex_to_float_0, 0), (self.blocks_wavfile_sink_0, 0))
        self.connect((self.blocks_conjugate_cc_0, 0), (self.lora_rx_0, 0))
        self.connect((self.blocks_float_to_complex_0, 0), (self.blocks_multiply_xx_0, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.blocks_complex_to_float_0, 0))
        self.connect((self.blocks_multiply_xx_0, 0), (self.blocks_conjugate_cc_0, 0))
        self.connect((self.blocks_multiply_xx_0_0, 0), (self.blocks_multiply_const_vxx_0, 0))
        self.connect((self.lora_tx_0, 0), (self.blocks_multiply_xx_0_0, 1))


    def get_message_str(self):
        return self.message_str

    def set_message_str(self, message_str):
        self.message_str = message_str

    def get_mult_amp(self):
        return self.mult_amp

    def set_mult_amp(self, mult_amp):
        self.mult_amp = mult_amp
        self.blocks_multiply_const_vxx_0.set_k(self.mult_amp)

    def get_tx_cr(self):
        return self.tx_cr

    def set_tx_cr(self, tx_cr):
        self.tx_cr = tx_cr
        self.lora_tx_0.set_cr(self.tx_cr)

    def get_tx_rx_bw(self):
        return self.tx_rx_bw

    def set_tx_rx_bw(self, tx_rx_bw):
        self.tx_rx_bw = tx_rx_bw

    def get_tx_rx_mix_freq(self):
        return self.tx_rx_mix_freq

    def set_tx_rx_mix_freq(self, tx_rx_mix_freq):
        self.tx_rx_mix_freq = tx_rx_mix_freq
        self.analog_sig_source_x_0.set_frequency((-self.tx_rx_mix_freq))
        self.analog_sig_source_x_0_0.set_frequency(self.tx_rx_mix_freq)

    def get_tx_rx_sf(self):
        return self.tx_rx_sf

    def set_tx_rx_sf(self, tx_rx_sf):
        self.tx_rx_sf = tx_rx_sf
        self.lora_tx_0.set_sf(self.tx_rx_sf)

    def get_tx_rx_sync_word(self):
        return self.tx_rx_sync_word

    def set_tx_rx_sync_word(self, tx_rx_sync_word):
        self.tx_rx_sync_word = tx_rx_sync_word

    def get_wav_file_path(self):
        return self.wav_file_path

    def set_wav_file_path(self, wav_file_path):
        self.wav_file_path = wav_file_path
        self.blocks_wavfile_sink_0.open(self.wav_file_path)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.analog_sig_source_x_0.set_sampling_freq(self.samp_rate)
        self.analog_sig_source_x_0_0.set_sampling_freq(self.samp_rate)



def argument_parser():
    parser = ArgumentParser()
    parser.add_argument(
        "--message-str", dest="message_str", type=str, default='TEST',
        help="Set message_str [default=%(default)r]")
    parser.add_argument(
        "--mult-amp", dest="mult_amp", type=eng_float, default=eng_notation.num_to_str(float(0.5)),
        help="Set mult_amp [default=%(default)r]")
    parser.add_argument(
        "--tx-cr", dest="tx_cr", type=intx, default=1,
        help="Set tx_cr [default=%(default)r]")
    parser.add_argument(
        "--tx-rx-bw", dest="tx_rx_bw", type=intx, default=8000,
        help="Set tx_rx_bw [default=%(default)r]")
    parser.add_argument(
        "--tx-rx-mix-freq", dest="tx_rx_mix_freq", type=intx, default=1000,
        help="Set tx_rx_mix_freq [default=%(default)r]")
    parser.add_argument(
        "--tx-rx-sf", dest="tx_rx_sf", type=intx, default=7,
        help="Set tx_rx_sf [default=%(default)r]")
    parser.add_argument(
        "--wav-file-path", dest="wav_file_path", type=str, default='',
        help="Set wav_file_path [default=%(default)r]")
    return parser


def main(top_block_cls=tup_rdo, options=None):
    if options is None:
        options = argument_parser().parse_args()
    tb = top_block_cls(message_str=options.message_str, mult_amp=options.mult_amp, tx_cr=options.tx_cr, tx_rx_bw=options.tx_rx_bw, tx_rx_mix_freq=options.tx_rx_mix_freq, tx_rx_sf=options.tx_rx_sf, wav_file_path=options.wav_file_path)

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()

    try:
        input('Press Enter to quit: ')
    except EOFError:
        pass
    tb.stop()
    tb.wait()


if __name__ == '__main__':
    main()
