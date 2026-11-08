// Word alignment between two transcripts (LCS), so a transcript can change word by word in reading order.
export type Op = { from: string | null; to: string | null };

export function alignWords(a: string, b: string): Op[] {
  const A = a.split(/\s+/).filter(Boolean);
  const B = b.split(/\s+/).filter(Boolean);
  const n = A.length, m = B.length;
  const L = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      L[i][j] = A[i] === B[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  const ops: Op[] = [];
  let i = 0, j = 0;
  while (i < n || j < m) {
    if (i < n && j < m && A[i] === B[j]) { ops.push({ from: A[i], to: B[j] }); i++; j++; }
    else if (i < n && j < m && L[i + 1][j] === L[i][j + 1]) { ops.push({ from: A[i], to: B[j] }); i++; j++; } // substitution
    else if (j < m && (i >= n || L[i][j + 1] >= L[i + 1][j])) { ops.push({ from: null, to: B[j] }); j++; }
    else { ops.push({ from: A[i], to: null }); i++; }
  }
  return ops;
}

/** Show `a` turning into `b`: the first round(t * changes) changed words have switched. */
export function morph(ops: Op[], t: number): { word: string; changed: boolean }[] {
  const changedIdx = ops.map((o, i) => (o.from !== o.to ? i : -1)).filter((i) => i >= 0);
  const k = Math.round(t * changedIdx.length);
  const switched = new Set(changedIdx.slice(0, k));
  const out: { word: string; changed: boolean }[] = [];
  ops.forEach((o, i) => {
    const w = switched.has(i) ? o.to : o.from;
    if (w) out.push({ word: w, changed: switched.has(i) && o.from !== o.to });
  });
  return out;
}
