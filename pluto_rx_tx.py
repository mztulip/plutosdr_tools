import adi
# https://github.com/analogdevicesinc/pyadi-iio/blob/master/adi/ad936x.py
import matplotlib.pyplot as plt
import time

sample_rate = 10e6 # Hz
center_freq = 100e6 # Hz

sdr = adi.Pluto("ip:pluto.local")
# sdr = adi.Pluto("ip:192.168.2.137")
# sdr = adi.ad9361("ip:pluto.local")
# sdr.rx_enabled_channels     = [0]
# print(sdr._rx_channel_names)

sdr.rx_hardwaregain_chan0   = 30
sdr.sample_rate = int(sample_rate)
sdr.rx_rf_bandwidth = int(sample_rate) # filter cutoff, just set it to the same as sample rate
sdr.rx_lo = int(center_freq)
sdr.rx_buffer_size = 1024 # this is the buffer the Pluto uses to buffer samples
samples = sdr.rx() # receive samples off Pluto
print(samples)

exit = False

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
            if char2 == "D": #left
                pass
            if char2 == "C": #right
                pass
            if char2 == "A": #up
                pass
            if char2 == "B": #down
                pass
        time.sleep(0.1)
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

keyb_thread = threading.Thread(target=keyboard_thread_func)

keyb_thread.start()
print("Press q to exit, <-,-> to change attenuation, up/down-change frequency")

while exit is False:
    time.sleep(0.5)