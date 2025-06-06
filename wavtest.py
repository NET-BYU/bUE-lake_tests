from gnuradio import gr, blocks, analog
from gnuradio.blocks import wavfile_format_t, wavfile_subformat_t

class test(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self)
        # Generate a 1 kHz tone
        src = analog.sig_source_f(48000, analog.GR_SIN_WAVE, 1000, 0.5)
        sink = blocks.wavfile_sink(
        'test.wav',
        1,
        48000,
        format = 1,
        subformat = 2)

        self.connect(src, sink)

tb = test()
tb.start()
import time; time.sleep(2)
tb.stop()
tb.wait()