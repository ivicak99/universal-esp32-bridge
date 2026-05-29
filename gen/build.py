#!/usr/bin/env python3
"""Generate the Universal ESP32 Button/Signal Bridge KiCad project.
Full design: power + MCU + 8 isolated inputs + 8 PhotoMOS + 2 relays + 4 cap-inject,
as hierarchical sheets. Connectivity via power symbols (rails) + labels (signals)."""
import os, shutil, itertools, kisch
from kisch import Project

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN  = os.path.join(ROOT, "gen")
shutil.copy(os.path.join(GEN, "bridge.kicad_sym"), os.path.join(ROOT, "bridge.kicad_sym"))
kisch.CUSTOM_LIBS["bridge"] = os.path.join(ROOT, "bridge.kicad_sym")

FP = dict(
    r0603="Resistor_SMD:R_0603_1608Metric",
    r1206="Resistor_SMD:R_1206_3216Metric",
    c0603="Capacitor_SMD:C_0603_1608Metric",
    c1206="Capacitor_SMD:C_1206_3216Metric",
    c0805="Capacitor_SMD:C_0805_2012Metric",
    l="Inductor_SMD:L_1210_3225Metric",
    led="LED_SMD:LED_0603_1608Metric",
    smc="Diode_SMD:D_SMC", sma="Diode_SMD:D_SMA", sod323="Diode_SMD:D_SOD-323",
    sot23="Package_TO_SOT_SMD:SOT-23", sot235="Package_TO_SOT_SMD:SOT-23-5",
    sot236="Package_TO_SOT_SMD:SOT-23-6", sop4="Package_SO:SOP-4_4.4x2.6mm_P1.27mm",
    usbc="Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
    relay="Relay_THT:Relay_SPDT_Fujitsu_FTR-LYCA005x_FormC_Vertical",  # PLACEHOLDER: verify HK4100F land pattern
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

def G(sh, c, pin, net): sh.glabel(net, c.pin(pin))
def L(sh, c, pin, net): sh.label(net, c.pin(pin))
def P(sh, c, pin, sym): sh.power(sym, c.pin(pin))
def NC(sh, c, pin): sh.nc(c.pin(pin))

# =============================== POWER ===============================
pw = p.add_sheet("Power", "power.kicad_sch", "Power - USB-C / diode-OR / SY8089 buck 3.3V")
pw.root_pos=(38, 38)
jusb = pw.place("Connector","USB_C_Receptacle_USB2.0_16P",ref("J"),"USB-C",(60,80),footprint=FP["usbc"])
for n in ("A4","A9","B4","B9"): L(pw, jusb, n, "VBUS")
for n in ("A1","A12","B1","B12","SH"): P(pw, jusb, n, "GND")
for n in ("A6","B6"): L(pw, jusb, n, "USB_DP_RAW")
for n in ("A7","B7"): L(pw, jusb, n, "USB_DM_RAW")
NC(pw, jusb, "A8"); NC(pw, jusb, "B8")
rc1=pw.place("Device","R",ref("R"),"5.1k",(150,40),footprint=FP["r0603"]); L(pw,jusb,"A5","CC1"); L(pw,rc1,"1","CC1"); P(pw,rc1,"2","GND")
rc2=pw.place("Device","R",ref("R"),"5.1k",(150,75),footprint=FP["r0603"]); L(pw,jusb,"B5","CC2"); L(pw,rc2,"1","CC2"); P(pw,rc2,"2","GND")
uesd=pw.place("Power_Protection","USBLC6-2P6",ref("U"),"USBLC6-2SC6",(150,130),footprint=FP["sot236"])
L(pw,uesd,"1","USB_DP_RAW"); L(pw,uesd,"3","USB_DM_RAW"); P(pw,uesd,"2","GND"); L(pw,uesd,"5","VBUS")
G(pw,uesd,"6","USB_D+"); G(pw,uesd,"4","USB_D-")
d1=pw.place("Device","D_Schottky",ref("D"),"SS54",(240,40),footprint=FP["smc"]); L(pw,d1,"2","VBUS"); P(pw,d1,"1","+5V")
jext=pw.place("Connector_Generic","Conn_01x02",ref("J"),"EXT 5V",(240,90),footprint=FP["tb2"]); L(pw,jext,"1","EXT5V"); P(pw,jext,"2","GND")
d2=pw.place("Device","D_Schottky",ref("D"),"SS54",(240,150),footprint=FP["smc"]); L(pw,d2,"2","EXT5V"); P(pw,d2,"1","+5V")
c1=pw.place("Device","C",ref("C"),"100uF",(310,40),footprint=FP["c1206"]); P(pw,c1,"1","+5V"); P(pw,c1,"2","GND")
c2=pw.place("Device","C",ref("C"),"100nF",(310,80),footprint=FP["c0603"]); P(pw,c2,"1","+5V"); P(pw,c2,"2","GND")
buck=pw.place("bridge","SY8089",ref("U"),"SY8089AAAC",(380,90),footprint=FP["sot235"])
P(pw,buck,"4","+5V"); P(pw,buck,"1","+5V"); P(pw,buck,"2","GND"); L(pw,buck,"3","SW"); L(pw,buck,"5","FB")
cin=pw.place("Device","C",ref("C"),"22uF",(380,160),footprint=FP["c0805"]); P(pw,cin,"1","+5V"); P(pw,cin,"2","GND")
l1=pw.place("Device","L",ref("L"),"2.2uH",(450,40),footprint=FP["l"]); L(pw,l1,"1","SW"); P(pw,l1,"2","+3V3")
cout=pw.place("Device","C",ref("C"),"22uF",(450,90),footprint=FP["c0805"]); P(pw,cout,"1","+3V3"); P(pw,cout,"2","GND")
r3=pw.place("Device","R",ref("R"),"453k",(520,40),footprint=FP["r0603"]); P(pw,r3,"1","+3V3"); L(pw,r3,"2","FB")
r4=pw.place("Device","R",ref("R"),"100k",(520,80),footprint=FP["r0603"]); L(pw,r4,"1","FB"); P(pw,r4,"2","GND")
for net,x in (("+5V",590),("+3V3",630),("GND",670),("VBUS",710)):
    pw.power("PWR_FLAG",(x,210)); pw.power(net,(x,210))
for nm,net,x in (("+5V","+5V",590),("+3V3","+3V3",630),("GND","GND",670)):
    tp=pw.place("Connector","TestPoint",ref("TP"),nm,(x,40),footprint=FP["tp"]); P(pw,tp,"1",net)
pw.text("USB-C diode-OR -> SY8089 buck (2.7-5.5Vin,2A) -> 3.3V. EN tied +5V. Vout=0.6*(1+R/R)=3.32V.",(40,25))

# =============================== MCU ===============================
mc = p.add_sheet("MCU","mcu.kicad_sch","ESP32-S3-WROOM-1-N8")
mc.root_pos=(90,38)
esp=mc.place("RF_Module","ESP32-S3-WROOM-1",ref("U"),"ESP32-S3-WROOM-1-N8",(160,150),footprint=FP["esp"])
P(mc,esp,"2","+3V3")
for n in ("1","40","41"): P(mc,esp,n,"GND")
for pin,net in zip(("4","5","6","7","8","9","10","11"),["IN%d"%i for i in range(1,9)]): G(mc,esp,pin,net)
for pin,net in zip(("12","17","18","19","20","21","22","23"),["OUT%d"%i for i in range(1,9)]): G(mc,esp,pin,net)
G(mc,esp,"28","RLY1"); G(mc,esp,"29","RLY2")
for pin,net in zip(("30","31","32","33"),["CAP1","CAP2","CAP3","CAP4"]): G(mc,esp,pin,net)
G(mc,esp,"13","USB_D-"); G(mc,esp,"14","USB_D+")
for n in ("15","16","26"): NC(mc,esp,n)   # strapping IO3/IO46/IO45 unused
juart=mc.place("Connector_Generic","Conn_01x03",ref("J"),"UART",(40,40),footprint=FP["hdr3"])
L(mc,esp,"37","DBG_TX"); L(mc,juart,"1","DBG_TX")
L(mc,esp,"36","DBG_RX"); L(mc,juart,"2","DBG_RX"); P(mc,juart,"3","GND")
jsp=mc.place("Connector_Generic","Conn_01x06",ref("J"),"SPARE GPIO",(40,90),footprint=FP["hdr6"])
for pin,hp in zip(("24","25","34","35","39"),("1","2","3","4","5")):
    nn="SP_%s"%pin; L(mc,esp,pin,nn); L(mc,jsp,hp,nn)
P(mc,jsp,"6","GND")
ren=mc.place("Device","R",ref("R"),"10k",(40,150),footprint=FP["r0603"]); P(mc,ren,"1","+3V3"); L(mc,ren,"2","EN_NET")
cen=mc.place("Device","C",ref("C"),"1uF",(40,185),footprint=FP["c0603"]); L(mc,cen,"1","EN_NET"); P(mc,cen,"2","GND")
swr=mc.place("Switch","SW_Push",ref("SW"),"RESET",(40,220),footprint=FP["btn"]); L(mc,swr,"1","EN_NET"); P(mc,swr,"2","GND")
L(mc,esp,"3","EN_NET")
rb=mc.place("Device","R",ref("R"),"10k",(280,150),footprint=FP["r0603"]); P(mc,rb,"1","+3V3"); L(mc,rb,"2","BOOT_NET")
cb=mc.place("Device","C",ref("C"),"100nF",(280,185),footprint=FP["c0603"]); L(mc,cb,"1","BOOT_NET"); P(mc,cb,"2","GND")
swb=mc.place("Switch","SW_Push",ref("SW"),"BOOT",(280,220),footprint=FP["btn"]); L(mc,swb,"1","BOOT_NET"); P(mc,swb,"2","GND")
L(mc,esp,"27","BOOT_NET")
rl=mc.place("Device","R",ref("R"),"1k",(330,40),footprint=FP["r0603"]); L(mc,esp,"38","LEDNET"); L(mc,rl,"1","LEDNET"); L(mc,rl,"2","LED_AK")
led=mc.place("Device","LED",ref("D"),"STATUS",(330,80),footprint=FP["led"]); L(mc,led,"2","LED_AK"); P(mc,led,"1","GND")
for i,(x,val) in enumerate([(380,"100nF"),(420,"100nF"),(460,"10uF")]):
    c=mc.place("Device","C",ref("C"),val,(x,150),footprint=FP["c0603"]); P(mc,c,"1","+3V3"); P(mc,c,"2","GND")
mc.text("ESP32-S3-WROOM-1-N8. Strapping IO3/45/46=NC. IO0=BOOT, EN=RESET. Native USB IO19/20. Status LED IO2.",(40,25))

# ====================== channel builders ======================
def input_channel(sh, i, x):
    jin=sh.place("Connector_Generic","Conn_01x02",ref("J"),"IN%d"%i,(x,60),footprint=FP["tb2"])
    L(sh,jin,"1","IN%d_FP"%i); L(sh,jin,"2","IN%d_FM"%i)
    rlim=sh.place("Device","R",ref("R"),"2.2k",(x,100),footprint=FP["r1206"]); L(sh,rlim,"1","IN%d_FP"%i); L(sh,rlim,"2","IN%d_LED"%i)
    opto=sh.place("Isolator","PC817",ref("U"),"EL357N",(x,140),footprint=FP["sop4"])
    L(sh,opto,"1","IN%d_LED"%i); L(sh,opto,"2","IN%d_FM"%i)
    drev=sh.place("Device","D",ref("D"),"1N4148WS",(x,180),footprint=FP["sod323"]); L(sh,drev,"2","IN%d_FM"%i); L(sh,drev,"1","IN%d_LED"%i)
    rpu=sh.place("Device","R",ref("R"),"10k",(x,215),footprint=FP["r0603"]); P(sh,rpu,"1","+3V3"); L(sh,rpu,"2","IN%d_RAW"%i)
    L(sh,opto,"4","IN%d_RAW"%i); P(sh,opto,"3","GND")
    rf=sh.place("Device","R",ref("R"),"1k",(x,250),footprint=FP["r0603"]); L(sh,rf,"1","IN%d_RAW"%i); G(sh,rf,"2","IN%d"%i)
    cf=sh.place("Device","C",ref("C"),"100nF",(x+30,250),footprint=FP["c0603"]); G(sh,cf,"1","IN%d"%i); P(sh,cf,"2","GND")
    tp=sh.place("Connector","TestPoint",ref("TP"),"IN%d"%i,(x+30,215),footprint=FP["tp"]); G(sh,tp,"1","IN%d"%i)

def photomos_channel(sh, i, x):
    rd=sh.place("Device","R",ref("R"),"330",(x,60),footprint=FP["r0603"]); G(sh,rd,"1","OUT%d"%i); L(sh,rd,"2","OUT%d_LED"%i)
    pm=sh.place("bridge","AQY212GS",ref("U"),"AQY212GS",(x,110),footprint=FP["sop4"])
    L(sh,pm,"1","OUT%d_LED"%i); P(sh,pm,"2","GND")
    jo=sh.place("Connector_Generic","Conn_01x02",ref("J"),"OUT%d"%i,(x,160),footprint=FP["tb2"])
    L(sh,pm,"4","OUT%d_A"%i); L(sh,jo,"1","OUT%d_A"%i); L(sh,pm,"3","OUT%d_B"%i); L(sh,jo,"2","OUT%d_B"%i)
    tp=sh.place("Connector","TestPoint",ref("TP"),"OUT%d"%i,(x+30,60),footprint=FP["tp"]); L(sh,tp,"1","OUT%d_A"%i)

def relay_channel(sh, i, x):
    rg=sh.place("Device","R",ref("R"),"100",(x,60),footprint=FP["r0603"]); G(sh,rg,"1","RLY%d"%i); L(sh,rg,"2","RLY%d_G"%i)
    q=sh.place("Transistor_FET","Q_NMOS_GSD",ref("Q"),"AO3400A",(x,110),footprint=FP["sot23"])
    L(sh,q,"1","RLY%d_G"%i); P(sh,q,"2","GND"); L(sh,q,"3","RLY%d_COIL"%i)
    rpd=sh.place("Device","R",ref("R"),"100k",(x,150),footprint=FP["r0603"]); L(sh,rpd,"1","RLY%d_G"%i); P(sh,rpd,"2","GND")
    k=sh.place("Relay","Relay_SPDT",ref("K"),"HK4100F-DC5V",(x+40,120),footprint=FP["relay"])
    P(sh,k,"A1","+5V"); L(sh,k,"A2","RLY%d_COIL"%i)
    dfb=sh.place("Device","D",ref("D"),"M7",(x,200),footprint=FP["sma"]); P(sh,dfb,"1","+5V"); L(sh,dfb,"2","RLY%d_COIL"%i)
    jr=sh.place("Connector_Generic","Conn_01x03",ref("J"),"RLY%d"%i,(x+40,180),footprint=FP["tb3"])
    L(sh,k,"11","RLY%d_COM"%i); L(sh,jr,"1","RLY%d_COM"%i)
    L(sh,k,"14","RLY%d_NO"%i);  L(sh,jr,"2","RLY%d_NO"%i)
    L(sh,k,"12","RLY%d_NC"%i);  L(sh,jr,"3","RLY%d_NC"%i)

def cap_channel(sh, i, x):
    r100=sh.place("Device","R",ref("R"),"100k",(x,60),footprint=FP["r0603"]);  G(sh,r100,"1","CAP%d"%i); L(sh,r100,"2","CAP%d_OUT"%i)
    r470=sh.place("Device","R",ref("R"),"470k",(x,100),footprint=FP["r0603"]); G(sh,r470,"1","CAP%d"%i); L(sh,r470,"2","CAP%d_OUT"%i)
    r1m =sh.place("Device","R",ref("R"),"1M",(x,140),footprint=FP["r0603"]);   G(sh,r1m,"1","CAP%d"%i);  L(sh,r1m,"2","CAP%d_OUT"%i)
    jc=sh.place("Connector_Generic","Conn_01x02",ref("J"),"CAP%d"%i,(x,185),footprint=FP["tb2"]); L(sh,jc,"1","CAP%d_OUT"%i); P(sh,jc,"2","GND")
    tp=sh.place("Connector","TestPoint",ref("TP"),"CAP%d"%i,(x+30,60),footprint=FP["tp"]); L(sh,tp,"1","CAP%d_OUT"%i)

inp=p.add_sheet("Inputs","inputs.kicad_sch","8x isolated inputs (3-24V, active-LOW)")
inp.root_pos=(142,38); inp.text("Wide-range isolated input x8. R(2.2k/1206)+EL357N+anti-parallel diode. RC filter. Active-LOW.",(20,15))
for i in range(1,9): input_channel(inp, i, 20+(i-1)*70)

pmo=p.add_sheet("PhotoMOS","photomos.kicad_sch","8x PhotoMOS dry-contact outputs")
pmo.root_pos=(194,38); pmo.text("PhotoMOS isolated dry contact x8. GPIO->330R->AQY212GS. HIGH=closed. <=60V/<=0.5A.",(20,15))
for i in range(1,9): photomos_channel(pmo, i, 20+(i-1)*70)

rel=p.add_sheet("Relays","relays.kicad_sch","2x relay outputs  LV CONTACTS ONLY")
rel.root_pos=(246,38); rel.text("MOSFET-driven relay x2 + flyback + gate pulldown. LOW VOLTAGE CONTACTS ONLY - NOT MAINS.",(20,15))
for i in range(1,3): relay_channel(rel, i, 20+(i-1)*110)

cap=p.add_sheet("CapInject","capinject.kicad_sch","4x capacitive injection outputs")
cap.root_pos=(298,38); cap.text("Cap-inject x4. Populate ONE of 100k/470k/1M (default 470k). High-Z to ext touch pad.",(20,15))
for i in range(1,5): cap_channel(cap, i, 20+(i-1)*70)

# =============================== WRITE ===============================
for s in p.sheets: p.write_sheet(s)
p.write_root("Universal ESP32 Button/Signal Bridge",
             ["LOW VOLTAGE ONLY - NOT FOR 230V MAINS SWITCHING",
              "ESP32-S3-WROOM-1-N8 | SY8089 buck 3.3V | 8 iso-in, 8 PhotoMOS, 2 relay, 4 cap-inject",
              "Schematic ERC clean before PCB layout."])
p.write_libtables()
print("WROTE", ROOT, "| sheets:", len(p.sheets), "| components:", sum(_ctr.values()), _ctr)
