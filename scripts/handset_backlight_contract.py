"""Independent CAT4004A topology and current-setting contract (onsemi rev3)."""
import math
PINS={
 'U32':{'1':'LCD_BL_GATE','2':'GND','3':'LCD_K1','4':'LCD_K2','5':'LCD_K3','6':'LCD_K4','7':'LCD_BL_RSET','8':'+5V_RF','9':'GND'},
 'R82':{'1':'LCD_BL_RSET','2':'GND'},'C90':{'1':'+5V_RF','2':'GND'},
 'R56':{'1':'LCD_BL_EN','2':'LCD_BL_GATE'},'R57':{'1':'LCD_BL_GATE','2':'GND'},
 'U2':{'14':'LCD_BL_EN'},'J26':{'1':'+5V_RF','2':'LCD_K1','3':'LCD_K2','4':'LCD_K3','5':'LCD_K4'},
}
PARTS={'U32':('CAT4004AHU2-GT3','CAT4004AHU2-GT3'),'R82':('4.99k 1%','RC0402FR-074K99L'),'C90':('1uF 10% X7R 25V','GRM188R71E105KA12D')}

def validate(spec,values,nets,fields):
 for ref in ['Q2','R52','R53','R54','R55']:
  if ref in spec or ref in values:raise ValueError('Superseded backlight part: '+ref)
 for ref,pins in PINS.items():
  if ref not in spec or values.get(ref)!=spec[ref]['value']:raise ValueError('Backlight CAD value mismatch: '+ref)
  for pin,net in pins.items():
   if spec[ref]['nets'].get(pin)!=net or nets.get((ref,pin))!=net:raise ValueError('Re-audit backlight topology: '+ref+'.'+pin)
 for ref,(value,mpn) in PARTS.items():
  if values.get(ref)!=value or spec[ref].get('mpn')!=mpn or fields.get(ref,{}).get('MPN')!=mpn:raise ValueError('Re-audit backlight part: '+ref)
 if values['R56']!='100' or values['R57']!='100k':raise ValueError('Backlight default-off network changed')
 if spec['U32']['footprint']!='Handset:CAT4004A_UDFN-8_2x2mm_P0.5mm_EP1x1.73mm':raise ValueError('Backlight footprint changed')

def screening(vmax):
 if not math.isfinite(vmax) or not 2.4<=vmax<=5.5:raise ValueError('Backlight rail outside recommended VIN range')
 nominal=125*.6/4990
 # Deliberately NOT a guaranteed limit: gain and drift are not bounded here.
 screen=125*.63/(4990*.99)*1.05
 return dict(driver='CAT4004AHU2-GT3',rset_ohms=4990,nominal_channel_a=nominal,
  nominal_total_a=4*nominal,conditional_channel_screen_a=screen,
  conditional_total_screen_a=4*screen,conditional_zero_vf_led_sink_power_w=vmax*4*screen,
  guaranteed_maximum_current_a=None,qualified_input_peak_a=None,
  screening_conditions='Typical gain 125; VRSET maximum 0.63V; RSET -1%; +5% channel mismatch applied conservatively. Gain variation and temperature drift unbounded; excludes IC supply current and transients.',
  control='U2 GPIO on/off only. Initialize low >=10ms, then hold high. EN/DIM uses counted pulses, not ordinary PWM; dimming disabled pending timing qualification.',
  thermal_status='LED-short heat, exposed-pad assembly, copper thermal resistance and normal operation temperature require qualification. Typical 150C thermal shutdown exceeds 125C junction rating and is not a normal operating limit.')
