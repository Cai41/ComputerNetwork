import matplotlib as mpl
mpl.use('Agg')
from subprocess import call
import matplotlib.pyplot as plt
import os

DEV = False 

TCPType = {'Tahoe':'Agent/TCP', 'Reno':'Agent/TCP/Reno', 'Newreno':'Agent/TCP/Newreno', 'Vegas':'Agent/TCP/Vegas'}
TestCase = [['Reno', 'Reno'], ['Newreno', 'Reno'], ['Vegas','Vegas'], ['Newreno','Vegas']]

def statistic(fname, duration):
    with open(fname) as f:
        lines = f.readlines()
    window1, window2 = {}, {}
    send1, send2 = 0, 0
    recv1, recv2 = 0, 0
    total_rtt1, total_rtt2 = 0, 0
    size1, size2 = 0, 0
    for l in lines:
        fields = l.split()
        action = fields[0]
        time = float(fields[1])
        source = fields[2]
        dest = fields[3]
        packetType = fields[4]
        seq = fields[10]
        if action == '+' and source == '0':
            window1[seq] = time
            send1 += 1
        elif action == '+' and source == '4':
            if seq not in window2:
                window2[seq] = time
            send2 += 1
        elif action == 'r' and dest == '0' and packetType == 'ack' and (seq in window1):
            recv1 += 1
            total_rtt1 += time - window1[seq]
            window1.pop(seq)
        elif action == 'r' and dest == '4' and packetType == 'ack' and (seq in window2):
            recv2 += 1
            total_rtt2 += time - window2[seq]
            window2.pop(seq)
    throughput1 = recv1 * 1040 * 8.0 / duration / 1024
    drop1 = (send1-recv1)*1.0/send1*100
    latency1 = total_rtt1*1.0/recv1
    throughput2 = recv2 * 1040 * 8.0 / duration / 1024
    drop2 = (send2-recv2)*1.0/send2*100
    latency2 = total_rtt2*1.0/recv2
    return throughput1, drop1, latency1, throughput2, drop2, latency2

def runExp1(cbr_start, cbr_end, step):
    stat1 = {'thpt':[], 'drop':[], 'lat':[]}
    stat2 = {'thpt':[], 'drop':[], 'lat':[]}
    for t in TestCase:
        typeName1 = t[0]
        typeName2 = t[1]
        throughput1, throughput2 = [], []
        drop1, drop2 = [], []
        latency1, latency2 = [], []
        for i in range(cbr_start, cbr_end):
            print typeName1 + ': ' + str(i*step) + 'mb'
            print typeName2 + ': ' + str(i*step) + 'mb'
            fname = 'exp2_{0}_{1}_{2}.tr'.format(typeName1, typeName2, str(i*step*10))
            if not DEV:
                call(["/course/cs4700f12/ns-allinone-2.35/bin/ns", "experiment2.tcl", TCPType[typeName1], TCPType[typeName2], str(i*step), fname, str(2.0), str(10.0)])
            else:
                call(["ns", "experiment2.tcl", TCPType[typeName1], TCPType[typeName2], str(i*step), fname, str(2.0), str(10.0)])
            t1, d1, l1, t2, d2, l2 = statistic(fname, 8.0)
            throughput1.append(t1)
            drop1.append(d1)
            latency1.append(l1)
            throughput2.append(t2)
            drop2.append(d2)
            latency2.append(l2)            
        stat1['thpt'].append(throughput1)
        stat1['drop'].append(drop1)
        stat1['lat'].append(latency1)
        stat2['thpt'].append(throughput2)
        stat2['drop'].append(drop2)
        stat2['lat'].append(latency2)
    return stat1, stat2

def main():
    cbr_start = 1
    cbr_end = 21
    step = 0.5
    color = {'Tahoe':'-o', 'Reno':'-^', 'Newreno':'-s', 'Vegas':'-*'}
    stat1, stat2 = runExp1(cbr_start, cbr_end, step)
    nfig = 0
    for k in stat1:
        for i in range(4):
            plt.figure(nfig)
            nfig += 1
            plt.plot([x * step for x in range(cbr_start, cbr_end)], stat1[k][i], color[TestCase[i][0]], label = TestCase[i][0])
            plt.plot([x * step for x in range(cbr_start, cbr_end)], stat2[k][i], color[TestCase[i][1]], label = TestCase[i][1])
            plt.xlabel('CBR rate: Mbps')
            if k == 'thpt':
                plt.ylabel('Throughpt: kbps')
            elif k == 'drop':
                plt.ylabel('Drop rate: %')
            else:
                plt.ylabel('Latency: s')
            # plt.show()
            plt.legend()
            plt.savefig('exp2_'+TestCase[i][0]+'_'+TestCase[i][1]+'_'+k)

main()
