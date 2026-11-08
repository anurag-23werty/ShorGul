import { useCallback, useEffect, useRef, useState } from "react";

/** Lazy audio: nothing is downloaded until the visitor presses play. */
export function useClip() {
  const audio = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState<string | null>(null);
  const progress = useRef(0);

  const stop = useCallback(() => {
    audio.current?.pause();
    setPlaying(null);
  }, []);

  const play = useCallback((key: string, src: string, onEnd?: () => void) => {
    if (!audio.current) {
      audio.current = new Audio();
      audio.current.preload = "none";
      audio.current.addEventListener("timeupdate", () => {
        const a = audio.current!;
        progress.current = a.duration ? a.currentTime / a.duration : 0;
      });
    }
    const a = audio.current;
    a.onended = () => { setPlaying(null); onEnd?.(); };
    a.src = src;
    a.currentTime = 0;
    progress.current = 0;
    a.play().then(() => setPlaying(key)).catch(() => setPlaying(null));
  }, []);

  useEffect(() => () => audio.current?.pause(), []);
  return { play, stop, playing, progress };
}
