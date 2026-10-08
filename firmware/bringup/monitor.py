#!/usr/bin/env python3
"""Line-oriented USB monitor; does not flash or automatically start scanning."""
import argparse,sys,threading
import serial

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('port');args=parser.parse_args()
 device=serial.Serial(port=None,baudrate=115200,timeout=0.1,write_timeout=1)
 device.dtr=False;device.rts=False;device.port=args.port
 stopped=threading.Event()
 def receive():
  try:
   while not stopped.is_set():
    data=device.read(1024)
    if data:sys.stdout.write(data.decode('utf-8',errors='replace'));sys.stdout.flush()
  except (serial.SerialException,OSError) as error:
   print('\nUSB disconnected: '+str(error),file=sys.stderr);stopped.set()
 device.open();reader=threading.Thread(target=receive,daemon=True);reader.start()
 print('Commands: start (all keys released), stop, status. Ctrl-C exits.',flush=True)
 try:
  for line in sys.stdin:
   if stopped.is_set():break
   device.write(line.rstrip('\r\n').encode('ascii')+b'\n')
 except (KeyboardInterrupt,serial.SerialException,OSError,UnicodeEncodeError) as error:
  print('\nMonitor stopped: '+str(error),file=sys.stderr)
 finally:
  stopped.set();reader.join(timeout=1);device.close()
if __name__=='__main__':main()
