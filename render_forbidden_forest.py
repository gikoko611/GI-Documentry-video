#!/usr/bin/env python3
"""Render G.I KO KO Forbidden Forest: 5 min, 720x1280, bilingual subtitles."""
import asyncio, json, os, random, subprocess
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import edge_tts

ROOT=Path(__file__).resolve().parent
ASSETS=ROOT/"assets"; IMAGES=ASSETS/"images"; WORK=ROOT/"work"
OUT=Path(os.environ.get("OUTPUT_DIR",ROOT/"output"))
STORY=json.loads((ROOT/"story.json").read_text(encoding="utf-8"))
W,H,FPS,CLIP=720,1280,24,30
VIDEO=OUT/"forbidden_forest_gi_koko_720x1280.mp4"
random.seed(24)

def run(cmd): subprocess.run(cmd,check=True)
def fnt(size,bold=False):
    p="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    return ImageFont.truetype(p,size) if Path(p).exists() else ImageFont.load_default()

def make_logo():
    ASSETS.mkdir(parents=True,exist_ok=True); p=ASSETS/"gi_logo.png"
    im=Image.new("RGBA",(420,150),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.rounded_rectangle((4,4,416,146),radius=26,fill=(4,13,12,225),outline=(204,166,75,255),width=5)
    d.ellipse((22,23,124,125),fill=(14,45,35,255),outline=(218,183,95,255),width=4)
    d.text((39,43),"GI",font=fnt(48,True),fill=(245,220,150,255))
    d.text((143,30),"G.I KO KO",font=fnt(36,True),fill=(245,220,150,255))
    d.text((145,82),"MYSTERY DOCUMENTARY",font=fnt(17,True),fill=(225,235,220,255))
    im.save(p); return p

def fallback_forest():
    im=Image.new("RGB",(W,H),(5,17,18)); px=im.load()
    for y in range(H):
        t=y/H
        for x in range(W):
            glow=max(0,1-abs(x-W*.52)/(W*.75))*max(0,1-t)
            px[x,y]=(int(4+5*glow),int(13+24*glow),int(16+16*glow))
    d=ImageDraw.Draw(im,"RGBA")
    for _ in range(65):
        x=random.randint(-80,W+80); wd=random.randint(12,50)
        top=random.randint(40,650)
        d.polygon([(x-wd,H),(x-wd//2,top+120),(x+wd//2,top),(x+wd,H)],fill=(2,8,7,220))
        for __ in range(4):
            yy=random.randint(250,H)
            d.ellipse((x-120,yy-90,x+120,yy+90),fill=(7,34,20,110))
    for _ in range(9):
        yy=random.randint(200,1100); d.ellipse((-120,yy-45,W+120,yy+45),fill=(190,205,190,13))
    return im.filter(ImageFilter.GaussianBlur(2))

QUERIES=[
 "tropical rainforest mist fog","rainforest jungle trail dense forest","tropical rainforest night forest",
 "abandoned research station forest","misty forest lights night","jungle cave entrance tropical forest",
 "underground cave roots rainforest","dark forest cave blue water","rainforest trail night flashlight",
 "dense tropical forest dawn fog"
]
def get_image(query,index):
    IMAGES.mkdir(parents=True,exist_ok=True); api="https://commons.wikimedia.org/w/api.php"
    params={"action":"query","generator":"search","gsrsearch":query,"gsrnamespace":6,"gsrlimit":18,
            "prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":1100,"format":"json"}
    headers={"User-Agent":"GIKOKOForbiddenForest/0.0.1 (creative documentary)"}
    try:
        data=requests.get(api,params=params,headers=headers,timeout=30).json()
        for page in data.get("query",{}).get("pages",{}).values():
            info=page.get("imageinfo",[{}])[0]; meta=info.get("extmetadata",{})
            lic=meta.get("LicenseShortName",{}).get("value",""); up=lic.upper()
            ok=("PUBLIC DOMAIN" in up or "CC0" in up or ("CC BY" in up and "NC" not in up and "ND" not in up))
            url=info.get("thumburl") or info.get("url")
            if not ok or not url: continue
            r=requests.get(url,headers=headers,timeout=40); r.raise_for_status()
            (IMAGES/f"source_{index:02d}").write_bytes(r.content)
            with (ASSETS/"ATTRIBUTION.txt").open("a",encoding="utf-8") as f:
                f.write(f"Scene {index}: {page.get('title','')} | {lic} | {meta.get('Artist',{}).get('value','Unknown')} | {info.get('descriptionurl','')}\n")
            return Image.open(IMAGES/f"source_{index:02d}").convert("RGB")
    except Exception as e: print(f"Image lookup fallback scene {index}: {e}")
    return fallback_forest()

def prepare_image(index,query):
    im=get_image(query,index); iw,ih=im.size; scale=max(W/iw,H/ih)
    im=im.resize((int(iw*scale),int(ih*scale)),Image.Resampling.LANCZOS)
    x=(im.width-W)//2; y=(im.height-H)//2; im=im.crop((x,y,x+W,y+H)).convert("RGB")
    im=Image.blend(im,Image.new("RGB",(W,H),(0,12,10)),0.25)
    p=IMAGES/f"scene_{index:02d}.jpg"; im.save(p,quality=87,optimize=True); return p

def stamp(sec):
    ms=int(round(sec*1000)); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def local_srt(item,path):
    words=item["en"].split(); mid=max(1,len(words)//2); mm_words=item["mm"].split(); mmid=max(1,len(mm_words)//2)
    entries=[]
    for n,(a,b) in enumerate(((0,15),(15,30))):
        en=" ".join(words[:mid]) if n==0 else " ".join(words[mid:])
        my=" ".join(mm_words[:mmid]) if n==0 else " ".join(mm_words[mmid:])
        entries += [str(n+1),f"{stamp(a)} --> {stamp(b)}",en+"\n"+my,""]
    path.write_text("\n".join(entries),encoding="utf-8")

async def generate_speech():
    for i,item in enumerate(STORY,1):
        p=WORK/f"narration_{i:02d}.mp3"
        await edge_tts.Communicate(item["en"],"en-US-GuyNeural",rate="-5%",pitch="-2Hz").save(str(p))
        if not p.exists() or p.stat().st_size<1000: raise RuntimeError(f"TTS failed: scene {i}")
        print(f"Speech {i}/10 generated")

def main():
    for tool in ("ffmpeg","ffprobe"):
        if subprocess.call(["bash","-lc",f"command -v {tool} >/dev/null 2>&1"])!=0: raise SystemExit(f"Missing {tool}")
    WORK.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True); IMAGES.mkdir(parents=True,exist_ok=True)
    logo=make_logo(); (ASSETS/"ATTRIBUTION.txt").write_text("Reusable image credits (Wikimedia Commons).\n",encoding="utf-8")
    print("Preparing forest scenes...")
    for i,q in enumerate(QUERIES,1): prepare_image(i,q)
    print("Generating English narration...")
    asyncio.run(generate_speech())
    clips=[]
    for i,item in enumerate(STORY,1):
        img=IMAGES/f"scene_{i:02d}.jpg"; audio=WORK/f"narration_{i:02d}.mp3"
        subs=WORK/f"scene_{i:02d}.srt"; local_srt(item,subs)
        out=WORK/f"clip_{i:02d}.mp4"
        vf=("scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,"
            "zoompan=z='min(zoom+0.00022,1.045)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=720x1280:fps=24,"
            f"subtitles=filename='{subs.as_posix()}':fontsdir='/usr/share/fonts/truetype':"
            "force_style='FontName=Noto Sans Myanmar,FontSize=18,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&HCC000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=120'")
        fc=("[1:a]aresample=44100,apad=pad_dur=30,atrim=duration=30,volume=1.0[voice];"
            "anoisesrc=color=brown:amplitude=0.012:sample_rate=44100:duration=30,"
            "lowpass=f=900,volume=0.18[amb];[voice][amb]amix=inputs=2:duration=longest:normalize=0[a]")
        run(["ffmpeg","-hide_banner","-loglevel","error","-y","-loop","1","-framerate","24","-i",str(img),
             "-i",str(audio),"-filter_complex",fc,"-vf",vf,"-map","0:v:0","-map","[a]","-t","30",
             "-c:v","libx264","-preset","veryfast","-crf","29","-maxrate","900k","-bufsize","1800k",
             "-pix_fmt","yuv420p","-r","24","-threads","2","-c:a","aac","-b:a","96k",
             "-movflags","+faststart",str(out)])
        clips.append(out); print(f"Rendered scene {i}/10")
    concat=WORK/"concat.txt"; concat.write_text("".join(f"file '{p.resolve()}'\n" for p in clips),encoding="utf-8")
    joined=WORK/"joined.mp4"
    run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",str(concat),
         "-c","copy","-movflags","+faststart",str(joined)])
    run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(joined),"-i",str(logo),
         "-filter_complex","[0:v][1:v]overlay=W-w-18:22:format=auto[v]","-map","[v]","-map","0:a:0",
         "-c:v","libx264","-preset","veryfast","-crf","29","-maxrate","900k","-bufsize","1800k",
         "-pix_fmt","yuv420p","-r","24","-c:a","copy","-t","300","-movflags","+faststart",str(VIDEO)])
    meta=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration,size",
        "-of","json",str(VIDEO)],text=True))["format"]
    duration=float(meta["duration"]); size=int(meta["size"])/1024/1024
    print(f"SUCCESS: {VIDEO} | {duration:.2f}s | {size:.2f} MB")
    if not 299<=duration<=301: raise SystemExit("Duration verification failed: expected about 300 seconds")
if __name__=="__main__": main()
