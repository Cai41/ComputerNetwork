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
            self.recv_sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
        except socket.error , msg:
            print 'Socket could not be created. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
            if msg[0] == 1:
                print "Need sudo!"
            sys.exit()

        self.send_sock.bind(('eth0', 0))
        self.recv_sock.settimeout(5.0)

        # gateway_ip, local_mac, local_ip, gateway_mac are all binary
        try:
            self.gateway_ip = socket.inet_aton(utils.get_default_gateway_linux())
            # print 'gateway_ip:', socket.inet_ntoa(self.gateway_ip)
        except:
            sys.exit()
        self.local_mac= self.send_sock.getsockname()[4]
        self.local_ip = socket.inet_aton(utils.get_local_ip_address('eth0'))
        # print 'local_mac is {}'.format(self.local_mac)
        # print 'local_ip is {}'.format(socket.inet_ntoa(self.local_ip))
        self.gateway_mac = None

    def _build_frame_header(self, dest_mac, ptype =
            utils.ETHERNET_PROTOCOL_TYPE_IP):
        frame_header = ''.join([dest_mac, self.local_mac, ptype])
        return frame_header

    def send(self, packet, dest_mac = None, ptype = utils.ETHERNET_PROTOCOL_TYPE_IP):
        """dest_mac, packet, ptype default is IP"""
        if dest_mac == None:
            dest_mac = self.gateway_mac
            if self.gateway_mac == None:
                print 'gateway_mac cannot be None by now'
                sys.exit()
                
        frame = self._build_frame_header(dest_mac, ptype = ptype) + packet
        self.send_sock.send(frame)

    def recv(self):
        frame = None
        try:
            while frame == None:
                frame = self.recv_sock.recv(65535)
                if frame[:6] != self.local_mac:
                    #print 'got a packet not sending to us'
                    frame = None
                elif frame[12:14] != utils.ETHERNET_PROTOCOL_TYPE_IP:
                    #print 'got a non-ip packet'
                    frame = None

        except:
            sys.exit()
        packet = frame[14:]
        return packet

if __name__ == '__main__':
    e = Ethernet()
    #dest_mac = struct.pack('6B', 0x525400123502)
    dest_mac = '525400123502'.decode('hex')
    packet1 = '4500002859210000ff0691480a00020fd861ecf5'.decode('hex')
    packet2 = '59e800502cc7919c0000000050021000b5e00000'.decode('hex')
    e.send(packet1+packet2, dest_mac = dest_mac)
