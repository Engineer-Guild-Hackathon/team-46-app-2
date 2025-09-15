import csv
import re
import pickle
with open('dictionary/OANC_wordlist_short.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    lines=list(reader)

d={}
for line in lines:
    d[line[0]]=line[2]

with open('dictionary/NGSL.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    lines=list(reader)

for line in lines:
    s=line[4].split('/')[0]
    s=re.sub(r"《.*?》","",s)
    s=re.sub(r"〈.*?〉","",s)
    if line[3] in d:
        d[line[3]]=s

print(d)
with open('OANC.pkl', 'wb') as f:
    pickle.dump(d,f)