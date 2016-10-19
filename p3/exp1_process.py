from subprocess import call
import matplotlib.pyplot as plt

TCPType = {'Tahoe':'Agent/TCP', 'Reno':'Agent/TCP/Reno', 'Newreno':'Agent/TCP/Newreno', 'Vegas':'Agent/TCP/Vegas'}

def statistic(fname, duration):
    with open(fname) as f:
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
    throughput = size*1.0/duration/1024
    drop = (send-recv)*1.0/send*10
    latency = triptime*1.0/recv
    print 'Throughput: ' + str(throughput) + ' kbps'
    print 'Drop rate: ' + str(drop) + '%'
    print 'latency: ' + str(latency) + 's'
    return throughput, drop, latency

def runExp1():
    for typeName in TCPType:
        for i in range(1, 11):
            print typeName + ': ' + str(i) + 'mb'
            call(["/course/cs4700f12/ns-allinone-2.35/bin/ns", "experiment1.tcl", TCPType[typeName], str(i)+'mb'])
            statistic('exp1_out.tr', 4.0)

runExp1()


