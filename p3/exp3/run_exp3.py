import matplotlib as mpl
mpl.use('Agg')
from subprocess import call
import matplotlib.pyplot as plt
import os

TCPType = {'SACK':'Agent/TCP/Sack1', 'Reno':'Agent/TCP/Reno'}
QueueType = {'RED', 'DropTail'}

def statistic(fname, duration):
    # Open and read the trace file
    with open(fname) as f:
        lines = f.readlines()
    total_rtt = {}
    send = {}
    recv = {}
    window = {}
    thpt = []
    latency = []
    drop = []
    for i in range(duration):
        send[i] = recv[i] = total_rtt[i] = 0
    for l in lines:
        fields = l.split()
        action = fields[0]
        time = float(fields[1])
        source = fields[2]
        dest = fields[3]
        packetType = fields[4]
        seq = fields[10]

        if action == '+' and source == '0':
            timeSlot = int(float(time))
            window[seq] = time
            send[timeSlot] += 1
        elif action == 'r' and dest == '0' and packetType == 'ack' and seq in window:
            timeSlot = int(float(fields[1]))
            recv[timeSlot] += 1
            total_rtt[timeSlot] += time - window[seq]
            window.pop(seq)
    for i in range(duration):
        thpt.append(recv[i]*1040*8.0/1024)
        latency.append(total_rtt[i]*1.0/recv[i] if recv[i] != 0 else None)
        drop.append((send[i]-recv[i])*1.0/send[i]*100 if send[i] != 0 else None)
    return thpt, latency, drop

def runExp1(duration):
    stat = {'thpt':{},'lat':{}, 'drop':{}}
    # Do experiment on each TCP variant
    for typeName in TCPType:
        # For each queue type
        for queueName in QueueType:
            fname = 'exp3_{0}_{1}.tr'.format(typeName, queueName)
            #call(["ns", "experiment3.tcl", TCPType[typeName], queueName, fname, str(duration)])
            call(["/course/cs4700f12/ns-allinone-2.35/bin/ns", "experiment3.tcl", TCPType[typeName], queueName, fname, str(duration)])
            t, l, d = statistic(fname, duration)
            stat['thpt'][typeName+'_'+queueName] = t
            stat['lat'][typeName+'_'+queueName] = l
            stat['drop'][typeName+'_'+queueName] = d            
    return stat

def main():
    color = {'SACK_DropTail':'-o', 'SACK_RED':'-^', 'Reno_DropTail':'-s', 'Reno_RED':'-*'}
    duration = 30
    stat = runExp1(duration)
    nfig = 0
    for k in stat:
        plt.figure(nfig)
        nfig += 1
        for combination in stat[k]:
            plt.plot(range(duration), stat[k][combination], color[combination], label = combination)
        plt.xlabel('Time: seconds')
        if k == 'thpt':
            plt.ylabel('Throughpt: kbps')
        elif k == 'drop':
            plt.ylabel('Drop rate: %')
        else:
            plt.ylabel('Latency: s')
        plt.legend()
        # plt.show()
        plt.savefig('exp3_'+k)

main()
