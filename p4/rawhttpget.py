import argparse
from tcp import TCP
import urlparse
import re
import time

def parseURL(url):
    u = urlparse.urlparse(url)
    path = u.path
    if u.path == '':
        path += '/index.html'
    elif u.path[-1] == '/':
        path += 'index.html'        
    return u.netloc, path

def run(host, uri):
    lenPattern = re.compile(r'Content-Length: ([0-9]+)')
    tcp = TCP(host, uri)
    try:
        tcp.handshake()
    except:
        print 'Can not connect to server'
        tcp.fin = True
        return
    tcp.print_info()
    send_data = 'GET {} HTTP/1.0\r\nHost: {}\r\nConnection: keep-alive\r\n\r\n'.format(tcp.uri, tcp.host)
    for s in send_data:
        tcp.send(s)
    # tcp.send('GET {} HTTP/1.0\r\nHost: {}\r\nConnection: keep-alive\r\n\r\n'.format(tcp.uri, tcp.host))
    tcp.print_info()
    data = ''
    filename = uri.split('/')[-1]
    f = open(filename, 'w')
    httpEnd = -1
    tot_len = 0
    length = None
    t = time.time()
    while time.time() - t < 300:
        if tcp.fin: break
        try:
            tmp = tcp.recv()
        except:
            print 'Ethernet timeout'
            continue

        # return None means received FIN/RST from server
        if tmp == None: break

        data += tmp
        t = time.time()
        if httpEnd == -1:
            httpEnd = data.find('\r\n\r\n')
            if httpEnd != -1:
                length = lenPattern.search(data[:httpEnd])
                header = data[:httpEnd + 4].split()
                data = data[httpEnd + 4:]
                if (header[1] != '200'):
                    print 'HTTP Response code is not 200, exit'
                    return
        else:
            if len(data) > 40960:
                f.write(data)
                tot_len += len(data)
                data = ''
                print 'Data recieved: ', tot_len
            # If there is Content-Length in header, the compare data received with it
            if length is not None and tot_len + len(data) == int(length.group(1)):
                break
    if time.time() - t > 180:
        print 'No data received within 3 minutes'
    f.write(data)
    f.close()    
    tot_len += len(data)
    if length is not None:
        tcp.teardown()
    print tot_len
    tcp.print_info()
    print 'we are done'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog = 'rawHttp')
    parser.add_argument('url')
    args = parser.parse_args()

    host, uri =  parseURL(args.url)
    print host, uri

    run(host, uri)
