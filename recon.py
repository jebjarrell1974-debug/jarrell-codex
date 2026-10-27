import re, glob, collections, os
BASE="/home/claude/bible/sources/stepbible/Translators Amalgamated OT+NT"
heb_re=re.compile(r'^([1-5A-Za-z]{2,3})\.(\d+)\.(\d+)(?:\([^)]*\))?#(\d+)(?:\.\d+)?=([A-Za-z()+]+)\t')
grk_re=re.compile(r'^([1-5A-Za-z]{2,3})\.(\d+)\.(\d+)(?:[\[\(\{][^\]\)\}]*[\]\)\}])?#(\d+)(?:\.\d+)?=([A-Za-z()+]+)\t')
for f in sorted(glob.glob(BASE+"/TA*.txt")):
    name=os.path.basename(f)[:12]
    rx = heb_re if "TAHOT" in f else grk_re
    n=0; cols=collections.Counter(); books=collections.Counter(); types=collections.Counter(); bad=0; firstbad=None
    with open(f,encoding='utf-8-sig') as fh:
        for line in fh:
            m=rx.match(line)
            if m:
                n+=1
                cols[line.rstrip('\n').count('\t')+1]+=1
                books[m.group(1)]+=1
                types[m.group(5)]+=1
            elif '\t' in line and re.match(r'^[1-5A-Za-z]{2,3}\.\d+\.\d+', line):
                bad+=1
                if firstbad is None: firstbad=line[:120]
    print(f"{name:14s} rows={n:7d}  books={len(books):2d}  colcounts={dict(cols.most_common(3))}")
    print(f"{'':14s} top types={dict(types.most_common(6))}")
    print(f"{'':14s} unmatched-but-reflike={bad}  {('first='+repr(firstbad)) if firstbad else ''}")
