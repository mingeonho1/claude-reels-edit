#!/usr/bin/env python3
"""2-speaker diarization: sliding-window (1.2s win, 0.3s hop) ERes2Net embeddings over voiced frames,
agglomerative clustering (cosine) into K=2, median smoothing. Output: per-window labels + merged turns.
usage: diarize.py IN.wav OUT.json [--k 2]
"""
import sys,os,json,subprocess,argparse,numpy as np,sherpa_onnx
ap=argparse.ArgumentParser();ap.add_argument('inp');ap.add_argument('out');ap.add_argument('--k',type=int,default=2)
ap.add_argument('--models',default=os.environ.get('REELS_MODELS', os.path.expanduser('~/reels_models')));a=ap.parse_args()
raw=subprocess.run(['ffmpeg','-v','error','-i',a.inp,'-vn','-ac','1','-ar','16000','-af','highpass=f=70,dynaudnorm=f=150:g=15:p=0.9:m=20','-f','f32le','-'],capture_output=True,check=True).stdout
x=np.frombuffer(raw,dtype=np.float32)
# voiced mask from silero vad
vc=sherpa_onnx.VadModelConfig();vc.silero_vad.model=f'{a.models}/silero_vad.onnx';vc.silero_vad.threshold=0.35;vc.silero_vad.min_silence_duration=0.15;vc.silero_vad.min_speech_duration=0.1;vc.sample_rate=16000
vad=sherpa_onnx.VoiceActivityDetector(vc,buffer_size_in_seconds=900)
sp=[]
for i in range(0,len(x),512):
    vad.accept_waveform(x[i:i+512])
    while not vad.empty(): s=vad.front;sp.append((s.start/16000,(s.start+len(s.samples))/16000));vad.pop()
vad.flush()
while not vad.empty(): s=vad.front;sp.append((s.start/16000,(s.start+len(s.samples))/16000));vad.pop()
ex=sherpa_onnx.SpeakerEmbeddingExtractor(sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=f'{a.models}/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx',num_threads=2))
win,hop=1.2,0.3; W=[];E=[]
for s,e in sp:
    t=s
    while True:
        c=min(t+win/2,e) if e-s<win else t+win/2
        a0=max(s,c-win/2);a1=min(e,c+win/2)
        if a1-a0<0.5: break
        st=ex.create_stream();st.accept_waveform(16000,x[int(a0*16000):int(a1*16000)]);st.input_finished()
        v=np.array(ex.compute(st));E.append(v/np.linalg.norm(v));W.append(round(c,2))
        t+=hop
        if t+win/2>e+hop/2 or e-s<win: break
E=np.array(E)
# agglomerative average-linkage on cosine
from scipy.cluster.hierarchy import linkage,fcluster
Z=linkage(E,'average',metric='cosine');lab=fcluster(Z,a.k,'maxclust')-1
# relabel by size; smooth with 5-window median within each speech region
lab=np.array(lab)
cnt=np.bincount(lab,minlength=a.k);order=np.argsort(-cnt);remap={o:i for i,o in enumerate(order)};lab=np.array([remap[l] for l in lab])
sm=lab.copy()
for i in range(len(lab)):
    lo,hi=max(0,i-2),min(len(lab),i+3);sm[i]=np.bincount(lab[lo:hi]).argmax()
cent=[E[sm==k].mean(0).tolist() for k in range(a.k)]
# turns: assign each voiced region slice by nearest window
turns=[]
for s,e in sp:
    idx=[i for i,c in enumerate(W) if s-0.01<=c<=e+0.01]
    if not idx: continue
    cur=sm[idx[0]];st=s
    for j in range(1,len(idx)):
        if sm[idx[j]]!=cur:
            b=(W[idx[j-1]]+W[idx[j]])/2;turns.append(dict(start=round(st,2),end=round(b,2),spk=int(cur)));st=b;cur=sm[idx[j]]
    turns.append(dict(start=round(st,2),end=round(e,2),spk=int(cur)))
json.dump(dict(speech=[[round(s,3),round(e,3)] for s,e in sp],windows=[dict(t=c,spk=int(l)) for c,l in zip(W,sm)],turns=turns,centroids=cent,cluster_sizes=np.bincount(sm,minlength=a.k).tolist()),open(a.out,'w'))
print('windows',len(W),'sizes',np.bincount(sm,minlength=a.k),'turns',len(turns))
