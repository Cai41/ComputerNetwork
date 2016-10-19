def preprocess():
    with open('exp1_out.tr') as f:
        lines = f.readlines()
    allPackets = {}
    send = 0
    recv = 0
    triptime = 0
    size = 0
    for l in lines:
        fields = l.split()
        if fields[0] == '+' and fields[2] == '0':
            allPackets[fields[11]] = {'stime':float(fields[1]), 'size':int(fields[5]), 'etime':None}
            send += 1
        elif fields[0] == 'r' and fields[3] == '3':
            allPackets[fields[11]]['etime'] = float(fields[1])
            recv += 1
            size += allPackets[fields[11]]['size']
            triptime += allPackets[fields[11]]['etime'] - allPackets[fields[11]]['stime']
    print 'all send: ' + str(send)
    print 'all recv: ' + str(recv)
    print 'triptime of all recv packets: ' + str(triptime)
    print 'size of all recv packets: ' + str(size)

preprocess()


