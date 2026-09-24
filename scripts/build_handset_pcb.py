#!/usr/bin/env python3
"""Generate the reviewable handset Rev A electrical/placement work in progress.

Only writes hardware/handset-rev-a/generated. Never overwrites hand-edited boards.
Missing circuits remain explicitly open; this is not a fabrication generator.
"""
import copy
import csv
import json
import math
from pathlib import Path
import uuid

import pcbnew as pcb
from cad_sexpr import Q, child, children, dump, parse, prop

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'hardware/handset-rev-a/generated'
if (OUT/'handset.kicad_pcb').exists():
    raise SystemExit('Saved PCB exists. Edit it directly; refusing to overwrite user placement.')
OUT.mkdir(exist_ok=True)
(OUT/'Handset.pretty').mkdir(exist_ok=True)
(OUT/'previews').mkdir(exist_ok=True)
LIB = Path('/usr/share/kicad/symbols')
FPLIB = Path('/usr/share/kicad/footprints')
pcb.SwigPyIterator.next = pcb.SwigPyIterator.__next__
uid = lambda key: str(uuid.uuid5(uuid.NAMESPACE_URL, 'mesh-phone/handset-a/' + key))
mm = lambda x: pcb.FromMM(x)
vec = lambda x, y: pcb.VECTOR2I(mm(x), mm(y))
components = []
custom = {}
cache = {}

def symbol(libid):
    if libid in custom:
        return copy.deepcopy(custom[libid])
    lib, name = libid.split(':')
    if lib not in cache:
        cache[lib] = {str(s[1]): s for s in children(parse((LIB / (lib+'.kicad_sym')).read_text()), 'symbol')}
    s = copy.deepcopy(cache[lib][name])
    if child(s, 'extends'):
        raise ValueError('Resolve inherited symbol before use: '+libid)
    s[1] = Q(libid)
    return s

def make_symbol(name, pins, footprint):
    # Datasheet pin numbers; physical land pattern is independently selected.
    n = len(pins)
    height = (math.ceil(n/2)+1)*2.54
    s = parse(f'''(symbol "Handset:{name}" (pin_names (offset 0.5))
      (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 0 0) (effects (font (size 1.27 1.27))))
      (property "Value" "{name}" (at 0 -2.54 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "{footprint}" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
      (symbol "{name}_0_1" (rectangle (start -10.16 {height/2}) (end 10.16 {-height/2})
       (stroke (width 0.254) (type default)) (fill (type background)))))''')
    u = ['symbol', Q(name+'_1_1')]
    for i, (num, label, typ) in enumerate(pins):
        right = i >= math.ceil(n/2)
        j = i-math.ceil(n/2) if right else i
        y = height/2 - 2.54*(j+1)
        u.append(parse(f'(pin {typ} line (at {15.24 if right else -15.24} {y} {180 if right else 0}) (length 5.08) (name "{label}" (effects (font (size 1 1)))) (number "{num}" (effects (font (size 1 1)))))'))
    s.append(u)
    custom['Handset:'+name] = s

def add(ref, value, libid, nets, x, y, side='B', angle=0, sheet='core', footprint=None):
    s = symbol(libid)
    fp = footprint or str(prop(s, 'Footprint')[2])
    assert fp, ref
    components.append(dict(ref=ref,value=value,libid=libid,nets={str(k):v for k,v in nets.items()},
                           x=x,y=y,side=side,angle=angle,sheet=sheet,footprint=fp))

def passive(ref, value, nets, x, y, sheet='power', side='B', size='0402', angle=0):
    kind = ref[0]
    libid = {'R':'Device:R','C':'Device:C','L':'Device:L'}[kind]
    directory = {'R':'Resistor_SMD','C':'Capacitor_SMD','L':'Inductor_SMD'}[kind]
    dims = {'0402':'1005','0603':'1608','0805':'2012'}[size]
    add(ref,value,libid,dict(enumerate(nets,1)),x,y,side,angle,sheet,f'{directory}:{kind}_{size}_{dims}Metric')

def connector(ref, value, nets, x, y, count=None, side='B', angle=0, footprint=None, sheet='interfaces'):
    count = count or len(nets)
    fp = footprint or f'Connector_JST:JST_GH_BM{count:02}B-GHS-TBT_1x{count:02}-1MP_P1.25mm_Vertical'
    add(ref,value,f'Connector_Generic:Conn_01x{count:02}',dict(enumerate(nets,1)),x,y,side,angle,sheet,fp)

