import os
import urllib2

f = open('init_300', 'r')
nf = open('notFound', 'w')
fd = open('found', 'w')
lines = f.read().splitlines()
total = 0
i = 0
for l in lines:
    print i
    i += 1
    try:
        response = urllib2.urlopen('http://ec2-54-167-4-20.compute-1.amazonaws.com:8080'+l)
        print 'http://ec2-54-167-4-20.compute-1.amazonaws.com:8080'+l
        html = response.read()
    except Exception as e:
        nf.write(l+'\n')
        print e.code
        continue
    if total < 8.5*1024*1024:
        fd.write(l+'\n')
        total += len(html)
    
print total
f.close()
nf.close()
fd.close()
