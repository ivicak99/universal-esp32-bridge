#!/usr/bin/env python3
"""Generate the Universal ESP32 Button/Signal Bridge KiCad project (tidy layout).
Power + MCU + 8 inputs + 8 PhotoMOS + 2 relays + 4 cap-inject, hierarchical.
Each pin gets a short wire stub with its label/power symbol offset outward,
components spaced on a grid -> human-readable while staying ERC-clean."""
import os, shutil, kisch
from kisch import Project

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN  = os.path.join(ROOT, "gen")
shutil.copy(os.path.join(GEN, "bridge.kicad_sym"), os.path.join(ROOT, "bridge.kicad_sym"))
kisch.CUSTOM_LIBS["bridge"] = os.path.join(ROOT, "bridge.kicad_sym")

FP = dict(
    r0603="Resistor_SMD:R_0603_1608Metric", r1206="Resistor_SMD:R_1206_3216Metric",
    c0603="Capacitor_SMD:C_0603_1608Metric", c1206="Capacitor_SMD:C_1206_3216Metric",
    c0805="Capacitor_SMD:C_0805_2012Metric", l="Inductor_SMD:L_1210_3225Metric",
    led="LED_SMD:LED_0603_1608Metric", smc="Diode_SMD:D_SMC", sma="Diode_SMD:D_SMA",
    sod323="Diode_SMD:D_SOD-323", sot23="Package_TO_SOT_SMD:SOT-23",
    sot235="Package_TO_SOT_SMD:SOT-23-5", sot236="Package_TO_SOT_SMD:SOT-23-6",
    photomos="bridge:AQY212GS_SOP-4", opto="bridge:EL357N_SOP-4", relay="bridge:HK4100F-DC5V-SHG",
    usbc="Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
    tb2="TerminalBlock:TerminalBlock_MaiXu_MX126-5.0-02P_1x02_P5.00mm",
    tb3="TerminalBlock:TerminalBlock_MaiXu_MX126-5.0-03P_1x03_P5.00mm",
    hdr3="Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
    hdr6="Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
    btn="Button_Switch_SMD:Panasonic_EVQPUJ_EVQPUA", tp="TestPoint:TestPoint_Pad_D1.5mm",
    esp="RF_Module:ESP32-S3-WROOM-1",
)

p = Project("universal-esp32-bridge", ROOT)
_ctr = {}
def ref(prefix):
    _ctr[prefix] = _ctr.get(prefix, 0) + 1
    return "%s%d" % (prefix, _ctr[prefix])

# ---- stub-based connection helpers (label/power offset from pin) ----
_ANG = {'R':0,'U':90,'L':180,'D':270}
def _end(pt,d,ln):
    x,y=pt; return {'U':(x,y-ln),'D':(x,y+ln),'L':(x-ln,y),'R':(x+ln,y)}[d]
def autodir(c,pin):
    return c.outdir(pin)  # outward direction from the pin's true orientation angle
def NL(sh,c,pin,net,d=None,ln=5.08,glob=False):
    d=autodir(c,pin)  # always route outward from the pin's true orientation
    pt=c.pin(pin); e=_end(pt,d,ln); sh.wire(pt,e)
    (sh.glabel if glob else sh.label)(net,e,angle=_ANG[d])
def GL(sh,c,pin,net,d=None,ln=5.08): NL(sh,c,pin,net,d,ln,glob=True)
def PW(sh,c,pin,sym,d=None,ln=5.08):
    d=autodir(c,pin)
    pt=c.pin(pin); e=_end(pt,d,ln); sh.wire(pt,e); sh.power(sym,e)
def NC(sh,c,pin): sh.nc(c.pin(pin))

