import re,subprocess,sys,difflib,collections
root=sys.argv[1]
TOK=re.compile(r"[A-Za-z_]\w*|\d+\.?\d*[fF]?|>=|<=|==|!=|&&|\|\||<<|>>|[-+*/<>=!&|^%(),;\[\]{}.]")
def toks(s): return TOK.findall(s)
def shape(a,b):
    if re.match(r"\s*(\*|//|/\*|#)",a) or re.match(r"\s*(\*|//|/\*|#)",b): return None
    if re.search(r"version|revision|_major|_minor|patch",a+b,re.I): return None
    ta,tb=toks(a),toks(b)
    if not ta or not tb or ta==tb: return None
    ops=[o for o in difflib.SequenceMatcher(None,ta,tb).get_opcodes() if o[0]!="equal"]
    if len(ops)!=1: return None
    tag,i1,i2,j1,j2=ops[0]; x,y=ta[i1:i2],tb[j1:j2]
    if tag=="replace" and len(x)==1 and len(y)==1:
        p={x[0],y[0]}
        if p<= {">=",">"} or p<={"<=","<"}: return "boundary"
        if p<= {"==","!="} or p<={"<",">"} or p<={"<=",">="}: return "compare"
        if p<= {"+","-"} or p<={"*","/"}: return "operator"
        if p<= {"&&","||"}: return "logic"
        if re.fullmatch(r"\d+",x[0]) and re.fullmatch(r"\d+",y[0]) and abs(int(x[0])-int(y[0]))==1: return "off-by-one"
        return None
    if tag in("insert","delete"):
        z=x or y
        if z==["-"]: return "sign"
        if z in(["+","1"],["-","1"]): return "off-by-one"
        if z==["!"]: return "logic"
    return None
log=subprocess.run(["git","-C",root,"log","--no-merges","-U0","--format=COMMIT\t%H\t%s","-p","--","*.c","*.cpp","*.h","*.hpp"],capture_output=True,text=True,errors="replace").stdout
total=0; fixish=0; hits=collections.Counter(); hit_commits=0; fix_hits=0; examples=[]
cur=None; subj=""; minus=[]; plus=[]; found=set(); curfile=""
FIX=re.compile(r"fix|bug|crash|wrong|incorrect|regress|issue|broken|error",re.I)
def flush():
    global hit_commits,fix_hits
    if cur is None: return
    if re.search(r"(^|/)(test|tests|unit-test|unittest|testbed|samples?|benchmark)s?/",curfile): return
    if len(minus)==1 and len(plus)==1:
        s=shape(minus[0],plus[0])
        if s: found.add(s); 
        if s and len(examples)<8: examples.append((s,subj[:60],minus[0].strip()[:70],plus[0].strip()[:70]))
def endcommit():
    global hit_commits,fix_hits,total,fixish
    flush()
    if cur is not None:
        total+=1
        if FIX.search(subj): fixish+=1
        if found:
            hit_commits+=1
            if FIX.search(subj): fix_hits+=1
            for s in found: hits[s]+=1
for line in log.splitlines():
    if line.startswith("COMMIT\t"):
        endcommit(); _,cur,subj=line.split("\t",2); minus=[];plus=[];found=set()
    elif line.startswith("+++ "):
        curfile=line[4:]
    elif line.startswith("@@"):
        flush(); minus=[];plus=[]
    elif line.startswith("+") and not line.startswith("+++"): plus.append(line[1:])
    elif line.startswith("-") and not line.startswith("---"): minus.append(line[1:])
endcommit()
dates=subprocess.run(["git","-C",root,"log","--no-merges","--format=%ct","--","*.c","*.cpp","*.h","*.hpp"],capture_output=True,text=True).stdout.split()
years=(int(dates[0])-int(dates[-1]))/31557600 if len(dates)>1 else 0
print(f"{root.rsplit('/',1)[-1]}: {total} source commits over {years:.1f} years, {fixish} fix-worded")
print(f"  commits containing a single-line, single-token shape change: {hit_commits}  (of those, fix-worded: {fix_hits})")
for s,n in hits.most_common(): print(f"    {s:12s} {n}")
print(f"  agent tokens at 43,006/defect (measured 2026-09-07, armA/armB beside this file): {hit_commits*43006:,}  |  fluidfix: 0")
print(f"  per year: {hit_commits/years:.1f} taught-shape commits, {hit_commits*43006/years:,.0f} agent tokens") if years else None
print("  examples:")
for e in examples: print(f"    [{e[0]}] {e[1]}\n        - {e[2]}\n        + {e[3]}")
