# parameters: TCP type, CBR rate, trace file path, start time, end time
set tcpType [lindex $argv 0]
set rate [lindex $argv 1]
set fpath [lindex $argv 2]
set start [lindex $argv 3]
set end [lindex $argv 4]

#Create a simulator object
set ns [new Simulator]

#Open the trace file
set tf [open $fpath w]
$ns trace-all $tf

#Define a 'finish' procedure
proc finish {} {
    global ns tf
    $ns flush-trace
    #Close the trace file
    close $tf
    exit 0
}

#Create six nodes
set n1 [$ns node]
set n2 [$ns node]
set n3 [$ns node]
set n4 [$ns node]
set n5 [$ns node]
set n6 [$ns node]

#Create links between the nodes
$ns duplex-link $n1 $n2 10Mb 10ms DropTail
$ns duplex-link $n2 $n3 10Mb 10ms DropTail
$ns duplex-link $n3 $n4 10Mb 10ms DropTail
$ns duplex-link $n2 $n5 10Mb 10ms DropTail
$ns duplex-link $n3 $n6 10Mb 10ms DropTail

#Setup a TCP connection: Agent/TCP, Agent/TCP/Reno,Agent/TCP/Newreno,Agent/TCP/Vegas
set tcp [new $tcpType]
$ns attach-agent $n1 $tcp
set sink [new Agent/TCPSink]
$ns attach-agent $n4 $sink
$ns connect $tcp $sink
$tcp set packetSize_ 1000
$tcp set fid_ 1

#Setup a FTP over TCP connection
set ftp [new Application/FTP]
$ftp attach-agent $tcp
$ftp set type_ FTP

#Setup a UDP connection
set udp [new Agent/UDP]
$ns attach-agent $n2 $udp
set null [new Agent/Null]
$ns attach-agent $n3 $null
$ns connect $udp $null
$udp set fid_ 2

#Setup a CBR over UDP connection
set cbr [new Application/Traffic/CBR]
$cbr attach-agent $udp
$cbr set type_ CBR
$cbr set rate_ ${rate}Mb
$cbr set random_ 1
$cbr set packetSize_ 1000

#Schedule events for the CBR and FTP agents
$ns at 1.0 "$cbr start"
$ns at $start "$ftp start"
$ns at $end "$ftp stop"
$ns at 15.0 "$cbr stop"

#Detach tcp and sink agents (not really necessary)
$ns at $end "$ns detach-agent $n1 $tcp ; $ns detach-agent $n4 $sink"

#Call the finish procedure after 5 seconds of simulation time
$ns at 16.0 "finish"

$defaultRNG seed 0

#Run the simulation
$ns run
