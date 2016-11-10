import argparse
from tcp import TCP
import urlparse

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
    
    tcp = TCP(host, uri)
    tcp.handshake()
    tcp.print_info()
    tcp.send('GET {} HTTP/1.1\r\nHost: {}\r\n\r\n'.format(tcp.uri, tcp.host))
    tcp.print_info()
    data = ''
    filename = uri.split('/')[-1]
    f = open(filename, 'a')
    httpEnd = -1
    tot_len = 0
    while True:
        try:
            tmp = tcp.recv()
        except:
            break
        data += tmp
        if httpEnd == -1:
            httpEnd = data.find('\r\n\r\n')
            if httpEnd != -1:
                data = data[httpEnd + 4:]
        elif len(data) > 40960:
            f.write(data)
            tot_len += len(data)
            data = ''
            print tot_len
    tcp.teardown()
    f.write(data)
    tot_len += len(data)
    print tot_len
    f.close()
    tcp.print_info()    

