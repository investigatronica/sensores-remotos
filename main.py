from machine import Pin, I2C
import ssd1306, dht, ujson, os, network,errno
from time import sleep_ms,ticks_ms, ticks_diff,sleep
from rotary_irq_esp import RotaryIRQ
from umqtt.simple import MQTTClient
from button import Button
from boot import do_connect

wlan = network.WLAN(network.STA_IF)
i2c = I2C(-1, scl=Pin(5), sda=Pin(4))
oled_width = 128
oled_height = 64
oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)
oled.fill(0)
oled.show()

def mqtt(temperatura,humedad,setpoint,ventilador,c):
    try:
        c.connect()
    except OSError as e:
        print("no hsot")
    else:
        envio=ujson.dumps({'temperatura':temperatura,'humedad':humedad,'setpoint':setpoint,'rele':ventilador})
        topico=b"sensores_remotos/"+mac
        c.publish(topico, envio)
        print("publicado")
        print(envio)
    # c.disconnect()

def button_a_callback(topic, msg):
    global r
    global disp_SP
    global setpoint
    global nuevo_sp
    if setpoint!=disp_SP and msg==None:
        setpoint=disp_SP
        r.set(value=setpoint)
    else:
        print(msg)
        print(int(msg))
        setpoint=int(msg)
        r.set(value=setpoint)
    print("setpoint cambiado "+str(setpoint))
    f=open("setpoint.dat","w")
    f.write(str(setpoint))
    f.close()
    print("grabado nuevo SP")
    disp_SP=setpoint
    nuevo_sp=1
    # r.set(disp_SP)
    # print("Button A (%s) changed to: %r" % (pin, pin.value()))

button_a = Button(pin=Pin(2, mode=Pin.IN, pull=Pin.PULL_UP), callback=button_a_callback)

d = dht.DHT22(Pin(13))
nuevo_sp=0
ventilador=0
histeresis=2
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
y_SP=28
y_vent=39
y_wifi=51
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

server="url"
c = MQTTClient(mac, server)
c.set_callback(button_a_callback)
try:
    c.connect()
except OSError as e:
    print("no hsot")

c.subscribe(b"sensores_remotos/"+mac+b"/setpoint")

i=0
j=0
start2 = ticks_ms()
temperatura=0
humedad=0
enviando=0

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
    if i%20==0:
        try:
            c.check_msg()
        except:
            try:
                c.connect()
            except OSError as e:
                print("no hsot")

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
    if j==2 or nuevo_sp==1:
        j=0
        if ventilador==1 and temperatura < setpoint-histeresis:
            ventilador=0
            oled.fill_rect(0,y_vent,128,8,0)
            oled.text("Ventilador:   NO",0,y_vent)
            rele.on()
        elif ventilador==0 and temperatura > setpoint+histeresis:
            oled.fill_rect(0,y_vent,128,8,0)
            ventilador=1
            oled.text("Ventilador:   SI",0,y_vent)
            rele.off()
        print(ventilador)
    if ticks_diff(ticks_ms(), start2)>180000 or nuevo_sp==1:
        start2 = ticks_ms()
        nuevo_sp=0
        if wlan.isconnected():
            mqtt(temperatura,humedad,setpoint,ventilador,c)
            enviando=8
            oled.fill_rect(0,y_wifi-2,128,12,0)
            oled.text("WiFi: "+ wlan.config('essid'),0,y_wifi)
            inicio=ticks_ms()+500
        else:
            oled.fill_rect(0,y_wifi-2,128,12,1)
            oled.text("WiFi:         NO",0,y_wifi,0)
            do_connect()

    if enviando>0:
        if (enviando % 2)==0 and ticks_diff(ticks_ms(), inicio)>249:
            oled.hline(0,63,128,1)
            inicio=ticks_ms()
            enviando-=1
        elif (enviando % 2)!=0 and ticks_diff(ticks_ms(), inicio)>249:
            oled.hline(0,63,128,0)
            inicio=ticks_ms()
            enviando-=1
    oled.show()
    sleep_ms(50)
