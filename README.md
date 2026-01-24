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

---

## Prerequisites

### ROS 2

A working ROS 2 installation (e.g. Jazzy, Iron, Humble).
```bash
source /opt/ros/<distro>/setup.bash
```

### SocketCAN

A configured CAN interface (example shown for 250 kbit/s):
```bash
sudo ip link set can0 down
sudo ip link set can0 up type can bitrate 250000
sudo ip link set can0 up
```

### Python CAN library

On Debian / Ubuntu:
```bash
sudo apt install python3-can
```

---

## Installation

Clone this repository into a ROS 2 workspace:
```bash
mkdir -p ~/ros_ws/src
cd ~/ros_ws/src
git clone https://github.com/RIPLaboratoryUH/DalyBmsCanPublisher.git
```
Build the package:
```bash
cd ~/ros_ws
colcon build --packages-select daly_bms_can
source install/setup.bash
```

---

## Running the Node

Run with default parameters:
```bash
ros2 run daly_bms_can daly_bms_can_publisher
```

Run with custom parameters:
```bash
ros2 run daly_bms_can daly_bms_can_publisher --ros-args
-p channel:=can0
-p topic:=/battery/status
-p period_s:=0.5
```

Verify output:
```bash
ros2 topic echo /battery/status
```

---

## Parameters

- channel (string, default: `can0`)
  SocketCAN interface name

- topic (string, default: `/battery/status`)
  ROS topic used for publishing

- period_s (double, default: `1.0`)
  Publish period in seconds

---

## Notes

- `NUM_STRINGS` is set to 7 by default.
  Update this value in the source if your battery has a different series count.
- This node publishes a String message for simplicity.
  It can be extended to publish a structured custom message if needed.
- If you see repeated `No 0x90 response` warnings, verify:
  - CAN bitrate
  - Wiring
  - Daly CAN protocol compatibility
  - That the BMS is powered and active on the bus

---

## License

MIT License