# Existing N16R8 module stays. GPIO35/36/37 are occupied by octal PSRAM.
gpio = {4:'GPS_HOST_TX',5:'GPS_HOST_RX',6:'GPS_PPS',7:'EXP_CS',15:'EXP_IRQ',
        16:'SX_RESET',17:'SX_BUSY',18:'SX_DIO1',8:'KEY_IRQ',9:'I2C_SCL',10:'I2C_SDA',
        11:'LCD_CS',12:'SPI_SCK',13:'SPI_MOSI',14:'SPI_MISO',21:'SX_CS',47:'CC_CS',48:'CC_GDO0',
        38:'I2S_BCLK',39:'I2S_LRCLK',40:'I2S_DOUT',41:'I2S_DIN',42:'IR_TX',2:'SD_CS',1:'NFC_CS'}
mcu = {1:'GND',2:'+3V3',3:'MCU_EN',13:'USB_D_N',14:'USB_D_P',15:None,16:None,26:None,27:'MCU_BOOT',28:None,29:None,30:None,36:'LTE_HOST_RX',37:'LTE_HOST_TX',40:'GND',41:'GND'}
for u in children(symbol('RF_Module:ESP32-S3-WROOM-1'),'symbol'):
    for p in children(u,'pin'):
        name = str(child(p,'name')[1])
        if name.startswith('IO') and name[2:].isdigit() and int(name[2:]) in gpio:
            mcu[str(child(p,'number')[1])] = gpio[int(name[2:])]
add('U1','ESP32-S3-WROOM-1-N16R8','RF_Module:ESP32-S3-WROOM-1',mcu,83,45,angle=180)
passive('R1','10k',['+3V3','MCU_EN'],73,61,sheet='core')
passive('R2','10k',['+3V3','MCU_BOOT'],76,61,sheet='core')
passive('C1','1uF',['MCU_EN','GND'],73,64,sheet='core')
passive('C2','10uF',['+3V3','GND'],80,61,sheet='core',size='0805')
passive('C3','100nF',['+3V3','GND'],83,61,sheet='core')
for ref, net, x in [('SW17','MCU_BOOT',78),('SW18','MCU_EN',87)]:
    add(ref,net,'Switch:SW_Push',{1:net,2:'GND'},x,166,side='F',sheet='core',footprint='Button_Switch_SMD:SW_SPST_TL3342')

make_symbol('TCA8418',[(i,n,'power_in' if n in ['VCC','GND','EP'] else 'bidirectional') for i,n in enumerate(
 ['ROW7','ROW6','ROW5','ROW4','ROW3','ROW2','ROW1','ROW0','COL0','COL1','COL2','COL3','COL4','COL5','COL6','COL7','COL8','COL9','GND','RESET_N','VCC','SDA','SCL','INT_N','EP'],1)],
 'Package_DFN_QFN:Texas_RTW_WQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm')
keynets = {19:'GND',20:'MCU_EN',21:'+3V3',22:'I2C_SDA',23:'I2C_SCL',24:'KEY_IRQ',25:'GND'}
for i in range(4):
    keynets[8-i] = 'KEY_ROW'+str(i)
    keynets[9+i] = 'KEY_COL'+str(i)
# Spare scanner GPIO supplies slow controls; timing-sensitive inputs stay on ESP32.
for pin,net in {1:'LCD_DC',2:'LCD_RESET',3:'TOUCH_RESET',4:'MEDIA_EN',13:'LTE_ON',14:'IR_RX',15:'TOUCH_IRQ',16:'NFC_IRQ',17:'RFID_DIN',18:'RFID_CLK'}.items():
    keynets[pin]=net
add('U2','TCA8418RTWR','Handset:TCA8418',keynets,123,119,side='F',sheet='keys')
passive('C4','100nF',['+3V3','GND'],128,119,sheet='keys',side='F')
for i,(net,x) in enumerate([('I2C_SCL',119),('I2C_SDA',122),('KEY_IRQ',125)]):
    passive('R'+str(3+i),'4.7k' if i<2 else '10k',['+3V3',net],x,115,sheet='keys',side='F')
for row,y in enumerate([111,126,141,156]):
    for col,x in enumerate([77.5,92.5,107.5,122.5]):
        add('SW'+str(row*4+col+1),str(row*4+col+1),'Switch:SW_Push',
            {1:'KEY_ROW'+str(row),2:'KEY_COL'+str(col)},x,y,side='F',sheet='keys',footprint='Button_Switch_SMD:SW_SPST_TL3342')

