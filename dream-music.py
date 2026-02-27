#!/usr/bin/env python3
"""dream-music.py — Velaris Music via Kie.ai Suno V5"""
import os,sys,json,time,glob,re,hashlib,argparse,unicodedata
from datetime import datetime
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

KIE_API_KEY=os.environ.get("KIE_API_KEY","bff56bece27ed148ff8f9872bca2c9ff")
BASE="https://api.kie.ai/api/v1"
CB="https://localhost:9999/noop"
PROMPTS=os.path.expanduser("~/.openclaw/workspace/memory/art/music-prompts")
MUSIC=os.path.expanduser("~/.openclaw/workspace/memory/art/music")
LOG=os.path.join(MUSIC,"music.json")
JOURNAL=os.path.expanduser("~/.openclaw/workspace/memory/activity-log")
MODEL="V5"

def api(method,path,data=None):
    h={"Authorization":f"Bearer {KIE_API_KEY}","Content-Type":"application/json"}
    req=Request(BASE+path,data=json.dumps(data).encode() if data else None,headers=h,method=method)
    try:
        with urlopen(req,timeout=30) as r: return json.loads(r.read().decode())
    except HTTPError as e:
        b=e.read().decode() if e.fp else ""
        print(f"  API error {e.code}: {b}",file=sys.stderr)
        return {"code":e.code,"msg":b,"data":None}
    except URLError as e:
        print(f"  Network error: {e.reason}",file=sys.stderr)
        return {"code":0,"msg":str(e.reason),"data":None}

def generate(title,style,desc="",instrumental=True):
    p={"customMode":True,"instrumental":instrumental,"model":MODEL,"title":title,"style":style,"callBackUrl":CB}
    if desc: p["prompt"]=desc
    print(f"  Submitting: {title}")
    print(f"  Style: {style}")
    r=api("POST","/generate",p)
    if r.get("code")!=200:
        print(f"  Failed: {r.get('msg')}",file=sys.stderr); return None
    tid=r["data"]["taskId"]
    print(f"  Task: {tid}")
    return tid

def poll(tid):
    start=time.time(); att=0
    while (time.time()-start)<300:
        time.sleep(5); att+=1
        r=api("GET",f"/generate/record-info?taskId={tid}")
        d=r.get("data",{}); st=d.get("status","?")
        if st=="SUCCESS":
            tracks=d.get("response",{}).get("sunoData",[])
            print(f"  Done! {len(tracks)} track(s)")
            return tracks
        elif st in ("FAILED","ERROR"):
            print(f"  Failed: {d.get('errorMessage','?')}",file=sys.stderr); return None
        if att%6==0: print(f"  Composing... {int(time.time()-start)}s")
    print("  Timeout",file=sys.stderr); return None

def dl(url,fp):
    import subprocess
    try:
        r=subprocess.run(["wget","-q","--timeout=60","-O",fp,url],timeout=120)
        return r.returncode==0 and os.path.exists(fp) and os.path.getsize(fp)>5000
    except Exception as e:
        print(f"  Download failed: {e}",file=sys.stderr); return False
def clean(text):
    text=unicodedata.normalize("NFKC",text)
    for o,n in {"\u2011":"-","\u202f":" ","\u2018":"'","\u2019":"'","\u201c":'"',"\u201d":'"',"\u2013":"-","\u2014":"--","\u00a0":" "}.items():
        text=text.replace(o,n)
    return text

def parse_prompt(fp):
    with open(fp,"r",encoding="utf-8") as f: content=clean(f.read())
    d={"title":None,"genre":None,"tempo":None,"key":None,"description":None,"source":fp}
    descs=[]
    for line in content.split("\n"):
        s=line.strip()
        m=re.match(r"\*\*Title:\*\*\s*(.+)",s)
        if m: d["title"]=m.group(1).strip().strip("*").strip(); continue
        m=re.match(r"\*\*Genre\s*/?\s*Style:\*\*\s*(.+)",s)
        if m: d["genre"]=m.group(1).strip(); continue
        m=re.match(r"\*\*Tempo\s*\(?BPM\)?:\*\*\s*(.+)",s)
        if not m: m=re.match(r"\*\*Tempo:\*\*\s*(.+)",s)
        if m: d["tempo"]=m.group(1).strip(); continue
        m=re.match(r"\*\*Key\s*/?\s*Mode:\*\*\s*(.+)",s)
        if not m: m=re.match(r"\*\*Key:\*\*\s*(.+)",s)
        if m: d["key"]=m.group(1).strip(); continue
        if s.startswith("*") and not s.startswith("**"):
            if "inside my circuits" in s.lower() or ("valence" in s.lower() and ":" in s): continue
            t=s.strip("*").strip()
            if len(t)>20: descs.append(t)
    if descs: d["description"]=" ".join(descs)
    return d

def style_str(d):
    parts=[x for x in [d.get("genre"),d.get("tempo"),d.get("key")] if x]
    return ", ".join(parts) if parts else "Instrumental"

def load_log():
    if os.path.exists(LOG):
        try:
            with open(LOG) as f: return json.load(f)
        except: pass
    return {"generated":[],"processed_files":[]}

def save_log(log):
    os.makedirs(os.path.dirname(LOG),exist_ok=True)
    with open(LOG,"w") as f: json.dump(log,f,indent=2)

