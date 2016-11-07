import struct
import fcntl
import sys
import socket
import utils


class Ethernet:
    def __init__(self):
        try:
            #s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.IPPROTO_RAW)
            self.send_sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
            self.recv_sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0800))
        except socket.error , msg:
            print 'Socket could not be created. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
            if msg[0] == 1:
                print "Need sudo!"
            sys.exit()

        self.send_sock.bind(('eth0', socket.SOCK_RAW))
        #self.recv_sock.setblocking(0)

        try:
            self.gateway_ip = utils.get_default_gateway_linux()
            print 'gateway_ip:', self.gateway_ip
        except:
            sys.exit()
        self.local_mac= self.send_sock.getsockname()[4]
        self.local_ip = utils.get_local_ip_address('eth0')
        self.gateway_mac = utils.BCAST_MAC

    def _build_frame_header(self, dest_mac, ptype =
            utils.ETHERNET_PROTOCOL_TYPE_IP):
        frame_header = ''.join([dest_mac, self.local_mac, ptype])
        return frame_header

    def send(self, packet, dest_mac = None, ptype = utils.ETHERNET_PROTOCOL_TYPE_IP):
        """dest_mac, packet, ptype default is IP"""
        if dest_mac == None:
            dest_mac = self.gateway_mac
        frame = self._build_frame_header(dest_mac, ptype = ptype) + packet
        self.send_sock.send(frame)

    def recv(self):
        frame = self.recv_sock.recv(65535)
        packet = frame[14:]
        return packet

if __name__ == '__main__':
    ether = Ethernet()
    ether.send('')
    packet = ether.recv()
    print packet


        