make_symbol('BQ25185',[(i,n,'power_in' if n in ['IN','BAT','GND','EP'] else 'passive') for i,n in enumerate(
 ['SYS','BAT','STAT2','CE_N','GND','TS_MR','ILIM_VSET','ISET','STAT1','IN','EP'],1)],
 'Package_DFN_QFN:Texas_DLH0010A_WSON-10-1EP_2.2x2mm_P0.4mm_EP0.9x1.5mm')
add('U3','BQ25185DLHR','Handset:BQ25185',{1:'VSYS',2:'VBAT',3:'CHG_STAT2',4:'GND',5:'GND',6:'BAT_TS',7:'CHG_ILIM',8:'CHG_ISET',9:'CHG_STAT1',10:'USB_VBUS',11:'GND'},121,61,sheet='power')
connector('J1','BATTERY_POLARITY_VERIFY',['VBAT','GND'],125,103,footprint='Connector_JST:JST_PH_B2B-PH-SM4-TB_1x02-1MP_P2.00mm_Vertical',sheet='power')
connector('J2','PACK_NTC_10K_B3435',['BAT_TS','GND'],118,71,sheet='power')
passive('R6','24k 1% / 4.2V 100mA input',['CHG_ILIM','GND'],118,65)
passive('R7','1k 1% / 300mA charge',['CHG_ISET','GND'],121,65)
for ref,val,net,x,y in [('C5','1uF','USB_VBUS',125,64),('C6','10uF','VSYS',118,58),('C7','1uF','VBAT',122,58)]:
    passive(ref,val,[net,'GND'],x,y,size='0805' if val=='10uF' else '0402')

# USB-C remains native USB2 to ESP32. Modem USB must terminate on its adapter.
usbfp='Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal'
add('USB1','USB4105','Connector:USB_C_Receptacle_USB2.0_16P',
 {'A1':'GND','A4':'USB_VBUS','A5':'USB_CC1','A6':'USB_D_P','A7':'USB_D_N','A8':None,'A9':'USB_VBUS','A12':'GND',
  'B1':'GND','B4':'USB_VBUS','B5':'USB_CC2','B6':'USB_D_P','B7':'USB_D_N','B8':None,'B9':'USB_VBUS','B12':'GND','SH':'GND'},
 130,56,side='F',angle=90,sheet='core',footprint=usbfp)
passive('R8','5.1k 1%',['USB_CC1','GND'],124,55,sheet='core',side='F')
passive('R9','5.1k 1%',['USB_CC2','GND'],124,58,sheet='core',side='F')

sx={1:'SX_VREG',2:'GND',3:'SX_XTA',4:'SX_XTB',5:'GND',6:'SX_TCXO_PWR',7:'SX_VREG',8:'GND',9:'SX_DCC_SW',10:'+3V3',11:'+3V3',12:'SX_RF_SW',13:'SX_DIO1',14:'SX_BUSY',15:'SX_RESET',16:'SPI_MISO',17:'SPI_MOSI',18:'SPI_SCK',19:'SX_CS',20:'GND',21:'SX_RFI_P',22:'SX_RFI_N',23:'SX_RFO',24:'SX_VR_PA',25:'GND'}
add('U4','SX1262IMLTRT','RF:SX1262IMLTRT',sx,113,36,sheet='radios')
for ref,net,x,y in [('C8','+3V3',110,39),('C9','SX_VREG',113,40),('C10','SX_VR_PA',117,37)]:
    passive(ref,'100nF',[net,'GND'],x,y,sheet='radios')
passive('R10','10k',['+3V3','SX_CS'],110,42,sheet='radios')
make_symbol('CC1101',[(i,n,'power_in' if n in ['DVDD','AVDD','DGUARD','GND','EP'] else 'bidirectional') for i,n in enumerate(
 ['SCLK','SO','GDO2','DVDD','DCOUPL','GDO0','CS_N','XOSC_Q1','AVDD','XOSC_Q2','AVDD','RF_P','RF_N','AVDD','AVDD','GND','RBIAS','DGUARD','GND','SI','EP'],1)],
 'Package_DFN_QFN:Texas_RGP0020D_VQFN-20-1EP_4x4mm_P0.5mm_EP2.7x2.7mm')
