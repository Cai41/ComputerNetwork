import os
import urllib2

fd = open('found', 'w')
lines = fd.read().splitlines()
total = 0
for l in reversed(lines):
    try:
        response = urllib2.urlopen('http://ec2-54-167-4-20.compute-1.amazonaws.com:8080/wiki/'+l)
        html = response.read()
    except:
        nf.write(l+'\n')
        continue
    
    if total >= 9*1024*1024:
        break

    fd.write(l+'\n')
    fpath = os.getcwd()+'/data/wiki/'+l
    fdir = os.path.dirname(fpath)
    if fdir != '' and not os.path.isdir(fdir):
        os.makedirs(fdir)
    f1 = open(fpath, 'w')
    f1.write(html)
    f1.close()
    total += len(html)

fd.close()
