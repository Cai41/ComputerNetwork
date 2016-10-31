import struct
import fcntl
import sys
import socket
import utils


class Ethernet:
    def __init__(self):
        try:
            #s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.IPPROTO_RAW)
            self.sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
        except socket.error , msg:
            print 'Socket could not be created. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
            if msg[0] == 1:
                print "Need sudo!"
            sys.exit()

        self.sock.bind(('eth0', socket.SOCK_RAW))
        try:
            self.gateway_ip = utils.get_default_gateway_linux()
            print 'gateway_ip:', self.gateway_ip
        except:
            sys.exit()
        self.local_mac= sock.getsockname()[4]
        self.local_ip = utils.get_local_ip_address('eth0')
        self.gateway_mac = None

    def _build_frame_header(self, dest_mac, ptype =
            utils.ETHERNET_PROTOCOL_TYPE_IP):
        frame_header = ''.join([dest_mac, self.local_mac, ptype])
        return frame_header

    def send(self, dest_mac, packet):

        frame = self._build_frame_header(dest_mac) + packet
        self.sock.send(frame)

if __name__ == '__main__':
    ether = Ethernet()
    ether.send(utils.BCAST_MAC, '')


        


