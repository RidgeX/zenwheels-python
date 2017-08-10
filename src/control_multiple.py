#!/usr/bin/python3

from bluetooth import *
from protocol import *
import errno
import queue
import select
import sys
import threading
import time

def chunks(l, n):
  """
  Yield successive n-sized chunks from l.
  """
  for i in range(0, len(l), n):
    yield l[i:i + n]

class Car:
  def __init__(self, address, socket):
    self.address = address
    self.out_queue = queue.Queue()
    self.socket = socket

# List of MAC addresses to automatically connect to
# (Use `hcitool scan` to display available devices)
addresses = [
  '00:06:66:49:89:E3',  # MicroCar-27
  '00:06:66:61:AC:9E'   # MicroCar-58
]

# List of currently connected cars
cars = []

# Whether this is being run on a Windows machine
os_windows = (os.name == 'nt')

# Whether the communication threads are running
running = True

def discover():
  """
  Try establishing a connection for each car in the list
  that isn't already connected.
  """
  while running:
    connected = []
    for car in cars:
      connected.append(car.address)
    for address in addresses:
      if address not in connected:
        try:
          socket = BluetoothSocket(RFCOMM)
          if os_windows:
            socket.settimeout(5)
          else:
            socket.settimeout(0)
          socket.connect((address, 1))
          cars.append(Car(address, socket))
        except (BluetoothError, OSError) as e:
          if not os_windows:
            result = eval(e.args[0])
            if result[0] == errno.EINPROGRESS:
              cars.append(Car(address, socket))
    time.sleep(1)

def process():
  """
  Read incoming messages and process outgoing message queues.
  """
  while running:
    for car in cars:
      address = car.address
      out_queue = car.out_queue
      socket = car.socket
      try:
        can_read, can_write, has_error = select.select([socket], [socket], [], 0)
        if socket in can_read:
          data = socket.recv(1024)
          for msg in chunks(data, 2):
            if msg[0] == HALL_SENSOR and msg[1] == HALL_SENSOR_ON:
              print(address, 'Magnet detected')
            elif msg[0] == BATTERY:
              print(address, '{0:.1f}V'.format(msg[1] / 10.0))
        if socket in can_write:
          # TODO: Buffer messages into a single packet
          try:
            msg = out_queue.get_nowait()
          except queue.Empty:
            pass
          else:
            socket.send(msg)
      except (BluetoothError, OSError, ValueError) as e:
        socket.close()
        cars.remove(car)

def main():
  global running

  # Start communication threads
  t_discover = threading.Thread(target=discover)
  t_discover.daemon = True
  t_discover.start()
  t_process = threading.Thread(target=process)
  t_process.daemon = True
  t_process.start()

  # Main loop
  try:
    while True:
      c = sys.stdin.read(1)  # This waits until Enter is pressed
      if c == 'z':
        for car in cars:
          car.out_queue.put(bytes([THROTTLE, 0x10]))
      if c == 'x':
        for car in cars:
          car.out_queue.put(bytes([THROTTLE, 0x70]))
      if c == 'c':
        for car in cars:
          car.out_queue.put(bytes([THROTTLE, 0x0]))
      if c == 'n':
        for car in cars:
          car.out_queue.put(bytes([HEADLIGHT, HEADLIGHT_BRIGHT]))
      if c == 'm':
        for car in cars:
          car.out_queue.put(bytes([HEADLIGHT, HEADLIGHT_OFF]))
  except KeyboardInterrupt:
    # Ctrl-C pressed
    pass

  # Cleanup sockets
  print('Shutting down...')
  running = False
  t_discover.join()
  t_process.join()
  for car in cars:
    car.socket.close()

if __name__ == '__main__':
  main()