add('U5','CC1101RGPR','Handset:CC1101',{1:'SPI_SCK',2:'SPI_MISO',3:'CC_GDO2',4:'+3V3',5:'CC_DCOUPL',6:'CC_GDO0',7:'CC_CS',8:'CC_X1',9:'+3V3',10:'CC_X2',11:'+3V3',12:'CC_RF_P',13:'CC_RF_N',14:'+3V3',15:'+3V3',16:'GND',17:'CC_RBIAS',18:'+3V3',19:'GND',20:'SPI_MOSI',21:'GND'},125,36,sheet='radios')
passive('R11','56k 1%',['CC_RBIAS','GND'],127,40,sheet='radios')
passive('R12','10k',['+3V3','CC_CS'],123,42,sheet='radios')
passive('C11','100nF',['CC_DCOUPL','GND'],122,39,sheet='radios')
passive('C12','100nF',['+3V3','GND'],129,38,sheet='radios')

add('U6','MAX98357AETE+','Audio:MAX98357A',{1:'I2S_DOUT',2:None,3:'GND',4:'MEDIA_EN',5:None,6:None,7:'+3V3',8:'+3V3',9:'SPK_P',10:'SPK_N',11:'GND',12:None,13:None,14:'I2S_LRCLK',15:'GND',16:'I2S_BCLK',17:'GND'},73,76,sheet='audio')
passive('C13','100nF',['+3V3','GND'],77,76,sheet='audio')
passive('C14','10uF',['+3V3','GND'],73,80,sheet='audio',size='0805')
passive('R13','100k',['MEDIA_EN','GND'],76,80,sheet='audio')
connector('J3','MEDIA_SPEAKER_DIFFERENTIAL',['SPK_P','SPK_N'],73,69,sheet='audio')
add('MK1','SPH0645LM4H-1','Sensor_Audio:SPH0645LM4H',{1:'I2S_LRCLK',2:'GND',3:'GND',4:'I2S_BCLK',5:'+3V3',6:'I2S_DIN'},100,168,side='F',sheet='audio')
passive('C15','100nF',['+3V3','GND'],104,168,sheet='audio',side='F')
connector('J4','CALL_AUDIO_FROM_MODEM_ADAPTER',['CALL_SPK_P','CALL_SPK_N','CALL_MIC_P','CALL_MIC_N'],85,69,sheet='audio')
connector('J5','CALL_EARPIECE',['CALL_SPK_P','CALL_SPK_N'],73,86,sheet='audio')
connector('J6','CALL_MIC',['CALL_MIC_P','CALL_MIC_N'],74,158,sheet='audio')

# J16 pin order preserves the Rev F cable contract. Signals require protection.
connector('J16','EXPANSION_J16',['GND','EXP_3V3','EXP_SCL','EXP_SDA','EXP_SCK','EXP_MOSI','EXP_MISO','EXP_CS_PORT','EXP_IRQ_PORT','GND'],100,72)
for i,(a,b) in enumerate([('I2C_SCL','EXP_SCL'),('I2C_SDA','EXP_SDA'),('SPI_SCK','EXP_SCK'),('SPI_MOSI','EXP_MOSI'),('SPI_MISO','EXP_MISO'),('EXP_CS','EXP_CS_PORT'),('EXP_IRQ','EXP_IRQ_PORT')]):
    passive('R'+str(20+i),'33',[a,b],94+i*2,78,sheet='interfaces')
connector('J7','PIM447_HARNESS_VERIFY',['+3V3','GND','I2C_SDA','I2C_SCL','TRACKBALL_INT','GND'],121,89)
connector('J8','MODEM_ADAPTER_3V3_LOGIC',['GND','LTE_HOST_TX','LTE_HOST_RX','LTE_ON','GND','MODEM_STATUS'],100,52)
connector('J9','MODEM_POWER_ADAPTER_REQUIRED',['MODEM_SUPPLY','GND','MODEM_SUPPLY','GND'],110,61)
# Do not connect MODEM_SUPPLY to VSYS: charger SYS can exceed A7672's 4.2V max.

