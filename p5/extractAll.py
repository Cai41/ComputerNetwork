
f = open('popular_raw.html', 'r')
res5000 = open('init_5000', 'w')
res300 = open('init_300', 'w')

html = f.read()
html1 = html
total = 0
first100 = 0
i = 0

while html1.find('<td align=\"right') != -1:
    pos = html1.find('<td align=\"right')
    end = html1.find('</td>', pos)
    total += int(html1[pos+18: end].replace(',',''))
    if i < 100:
        first100 += int(html1[pos+18: end].replace(',',''))
    html1 = html1[end+5:]
    i += 1

i = 0
while html.find('<a href=\"') != -1:
    pos = html.find('<a href=\"')
    end = html.find('\"', pos+9)
    url = html[pos+9:end]
    html = html[end+1:]
    if 'File' not in url:
        res5000.write(url+'\n')            
        if i < 300:
            res300.write(url+'\n')            
        print url
        i += 1
        
print total, first100

res5000.close()
res300.close()
f.close()

# 327 073 941
