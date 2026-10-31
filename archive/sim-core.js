"use strict";
// ---------- Core simulation: port of benchmark.py ----------
// Extracted verbatim from index.html (sim core) for reuse by game.html.
// Loaded as a classic <script src> so file:// keeps working; top-level
// declarations stay global for the rest of the page.
const SKILLS = ["knife", "heat", "timing"];
const ACTIONS = [
  { name: "knife_drill",    w: [1.0, 0.0, 0.1], pre: [0, 0, 0] },
  { name: "heat_drill",     w: [0.0, 1.0, 0.2], pre: [0, 0, 0] },
  { name: "timing_drill",   w: [0.1, 0.1, 1.0], pre: [0, 0, 0] },
  { name: "easy_recipe",    w: [0.5, 0.5, 0.5], pre: [0.2, 0.2, 0.2] },
  { name: "stretch_recipe", w: [0.9, 0.9, 0.9], pre: [0.5, 0.45, 0.4] },
];
const clip = (v, a, b) => Math.min(b, Math.max(a, v));
const sum = xs => xs.reduce((p, c) => p + c, 0);
function mulberry32(seed) {
  let t = seed >>> 0;
  return function () {
    t += 0x6D2B79F5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}
function makeGauss(rng) {
  let spare = null;
  return function () {
    if (spare !== null) { const v = spare; spare = null; return v; }
    let u = 0, v = 0;
    while (u === 0) u = rng();
    v = rng();
    const m = Math.sqrt(-2 * Math.log(u)), a = 2 * Math.PI * v;
    spare = m * Math.sin(a);
    return m * Math.cos(a);
  };
}
function gateFn(s, a, k) {
  let sh = 0;
  for (let i = 0; i < 3; i++) sh += Math.max(0, a.pre[i] - s[i]);
  return Math.exp(-k * sh);
}
function makeEnv(seed, o) {
  const rng = mulberry32(seed * 7919 + 13);
  return {
    rng, gauss: makeGauss(rng), s: [0.65, 0.15, 0.35], s0: [0.65, 0.15, 0.35],
    alpha: [0.11, 0.14, 0.12].map(x => x * o.lrScale), prev: [0.65, 0.15, 0.35], t: 0,
  };
}
function envDrift(env, o) { env.s[1] *= 0.65; env.alpha[1] = 0.055 * o.lrScale; }
function envStep(env, a, o) {
  env.t += 1;
  const prev = env.s.slice();
  const g = gateFn(env.s, a, o.gateK);
  for (let k = 0; k < 3; k++)
    env.s[k] = clip(env.s[k] + env.alpha[k] * a.w[k] * g * (1 - env.s[k]), 0, 1);
  const obs = env.s.map(v => clip(v + env.gauss() * o.noise, 0, 1));
  return { obs, score: sum(obs) - sum(prev) };
}
const envGain = env => sum(env.s) - sum(env.s0);

function makeBandit() { return { n: [0,0,0,0,0], q: [0.22,0.22,0.22,0.22,0.22], t: 0 }; }
function banditUCBValues(q, n, t) {
  return ACTIONS.map((_, i) => q[i] + 0.06 * Math.sqrt(Math.log(t + 1) / (n[i] + 1e-9)));
}
function banditSelect(B) {
  B.t += 1;
  const values = banditUCBValues(B.q, B.n, B.t);
  let bi = 0, bs = -Infinity;
  for (let i = 0; i < values.length; i++) {
    if (values[i] > bs) { bs = values[i]; bi = i; }
  }
  return bi;
}
function banditUpdate(B, i, score) { B.n[i] += 1; B.q[i] += (score - B.q[i]) / B.n[i]; }

function makeWorld(o) {
  return { mu: [0.4, 0.4, 0.4], var: [0.05, 0.05, 0.05], ah: [0.12, 0.12, 0.12],
           obsVar: o.noise * o.noise, ema: 0.25, gateHat: 0, gateLr: 1.2 };
}
function worldPredict(W, mu, vr, a) {
  const g = gateFn(mu, a, W.gateHat);
  return { mu: mu.map((m, k) => clip(m + W.ah[k] * a.w[k] * g * (1 - m), 0, 1)),
           var: vr.map(v => v + 0.002) };
}
function worldCandidateScores(W) {
  return ACTIONS.map((a1) => {
    const p1 = worldPredict(W, W.mu, W.var, a1);
    let best2 = -Infinity;
    let best2Action = ACTIONS[0].name;
    for (let j = 0; j < 5; j++) {
      const gain = sum(worldPredict(W, p1.mu, p1.var, ACTIONS[j]).mu) - sum(p1.mu);
      if (gain > best2) { best2 = gain; best2Action = ACTIONS[j].name; }
    }
    const immediate = sum(p1.mu) - sum(W.mu);
    return { action: a1.name, immediate, best2, best2Action, total: immediate + 0.9 * best2 };
  });
}
function worldSelect(W) {
  const scores = worldCandidateScores(W);
  let bi = 0, bs = -Infinity;
  for (let i = 0; i < scores.length; i++) {
    if (scores[i].total > bs) { bs = scores[i].total; bi = i; }
  }
  return bi;
}
function worldPlan(W, horizon) {
  let mu = W.mu.slice(), vr = W.var.slice(); const seq = [];
  for (let h = 0; h < horizon; h++) {
    let bi = 0, bs = -Infinity;
    ACTIONS.forEach((a, i) => {
      const g = sum(worldPredict(W, mu, vr, a).mu) - sum(mu);
      if (g > bs) { bs = g; bi = i; }
    });
    seq.push(ACTIONS[bi].name);
    const p = worldPredict(W, mu, vr, ACTIONS[bi]); mu = p.mu; vr = p.var;
  }
  return seq;
}
function worldUpdate(W, idx, obs) {
  const a = ACTIONS[idx], prevMu = W.mu.slice();
  const pred = worldPredict(W, W.mu, W.var, a);
  const predGain = sum(pred.mu) - sum(prevMu);
  const innov = obs.map((v, k) => v - pred.mu[k]);
  let pvar = pred.var.slice();
  if (innov.some(v => Math.abs(v) > 0.12)) pvar = pvar.map(v => v + 0.03);
  const kg = pvar.map(v => v / (v + W.obsVar));
  W.mu = pred.mu.map((m, k) => clip(m + kg[k] * innov[k], 0, 1));
  W.var = pvar.map((v, k) => (1 - kg[k]) * v);
  const realised = sum(W.mu) - sum(prevMu);
  if (sum(a.pre) > 0 && predGain > 0.03) {
    const miss = clip(1 - realised / Math.max(predGain, 1e-9), 0, 1);
    W.gateHat = clip(W.gateHat + W.gateLr * miss, 0, 8);
  }
  for (let k = 0; k < 3; k++) {
    const den = a.w[k] * gateFn(prevMu, a, W.gateHat) * (1 - prevMu[k]);
    if (den > 0.05) {
      const est = clip((W.mu[k] - prevMu[k]) / den, 0.02, 0.5);
      W.ah[k] = 0.75 * W.ah[k] + 0.25 * est;
    }
  }
}
function oracleNext(prevS, alpha, o, a) {
  return prevS.map((v, k) =>
    clip(v + alpha[k] * a.w[k] * gateFn(prevS, a, o.gateK) * (1 - v), 0, 1));
}
function oracleCandidateScores(prevS, alpha, o) {
  return ACTIONS.map((a1) => {
    const s1 = oracleNext(prevS, alpha, o, a1);
    let best2 = -Infinity;
    let best2Action = ACTIONS[0].name;
    ACTIONS.forEach((a2) => {
      const gain = sum(oracleNext(s1, alpha, o, a2)) - sum(s1);
      if (gain > best2) { best2 = gain; best2Action = a2.name; }
    });
    const immediate = sum(s1) - sum(prevS);
    return { action: a1.name, immediate, best2, best2Action, total: immediate + 0.9 * best2, next: s1 };
  });
}
function oracleSelect(env, o) {
  const scores = oracleCandidateScores(env.s, env.alpha, o);
  let bi = 0, bs = -Infinity;
  scores.forEach((cand, i) => { if (cand.total > bs) { bs = cand.total; bi = i; } });
  return bi;
}
function copyWorld(W) {
  return { mu: W.mu.slice(), var: W.var.slice(), ah: W.ah.slice(),
    obsVar: W.obsVar, ema: W.ema, gateHat: W.gateHat, gateLr: W.gateLr };
}
function envArithmetic(prevS, alpha, action, o, nextS) {
  const g = gateFn(prevS, action, o.gateK);
  return {
    prev: prevS.slice(),
    gate: g,
    increments: prevS.map((v, k) => alpha[k] * action.w[k] * g * (1 - v)),
    next: nextS.slice(),
  };
}
function bestIndexByTotal(scores) {
  let bi = 0, bs = -Infinity;
  scores.forEach((cand, i) => { if (cand.total > bs) { bs = cand.total; bi = i; } });
  return bi;
}
function reconstructWorldUpdate(beforeW, action, obs, afterW) {
  const pred = worldPredict(beforeW, beforeW.mu, beforeW.var, action);
  const predGain = sum(pred.mu) - sum(beforeW.mu);
  const innovation = obs.map((v, k) => v - pred.mu[k]);
  let pvar = pred.var.slice();
  if (innovation.some(v => Math.abs(v) > 0.12)) pvar = pvar.map(v => v + 0.03);
  const kg = pvar.map(v => v / (v + beforeW.obsVar));
  const realized = sum(afterW.mu) - sum(beforeW.mu);
  let miss = null;
  if (sum(action.pre) > 0 && predGain > 0.03) {
    miss = clip(1 - realized / Math.max(predGain, 1e-9), 0, 1);
  }
  const rates = [0, 1, 2].map((k) => {
    const denom = action.w[k] * gateFn(beforeW.mu, action, afterW.gateHat) * (1 - beforeW.mu[k]);
    if (denom <= 0.05) return { denom, est: null, next: afterW.ah[k] };
    const est = clip((afterW.mu[k] - beforeW.mu[k]) / denom, 0.02, 0.5);
    return { denom, est, next: afterW.ah[k] };
  });
  return { pred, predGain, innovation, pvar, kg, realized, miss, rates };
}
function runEpisode(kind, seed, o, sessions = 40, wantDetail = false) {
  const env = makeEnv(seed, o);
  const coach = kind === "A" ? makeBandit() : kind === "B" ? makeWorld(o) : null;
  const gains = [], actions = [], truth = [], belief = [], alphaHeat = [], gateHat = [];
  const steps = [];
  for (let t = 1; t <= sessions; t++) {
    if (o.drift && t === 21) envDrift(env, o);
    const detail = { session: t, kind };
    let idx;
    if (kind === "A") {
      detail.before = { q: coach.q.slice(), n: coach.n.slice(), t: coach.t };
      detail.ucb = banditUCBValues(detail.before.q, detail.before.n, detail.before.t + 1);
      idx = bestIndexByTotal(detail.ucb.map((total, i) => ({ total, action: ACTIONS[i].name })));
    } else if (kind === "B") {
      detail.beforeW = copyWorld(coach);
      detail.candidates = worldCandidateScores(detail.beforeW);
      idx = bestIndexByTotal(detail.candidates);
    } else {
      detail.prevS = env.s.slice();
      detail.prevAlpha = env.alpha.slice();
      detail.candidates = oracleCandidateScores(detail.prevS, detail.prevAlpha, o);
      idx = bestIndexByTotal(detail.candidates);
    }
    detail.idx = idx;
    detail.action = ACTIONS[idx].name;
    detail.envPrev = env.s.slice();
    detail.alphaPrev = env.alpha.slice();
    const { obs, score } = envStep(env, ACTIONS[idx], o);
    if (kind === "A") {
      banditUpdate(coach, idx, score);
      detail.after = { q: coach.q.slice(), n: coach.n.slice(), t: coach.t };
    }
    if (kind === "B") {
      worldUpdate(coach, idx, obs);
      detail.afterW = copyWorld(coach);
      detail.update = reconstructWorldUpdate(detail.beforeW, ACTIONS[idx], obs, detail.afterW);
    }
    detail.env = envArithmetic(detail.envPrev, detail.alphaPrev, ACTIONS[idx], o, env.s);
    detail.obs = obs.slice();
    detail.score = score;
    gains.push(envGain(env)); actions.push(ACTIONS[idx].name);
    truth.push(env.s.slice());
    if (kind === "B") { belief.push(coach.mu.slice()); alphaHeat.push(coach.ah[1]); gateHat.push(coach.gateHat); }
    if (wantDetail) steps.push(detail);
  }
  return { gains, actions, truth, belief, alphaHeat, gateHat, steps };
}
function aggregate(o, sessions = 40, nSeeds = 40) {
  const acc = { A: [], B: [], O: [] };
  for (const kind of ["A", "B", "O"]) {
    const rows = [];
    for (let s = 0; s < nSeeds; s++) rows.push(runEpisode(kind, s, o, sessions).gains);
    acc[kind] = Array.from({ length: sessions }, (_, t) => sum(rows.map(r => r[t])) / nSeeds);
    acc[kind + "Rows"] = rows;
  }
  return acc;
}
// ---------- Execution vector (render-side only; never touches dynamics) ----------
// q = observed plate quality o_t; action = chosen action; gate = true gate;
// gain = this session's true cumulative-gain delta; rng = uniform [0,1) source.
function execVector(q, actionName, gate, gain, rng) {
  const j = () => (rng() - 0.5) * 0.06;
  return {
    cut_spread: 0.05 + 0.55 * (1 - q[0]) + j(),
    pan_temp_c: 180 + 140 * (1 - q[1]) + (rng() - 0.5) * 8,
    late_s: 45 * (1 - q[2]) + (rng() - 0.5) * 4,
    ready: gate >= 0.5,
    learned: Math.max(0, gain),
    action: actionName,
  };
}
// One call the 3D page uses per (seed, opts): full A + B traces with detail.
function trace(seed, o, sessions = 40) {
  return {
    A: runEpisode("A", seed, o, sessions, true),
    B: runEpisode("B", seed, o, sessions, true),
  };
}
globalThis.SimCore = {
  SKILLS, ACTIONS, clip, sum, mulberry32, makeGauss, gateFn,
  makeEnv, envDrift, envStep, envGain,
  makeBandit, banditUCBValues, banditSelect, banditUpdate,
  makeWorld, worldPredict, worldCandidateScores, worldSelect, worldPlan, worldUpdate,
  oracleNext, oracleCandidateScores, oracleSelect,
  copyWorld, envArithmetic, bestIndexByTotal, reconstructWorldUpdate,
  runEpisode, aggregate, execVector, trace,
};
if (typeof module !== "undefined" && module.exports) module.exports = globalThis.SimCore;