# TPS63802 DLA0010A land pattern: TI drawing 4223750/D, datasheet p36.
# Unlike a generic DFN, right-side power pads have unequal lengths.
dla=pcb.FOOTPRINT(None)
dla.SetReference('REF**'); dla.SetValue('TPS63802DLA')
dla.SetAttributes(pcb.FP_SMD)
for number in range(1,11):
    left=number<=5
    px=-.9 if left else (.55 if number==8 else .75)
    py=(number-1)*.5-1 if left else (10-number)*.5-1
    p=pcb.PAD(dla); p.SetNumber(str(number));p.SetAttribute(pcb.PAD_ATTRIB_SMD)
    p.SetShape(pcb.PAD_SHAPE_ROUNDRECT);p.SetRoundRectRadiusRatio(.2)
    p.SetSize(vec(.6 if left else (1.3 if number==8 else .9),.25))
    layers=pcb.LSET()
    for layer in [pcb.F_Cu,pcb.F_Paste,pcb.F_Mask]: layers.AddLayer(layer)
    p.SetPosition(vec(px,py));p.SetLayerSet(layers);dla.Add(p)
for layer,w,h in [(pcb.F_Fab,2,3),(pcb.F_CrtYd,2.9,3.5)]:
    outline=pcb.PCB_SHAPE(dla);outline.SetShape(pcb.SHAPE_T_RECT)
    outline.SetStart(vec(-w/2,-h/2));outline.SetEnd(vec(w/2,h/2));outline.SetLayer(layer);outline.SetWidth(mm(.05));dla.Add(outline)
dla.SetFPID(pcb.LIB_ID('Handset','TPS63802_DLA0010A'))
pcb.PCB_IO_KICAD_SEXPR().FootprintSave(str(OUT/'Handset.pretty'),dla)
make_symbol('TPS63802',[(i,n,'power_out' if n=='VOUT' else 'power_in' if n in ['VIN','GND','AGND'] else 'passive') for i,n in enumerate(
 ['EN','MODE','AGND','FB','PG','VOUT','L2','GND','L1','VIN'],1)],'Handset:TPS63802_DLA0010A')
add('U7','TPS63802DLAR','Handset:TPS63802',{1:'SYS_EN',2:'GND',3:'GND',4:'REG3_FB',5:'REG3_PG',6:'+3V3',7:'REG3_L2',8:'GND',9:'REG3_L1',10:'VSYS'},124,131,sheet='power')
add('SW19','POWER','Switch:SW_SPDT',{1:'VSYS',2:'SYS_EN',3:'GND'},70,41,side='F',angle=90,sheet='power',footprint='Button_Switch_SMD:SW_SPDT_PCM12')
passive('R30','100k',['SYS_EN','GND'],120,133)
passive('R31','560k 1%',['+3V3','REG3_FB'],121,136)
passive('R32','100k 1%',['REG3_FB','GND'],124,136)
passive('R33','100k',['+3V3','REG3_PG'],128,136)
passive('L1','0.47uH / Isat >=5.5A / exact MPN pending',['REG3_L1','REG3_L2'],128,131,size='0805',angle=90)
passive('C20','10uF',['VSYS','GND'],120,129,size='0805')
passive('C21','22uF',['+3V3','GND'],122,139,size='0805')
passive('C22','22uF',['+3V3','GND'],126,139,size='0805')
make_symbol('MAX17048',[(i,n,'power_in' if n in ['CTG','CELL','VDD','GND','EP'] else 'bidirectional') for i,n in enumerate(
 ['CTG','CELL','VDD','GND','ALRT','QSTRT','SCL','SDA','EP'],1)],'Package_DFN_QFN:TDFN-8-1EP_2x2mm_P0.5mm_EP0.8x1.2mm')
add('U8','MAX17048G+T','Handset:MAX17048',{1:'GND',2:'VBAT',3:'VBAT',4:'GND',5:None,6:'GND',7:'I2C_SCL',8:'I2C_SDA',9:'GND'},126,112,sheet='power')
passive('C23','100nF',['VBAT','GND'],129,112)

# LF frontend is retained with explicit unfinished timing/level-shift/coil nets.
add('U9','HTRC11001T','RF_RFID:HTRC11001T',{1:'GND',2:'LF_TX2',3:'+5V_RF',4:'LF_TX1',5:'LF_MODE',6:'LF_X1',7:'LF_X2',8:'LF_CLK_5V',9:'LF_DIN_5V',10:'LF_DOUT_5V',12:'LF_CEXT',13:'LF_QGND',14:'LF_RX'},73,137,sheet='radios')
passive('C24','100nF',['+5V_RF','GND'],78,137,sheet='radios')
connector('J10','LF_COIL_TUNING_REQUIRED',['LF_COIL_A','LF_COIL_B'],73,148)

