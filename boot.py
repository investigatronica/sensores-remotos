import network
from time import sleep

def do_connect(veces):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect('essid', 'password')
        while not wlan.isconnected() and veces >0:
            sleep(5)
            veces-=1
            print(veces)
    if not wlan.isconnected():
             wlan.disconnect()
    print('network config:', wlan.ifconfig())


do_connect(5)
