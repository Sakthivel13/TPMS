# -*- coding: utf-8 -*-
"""
Created on Mon Aug 11 15:45:15 2025

@author: Sri.Sakthivel
"""
import can
import os
from can.message import Message

def log_message(direction, msg):
    formatted_data = ' '.join(f'{byte:02X}' for byte in msg.data)
    print(f"{direction} {msg.arbitration_id:04X} {msg.dlc} {formatted_data}")
    
def can_config(interface="can0",bitrate=500000):
    os.system(f"sudo ip link set {interface} down")
    os.system(f"sudo ip link set {interface} up type can bitrate {bitrate} ")

def WRITE_TPMS_FRONT(front_mac):
    print("TEST SEQUENCE : WRITE_TPMS_FRONT")
    if not front_mac or len(front_mac) != 12 or not all(c in '0123456789ABCDEFabcdef' for c in front_mac):
        print(f"Invalid MAC address: {front_mac}")
        return False

    try:
        can_config(interface="can0",bitrate=500000)
        bus = can.interface.Bus(interface='socketcan', channel='can0', bitrate=500000)
        # Format: ['01'] + MAC bytes + ['00']
        mac_bytes = [int(front_mac[i:i+2], 16) for i in range(0, len(front_mac), 2)]
        full_payload = [0x01] + mac_bytes + [0x00]

        message = Message(arbitration_id=0x7F3, data=bytearray(full_payload), is_fd=False, is_extended_id=False)
        log_message("Tx", message)
        bus.send(message)

        bus.set_filters([{"can_id": 0x7F1, "can_mask": 0x7FF, "extended": False}])
        response = bus.recv(timeout=2)

        if response:
            log_message("Rx", response)
            print("WRITE_TPMS_FRONT:PASSED")
            return True
        else:
            print("No response for Rear MAC Write.")
            return False

    except can.CanError as e:
        print(f"CAN error: {e}")
        return False

    finally:
        if 'bus' in locals():
            bus.shutdown()

if __name__ == "__main__":
    result = WRITE_TPMS_FRONT("C03687540000")