# TPS61023 uses a real 6-pin SOT563; this rail is ONLY for the LF frontend.
make_symbol('TPS61023',[(i,n,'power_out' if n=='VOUT' else 'power_in' if n in ['VIN','GND'] else 'passive') for i,n in enumerate(
 ['FB','EN','VIN','GND','SW','VOUT'],1)],'Package_TO_SOT_SMD:SOT-563')
add('U10','TPS61023DRLR','Handset:TPS61023',{1:'REG5_FB',2:'SYS_EN',3:'VSYS',4:'GND',5:'REG5_SW',6:'+5V_RF'},73,119,sheet='power')
passive('L2','1uH / exact current-rated MPN pending',['VSYS','REG5_SW'],77,119,size='0805')
passive('R34','732k 1%',['+5V_RF','REG5_FB'],71,123)
passive('R35','100k 1%',['REG5_FB','GND'],74,123)
passive('C25','10uF',['VSYS','GND'],72,115,size='0805')
passive('C26','22uF',['+5V_RF','GND'],77,123,size='0805')
make_symbol('TPS62840',[(i,n,'power_in' if n in ['VIN','GND'] else 'passive') for i,n in enumerate(
 ['GND','VIN','MODE','EN','VSET','STOP','SW','VOS'],1)],'Package_SON:VSON-8_1.5x2mm_P0.5mm')
add('U11','TPS62840DLCR','Handset:TPS62840',{1:'GND',2:'+3V3',3:'GND',4:'+3V3',5:'GND',6:'GND',7:'REG18_SW',8:'+1V8'},123,96,sheet='power')
passive('L3','2.2uH / current-rated MPN pending',['REG18_SW','+1V8'],127,96,size='0805')
passive('C27','4.7uF',['+3V3','GND'],120,96,size='0603')
passive('C28','10uF',['+1V8','GND'],117,99,size='0805')

# Mechanical drawing zones explicitly have NO pads and never count as fitted ICs.
reservations = [
 ('GNSS UBX-M10050 + RF / 1V8',114,47,17,9,'B'),
 ('NFC ST25R3916B + matching',121,80,15,11,'B'),
 ('LF timing / matching / level shifts',73,129,10,6,'B'),
 ('IR TX and RX harness',101,33,9,6,'B'),
 ('LCD FPC ordering code TBD',100,67,20,6,'F'),
 ('microSD 504077-1891 TBD',124,101,16,14,'F'),
 ('J16 load switch and ESD',78,97,10,10,'B'),
 ('Modem regulated supply',100,61,10,8,'B'),
]

board=pcb.BOARD()
board.SetCopperLayerCount(4)
board.GetDesignSettings().SetBoardThickness(mm(1.6))
nets={}
for c in components:
    for name in c['nets'].values():
        if name and name not in nets:
            net=pcb.NETINFO_ITEM(board,name)
            board.Add(net)
            nets[name]=net

def line(a,b,layer=pcb.Edge_Cuts,width=.05):
    item=pcb.PCB_SHAPE()
    item.SetShape(pcb.SHAPE_T_SEGMENT)
    item.SetStart(vec(*a)); item.SetEnd(vec(*b)); item.SetLayer(layer); item.SetWidth(mm(width)); board.Add(item)

def polygon(points,layer=pcb.Edge_Cuts):
    for a,b in zip(points,points[1:]+points[:1]): line(a,b,layer)

# Board origin (100,100) matches case (0,0), with Y inverted.
polygon([(68.5,29),(131.5,29),(133,30.5),(133,169.5),(131.5,171),(68.5,171),(67,169.5),(67,30.5)])
# Square cutout is a conservative envelope for the rounded case aperture.
polygon([(86.5,80),(113.5,80),(113.5,104),(86.5,104)])
for i,(x,y) in enumerate([(69.5,32),(130.5,32),(69.5,168),(130.5,168)],1):
    fp=pcb.FootprintLoad(str(FPLIB/'MountingHole.pretty'),'MountingHole_2.2mm_M2')
    fp.SetReference('H'+str(i)); fp.SetPosition(vec(x,y)); board.Add(fp)

def text(value,x,y,layer=pcb.Dwgs_User,size=1):
    t=pcb.PCB_TEXT(board); t.SetText(value); t.SetPosition(vec(x,y)); t.SetLayer(layer)
    t.SetTextSize(vec(size,size)); t.SetTextThickness(mm(.15)); board.Add(t)