# =============================== POWER (A3) ===============================
pw = p.add_sheet("Power", "power.kicad_sch", "Power - USB-C / diode-OR / SY8089 buck 3.3V")
pw.root_pos=(38,38)
jusb=pw.place("Connector","USB_C_Receptacle_USB2.0_16P",ref("J"),"USB-C",(60,90),footprint=FP["usbc"])
for n in ("A4","A9","B4","B9"): NL(pw,jusb,n,"VBUS",'R')
for n in ("A1","A12","B1","B12","SH"): PW(pw,jusb,n,"GND")
for n in ("A6","B6"): NL(pw,jusb,n,"USB_DP_RAW",'R')
for n in ("A7","B7"): NL(pw,jusb,n,"USB_DM_RAW",'R')
NC(pw,jusb,"A8"); NC(pw,jusb,"B8")
rc1=pw.place("Device","R",ref("R"),"5.1k",(120,45),footprint=FP["r0603"]); NL(pw,rc1,"1","CC1",'U'); PW(pw,rc1,"2","GND")
rc2=pw.place("Device","R",ref("R"),"5.1k",(150,45),footprint=FP["r0603"]); NL(pw,rc2,"1","CC2",'U'); PW(pw,rc2,"2","GND")
NL(pw,jusb,"A5","CC1",'D'); NL(pw,jusb,"B5","CC2",'D')
uesd=pw.place("Power_Protection","USBLC6-2P6",ref("U"),"USBLC6-2SC6",(120,140),footprint=FP["sot236"])
NL(pw,uesd,"1","USB_DP_RAW",'L'); NL(pw,uesd,"3","USB_DM_RAW",'L'); PW(pw,uesd,"2","GND"); NL(pw,uesd,"5","VBUS",'U')
GL(pw,uesd,"6","USB_D+",'R'); GL(pw,uesd,"4","USB_D-",'R')
d1=pw.place("Device","D_Schottky",ref("D"),"SS54",(220,50),footprint=FP["smc"]); NL(pw,d1,"2","VBUS",'U'); NL(pw,d1,"1","+5V",'D')
jext=pw.place("Connector_Generic","Conn_01x02",ref("J"),"EXT 5V",(220,110),footprint=FP["tb2"]); NL(pw,jext,"1","EXT5V",'R'); PW(pw,jext,"2","GND")
d2=pw.place("Device","D_Schottky",ref("D"),"SS54",(260,50),footprint=FP["smc"]); NL(pw,d2,"2","EXT5V",'U'); NL(pw,d2,"1","+5V",'D')
c1=pw.place("Device","C",ref("C"),"100uF",(300,50),footprint=FP["c1206"]); PW(pw,c1,"1","+5V"); PW(pw,c1,"2","GND")
c2=pw.place("Device","C",ref("C"),"100nF",(330,50),footprint=FP["c0603"]); PW(pw,c2,"1","+5V"); PW(pw,c2,"2","GND")
buck=pw.place("bridge","SY8089",ref("U"),"SY8089AAAC",(400,110),footprint=FP["sot235"])
PW(pw,buck,"4","+5V",'L'); PW(pw,buck,"1","+5V",'L',ln=10.16); PW(pw,buck,"2","GND"); NL(pw,buck,"3","SW",'R'); NL(pw,buck,"5","FB",'L')
cin=pw.place("Device","C",ref("C"),"22uF",(360,55),footprint=FP["c0805"]); PW(pw,cin,"1","+5V"); PW(pw,cin,"2","GND")
l1=pw.place("Device","L",ref("L"),"2.2uH",(470,60),footprint=FP["l"]); NL(pw,l1,"1","SW",'U'); NL(pw,l1,"2","+3V3",'D')
cout=pw.place("Device","C",ref("C"),"22uF",(500,110),footprint=FP["c0805"]); PW(pw,cout,"1","+3V3"); PW(pw,cout,"2","GND")
r3=pw.place("Device","R",ref("R"),"453k",(470,150),footprint=FP["r0603"]); PW(pw,r3,"1","+3V3"); NL(pw,r3,"2","FB",'D')
r4=pw.place("Device","R",ref("R"),"100k",(470,185),footprint=FP["r0603"]); NL(pw,r4,"1","FB",'U'); PW(pw,r4,"2","GND")
for net,x in (("+5V",300),("+3V3",340),("GND",380),("VBUS",420)):
    pw.power("PWR_FLAG",(x,230)); pw.power(net,(x,230))
for nm,net,y in (("+5V","+5V",40),("+3V3","+3V3",70),("GND","GND",100)):
    tp=pw.place("Connector","TestPoint",ref("TP"),nm,(560,y),footprint=FP["tp"]); PW(pw,tp,"1",net,'R')
