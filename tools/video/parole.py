import json,sys,wave
import numpy as np
from faster_whisper import WhisperModel
w=wave.open(sys.argv[1]); sr=w.getframerate(); ch=w.getnchannels()
a=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)/32768
if ch>1: a=a.reshape(-1,ch).mean(1)
n=int(len(a)*16000/sr); a=np.interp(np.linspace(0,len(a)-1,n),np.arange(len(a)),a).astype(np.float32)
m=WhisperModel("small",device="cpu",compute_type="int8",local_files_only=True)
segs,_=m.transcribe(a,language="it",word_timestamps=True)
out=[[x.word.strip(),round(x.start,2),round(x.end,2)] for s in segs for x in s.words]
json.dump(out,open(sys.argv[2],"w",encoding="utf-8"),ensure_ascii=False)
print(sr,ch,len(a)/16000); print(out)