for c in components:
    lib,name=c['footprint'].split(':')
    fp=pcb.FootprintLoad(str(OUT/'Handset.pretty' if lib=='Handset' else FPLIB/(lib+'.pretty')),name)
    if not fp: raise ValueError(c['footprint'])
    fp.SetReference(c['ref']); fp.SetValue(c['value'])
    fp.SetFPID(pcb.LIB_ID(lib,name)); fp.SetPosition(vec(c['x'],c['y']))
    board.Add(fp)
    if c['side']=='B': fp.Flip(vec(c['x'],c['y']),False)
    fp.SetOrientationDegrees(c['angle'])
    path=pcb.KIID_PATH()
    path.push_back(pcb.KIID(uid('root'))); path.push_back(pcb.KIID(uid('sheet/'+c['sheet'])))
    path.push_back(pcb.KIID(uid(c['ref'])))
    fp.SetPath(path)
    for p in fp.Pads():
        name=c['nets'].get(p.GetNumber())
        if name: p.SetNet(nets[name])
    fp.Reference().SetTextSize(vec(.8,.8)); fp.Reference().SetTextThickness(mm(.12))
    fp.Value().SetVisible(False)

# Route the fixed switch matrix first: row buses on F.Cu, columns on In2.Cu.
# Controller fanout and every other net remain visibly unrouted.
def track(net, a, b, layer, width=.2):
    t=pcb.PCB_TRACK(board); t.SetStart(vec(*a));t.SetEnd(vec(*b))
    t.SetWidth(mm(width));t.SetLayer(layer);t.SetNet(nets[net]);board.Add(t)
for row,y in enumerate([111,126,141,156]):
    track('KEY_ROW'+str(row),(74.35,y-1.9),(125.65,y-1.9),pcb.F_Cu)
    for col,x in enumerate([77.5,92.5,107.5,122.5]):
        net='KEY_COL'+str(col)
        track(net,(x-3.15,y+1.9),(x+3.15,y+1.9),pcb.F_Cu)
        v=pcb.PCB_VIA(board);v.SetPosition(vec(x,y+1.9));v.SetWidth(mm(.6));v.SetDrill(mm(.3))
        v.SetViaType(pcb.VIATYPE_THROUGH);v.SetLayerPair(pcb.F_Cu,pcb.B_Cu);v.SetNet(nets[net]);board.Add(v)
for col,x in enumerate([77.5,92.5,107.5,122.5]):
    track('KEY_COL'+str(col),(x,112.9),(x,157.9),pcb.In2_Cu)
for label,x,y,w,h,side in reservations:
    layer=pcb.User_1 if side=='B' else pcb.User_2
    polygon([(x-w/2,y-h/2),(x+w/2,y-h/2),(x+w/2,y+h/2),(x-w/2,y+h/2)],layer)
    text(label,x,y,layer,.6)
text('HANDSET REV A - ELECTRICAL WIP - NOT FOR FAB',100,176,size=1.2)
text('66 x 142 mm / 4 layers / 1.6 mm',100,179)
text('PIM447 CUTOUT',100,92,size=1)
polygon([(81,105.5),(119,105.5),(119,172.5),(81,172.5)],pcb.User_3)
text('BATTERY BELOW / BACK HEIGHT LIMIT 2.4 mm',100,151,pcb.User_3,.7)
pcb.SaveBoard(str(OUT/'handset.kicad_pcb'),board)