pw.text("USB-C diode-OR -> SY8089 buck (2.7-5.5Vin,2A) -> 3.3V. EN tied +5V. Vout=0.6*(1+R3/R4)=3.32V.",(40,25))

# =============================== MCU (A3) ===============================
mc=p.add_sheet("MCU","mcu.kicad_sch","ESP32-S3-WROOM-1-N8")
mc.root_pos=(90,38)
esp=mc.place("RF_Module","ESP32-S3-WROOM-1",ref("U"),"ESP32-S3-WROOM-1-N8",(210,150),footprint=FP["esp"])
PW(mc,esp,"2","+3V3");
for n in ("1","40","41"): PW(mc,esp,n,"GND")
for pin,net in zip(("4","5","6","7","8","9","10","11"),["IN%d"%i for i in range(1,9)]): GL(mc,esp,pin,net)
for pin,net in zip(("12","17","18","19","20","21","22","23"),["OUT%d"%i for i in range(1,9)]): GL(mc,esp,pin,net)
GL(mc,esp,"28","RLY1"); GL(mc,esp,"29","RLY2")
for pin,net in zip(("30","31","32","33"),["CAP1","CAP2","CAP3","CAP4"]): GL(mc,esp,pin,net)
GL(mc,esp,"13","USB_D-"); GL(mc,esp,"14","USB_D+")
for n in ("15","16","26"): NC(mc,esp,n)
juart=mc.place("Connector_Generic","Conn_01x03",ref("J"),"UART",(60,50),footprint=FP["hdr3"])
NL(mc,esp,"37","DBG_TX",'L'); NL(mc,juart,"1","DBG_TX",'L'); NL(mc,esp,"36","DBG_RX",'L'); NL(mc,juart,"2","DBG_RX",'L'); PW(mc,juart,"3","GND")
jsp=mc.place("Connector_Generic","Conn_01x06",ref("J"),"SPARE GPIO",(60,110),footprint=FP["hdr6"])
for pin,hp in zip(("24","25","34","35","39"),("1","2","3","4","5")):
    nn="SP_%s"%pin; NL(mc,esp,pin,nn,'R'); NL(mc,jsp,hp,nn,'L')
PW(mc,jsp,"6","GND")
ren=mc.place("Device","R",ref("R"),"10k",(40,180),footprint=FP["r0603"]); PW(mc,ren,"1","+3V3"); NL(mc,ren,"2","EN_NET",'D')
cen=mc.place("Device","C",ref("C"),"1uF",(75,180),footprint=FP["c0603"]); NL(mc,cen,"1","EN_NET",'U'); PW(mc,cen,"2","GND")
swr=mc.place("Switch","SW_Push",ref("SW"),"RESET",(110,180),footprint=FP["btn"]); NL(mc,swr,"1","EN_NET",'U'); PW(mc,swr,"2","GND")
NL(mc,esp,"3","EN_NET",'L')
rb=mc.place("Device","R",ref("R"),"10k",(330,180),footprint=FP["r0603"]); PW(mc,rb,"1","+3V3"); NL(mc,rb,"2","BOOT_NET",'D')
cb=mc.place("Device","C",ref("C"),"100nF",(365,180),footprint=FP["c0603"]); NL(mc,cb,"1","BOOT_NET",'U'); PW(mc,cb,"2","GND")
swb=mc.place("Switch","SW_Push",ref("SW"),"BOOT",(400,180),footprint=FP["btn"]); NL(mc,swb,"1","BOOT_NET",'U'); PW(mc,swb,"2","GND")
NL(mc,esp,"27","BOOT_NET",'R')
rl=mc.place("Device","R",ref("R"),"1k",(330,60),footprint=FP["r0603"]); NL(mc,esp,"38","LEDNET",'R'); NL(mc,rl,"1","LEDNET",'U'); NL(mc,rl,"2","LED_AK",'D')
led=mc.place("Device","LED",ref("D"),"STATUS",(330,100),footprint=FP["led"]); NL(mc,led,"2","LED_AK",'U'); PW(mc,led,"1","GND")
for i,(x,val) in enumerate([(400,"100nF"),(430,"100nF"),(460,"10uF")]):
    c=mc.place("Device","C",ref("C"),val,(x,70),footprint=FP["c0603"]); PW(mc,c,"1","+3V3"); PW(mc,c,"2","GND")
