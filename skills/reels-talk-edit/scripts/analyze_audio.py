#!/usr/bin/env python3
"""Shared audio analysis: VAD segments + Korean STT (whisper-turbo text, zipformer token timestamps)
+ speaker embeddings + 10ms RMS envelope.
usage: analyze_audio.py IN.(wav|mov|mp4) OUT.json [--models DIR]
"""
import re, sys, os, json, subprocess, argparse, numpy as np, soundfile as sf, sherpa_onnx, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from align_words import align_words
ap=argparse.ArgumentParser(); ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--models',default=os.environ.get('REELS_MODELS', os.path.expanduser('~/reels_models')))
ap.add_argument('--no-whisper',action='store_true'); a=ap.parse_args()
MD=a.models
tmp=a.out+'.16k.wav'
# 16k mono, boosted (source mics are ~-40 LUFS): dynaudnorm makes VAD/STT robust
subprocess.run(['ffmpeg','-v','error','-y','-i',a.inp,'-vn','-ac','1','-ar','16000','-af','highpass=f=70,dynaudnorm=f=150:g=15:p=0.9:m=20',tmp],check=True)
x,sr=sf.read(tmp,dtype='float32')
# raw envelope from original-level audio (for silence detection) at 10ms hop
raw=subprocess.run(['ffmpeg','-v','error','-i',a.inp,'-vn','-ac','1','-ar','16000','-f','f32le','-'],capture_output=True,check=True).stdout
r=np.frombuffer(raw,dtype=np.float32); hop=160; n=len(r)//hop
rms=np.sqrt((r[:n*hop].reshape(n,hop)**2).mean(1)+1e-12); db=20*np.log10(rms)
np.save(a.out.replace('.json','')+'_rms10ms.npy',db.astype(np.float32))
# VAD
vc=sherpa_onnx.VadModelConfig(); vc.silero_vad.model=f'{MD}/silero_vad.onnx'; vc.silero_vad.threshold=0.35
vc.silero_vad.min_silence_duration=0.25; vc.silero_vad.min_speech_duration=0.15; vc.silero_vad.max_speech_duration=12; vc.sample_rate=16000
vad=sherpa_onnx.VoiceActivityDetector(vc,buffer_size_in_seconds=600)
segs=[]; w=512
for i in range(0,len(x),w):
    vad.accept_waveform(x[i:i+w])
    while not vad.empty():
        s=vad.front; segs.append((s.start/16000,(s.start+len(s.samples))/16000)); vad.pop()
vad.flush()
while not vad.empty():
    s=vad.front; segs.append((s.start/16000,(s.start+len(s.samples))/16000)); vad.pop()
print('vad segs',len(segs),flush=True)
Z=f'{MD}/sherpa-onnx-zipformer-korean-2024-06-24'
zr=sherpa_onnx.OfflineRecognizer.from_transducer(encoder=f'{Z}/encoder-epoch-99-avg-1.int8.onnx',decoder=f'{Z}/decoder-epoch-99-avg-1.onnx',joiner=f'{Z}/joiner-epoch-99-avg-1.int8.onnx',tokens=f'{Z}/tokens.txt',num_threads=2,decoding_method='greedy_search')
if not a.no_whisper:
    W=f'{MD}/sherpa-onnx-whisper-turbo'
    wr=sherpa_onnx.OfflineRecognizer.from_whisper(encoder=f'{W}/turbo-encoder.int8.onnx',decoder=f'{W}/turbo-decoder.int8.onnx',tokens=f'{W}/turbo-tokens-hex.txt',language='ko',task='transcribe',num_threads=2)
ec=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=f'{MD}/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx',num_threads=2)
ex=sherpa_onnx.SpeakerEmbeddingExtractor(ec)
out=[]; t0=time.time()
for k,(s,e) in enumerate(segs):
    pad=0.08; a0=max(0,int((s-pad)*16000)); a1=min(len(x),int((e+pad)*16000)); chunk=x[a0:a1]
    st=zr.create_stream(); st.accept_waveform(16000,chunk); zr.decode_stream(st); R=st.result
    toks=[dict(t=tok,ts=round(a0/16000+ts,3)) for tok,ts in zip(R.tokens,R.timestamps)]
    wt=''
    if not a.no_whisper:
        sw=wr.create_stream(); sw.accept_waveform(16000,chunk); wr.decode_stream(sw); wt=bytes().join(bytes.fromhex(h) for h in re.findall('§([0-9a-f]*)§',sw.result.text)).decode('utf-8','replace').strip()
    emb=None
    if e-s>=0.4:
        se=ex.create_stream(); se.accept_waveform(16000,chunk); se.input_finished(); emb=[round(float(v),5) for v in ex.compute(se)]
    words=align_words(wt,toks,s,e) if wt else []
    out.append(dict(i=k,words=words,start=round(s,3),end=round(e,3),zip_text=R.text.strip(),whisper_text=wt,tokens=toks,emb=emb))
    if k%10==0: print(k,len(segs),round(time.time()-t0),'s',wt[:30],'|',R.text[:30],flush=True)
json.dump(dict(source=a.inp,duration=len(x)/16000,segments=out,rms_hop=0.01,rms_file=os.path.basename(a.out.replace('.json',''))+'_rms10ms.npy'),open(a.out,'w'),ensure_ascii=False)
os.remove(tmp); print('done',round(time.time()-t0),'s')
