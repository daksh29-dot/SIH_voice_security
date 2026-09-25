"""Explicit PCM decoding; no denoising/gain changes. Stateful stream resampling.

Legacy wire format is little-endian int16, mono, 16kHz. Clients can declare
sample_rate, sample_width_bytes (2=int16,4=float32), channels before audio.
Encoded WebM/Opus belongs on a file-upload endpoint, not the PCM WebSocket.
"""
import math
import numpy as np
from scipy.signal import resample_poly
from backend.models.w2v2_aasist import prepare_pcm


class AudioPreprocessor:
    def __init__(self, target_sample_rate=16000, min_rms_energy=.001,
                 min_peak_amplitude=.002, max_peak_amplitude=1.0, *, streaming=False):
        if target_sample_rate != 16000:
            raise ValueError('These models require 16000 Hz')
        self.target_sample_rate = target_sample_rate
        self.min_rms_energy = min_rms_energy
        self.min_peak_amplitude = min_peak_amplitude
        self.max_peak_amplitude = max_peak_amplitude
        self.streaming = streaming
        self.reset()

    def reset(self):
        self._byte_tail = b''
        self._format = None
        self._buffer = np.empty(0, dtype=np.float32)
        self._start = self._next_output = 0

    @staticmethod
    def pcm_to_float32(raw_bytes, sample_width_bytes=2):
        if sample_width_bytes not in (2, 4) or len(raw_bytes) % sample_width_bytes:
            raise ValueError('Incomplete or unsupported PCM sample')
        dtype = '<i2' if sample_width_bytes == 2 else '<f4'
        x = np.frombuffer(raw_bytes, dtype=dtype)
        return x.astype(np.float32)/32768 if sample_width_bytes == 2 else x.copy()

    @staticmethod
    def to_mono(audio):
        return prepare_pcm(audio, 16000)

    def resample_if_needed(self, audio, orig_sr):
        if orig_sr == 16000 or not len(audio):
            return audio
        g = math.gcd(orig_sr, 16000)
        up, down = 16000//g, orig_sr//g
        if not self.streaming:
            return resample_poly(audio, up, down).astype(np.float32)
        # Retain past filter support and defer outputs needing future samples.
        # _start is a multiple of down, preserving the global rational phase.
        support = math.ceil(10*max(up, down)/up)+2
        self._buffer = np.concatenate((self._buffer, audio))
        total = self._start+len(self._buffer)
        stop = max(self._next_output, (max(0,total-support)*up)//down)
        base = self._start*up//down
        y = resample_poly(self._buffer, up, down)
        result = y[self._next_output-base:stop-base].copy()
        self._next_output = stop
        keep_from = max(self._start, ((stop*down//up-support)//down)*down)
        self._buffer = self._buffer[keep_from-self._start:].copy()
        self._start = keep_from
        return result.astype(np.float32)

    @staticmethod
    def compute_energy(audio):
        if not len(audio):
            return 0., 0.
        x = np.asarray(audio,dtype=np.float64)
        return float(np.sqrt(np.mean(x*x))), float(np.max(np.abs(x)))

    def validate_energy(self, audio):
        if not len(audio):
            return False, dict(valid=False, reason='EMPTY_FRAME', rms=0., peak=0.)
        if not np.isfinite(audio).all():
            return False, dict(valid=False, reason='NON_FINITE_DATA_CORRUPTION', rms=0., peak=0.)
        rms, peak = self.compute_energy(audio)
        clipped = float(np.mean(np.abs(audio)>=.999))
        ac_rms = float(np.std(audio.astype(np.float64)))
        reason = 'OK'
        if clipped > .01 or peak > 1.5:
            reason = 'CLIPPED_FRAME'
        elif ac_rms < self.min_rms_energy:
            reason = 'SILENT_FRAME'
        return reason=='OK', dict(valid=reason=='OK',reason=reason,rms=rms,peak=peak,clipped_fraction=clipped)

    def process_chunk(self, chunk, input_sr=16000, sample_width_bytes=2, channels=1):
        try:
            if isinstance(input_sr,bool) or not isinstance(input_sr,(int,np.integer)) or not 8000<=input_sr<=192000:
                raise ValueError('Invalid source sample rate')
            if channels not in (1,2) or sample_width_bytes not in (2,4):
                raise ValueError('Unsupported PCM format')
            fmt = (int(input_sr),sample_width_bytes,channels)
            if self.streaming and self._format is not None and fmt != self._format:
                raise ValueError('Reset stream before changing audio format')
            self._format = fmt
            if isinstance(chunk,(bytes,bytearray)):
                if bytes(chunk[:4]) in (b'RIFF',b'OggS',b'\x1aE\xdf\xa3'):
                    raise ValueError('Encoded media is not PCM; use the file upload endpoint')
                raw = self._byte_tail+bytes(chunk)
                frame_bytes = sample_width_bytes*channels
                complete = len(raw)//frame_bytes*frame_bytes
                if not self.streaming and complete != len(raw):
                    raise ValueError('Incomplete PCM frame')
                self._byte_tail = raw[complete:] if self.streaming else b''
                audio = self.pcm_to_float32(raw[:complete],sample_width_bytes)
                if not len(audio):
                    return audio,False,dict(valid=False,reason='EMPTY_FRAME',rms=0.,peak=0.,samples=0,duration_ms=0.)
                if channels>1:
                    audio=audio.reshape(-1,channels).mean(axis=1)
            else:
                audio = np.asarray(chunk)
                if audio.size==0:
                    return np.empty(0,dtype=np.float32),False,dict(valid=False,reason='EMPTY_FRAME',rms=0.,peak=0.)
            audio=prepare_pcm(audio,16000)  # convert scale/channels, not rate yet
            audio=self.resample_if_needed(audio,int(input_sr))
            valid,info=self.validate_energy(audio)
            info.update(samples=len(audio),duration_ms=len(audio)/16,source_sample_rate=int(input_sr))
            return audio,valid,info
        except (ValueError,TypeError) as exc:
            self.reset()
            return np.empty(0,dtype=np.float32),False,dict(valid=False,reason='INVALID_PCM',error=str(exc),rms=0.,peak=0.)


_default_preprocessor=AudioPreprocessor()
def validate_and_convert_chunk(chunk,input_sr=16000,sample_width_bytes=2):
    return _default_preprocessor.process_chunk(chunk,input_sr,sample_width_bytes)
def check_audio_energy(audio,min_rms=.001):
    if len(audio)==0 or not np.isfinite(audio).all(): return False,0.
    rms,_=AudioPreprocessor.compute_energy(audio)
    return rms>=min_rms,rms
