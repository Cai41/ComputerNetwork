import argparse
from tcp import TCP
import urlparse
import re
import time

def parseURL(url):
    u = urlparse.urlparse(url)
    path = u.path
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
    # tcp.print_info()
    # GET request
    send_data = 'GET {} HTTP/1.0\r\nHost: {}\r\nUser-Agent: Mozilla/5.0 (Windows NT 6.0) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.97 Safari/537.11\r\nConnection: keep-alive\r\n\r\n'.format(tcp.uri, tcp.host)
    # print send_data
    # for s in send_data:
    #     tcp.send(s)
    tcp.send(send_data)
    # tcp.send('GET {} HTTP/1.0\r\nHost: {}\r\nConnection: keep-alive\r\n\r\n'.format(tcp.uri, tcp.host))
    # tcp.print_info()
    data = ''
    filename = uri.split('/')[-1] if uri[-1] != '/' else 'index.html'
    f = open(filename, 'w')
    httpEnd = -1
    tot_len = 0
    length = None
    t = time.time()
    while time.time() - t < 180:
        # If received FIN from server, then it is done
        if tcp.fin: break
        try:
            tmp = tcp.recv()
        except:
            # print 'Ethernet timeout'
            continue

        # return None means received FIN/RST from server
        if tmp == None: break

        data += tmp
        t = time.time()
        if httpEnd == -1:
            # this is the first packet, which contains HTTP header
            httpEnd = data.find('\r\n\r\n')
            if httpEnd != -1:
                length = lenPattern.search(data[:httpEnd])
                header = data[:httpEnd + 4].split()
                data = data[httpEnd + 4:]
                # print header
                if (header[1] != '200'):
                    print 'HTTP Response code is not 200, exit'
                    tcp.fin = True
                    return
        else:
            # If buffer is full, flush to file
            if len(data) > 40960:
                f.write(data)
                tot_len += len(data)
                data = ''
                # print 'Data recieved: ', tot_len
            # If there is Content-Length in header, the compare data received with it
            if length is not None and tot_len + len(data) == int(length.group(1)):
                break
    if time.time() - t > 180:
        print 'No data received within 3 minutes'
    f.write(data)
    f.close()    
    tot_len += len(data)
    if length is not None:
        # if we didn't find content-length in response header, server will close
        # connection (RST) after tranmission is done. No need for TCP teardown.
        tcp.teardown()
    # print tot_len
    # tcp.print_info()
    print 'Download complete'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog = 'rawHttp')
    parser.add_argument('url')
    args = parser.parse_args()

    host, uri =  parseURL(args.url)
    if uri is '':
        uri = '/'
    # print host, uri

    run(host, uri)
