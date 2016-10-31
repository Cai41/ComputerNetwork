import struct
import socket
import fcntl

# constants
BCAST_MAC = struct.pack('!6B', *(0xFF,)*6)
ZERO_MAC = struct.pack('!6B', *(0x00,)*6)
HARDWARE_TYPE_ETHERNET= struct.pack('!H', 0x0001)

ARPOP_REQUEST = struct.pack('!H', 0x0001)
ARPOP_REPLY = struct.pack('!H', 0x0002)

PROTOCOL_TYPE_IP = struct.pack('!H', 0x0800)
# Ethernet protocol type (=ARP)
ETHERNET_PROTOCOL_TYPE_ARP = struct.pack('!H', 0x0806)
ETHERNET_PROTOCOL_TYPE_IP = struct.pack('!H', 0x0800)

def get_default_gateway_linux():
    """Human readable gateway IP. Read the default gateway directly from /proc."""
    with open("/proc/net/route") as fh:
        for line in fh:
            fields = line.strip().split()
            if fields[1] != '00000000' or not int(fields[3], 16) & 2:
                continue

            return socket.inet_ntoa(struct.pack("<L", int(fields[2], 16)))

def get_local_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])
