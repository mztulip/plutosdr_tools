import numpy as np
import adi
import signal
import sys
import time
import humanize
import threading
import tty, termios
from scipy.signal import kaiserord, firwin, lfilter, fftconvolve, oaconvolve

# https://pysdr.org/content/pluto.html
# https://github.com/analogdevicesinc/pyadi-iio/blob/master/adi/ad936x.py

sample_rate = 32e6 # Hz
# center_freq = 2501e6 # Hz
center_freq = 900e6 # Hz

device = "pluto"
# device = "libresdr"

if device == "pluto":
    sdr = adi.Pluto("ip:pluto.local")
    # sdr = adi.ad9361("ip:pluto.local")
    # sdr.tx_enabled_channels     = [0]
elif device == "libresdr":
    # sdr = adi.Pluto("ip:192.168.2.137")
    sdr = adi.ad9361("ip:192.168.2.137")
    sdr.tx_enabled_channels     = [1]

sdr.sample_rate = int(sample_rate)
sdr.tx_rf_bandwidth = int(sample_rate) # filter cutoff, just set it to the same as sample rate
sdr.tx_lo = int(center_freq)
sdr.tx_hardwaregain_chan0 = -30 # Increase to increase tx power, valid range is -89 to 0 dB
sdr.gain_control_mode_chan0 = "manual"
sdr.rx_hardwaregain_chan0   = 0
sdr.rx_buffer_size          = 350000
sdr.rx_rf_bandwidth         = int(4e6)
sdr.tx_rf_bandwidth         = int(4e6)
sdr.sample_rate             = int(8e6)

#Normally at 1GHz
# -10 gives -10dBm
#but after some time this reduces to -28dBm

#This happens sometimes after some time of working
#PLuto Original
#1GHz
#0 -> -22dBm
#-10 -> -31dBm
#-20 -> -40dBm
#-30 -> -49dBm

#2GHz
#0 -> -25dBm

#3GHz
#0 -> -22dBm

#4GHz
#0 -> -19dBm

#5GHz
#0 -> -23dBm

#6GHz
#0 -> -23dBm

N = 10000 # number of samples to transmit at once
t = np.arange(N)/sample_rate

# mod_frequency = 100e3
mod_frequency = 524e3

#czesottliwosc wyjsciowa to jest center_freq+mod_frequency,ale nośną też kurcze widać.
# Więc nie da się pojedynczej częstotliwosci wygenerować. Gdy poda się czesottliwośc 0 to nośna znika,
# DAC nie może działać ponizęj 2MS/s pewnie dlatego że tor tego nie przenosi.

samples = 0.5*np.exp(2.0j*np.pi*mod_frequency*t) # Simulate a sinusoid of 100 kHz, so it should show up at 915.1 MHz at the receiver
samples *= 2**14 # The PlutoSDR expects samples to be between -2^14 and +2^14, not -1 and +1 like some SDRs
print(samples)
# Transmit our batch of samples 100 times, so it should be 1 second worth of samples total, if USB can keep up

sdr.tx_cyclic_buffer        = True
sdr.tx(samples)

exit = False

def signal_handler(sig, frame):
    global exit
    print('You pressed Ctrl+C!')
    exit = True

signal.signal(signal.SIGINT, signal_handler)
print('Press Ctrl+C')

def keyboard_thread_func():
    global exit
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setraw(sys.stdin.fileno())
    while exit is False:
        char = sys.stdin.read(1)
        # print(f"Stdin: {char}")
        if char == "q":
            exit = True
        if char == "[":
            char2 = sys.stdin.read(1)
            # print(char2)
            if char2 == "D":
                sdr.tx_hardwaregain_chan0 -= 1
            if char2 == "C":
                if sdr.tx_hardwaregain_chan0 < 0:
                    sdr.tx_hardwaregain_chan0 += 1
            if char2 == "A":
                sdr.tx_lo += int(1e6)
            if char2 == "B":
                sdr.tx_lo -= int(1e6)
        time.sleep(0.1)
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

keyb_thread = threading.Thread(target=keyboard_thread_func)

keyb_thread.start()
print("Press q to exit, <-,-> to change attenuation, up/down-change frequency")

sample_rate = 8e6
nyq_rate = sample_rate / 2.0

#Filter ribble 70 means also that attenuation in stop band is 70dB
FILT_RIPPLE_DB, FILT_CUTOFF_HZ, FILT_TRANS_WIDTH_HZ = 70, 500, 1000
N, beta = kaiserord(FILT_RIPPLE_DB, FILT_TRANS_WIDTH_HZ/nyq_rate)
print(f"N: {N}")
b_fir   = firwin(N, FILT_CUTOFF_HZ/nyq_rate, window=('kaiser', beta))

while exit is False:
    #clean old buffer data by empty reading
    sdr.rx()

    iq_buffer = np.zeros(350000 * 2, np.complex64)
    iq_buffer[0:350000] = sdr.rx()/(2**12)
    iq_buffer[350000:2*350000] = sdr.rx()/(2**12)

    # Move 524e3 TX tone to DC
    t = np.arange(len(iq_buffer)) / 8e6
    iq_data = iq_buffer * np.exp(-2j * np.pi * 524e3 * t)
    iq_filtered = fftconvolve(iq_data, b_fir, mode='same')
    #Remove FIR filter transient response
    iq_filtered = iq_filtered[N:]
    dc_value = np.abs(iq_filtered).mean()

    db_value = 20 * np.log10(dc_value)

    rssi = sdr._get_iio_attr('voltage0','rssi', False)
    print(f"\n\rTX hardware gain: {sdr.tx_hardwaregain_chan0 } Freq: {sdr.tx_lo/1e6}MHz RSSI: -{rssi}dB"
        f" db: {db_value}dB ADC(0-1): {dc_value}")

   


keyb_thread.join()

sdr.tx_hardwaregain_chan0 = -89
sdr.tx_destroy_buffer()