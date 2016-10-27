set tcpType [lindex $argv 0]
set queue [lindex $argv 1]
set fpath [lindex $argv 2]
set duration [lindex $argv 3]

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
$ns duplex-link $n1 $n2 10Mb 10ms $queue
$ns duplex-link $n2 $n3 10Mb 10ms $queue
$ns duplex-link $n3 $n4 10Mb 10ms $queue
$ns duplex-link $n2 $n5 10Mb 10ms $queue
$ns duplex-link $n3 $n6 10Mb 10ms $queue

$ns queue-limit $n1 $n2 30
$ns queue-limit $n2 $n3 30
$ns queue-limit $n3 $n4 30
$ns queue-limit $n2 $n5 30
$ns queue-limit $n3 $n6 30
###########################################################################################

#Setup a TCP connection: Agent/TCP/SACK, Agent/TCP/Reno
set tcp [new $tcpType]
$ns attach-agent $n1 $tcp
set sink [new Agent/TCPSink]
$ns attach-agent $n4 $sink
$ns connect $tcp $sink
$tcp set packetSize_ 1000
$tcp set fid_ 1
$tcp set window_ 25
#Setup a FTP over TCP connection
set ftp [new Application/FTP]
$ftp attach-agent $tcp
$ftp set type_ FTP

#######################################################################################

#Setup a UDP connection
set udp [new Agent/UDP]
$ns attach-agent $n5 $udp
set null [new Agent/Null]
$ns attach-agent $n6 $null
$ns connect $udp $null
$udp set fid_ 2

#Setup a CBR over UDP connection
set cbr [new Application/Traffic/CBR]
$cbr attach-agent $udp
$cbr set type_ CBR
$cbr set rate_ 6.5Mb
$cbr set random_ 1
$cbr set packetSize_ 1000

#######################################################################################

#Schedule events for the CBR and FTP agents
$ns at 0.0 "$ftp start"
$ns at 10.0 "$cbr start"
$ns at $duration "$cbr stop"
$ns at $duration "$ftp stop"

#Detach tcp and sink agents (not really necessary)
$ns at $duration "$ns detach-agent $n1 $tcp ; $ns detach-agent $n4 $sink"

#Call the finish procedure after 5 seconds of simulation time
$ns at $duration+1 "finish"

$defaultRNG seed 0

#Run the simulation
$ns run
