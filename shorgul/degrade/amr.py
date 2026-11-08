"""AMR-NB (3GPP mobile voice codec) round trip via libopencore-amrnb, the encoder ffmpeg itself wraps.

macOS: brew install opencore-amr · Debian/Ubuntu: apt-get install libopencore-amrnb0
Override the library path with SHORGUL_AMRNB_LIB.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import os
from functools import lru_cache

import numpy as np

FRAME = 160                  # 20 ms at 8 kHz
MODES = {"MR475": 0, "MR515": 1, "MR59": 2, "MR67": 3, "MR74": 4, "MR795": 5, "MR102": 6, "MR122": 7}
_CANDIDATES = ["/opt/homebrew/lib/libopencore-amrnb.dylib", "/usr/local/lib/libopencore-amrnb.dylib",
               "/usr/lib/x86_64-linux-gnu/libopencore-amrnb.so.0", "/usr/lib/aarch64-linux-gnu/libopencore-amrnb.so.0"]


@lru_cache(maxsize=1)
def _lib() -> ctypes.CDLL | None:
    paths = [os.environ.get("SHORGUL_AMRNB_LIB"), ctypes.util.find_library("opencore-amrnb"), *_CANDIDATES]
    for p in paths:
        if p and (os.path.exists(p) or not p.startswith("/")):
            try:
                lib = ctypes.CDLL(p)
            except OSError:
                continue
            lib.Encoder_Interface_init.restype = ctypes.c_void_p
            lib.Encoder_Interface_init.argtypes = [ctypes.c_int]
            lib.Encoder_Interface_Encode.restype = ctypes.c_int
            lib.Encoder_Interface_Encode.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_short),
                                                     ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int]
            lib.Encoder_Interface_exit.argtypes = [ctypes.c_void_p]
            lib.Decoder_Interface_init.restype = ctypes.c_void_p
            lib.Decoder_Interface_Decode.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ubyte),
                                                     ctypes.POINTER(ctypes.c_short), ctypes.c_int]
            lib.Decoder_Interface_exit.argtypes = [ctypes.c_void_p]
            return lib
    return None


def available() -> bool:
    return _lib() is not None


def amrnb_roundtrip(audio_8k: np.ndarray, mode: str = "MR122") -> np.ndarray:
    """float32 8 kHz -> AMR-NB frames at `mode` -> float32 8 kHz (same length). Deterministic."""
    lib = _lib()
    if lib is None:
        raise RuntimeError("libopencore-amrnb not found (macOS: brew install opencore-amr; "
                           "Ubuntu: apt-get install libopencore-amrnb0)")
    n = len(audio_8k)
    pcm = np.clip(audio_8k, -1, 1)
    pcm = np.pad((pcm * 32767).astype(np.int16), (0, (-n) % FRAME))
    enc, dec = lib.Encoder_Interface_init(0), lib.Decoder_Interface_init()
    out = np.zeros_like(pcm)
    buf = (ctypes.c_ubyte * 64)()
    frame_out = (ctypes.c_short * FRAME)()
    try:
        for i in range(0, len(pcm), FRAME):
            frame = np.ascontiguousarray(pcm[i:i + FRAME])
            nbytes = lib.Encoder_Interface_Encode(enc, MODES[mode], frame.ctypes.data_as(ctypes.POINTER(ctypes.c_short)),
                                                  buf, 0)
            if nbytes <= 0:
                raise RuntimeError("AMR-NB encode failed")
            lib.Decoder_Interface_Decode(dec, buf, frame_out, 0)
            out[i:i + FRAME] = np.frombuffer(frame_out, dtype=np.int16)
    finally:
        lib.Encoder_Interface_exit(enc)
        lib.Decoder_Interface_exit(dec)
    return (out[:n].astype(np.float32) / 32767).copy()
