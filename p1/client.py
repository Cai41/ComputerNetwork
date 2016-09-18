#! /usr/bin/env python

import socket, argparse, ssl
    
def main():
    parser = argparse.ArgumentParser(prog="client")
    parser.add_argument('-p', metavar='port', dest = 'port', help='port number.')
    parser.add_argument('-s', dest='ssl', action='store_true', default=False, help='using ssl')
    parser.add_argument('hostname')
    parser.add_argument('neuid')
    args = parser.parse_args()
    # print args
    
    port = 27993
    if args.port is not None:
        port = int(args.port)
    elif args.ssl:
        port = 27994
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientSocket = args.ssl and ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_SSLv23) or sock
    try:
        clientSocket.connect((args.hostname, port))
    except Exception as e:
        print 'can not connect to %s:%d, err:%s' % (args.hostname, port, e)
        clientSocket.close()
        return
    
    helloMsg = 'cs5700fall2016 HELLO ' + args.neuid + '\n'
    clientSocket.send(helloMsg)
    # print helloMsg
    
    while True:
        statusMsg = clientSocket.recv(256)
        # print statusMsg
        if 'STATUS' in statusMsg:
            statusPos = statusMsg.find('STATUS')
            replyMsg = "cs5700fall2016 " +  str(eval(statusMsg[statusPos+7:-1])) + "\n"
            clientSocket.send(replyMsg)
        elif 'BYE' in statusMsg:
            # print statusMsg
            pos1 = statusMsg.find('fall2016')
            pos2 = statusMsg.find('BYE')
            print statusMsg[pos1+9:pos2-1]
            break
        else:
            print "Unknow message"
            break
    clientSocket.close()

if __name__=='__main__':
    main()
