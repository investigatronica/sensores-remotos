from machine import Pin, I2C
import ssd1306, dht, ujson, os, network
from time import sleep_ms,ticks_ms, ticks_diff,sleep
from rotary_irq_esp import RotaryIRQ
from umqtt.simple import MQTTClient
from button import Button

wlan = network.WLAN(network.STA_IF)

def mqtt(temperatura,humedad,setpoint,ventilador,mac,server="url"):
    c = MQTTClient(mac, server)
    c.connect()
    envio=ujson.dumps({'temperatura':temperatura,'humedad':humedad,'setpoint':setpoint,'ventilador':ventilador})
    topico=b"sensores_remotos/"+mac
    c.publish(topico, envio)
    print("publicado")
    print(envio)
    c.disconnect()


i2c = I2C(-1, scl=Pin(5), sda=Pin(4))
oled_width = 128
oled_height = 64
oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)
oled.fill(0)
oled.show()

def button_a_callback(pin):
    global disp_SP
    global setpoint
    setpoint=disp_SP
    print("setpoint cambiado "+str(setpoint))
    f=open("setpoint.dat","w")
    f.write(str(setpoint))
    f.close()
    print("grabado nuevo SP")
    # r.set(disp_SP)
    # print("Button A (%s) changed to: %r" % (pin, pin.value()))

button_a = Button(pin=Pin(2, mode=Pin.IN, pull=Pin.PULL_UP), callback=button_a_callback)

d = dht.DHT22(Pin(13))
ventilador=0
rele= Pin(16, Pin.OUT,value=1)

f=open("setpoint.dat","r")
setpoint=int(f.read())
f.close()

#gpio12 == D6 NodeMCU
#gpio14 == D5 NodeMCU
r = RotaryIRQ(pin_num_clk=12,
              pin_num_dt=14,
              min_val=0,
              max_val=50,
              reverse=False,
              range_mode=RotaryIRQ.RANGE_WRAP)
r.set(value=setpoint)

disp_SP=setpoint
y_SP=30
y_vent=40
y_wifi=53
oled.text("Set Point:",0,y_SP)
oled.text(str(setpoint),112,y_SP)
oled.text("Ventilador:   NO",0,y_vent)
if wlan.isconnected():
    oled.text("WiFi: "+ wlan.config('essid'),0,y_wifi)
    nic=wlan.config('mac')
    mac=""
    for ot in list(nic):
        h = hex(ot)
        mac += h[2] + h[3]
    mac=mac.upper()
else:
    oled.fill_rect(0,y_wifi-2,128,12,1)
    oled.text("WiFi:         NO",0,y_wifi,0)


i=0
j=0
start2 = ticks_ms()
temperatura=0
humedad=0
while True:
    new_SP = r.value()

    if disp_SP != new_SP and new_SP != setpoint:
        print('result =', new_SP)
        oled.fill_rect(110,y_SP-2,21,11,1)
        oled.text("Set Point:",0,y_SP)
        oled.text(str(new_SP),112,y_SP,0)
        disp_SP=new_SP
        start = ticks_ms() # get millisecond counter
    elif new_SP==setpoint or ticks_diff(ticks_ms(), start)>5000:
        oled.fill_rect(110,y_SP-2,21,11,0)
        oled.text("Set Point:",0,y_SP)
        oled.text(str(setpoint),112,y_SP,1)
    if i==40:
        print("dht")
        i=0
        d.measure()
        temperatura=d.temperature()
        humedad=d.humidity()
        oled.fill_rect(0,0,128,18,0)
        oled.text("Temp.:     " + str(temperatura)+ "C",0,0)
        oled.text("Humedad:   " + str(humedad)+"%",0,10)
        # oled.show()
        j=j+1
    i=i+1
    if j==2:
        j=0
        if ventilador==1 and temperatura < setpoint-2:
            ventilador=0
            oled.fill_rect(0,y_vent,128,8,0)
            oled.text("Ventilador:   NO",0,y_vent)
            rele.on()
        elif ventilador==0 and temperatura > setpoint+2:
            oled.fill_rect(0,y_vent,128,8,0)
            ventilador=1
            oled.text("Ventilador:   SI",0,y_vent)
            rele.off()
        print(ventilador)
    oled.show()
    if ticks_diff(ticks_ms(), start2)>20000:
        start2 = ticks_ms()
        if wlan.isconnected():
            mqtt(temperatura,humedad,setpoint,ventilador,mac)
    sleep_ms(50)
