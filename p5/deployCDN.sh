#!/bin/bash

hosts=(ec2-54-210-1-206.compute-1.amazonaws.com
       ec2-54-67-25-76.us-west-1.compute.amazonaws.com
       ec2-35-161-203-105.us-west-2.compute.amazonaws.com
       ec2-52-213-13-179.eu-west-1.compute.amazonaws.com
       ec2-52-196-161-198.ap-northeast-1.compute.amazonaws.com
       ec2-54-255-148-115.ap-southeast-1.compute.amazonaws.com
       ec2-13-54-30-86.ap-southeast-2.compute.amazonaws.com
       ec2-52-67-177-90.sa-east-1.compute.amazonaws.com
       ec2-35-156-54-135.eu-central-1.compute.amazonaws.com
)

while [[ $# -gt 1 ]]
do
    key="$1"
    case $key in
	-p)
	    PORT="$2"
	    shift
	    ;;
	-o)
	    ORIGIN="$2"
	    shift
	    ;;
	-n)
	    NAME="$2"
	    shift
	    ;;
	-u)
	    USERNAME="$2"
	    shift
	    ;;
	-i)
	    KEYFILE="$2"
	    shift
	    ;;
    esac
shift 
done

for h in ${hosts[@]}; do
    scp -i $KEYFILE LRUCache.py httpserver httpserver.py init download.py $USERNAME@$h:
    ssh -i $KEYFILE $USERNAME@$h "mkdir data; chmod +x download.py; nohup python download.py  > /dev/null 2>&1 &"
done

scp -i $KEYFILE dnsserver dnsserver.py $USERNAME@cs5700cdnproject.ccs.neu.edu:
