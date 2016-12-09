import os
import urllib2

f = open('init', 'r')
lines = f.read().splitlines()
for l in lines:
    try:
        response = urllib2.urlopen('http://ec2-54-167-4-20.compute-1.amazonaws.com:8080/wiki/'+l)
        html = response.read()
    except:
        continue
    fpath = os.getcwd()+'/data/wiki/'+l
    fdir = os.path.dirname(fpath)
    if fdir != '' and not os.path.isdir(fdir):
        os.makedirs(fdir)    
    f1 = open(fpath, 'w')
    f1.write(html)
    f1.close()

f.close()

