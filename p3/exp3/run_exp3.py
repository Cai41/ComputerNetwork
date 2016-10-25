from subprocess import call
import matplotlib.pyplot as plt
import os

TCPType = {'SACK':'Agent/TCP/Sack1', 'Reno':'Agent/TCP/Reno'}
QueueType = {'RED', 'DropTail'}

def statistic(fname, duration):
    # Open and read the trace file
    with open(fname) as f:
        lines = f.readlines()
    sendTime = {}
    send = {}
    recv = {}
    triptime = {}
    size = {}
    thpt = []
    latency = []
    dp = {}
    drop = []
    for i in range(duration):
        dp[i] = send[i] = recv[i] = triptime[i] = size[i] = 0
    for l in lines:
        fields = l.split()
        if fields[0] == '+' and fields[2] == '0':
            sendTime[fields[11]] = float(fields[1])
            timeSlot = int(float(fields[1]))
            send[timeSlot] += 1
        elif fields[0] == 'r' and fields[3] == '3':
            timeSlot = int(float(fields[1]))
            recv[timeSlot] += 1
            size[timeSlot] += int(fields[5])
            triptime[timeSlot] += (float(fields[1]) - sendTime[fields[11]])
        elif fields[0] == 'd' and fields[4] == 'tcp':
            timeSlot = int(float(fields[1]))
            dp[timeSlot] += 1
    for i in range(duration):
        thpt.append(size[i]*8.0/1024)
        latency.append(triptime[i]*1.0/recv[i] if recv[i] != 0 else 0)
        drop.append(dp[i]*1.0/send[i]*100 if send[i] != 0 else 0)
    return thpt, latency, drop

def runExp1(duration):
    stat = {'thpt':{},'lat':{}, 'drop':{}}
    # Do experiment on each TCP variant
    for typeName in TCPType:
        # For each queue type
        for queueName in QueueType:
            fname = 'exp3_{0}_{1}.tr'.format(typeName, queueName)
            call(["/course/cs4700f12/ns-allinone-2.35/bin/ns", "experiment3.tcl", TCPType[typeName], queueName, fname, str(duration)])
            t, l, d = statistic(fname, duration)
            os.remove(fname)
            stat['thpt'][typeName+'_'+queueName] = t
            stat['lat'][typeName+'_'+queueName] = l
            stat['drop'][typeName+'_'+queueName] = d            
    return stat

def main():
    color = {'SACK_DropTail':'--o', 'SACK_RED':'--^', 'Reno_DropTail':'--s', 'Reno_RED':'--*'}
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

