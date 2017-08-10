#!/usr/bin/python3

from bluetooth import *
from protocol import *
import sys
import threading

def chunks(l, n):
  """
  Yield successive n-sized chunks from l.
  """
  for i in range(0, len(l), n):
    yield l[i:i + n]

# MAC address to connect to
address = '00:06:66:61:AC:9E'  # MicroCar-58

# Whether the processing thread is running
running = True

def process(socket):
  while running:
    data = socket.recv(1024)
    for msg in chunks(data, 2):
      if msg[0] == HALL_SENSOR and msg[1] == HALL_SENSOR_ON:
        print('Magnet detected')
      elif msg[0] == BATTERY:
        print('{0:.1f}V'.format(msg[1] / 10.0))

def main():
  global running

  # Open connection
  socket = BluetoothSocket(RFCOMM)
  socket.connect((address, 1))

  # Start processing thread
  t_process = threading.Thread(target=process, args=(socket,))
  t_process.daemon = True
  t_process.start()

  # Main loop
  try:
    while True:
      c = sys.stdin.read(1)  # This waits until Enter is pressed
      if c == 'z':
        socket.send(bytes([THROTTLE, 0x10]))
      if c == 'x':
        socket.send(bytes([THROTTLE, 0x70]))
      if c == 'c':
        socket.send(bytes([THROTTLE, 0x0]))
      if c == 'n':
        socket.send(bytes([HEADLIGHT, HEADLIGHT_BRIGHT]))
      if c == 'm':
        socket.send(bytes([HEADLIGHT, HEADLIGHT_OFF]))
  except KeyboardInterrupt:
    # Ctrl-C pressed
    pass

  # Cleanup socket
  print('Shutting down...')
  running = False
  t_process.join()
  socket.close()

if __name__ == '__main__':
  main()
