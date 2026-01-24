#!/usr/bin/env python3
import time
import struct
import can

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

CHANNEL = "can0"
PC   = 0x40
BMS  = 0x01
PRIO = 0x18
NUM_STRINGS = 7

# Daly current encoding (your confirmed layout)
CURRENT_WORD_OFFSET = 4
CURRENT_ZERO_OFFSET = 30000
CURRENT_SCALE_A_PER_LSB = 0.1

def can_id(did, rx, tx):
    return (PRIO << 24) | (did << 16) | (rx << 8) | tx

def parse_id(arbid):
    return (
        (arbid >> 24) & 0xFF,
        (arbid >> 16) & 0xFF,
        (arbid >> 8) & 0xFF,
        arbid & 0xFF
    )

def u16be(b, o): return struct.unpack_from(">H", b, o)[0]

class DalyBmsCanPublisher(Node):
    def __init__(self):
        super().__init__('daly_bms_can_publisher')

        self.declare_parameter('channel', CHANNEL)
        self.declare_parameter('topic', '/battery/status')
        self.declare_parameter('period_s', 1.0)

        channel = self.get_parameter('channel').get_parameter_value().string_value
        topic   = self.get_parameter('topic').get_parameter_value().string_value
        period  = self.get_parameter('period_s').get_parameter_value().double_value

        self.bus = can.interface.Bus(channel=channel, bustype="socketcan")

        self.pub = self.create_publisher(String, topic, 10)
        self.timer = self.create_timer(period, self.tick)

        self.get_logger().info(f"Publishing on {topic} every {period:.3f}s (CAN: {channel})")

        # cache last-known values
        self.last_cells = []
        self.last_t1 = None
        self.last_t2 = None
        self.last_mos = None

        # rotate extra queries to reduce BMS load on a busy CAN bus
        self.extras = ["cells", "temps", "mos"]
        self.extra_idx = 0

    def req(self, did):
        self.bus.send(can.Message(
            arbitration_id=can_id(did, BMS, PC),
            is_extended_id=True,
            data=b"\x00" * 8
        ))

    def recv_one_did(self, did, timeout_s):
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            msg = self.bus.recv(timeout=0.05)
            if msg is None or not msg.is_extended_id:
                continue
            pr, mdid, rx, tx = parse_id(msg.arbitration_id)
            if pr == PRIO and mdid == did and rx == PC and tx == BMS:
                return msg
        return None

    def recv_many_did(self, did, window_s):
        out = []
        t0 = time.time()
        while time.time() - t0 < window_s:
            msg = self.bus.recv(timeout=0.05)
            if msg is None or not msg.is_extended_id:
                continue
            pr, mdid, rx, tx = parse_id(msg.arbitration_id)
            if pr == PRIO and mdid == did and rx == PC and tx == BMS:
                out.append(msg)
        return out

    def req_retry_one(self, did, timeout_s, retries=2, gap_s=0.05):
        for _ in range(retries):
            self.req(did)
            time.sleep(gap_s)
            m = self.recv_one_did(did, timeout_s)
            if m:
                return m
        return None

    def req_retry_many(self, did, window_s, retries=2, gap_s=0.05):
        for _ in range(retries):
            self.req(did)
            time.sleep(gap_s)
            frames = self.recv_many_did(did, window_s)
            if frames:
                return frames
        return []

    def decode_0x90(self, d):
        voltage = u16be(d, 0) * 0.1

        raw_i = u16be(d, CURRENT_WORD_OFFSET)
        amps  = (raw_i - CURRENT_ZERO_OFFSET) * CURRENT_SCALE_A_PER_LSB

        soc = u16be(d, 6) * 0.1
        return voltage, amps, soc

    def decode_0x95(self, frames):
        frames = sorted(frames, key=lambda m: m.data[0])
        cells_mv = []
        for m in frames:
            b = bytes(m.data)
            for off in (1, 3, 5):
                mv = (b[off] << 8) | b[off + 1]
                if mv not in (0x0000, 0xFFFF):
                    cells_mv.append(mv)
        cells_mv = cells_mv[:NUM_STRINGS]
        return [mv / 1000.0 for mv in cells_mv]

    def decode_0x96(self, d):
        return d[1] - 40, d[2] - 40

    def decode_0x94_mos_temp(self, d):
        return d[7] - 40

    def tick(self):
        # Always get pack each tick
        m90 = self.req_retry_one(0x90, timeout_s=0.50)
        if not m90:
            self.get_logger().warn("No 0x90 response")
            return

        v, a, soc = self.decode_0x90(bytes(m90.data))

        # One extra per tick to reduce BMS load
        which = self.extras[self.extra_idx]
        self.extra_idx = (self.extra_idx + 1) % len(self.extras)

        if which == "cells":
            frames95 = self.req_retry_many(0x95, window_s=0.80)
            if frames95:
                cells = self.decode_0x95(frames95)
                if len(cells) == NUM_STRINGS:
                    self.last_cells = cells

        elif which == "temps":
            m96 = self.req_retry_one(0x96, timeout_s=0.60)
            if m96:
                self.last_t1, self.last_t2 = self.decode_0x96(bytes(m96.data))

        elif which == "mos":
            m94 = self.req_retry_one(0x94, timeout_s=0.60)
            if m94:
                self.last_mos = self.decode_0x94_mos_temp(bytes(m94.data))

        # Timestamp
        stamp = self.get_clock().now().to_msg()
        ts = f"{stamp.sec}.{stamp.nanosec:09d}"

        cells_str = " ".join(f"{x:.3f}" for x in self.last_cells) if len(self.last_cells) == NUM_STRINGS else "N/A"
        t1s = str(self.last_t1) if self.last_t1 is not None else "N/A"
        t2s = str(self.last_t2) if self.last_t2 is not None else "N/A"
        moss = str(self.last_mos) if self.last_mos is not None else "N/A"

        out = (
            f"stamp={ts} "
            f"soc={soc:.1f}% "
            f"amps={a:.2f}A "
            f"voltage={v:.1f}V "
            f"cells=[{cells_str}] "
            f"temp1={t1s}C temp2={t2s}C mos_temp={moss}C"
        )

        msg = String()
        msg.data = out
        self.pub.publish(msg)

def main():
    rclpy.init()
    node = DalyBmsCanPublisher()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()