mc.text("ESP32-S3-WROOM-1-N8. Strapping IO3/45/46=NC. IO0=BOOT, EN=RESET. Native USB IO19/20. Status LED IO2.",(40,25))

# ====================== channel builders (one vertical column each) ======================
def input_channel(sh, i, x):
    n="IN%d"%i; y=45
    j=sh.place("Connector_Generic","Conn_01x02",ref("J"),n,(x,y),footprint=FP["tb2"]); NL(sh,j,"1","%s_FP"%n,'L'); NL(sh,j,"2","%s_FM"%n,'L'); y+=24
    rl=sh.place("Device","R",ref("R"),"2.2k",(x,y),footprint=FP["r1206"]); NL(sh,rl,"1","%s_FP"%n,'L'); NL(sh,rl,"2","%s_LED"%n,'R'); y+=24
    op=sh.place("Isolator","PC817",ref("U"),"EL357N",(x,y),footprint=FP["opto"]); NL(sh,op,"1","%s_LED"%n,'L'); NL(sh,op,"2","%s_FM"%n,'L'); NL(sh,op,"4","%s_RAW"%n,'R'); PW(sh,op,"3","GND"); y+=26
    dr=sh.place("Device","D",ref("D"),"1N4148WS",(x,y),footprint=FP["sod323"]); NL(sh,dr,"2","%s_FM"%n,'L'); NL(sh,dr,"1","%s_LED"%n,'R'); y+=24
    pu=sh.place("Device","R",ref("R"),"10k",(x,y),footprint=FP["r0603"]); PW(sh,pu,"1","+3V3"); NL(sh,pu,"2","%s_RAW"%n,'L'); y+=24
    rf=sh.place("Device","R",ref("R"),"1k",(x,y),footprint=FP["r0603"]); NL(sh,rf,"1","%s_RAW"%n,'L'); GL(sh,rf,"2",n,'D'); y+=24
    cf=sh.place("Device","C",ref("C"),"100nF",(x+22,y-4),footprint=FP["c0603"]); GL(sh,cf,"1",n,'U'); PW(sh,cf,"2","GND")
    tp=sh.place("Connector","TestPoint",ref("TP"),n,(x+22,y-30),footprint=FP["tp"]); GL(sh,tp,"1",n,'R')

def photomos_channel(sh, i, x):
    n="OUT%d"%i; y=50
    rd=sh.place("Device","R",ref("R"),"330",(x,y),footprint=FP["r0603"]); GL(sh,rd,"1",n,'U'); NL(sh,rd,"2","%s_LED"%n,'D'); y+=30
    pm=sh.place("bridge","AQY212GS",ref("U"),"AQY212GS",(x,y),footprint=FP["photomos"]); NL(sh,pm,"1","%s_LED"%n,'L'); PW(sh,pm,"2","GND"); NL(sh,pm,"4","%s_A"%n,'R'); NL(sh,pm,"3","%s_B"%n,'R'); y+=34
    j=sh.place("Connector_Generic","Conn_01x02",ref("J"),n,(x,y),footprint=FP["tb2"]); NL(sh,j,"1","%s_A"%n,'L'); NL(sh,j,"2","%s_B"%n,'L')
    tp=sh.place("Connector","TestPoint",ref("TP"),n,(x+26,50),footprint=FP["tp"]); NL(sh,tp,"1","%s_A"%n,'R')

