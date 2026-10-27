import subprocess, json, os, hashlib, glob
SRC="/home/claude/bible/sources"
man={"repos":{},"files":{}}
for r in sorted(os.listdir(SRC)):
    p=os.path.join(SRC,r)
    if not os.path.isdir(os.path.join(p,".git")): continue
    try:
        h=subprocess.check_output(["git","-C",p,"rev-parse","HEAD"],text=True).strip()
        d=subprocess.check_output(["git","-C",p,"log","-1","--format=%cI"],text=True).strip()
        u=subprocess.check_output(["git","-C",p,"remote","get-url","origin"],text=True).strip()
        man["repos"][r]={"commit":h,"committed":d,"origin":u}
    except subprocess.CalledProcessError as e:
        man["repos"][r]={"error":str(e)}
for f in sorted(glob.glob(SRC+"/stepbible/**/*.txt",recursive=True)):
    if any(k in f for k in ["TAHOT","TAGNT","TBESH","TBESG","TEHMC","TEGMC","TVTMS","TIPNR"]) and "Older Formats" not in f:
        hh=hashlib.sha256(open(f,'rb').read()).hexdigest()[:16]
        man["files"][os.path.relpath(f,SRC)]={"sha256_16":hh,"bytes":os.path.getsize(f)}
os.makedirs("/home/claude/bible/build",exist_ok=True)
json.dump(man,open("/home/claude/bible/build/manifest.json","w"),indent=2)
print(json.dumps(man["repos"],indent=2))
print(f"\npinned {len(man['files'])} source files")
