from subprocess import call
import matplotlib.pyplot as plt

TCPType = {'Tahoe':'Agent/TCP', 'Reno':'Agent/TCP/Reno', 'Newreno':'Agent/TCP/Newreno', 'Vegas':'Agent/TCP/Vegas'}

def statistic(fname, duration):
    with open(fname) as f:
        lines = f.readlines()
    sendTime = {}
    send = 0
    recv = 0
    triptime = 0
    size = 0
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
    for typeName in TCPType:
        throughput = []
        drop = []
        latency = []
        for i in range(cbr_start, cbr_end):
            print typeName + ': ' + str(i*step) + 'mb'
            fname = 'exp1_{0}_{1}.tr'.format(typeName,str(i*step*10))
            t_sum = 0
            d_sum = 0
            l_sum = 0
            for times in range(5):
                call(["/course/cs4700f12/ns-allinone-2.35/bin/ns", "experiment1.tcl", TCPType[typeName], str(i*step), fname,
                      str(2.0), str(10.0+times*0.5)])
                t, d, l = statistic(fname, 10.0)
                t_sum += t
                d_sum += d
                l_sum += l
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
        plt.savefig(k)

main()

