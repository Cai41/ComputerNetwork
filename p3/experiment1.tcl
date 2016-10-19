#Create a simulator object
set ns [new Simulator]

#Open the trace file
set tf [open exp1_out.tr w]
$ns trace-all $tf

#Define a 'finish' procedure
proc finish {} {
    global ns nf tf
    $ns flush-trace
    #Close the trace file
    close $tf
    exit 0
}

#Create four nodes
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

$ns queue-limit $n2 $n3 10

#Setup a TCP connection
#Agent/TCP/FullTcp/Tahoe, Agent/TCP/Reno,Agent/TCP/FullTcp/Newreno,Agent/TCP/Vegas
set tcp [new Agent/TCP/Reno]
$tcp set class_ 2
$ns attach-agent $n1 $tcp
set sink [new Agent/TCPSink]
$ns attach-agent $n4 $sink
$ns connect $tcp $sink
$tcp set fid_ 1
$tcp set window_ 50
$tcp set packetSize_ 1000

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
$cbr set packet_size_ 1000
$cbr set rate_ 10mb
$cbr set random_ 1

#Schedule events for the CBR and FTP agents
$ns at 0.1 "$cbr start"
$ns at 1.0 "$ftp start"
$ns at 4.0 "$ftp stop"
$ns at 4.5 "$cbr stop"

#Detach tcp and sink agents (not really necessary)
$ns at 4.5 "$ns detach-agent $n1 $tcp ; $ns detach-agent $n3 $sink"

#Call the finish procedure after 5 seconds of simulation time
$ns at 5.0 "finish"

proc plotWindow {tcpSource outfile} {
    global ns

    set now [$ns now]
    set cwnd [$tcpSource set window_]

    ###Print TIME CWND   for  gnuplot to plot progressing on CWND
    puts  $outfile  "$now $cwnd"

    $ns at [expr $now+0.1] "plotWindow $tcpSource  $outfile"
}

$ns  at  0.0  "plotWindow $tcp stdout"

#Run the simulation
$ns run
