set tcpType1 [lindex $argv 0]
set tcpType2 [lindex $argv 1]
set rate [lindex $argv 2]
set fpath [lindex $argv 3]
set start [lindex $argv 4]
set end [lindex $argv 5]
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


########################################################################################################

#Setup a TCP connection between n1 and n4: Agent/TCP, Agent/TCP/Reno,Agent/TCP/Newreno,Agent/TCP/Vegas
set tcp1 [new $tcpType1]
$ns attach-agent $n1 $tcp1
set sink1 [new Agent/TCPSink]
$ns attach-agent $n4 $sink1
$ns connect $tcp1 $sink1
$tcp1 set packetSize_ 1000
$tcp1 set fid_ 1

#Setup a FTP over TCP connection
set ftp1 [new Application/FTP]
$ftp1 attach-agent $tcp1
$ftp1 set type_ FTP

############################################################################################################

#Setup a TCP connection between n5 and n6: Agent/TCP, Agent/TCP/Reno,Agent/TCP/Newreno,Agent/TCP/Vegas
set tcp2 [new $tcpType2]
$ns attach-agent $n5 $tcp2
set sink2 [new Agent/TCPSink]
$ns attach-agent $n6 $sink2
$ns connect $tcp2 $sink2
$tcp2 set packetSize_ 1000
$tcp2 set fid_ 3

#Setup a FTP over TCP connection
set ftp2 [new Application/FTP]
$ftp2 attach-agent $tcp2
$ftp2 set type_ FTP

#############################################################################################################

#Schedule events for the CBR and FTP agents
$ns at 1.0 "$cbr start"
$ns at $start "$ftp1 start"
$ns at $start "$ftp2 start"
$ns at $end "$ftp1 stop"
$ns at $end "$ftp2 stop"
$ns at 15.0 "$cbr stop"

#Detach tcp and sink agents (not really necessary)
$ns at $end "$ns detach-agent $n1 $tcp1 ; $ns detach-agent $n4 $sink1"
$ns at $end "$ns detach-agent $n5 $tcp2 ; $ns detach-agent $n6 $sink2"

#Call the finish procedure after 5 seconds of simulation time
$ns at 16.0 "finish"

$defaultRNG seed 0

#Run the simulation
$ns run
