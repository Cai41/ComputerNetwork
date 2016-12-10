import os
import urllib2

fd = open('init_5000', 'r')
lines = fd.read().splitlines()
total = 0
lines = lines[171:]
for l in lines:
    try:
        response = urllib2.urlopen('http://ec2-54-167-4-20.compute-1.amazonaws.com:8080'+l)
        html = response.read()
    except:
        continue
    
    if total >= 20*1024*1024:
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
