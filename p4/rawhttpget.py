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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog = 'rawHttp')
    parser.add_argument('url')
    args = parser.parse_args()

    host, uri =  parseURL(args.url)
    print uri

    lenPattern = re.compile(r'Content-Length: ([0-9]+)')
    tcp = TCP(host, uri)
    tcp.handshake()
    tcp.print_info()
    tcp.send('GET {} HTTP/1.0\r\nHost: {}\r\nConnection: keep-alive\r\n\r\n'.format(tcp.uri, tcp.host))
    tcp.print_info()
    data = ''
    filename = uri.split('/')[-1]
    f = open(filename, 'w')
    httpEnd = -1
    tot_len = 0
    length = 0
    t = time.time()
    while time.time() - t < 300:
        try:
            tmp = tcp.recv()
        except:
            print 'aaaaaaaaaaaaaaaaaaaaa'
            continue
        data += tmp
        t = time.time()
        if httpEnd == -1:
            httpEnd = data.find('\r\n\r\n')
            if httpEnd != -1:
                length = lenPattern.search(data[:httpEnd]).group(1)
                data = data[httpEnd + 4:]
        else:
            if len(data) > 40960:
                f.write(data)
                tot_len += len(data)
                data = ''
            print tot_len, length, tot_len + len(data)
            if tot_len + len(data) == int(length):
                break
    tcp.teardown()
    f.write(data)
    tot_len += len(data)
    print tot_len
    f.close()
    tcp.print_info()

