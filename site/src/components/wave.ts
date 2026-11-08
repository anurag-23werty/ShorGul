/** Mirrored waveform path from peak amplitudes (0..1). Pure function, so scenes can update `d` per frame. */
export function wavePath(peaks: number[], w: number, h: number, gain = 1): string {
  const n = peaks.length;
  const mid = h / 2;
  const top: string[] = [];
  const bot: string[] = [];
  for (let i = 0; i < n; i++) {
    const x = (i / (n - 1)) * w;
    const a = Math.min(1, peaks[i] * gain) * (mid - 1);
    top.push(`${x.toFixed(1)},${(mid - a).toFixed(1)}`);
    bot.push(`${x.toFixed(1)},${(mid + a).toFixed(1)}`);
  }
  return `M${top.join("L")}L${bot.reverse().join("L")}Z`;
}

export function lerpArr(a: number[], b: number[], t: number): number[] {
  return a.map((v, i) => v + (b[i] - v) * t);
}
