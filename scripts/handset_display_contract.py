"""Independent pin contract for the selected display-domain parts (TI pin tables)."""
PARTS={'U28':'TPS7A2030PDBVR','U29':'SN74LVC244APWR','U30':'SN74LVC2G125DCUR','U31':'TCA9406DCUR'}
PINS={
 'U28':{1:'+5V_RF',2:'GND',3:'SYS_EN',4:None,5:'LCD_3V0'},
 'U29':{1:'GND',2:'SPI_SCK',3:None,4:'SPI_MOSI',5:None,6:'LCD_CS',7:'PANEL_TOUCH_RESET',8:'LCD_DC',9:'PANEL_LCD_RESET',10:'GND',11:'LCD_RESET',12:'PANEL_LCD_DC',13:'TOUCH_RESET',14:'PANEL_LCD_CS',15:'GND',16:'PANEL_SPI_MOSI',17:'GND',18:'PANEL_SPI_SCK',19:'GND',20:'LCD_3V0'},
 'U30':{1:'LCD_CS',2:'PANEL_SPI_MISO',3:'TOUCH_IRQ',4:'GND',5:'PANEL_TOUCH_IRQ',6:'SPI_MISO',7:'GND',8:'+3V3'},
 'U31':{1:'I2C_SDA',2:'GND',3:'LCD_3V0',4:'PANEL_I2C_SDA',5:'PANEL_I2C_SCL',6:'LCD_3V0',7:'+3V3',8:'I2C_SCL'},
 'J26':{1:'+5V_RF',7:'LCD_3V0',8:'LCD_3V0',9:'LCD_3V0',10:'PANEL_LCD_RESET',33:'PANEL_SPI_MISO',34:'PANEL_SPI_MOSI',35:'LCD_3V0',36:'PANEL_LCD_DC',37:'PANEL_SPI_SCK',38:'PANEL_LCD_CS',40:'LCD_3V0',41:'LCD_3V0',42:'LCD_3V0',44:'PANEL_I2C_SCL',45:'PANEL_I2C_SDA',46:'PANEL_TOUCH_IRQ',47:'PANEL_TOUCH_RESET'},
 'R58':{1:'+3V3',2:'LCD_CS'},
 'R80':{1:'PANEL_SPI_MISO',2:'GND'},'R81':{1:'LCD_3V0',2:'PANEL_TOUCH_IRQ'},
 **{ref:{1:rail,2:'GND'} for ref,rail in [('C47','LCD_3V0'),('C48','LCD_3V0'),('C84','+5V_RF'),('C85','LCD_3V0'),('C86','LCD_3V0'),('C87','+3V3'),('C88','LCD_3V0'),('C89','+3V3')]},
}

def validate(spec,values,nets):
 for ref,value in PARTS.items():
  if values.get(ref)!=value or spec[ref]['value']!=value:
   raise ValueError('Display part model changed: '+ref)
 for ref,pins in PINS.items():
  for pin,expected in pins.items():
   actual=nets.get((ref,str(pin)))
   if spec[ref]['nets'].get(str(pin))!=expected or (actual!=expected if expected else not (actual or '').startswith('unconnected-(')):
    raise ValueError('Display topology changed: '+ref+'.'+str(pin))