def relay_channel(sh, i, x):
    n="RLY%d"%i; y=50
    rg=sh.place("Device","R",ref("R"),"100",(x,y),footprint=FP["r0603"]); GL(sh,rg,"1",n,'U'); NL(sh,rg,"2","%s_G"%n,'D'); y+=30
    q=sh.place("Transistor_FET","Q_NMOS_GSD",ref("Q"),"AO3400A",(x,y),footprint=FP["sot23"]); NL(sh,q,"1","%s_G"%n,'L'); PW(sh,q,"2","GND"); NL(sh,q,"3","%s_COIL"%n,'U'); y+=10
    pd=sh.place("Device","R",ref("R"),"100k",(x-26,y+6),footprint=FP["r0603"]); NL(sh,pd,"1","%s_G"%n,'U'); PW(sh,pd,"2","GND")
    k=sh.place("bridge","HK4100F",ref("K"),"HK4100F-DC5V",(x+34,55),footprint=FP["relay"])
    NL(sh,k,"4","%s_COIL"%n,'L'); PW(sh,k,"3","+5V",'L'); NL(sh,k,"5","%s_COM"%n,'R'); NL(sh,k,"6","%s_COM"%n,'R'); NL(sh,k,"1","%s_NO"%n,'R'); NL(sh,k,"2","%s_NC"%n,'R')
    db=sh.place("Device","D",ref("D"),"M7",(x+10,40),footprint=FP["sma"]); PW(sh,db,"1","+5V",'U'); NL(sh,db,"2","%s_COIL"%n,'D')
    j=sh.place("Connector_Generic","Conn_01x03",ref("J"),n,(x+70,60),footprint=FP["tb3"]); NL(sh,j,"1","%s_COM"%n,'R'); NL(sh,j,"2","%s_NO"%n,'R'); NL(sh,j,"3","%s_NC"%n,'R')

def cap_channel(sh, i, x):
    n="CAP%d"%i; y=50
    for val,dy in (("100k",0),("470k",26),("1M",52)):
        r=sh.place("Device","R",ref("R"),val,(x,y+dy),footprint=FP["r0603"]); GL(sh,r,"1",n,'L'); NL(sh,r,"2","%s_OUT"%n,'R')
    j=sh.place("Connector_Generic","Conn_01x02",ref("J"),n,(x+30,y+20),footprint=FP["tb2"]); NL(sh,j,"1","%s_OUT"%n,'R'); PW(sh,j,"2","GND")
    tp=sh.place("Connector","TestPoint",ref("TP"),n,(x+30,y-6),footprint=FP["tp"]); NL(sh,tp,"1","%s_OUT"%n,'R')

inp=p.add_sheet("Inputs","inputs.kicad_sch","8x isolated inputs (3-24V, active-LOW)"); inp.paper="A2"
inp.root_pos=(142,38); inp.text("Wide-range isolated input x8. R(2.2k/1206)+EL357N+anti-parallel diode + RC filter. Active-LOW.",(20,18))
for i in range(1,9): input_channel(inp,i,40+(i-1)*68)

pmo=p.add_sheet("PhotoMOS","photomos.kicad_sch","8x PhotoMOS dry-contact outputs"); pmo.paper="A2"
pmo.root_pos=(194,38); pmo.text("PhotoMOS isolated dry contact x8. GPIO->330R->AQY212GS. HIGH=closed. <=60V/<=0.5A.",(20,18))
for i in range(1,9): photomos_channel(pmo,i,40+(i-1)*60)

rel=p.add_sheet("Relays","relays.kicad_sch","2x relay outputs  LV CONTACTS ONLY"); rel.paper="A3"
rel.root_pos=(246,38); rel.text("MOSFET-driven relay x2 + flyback + gate pulldown. HK4100F coil=pin3/4, COM=5/6, NO=1, NC=2. LV ONLY.",(20,18))
for i in range(1,3): relay_channel(rel,i,60+(i-1)*150)

cap=p.add_sheet("CapInject","capinject.kicad_sch","4x capacitive injection outputs"); cap.paper="A3"
cap.root_pos=(298,38); cap.text("Cap-inject x4. Populate ONE of 100k/470k/1M (default 470k). High-Z to ext touch pad.",(20,18))
for i in range(1,5): cap_channel(cap,i,40+(i-1)*85)

for s in p.sheets: p.write_sheet(s)
p.write_root("Universal ESP32 Button/Signal Bridge",
             ["LOW VOLTAGE ONLY - NOT FOR 230V MAINS SWITCHING",
              "ESP32-S3-WROOM-1-N8 | SY8089 buck 3.3V | 8 iso-in, 8 PhotoMOS, 2 relay, 4 cap-inject",
              "Schematic ERC clean before PCB layout."])
p.write_libtables()
print("WROTE", ROOT, "| sheets:", len(p.sheets), "| components:", sum(_ctr.values()), _ctr)
