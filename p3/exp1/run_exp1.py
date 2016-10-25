import matplotlib as mpl
mpl.use('Agg')
from subprocess import call
import matplotlib.pyplot as plt
import os

TCPType = {'Tahoe':'Agent/TCP', 'Reno':'Agent/TCP/Reno', 'Newreno':'Agent/TCP/Newreno', 'Vegas':'Agent/TCP/Vegas'}

def statistic(fname, duration):
    # Open and read the trace file
    with open(fname) as f:
        lines = f.readlines()
    sendTime = {}
    send = 0
    recv = 0
    triptime = 0
    size = 0
    # For each line, split into serveral fields.
    # If the packet is sent by node 0, then send++, and record the sendtime
    # If the packet is received by node 3, the recv++, and calculate the triptime, sum the packet size
    for l in lines:
        fields = l.split()
        if fields[0] == '+' and fields[2] == '0':
            sendTime[fields[11]] = float(fields[1])
            send += 1
        elif fields[0] == 'r' and fields[3] == '3':
            recv += 1
            size += int(fields[5])
            triptime += (float(fields[1]) - sendTime[fields[11]])
    throughput = size*8.0/duration/1024
    drop = (send-recv)*1.0/send*100
    latency = triptime*1.0/recv
    print 'Throughput: ' + str(throughput) + ' kbps'
    print 'Drop rate: ' + str(drop)
    print 'latency: ' + str(latency) + 's'
    return throughput, drop, latency

def runExp1(cbr_start, cbr_end, step):
    stat = {'thpt':{}, 'drop':{}, 'lat':{}}
    # Do experiment on each TCP variant
    for typeName in TCPType:
        throughput = []
        drop = []
        latency = []
        # Change the cbr rate from cbr_start*step to cbr_end*step
        for i in range(cbr_start, cbr_end):
            print typeName + ': ' + str(i*step) + 'mb'
            fname = 'exp1_{0}_{1}.tr'.format(typeName,str(i*step*10))
            t_sum = 0
            d_sum = 0
            l_sum = 0
            # Run 5 times, vary the start time, and get the average result
            for j in range(1):
                call(["/course/cs4700f12/ns-allinone-2.35/bin/ns", "experiment1.tcl", TCPType[typeName], str(i*step), fname,
                      str(2.0+0.01*j), str(10.0+j*0.01)])
                t, d, l = statistic(fname, 10.0)
                t_sum += t
                d_sum += d
                l_sum += l
                os.remove(fname)
            throughput.append(t_sum/5)
            drop.append(d_sum/5)
            latency.append(l_sum/5)
        stat['thpt'][typeName] = throughput
        stat['drop'][typeName] = drop
        stat['lat'][typeName] = latency
    return stat

def main():
    cbr_start = 1
    cbr_end = 21
    step = 0.5
    color = {'Tahoe':'--o', 'Reno':'--^', 'Newreno':'--s', 'Vegas':'--*'}
    stat = runExp1(cbr_start, cbr_end, step)
    nfig = 0
    for k in stat:
        plt.figure(nfig)
        nfig += 1
        for tcpType in stat[k]:
            plt.plot([x * step for x in range(cbr_start, cbr_end)], stat[k][tcpType], color[tcpType], label = tcpType)
        plt.xlabel('CBR rate: Mbps')
        if k == 'thpt':
            plt.ylabel('Throughpt: kbps')
        elif k == 'drop':
            plt.ylabel('Drop rate: %')
        else:
            plt.ylabel('Latency: s')
        plt.legend()
        # plt.show()
        plt.savefig('exp1_'+k)

main()

