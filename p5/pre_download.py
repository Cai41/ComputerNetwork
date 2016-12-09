import os
import urllib2

fd = open('found', 'r')
lines = fd.read().splitlines()
total = 0
for l in reversed(lines):
    try:
        response = urllib2.urlopen('http://ec2-54-167-4-20.compute-1.amazonaws.com:8080'+l)
        html = response.read()
    except:
        continue
    
    if total >= 9*1024*1024:
        break

    fpath = os.getcwd()+'/data'+l
    fdir = os.path.dirname(fpath)
    if fdir != '' and not os.path.isdir(fdir):
        os.makedirs(fdir)
    f1 = open(fpath, 'w')
    f1.write(html)
    f1.close()
    total += len(html)
    print total

fd.close()