# Hierarchical sheets share global net names, so label scope is unambiguous.
rootid=uid('root')
root=parse(f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{rootid}") (paper "A3") (lib_symbols))')
sheetnames=list(dict.fromkeys(c['sheet'] for c in components))
for si,sheetname in enumerate(sheetnames):
    sid=uid('sheet/'+sheetname)
    sheet=parse(f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{sid}") (paper "A2") (lib_symbols))')
    libs=child(sheet,'lib_symbols')
    placed=[c for c in components if c['sheet']==sheetname]
    added=set()
    for i,c in enumerate(placed):
        s=symbol(c['libid'])
        if c['libid'] not in added: libs.append(s); added.add(c['libid'])
        x=63.5+(i%6)*88.9; y=76.2+(i//6)*63.5
        top=y-max(float(child(p,'at')[2]) for u in children(s,'symbol') for p in children(u,'pin'))-7.62
        inst=parse(f'''(symbol (lib_id "{c['libid']}") (at {x} {y} 0) (unit 1)
           (in_bom yes) (on_board yes) (dnp no) (uuid "{uid(c['ref'])}")
           (property "Reference" "{c['ref']}" (at {x} {top} 0) (effects (font (size 1.27 1.27))))
           (property "Value" {json.dumps(c['value'])} (at {x} {top+2.54} 0) (effects (font (size 1 1))))
           (property "Footprint" "{c['footprint']}" (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))
           (instances (project "handset" (path "/{rootid}/{sid}" (reference "{c['ref']}") (unit 1)))))''')
        for unit in children(s,'symbol'):
            for pin in children(unit,'pin'):
                num=str(child(pin,'number')[1]); at=child(pin,'at')
                px=x+float(at[1]); py=y-float(at[2]); angle=float(at[3])
                inst.append(parse(f'(pin "{num}" (uuid "{uid(c["ref"]+"/"+num)}"))'))
                net=c['nets'].get(num)
                if net:
                    ex=px-5.08*math.cos(math.radians(angle)); ey=py+5.08*math.sin(math.radians(angle))
                    sheet.append(parse(f'(wire (pts (xy {px} {py}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid "{uid(c["ref"]+"/wire/"+num)}"))'))
                    sheet.append(parse(f'(global_label "{net}" (shape input) (at {ex} {ey} {angle}) (effects (font (size 0.9 0.9)) (justify left)) (uuid "{uid(c["ref"]+"/label/"+num)}"))'))
                elif num in c['nets']:
                    sheet.append(parse(f'(no_connect (at {px} {py}) (uuid "{uid(c["ref"]+"/nc/"+num)}"))'))
        sheet.append(inst)
    sheet.append(parse(f'(text "REV A WORK IN PROGRESS: missing support circuits remain open; see README." (at 25 25 0) (effects (font (size 1.5 1.5)) (justify left)) (uuid "{uid(sheetname+"/note")}"))'))
    (OUT/(sheetname+'.kicad_sch')).write_text(dump(sheet)+'\n')
    x=30+(si%3)*120; y=55+(si//3)*65
    root.append(parse(f'''(sheet (at {x} {y}) (size 90 40) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0))
       (uuid "{sid}") (property "Sheetname" "{sheetname}" (at {x} {y-1} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
       (property "Sheetfile" "{sheetname}.kicad_sch" (at {x} {y+41} 0) (effects (font (size 1.27 1.27)) (justify left top)))
       (instances (project "handset" (path "/{rootid}" (page "{si+2}")))))'''))
root.append(parse(f'(text "HANDSET REV A / NOT FOR FABRICATION / core placement and partial circuits" (at 25 25 0) (effects (font (size 2 2)) (justify left)) (uuid "{uid("title")}"))'))
root.append(parse(f'(sheet_instances (path "/" (page "1")))'))
(OUT/'handset.kicad_sch').write_text(dump(root)+'\n')
(OUT/'handset.kicad_pro').write_text(json.dumps({'meta':{'filename':'handset.kicad_pro','version':1},'board':{'design_settings':{'rules':{'min_clearance':.15,'min_track_width':.15,'min_through_hole_diameter':.3}}},'net_settings':{'classes':[{'name':'Default','clearance':.15,'track_width':.2,'via_diameter':.6,'via_drill':.3}]}},indent=2)+'\n')
library_symbols=[]
for original in custom.values():
    s=copy.deepcopy(original)
    s[1]=Q(str(s[1]).split(':',1)[1])
    library_symbols.append(s)
(OUT/'Handset.kicad_sym').write_text(dump(['kicad_symbol_lib',['version','20250114'],['generator',Q('kicad_symbol_editor')]]+library_symbols)+'\n')
(OUT/'sym-lib-table').write_text('(sym_lib_table (lib (name "Handset") (type "KiCad") (uri "${KIPRJMOD}/Handset.kicad_sym") (options "") (descr "Datasheet-derived WIP symbols")))\n')
(OUT/'fp-lib-table').write_text('(fp_lib_table (lib (name "Handset") (type "KiCad") (uri "${KIPRJMOD}/Handset.pretty") (options "") (descr "Manufacturer land patterns")))\n')
with (OUT/'placement.csv').open('w') as f:
    writer=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet']);writer.writeheader()
    writer.writerows({k:c[k] for k in writer.fieldnames} for c in components)
(OUT/'connectivity.json').write_text(json.dumps(components,indent=2)+'\n')
(OUT/'reservations.json').write_text(json.dumps(reservations,indent=2)+'\n')
print(f'{len(components)} components; {len(nets)} nets; {len(sheetnames)} sheets; {len(reservations)} unresolved placement zones')
