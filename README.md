# DalyBmsCanPublisher
This package provides a ROS 2 Python node that queries a Daly Smart BMS over SocketCAN (e.g., can0) and publishes a human-readable status string on a ROS topic.


# DalyBmsCanPublisher

This package provides a ROS 2 Python node that queries a Daly Smart BMS over
SocketCAN (e.g. `can0`) and publishes a human-readable battery status string
on a ROS topic.

The node is intended for lightweight monitoring, logging, and debugging where
a simple text summary is sufficient.

---

## Features

- Communicates with a Daly Smart BMS via extended CAN frames
- Uses SocketCAN (`can0`, configurable)
- Publishes:
  - Pack voltage
  - Pack current (signed, with Daly offset handling)
  - State of charge (SOC)
  - Individual cell voltages
  - Temperature sensors
  - MOSFET temperature
- Rotates non-critical requests to reduce CAN bus and BMS load
- Implemented as a standard ROS 2 `ament_python` package

---

## Published Topic

Topic: `/battery/status` (default)  
Type: `std_msgs/msg/String`

Example output:
stamp=1700000000.123456789 soc=78.5% amps=-12.34A voltage=26.9V
cells=[3.842 3.840 3.841 3.839 3.843 3.842 3.841]
temp1=31C temp2=29C mos_temp=35C

yaml
Copy code

---

## Prerequisites

### ROS 2

A working ROS 2 installation (e.g. Jazzy, Iron, Humble).

source /opt/ros/<distro>/setup.bash

bash
Copy code

### SocketCAN

A configured CAN interface (example shown for 500 kbit/s):

sudo modprobe can can_raw
sudo ip link set can0 up type can bitrate 500000
ip -details link show can0

graphql
Copy code

### Python CAN library

On Debian / Ubuntu:

sudo apt install python3-can

yaml
Copy code

---

## Installation

Clone this repository into a ROS 2 workspace:
