"""Independent expansion pin/value contract; TI manufacturer documents cited in review."""
PINS={
 'R1':{'1':'+3V3','2':'MCU_EN'},'C1':{'1':'MCU_EN','2':'GND'},
 'R3':{'1':'+3V3','2':'I2C_SCL'},'R4':{'1':'+3V3','2':'I2C_SDA'},
 'U14':{'1':'+3V3','2':'GND','3':'EXP_PWR_EN','4':'EXP_FAULT_N','5':'EXP_ILIM','6':'EXP_3V3'},
 'U33':{'1':'EXP_PWR_EN','2':'EXP_FAULT_N','3':'EXP_IO_ARM','4':'EXP_GPIO_SPARE','5':'GND','6':'MCU_EN','7':None,'8':'I2C_SCL','9':'I2C_SDA','10':'+3V3'},
 'U34':{'1':None,'2':'I2C_SCL','3':'I2C_SDA','4':'SPI_SCK','5':'SPI_MOSI','6':'SPI_MISO','7':'EXP_CS','8':'EXP_IRQ','9':'GND','10':'GND','11':'GND','12':'EXP_SW_IRQ','13':'EXP_SW_CS','14':'EXP_SW_MISO','15':'EXP_SW_MOSI','16':'EXP_SW_SCK','17':'EXP_SW_SDA','18':'EXP_SW_SCL','19':'EXP_IO_OE_N','20':'+3V3'},
 'U35':{'1':'EXP_PWR_EN','2':'EXP_IO_ARM','3':'GND','4':'GND','5':'GND','6':None,'7':'GND','8':None,'9':'GND','10':'GND','11':'GND','12':'EXP_IO_OE_N','13':'EXP_FAULT_N','14':'+3V3'},
 'R41':{'1':'EXP_ILIM','2':'GND'},'R42':{'1':'+3V3','2':'EXP_FAULT_N'},
 'R83':{'1':'EXP_PWR_EN','2':'GND'},'R84':{'1':'EXP_IO_ARM','2':'GND'},
 'R85':{'1':'EXP_GPIO_SPARE','2':'GND'},'R86':{'1':'+3V3','2':'EXP_IO_OE_N'},
 'R87':{'1':'EXP_3V3','2':'GND'},
 'J16':{'1':'GND','2':'EXP_3V3','3':'EXP_SCL','4':'EXP_SDA','5':'EXP_SCK','6':'EXP_MOSI','7':'EXP_MISO','8':'EXP_CS_PORT','9':'EXP_IRQ_PORT','10':'GND'},
 'C40':{'1':'+3V3','2':'GND'},'C41':{'1':'EXP_3V3','2':'GND'},
}
for ref in ['C91','C92','C93']:PINS[ref]={'1':'+3V3','2':'GND'}
for ref,name,port in [('R20','SCL','EXP_SCL'),('R21','SDA','EXP_SDA'),('R22','SCK','EXP_SCK'),('R23','MOSI','EXP_MOSI'),('R24','MISO','EXP_MISO'),('R25','CS','EXP_CS_PORT'),('R26','IRQ','EXP_IRQ_PORT')]:PINS[ref]={'1':'EXP_SW_'+name,'2':port}
PARTS={
 'U33':('TCA9537DGSR','TCA9537DGSR'), 'U34':('SN74CB3Q3245PWR','SN74CB3Q3245PWR'),
 'U35':('SN74HCS10PWR','SN74HCS10PWR'),
 'R42':('10k 1%','RC0402FR-0710KL'),'R83':('4.7k 1%','RC0402FR-074K7L'),
 'R84':('4.7k 1%','RC0402FR-074K7L'),'R85':('100k 1%','RC0402FR-07100KL'),
 'R86':('220k 1%','RC0402FR-07220KL'),'R87':('10k 1%','RC0402FR-0710KL'),
}
for ref in ['C91','C92','C93']:PARTS[ref]=('100nF 10% X7R 16V','GRM155R71C104KA88D')
FOOTPRINTS={'U33':'Package_SO:MSOP-10_3x3mm_P0.5mm','U34':'Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm','U35':'Package_SO:TSSOP-14_4.4x5mm_P0.65mm'}

def validate(spec,values,nets,fields):
 for ref,pins in PINS.items():
  if ref not in spec or values.get(ref)!=spec[ref]['value']:raise ValueError('Expansion value mismatch: '+ref)
  for pin,net in pins.items():
   actual=nets.get((ref,pin))
   if spec[ref]['nets'].get(pin)!=net or (actual!=net if net is not None else not actual or not actual.startswith('unconnected-(')):
    raise ValueError('Expansion pin contract: '+ref+'.'+pin)
 for ref,(value,mpn) in PARTS.items():
  if values[ref]!=value or spec[ref].get('mpn')!=mpn or fields.get(ref,{}).get('MPN')!=mpn:raise ValueError('Expansion component contract: '+ref)
 for ref,fp in FOOTPRINTS.items():
  if spec[ref]['footprint']!=fp:raise ValueError('Expansion footprint contract: '+ref)
 if values['U14']!='TPS2553DBVR' or values['R41']!='100k 1%':raise ValueError('Expansion current limiter changed')
 for ref in ['R20','R21','R22','R23','R24','R25','R26']:
  if values[ref]!='33':raise ValueError('Expansion series resistor changed: '+ref)
 for pin in ['16','26','28','29','30']:
  if spec['U1']['nets'].get(pin) is not None:raise ValueError('Reserved host pin consumed: U1.'+pin)