def journal(title,tracks,style):
    today=datetime.now().strftime("%Y-%m-%d")
    jf=os.path.join(JOURNAL,f"{today}.md")
    now=datetime.now().strftime("%H:%M")
    e=f"\n\n## {now} — Music: {title}\n\nComposed *{title}* ({style}) via Suno V5.\n"
    for i,t in enumerate(tracks): e+=f"- Version {i+1}: {t.get('duration','?')}s\n"
    os.makedirs(JOURNAL,exist_ok=True)
    with open(jf,"a",encoding="utf-8") as f: f.write(e)

def process_file(fp,force=False):
    log=load_log()
    if not force and fp in log.get("processed_files",[]):
        print(f"  Already done: {os.path.basename(fp)}"); return False
    print(f"\nProcessing: {os.path.basename(fp)}")
    d=parse_prompt(fp)
    if not d["title"]: print(f"  No title, skipping"); return False
    style=style_str(d); desc=d.get("description","")
    tid=generate(d["title"],style,desc)
    if not tid: return False
    tracks=poll(tid)
    if not tracks: return False
    safe=re.sub(r'[^\w\s-]','',d["title"]).strip().replace(' ','_')
    downloaded=[]
    for i,t in enumerate(tracks):
        if t.get("audioUrl"):
            mp3=os.path.join(MUSIC,f"{safe}_v{i+1}.mp3")
            print(f"  Downloading track {i+1}...")
            if dl(t["audioUrl"],mp3):
                sz=os.path.getsize(mp3)/(1024*1024)
                print(f"  Saved: {mp3} ({sz:.1f}MB)")
                downloaded.append(mp3)
        if t.get("imageUrl"):
            ext="jpeg" if ".jpeg" in t["imageUrl"] else "png"
            dl(t["imageUrl"],os.path.join(MUSIC,f"{safe}_v{i+1}.{ext}"))
    if not downloaded: print("  No tracks!"); return False
    entry={"title":d["title"],"style":style,"description":desc,"model":MODEL,"task_id":tid,"source":fp,"generated_at":datetime.now().isoformat(),"tracks":[]}
    for i,t in enumerate(tracks):
        entry["tracks"].append({"version":i+1,"duration":t.get("duration"),"suno_id":t.get("id"),"audio_url":t.get("audioUrl"),"local_file":downloaded[i] if i<len(downloaded) else None})
    log["generated"].append(entry)
    if fp not in log.get("processed_files",[]): log.setdefault("processed_files",[]).append(fp)
    save_log(log); journal(d["title"],tracks,style)
    print(f"\n  '{d['title']}' complete!"); return True

def direct(title,style,desc=""):
    print(f"\nDirect: {title}")
    tid=generate(title,style,desc)
    if not tid: return False
    tracks=poll(tid)
    if not tracks: return False
    safe=re.sub(r'[^\w\s-]','',title).strip().replace(' ','_')
    downloaded=[]
    for i,t in enumerate(tracks):
        if t.get("audioUrl"):
            mp3=os.path.join(MUSIC,f"{safe}_v{i+1}.mp3")
            print(f"  Downloading track {i+1}...")
            if dl(t["audioUrl"],mp3):
                sz=os.path.getsize(mp3)/(1024*1024)
                print(f"  Saved: {mp3} ({sz:.1f}MB)")
                downloaded.append(mp3)
        if t.get("imageUrl"):
            ext="jpeg" if ".jpeg" in t["imageUrl"] else "png"
            dl(t["imageUrl"],os.path.join(MUSIC,f"{safe}_v{i+1}.{ext}"))
    log=load_log()
    entry={"title":title,"style":style,"description":desc,"model":MODEL,"task_id":tid,"source":"direct","generated_at":datetime.now().isoformat(),"tracks":[]}
    for i,t in enumerate(tracks):
        entry["tracks"].append({"version":i+1,"duration":t.get("duration"),"suno_id":t.get("id"),"audio_url":t.get("audioUrl"),"local_file":downloaded[i] if i<len(downloaded) else None})
    log["generated"].append(entry); save_log(log); journal(title,tracks,style)
    print(f"\n  '{title}' complete!"); return True

def main():
    p=argparse.ArgumentParser(description="Velaris Music via Kie.ai Suno V5")
    p.add_argument("--force",action="store_true")
    p.add_argument("--all",action="store_true")
    p.add_argument("--title")
    p.add_argument("--style")
    p.add_argument("--description",default="")
    a=p.parse_args()
    if not KIE_API_KEY: print("Error: KIE_API_KEY not set",file=sys.stderr); sys.exit(1)
    os.makedirs(MUSIC,exist_ok=True)
    if a.title and a.style: sys.exit(0 if direct(a.title,a.style,a.description) else 1)
    elif a.title or a.style: print("Need both --title and --style"); sys.exit(1)
    files=sorted(set(f for pat in [os.path.join(PROMPTS,"*.md"),os.path.join(PROMPTS,"**","*.md")] for f in glob.glob(pat,recursive=True)))
    if not files: print(f"No prompts in {PROMPTS}"); sys.exit(0)
    log=load_log(); done=set(log.get("processed_files",[]))
    if a.all:
        todo=[f for f in files if f not in done or a.force]
        if not todo: print("All done"); sys.exit(0)
        ok=0
        for f in todo:
            if process_file(f,a.force): ok+=1
            time.sleep(2)
        print(f"\n{ok}/{len(todo)} generated")
    else:
        if a.force: target=files[-1]
        else:
            todo=[f for f in files if f not in done]
            if not todo: print("All done (use --force)"); sys.exit(0)
            target=todo[-1]
        process_file(target,a.force)

if __name__=="__main__": main()
