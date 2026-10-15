// Dump per-round state from a .repl26a match record using the visualiser's own engine.
// Usage: node runner/replay_dump.mjs <replay.repl26a | bundle.repl26a> [--every N]
// Prints one JSON object: draft, per-round submitted/carried gems, deaths and kills.
// The engine WASM is the one `cambc view` caches; it is never copied into the repo.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { execFileSync } from 'node:child_process';

const SNAPSHOT = 184696;
const CHAMPS = { countOffset: 120, dataOffset: 140, stride: 456 };
const CAMPS = { countOffset: 124, dataOffset: 7436, stride: 232 };

function findWasm() {
  const root = path.join(os.homedir(), '.cache/cambc/assets');
  for (const sha of fs.readdirSync(root)) {
    const dir = path.join(root, sha, 'visualiser/assets');
    if (!fs.existsSync(dir)) continue;
    const f = fs.readdirSync(dir).find((n) => /^v0_0_1-.*\.wasm$/.test(n));
    if (f) return path.join(dir, f);
  }
  throw new Error('visualiser wasm not cached; run `cambc view` once');
}

function readReplayBytes(file) {
  const buf = fs.readFileSync(file);
  if (buf[0] === 0x50 && buf[1] === 0x4b) {  // outer ZIP bundle
    return execFileSync('unzip', ['-p', file, 'replay.repl26a'], { maxBuffer: 1 << 30 });
  }
  return buf;
}

async function main() {
  const file = process.argv[2];
  const every = Number(process.argv[process.argv.indexOf('--every') + 1]) || 1;
  let mem;
  const wasi = {
    random_get: () => 0, clock_time_get: (_a, _b, p) => { new DataView(mem.buffer).setBigUint64(p, 0n, true); return 0; },
    environ_sizes_get: (a, b) => { const d = new DataView(mem.buffer); d.setUint32(a, 0, true); d.setUint32(b, 0, true); return 0; },
    environ_get: () => 0, args_sizes_get: (a, b) => { const d = new DataView(mem.buffer); d.setUint32(a, 0, true); d.setUint32(b, 0, true); return 0; },
    args_get: () => 0, fd_close: () => 0, fd_fdstat_get: () => 0, fd_prestat_get: () => 8, fd_prestat_dir_name: () => 8,
    fd_read: () => 8, fd_seek: () => 70, proc_exit: (c) => { throw new Error('exit ' + c); },
    fd_write: (_fd, iov, n, out) => { const d = new DataView(mem.buffer); let t = 0; for (let i = 0; i < n; i++) t += d.getUint32(iov + i * 8 + 4, true); d.setUint32(out, t, true); return 0; },
  };
  const { instance } = await WebAssembly.instantiate(fs.readFileSync(findWasm()), {
    wasi_snapshot_preview1: wasi, deep_wasm: { on_assert_fail_impl: () => 1 },
  });
  const x = instance.exports;
  mem = x.memory;
  x._initialize();
  const outBuf = x.Engine_Malloc(32);
  const check = (code) => { if (code !== 0) throw new Error('engine error ' + code); };
  const bytes = readReplayBytes(file);
  const p = x.Engine_Malloc(bytes.length);
  new Uint8Array(mem.buffer, p, bytes.length).set(bytes);
  check(x.Game_FromReplayFileBytes(p, bytes.length, outBuf));
  const dv = () => new DataView(mem.buffer);
  const game = dv().getBigUint64(outBuf, true);
  const snap = x.Engine_Malloc(SNAPSHOT);
  const args = x.Engine_Malloc(128);
  check(x.Game_Runner_SetCheckpointsEnabled(game, 1));
  check(x.Game_Visualiser_Timeline_GetMain(game, outBuf));
  const timeline = dv().getBigUint64(outBuf, true);
  check(x.Game_Visualiser_Timeline_Info(game, timeline, args, args + 8, args + 16));
  const size = dv().getUint32(args, true);
  const persp = args + 48;

  function read() {
    const d = dv();
    d.setUint32(persp, 2, true); d.setUint32(persp + 4, 0xffffffff, true);  // spectator
    check(x.Game_Visualiser_ReadState(game, persp, snap));
    const d2 = dv();
    const u = (o) => d2.getUint32(snap + o, true);
    const n = u(CHAMPS.countOffset);
    const champs = [];
    for (let i = 0; i < n; i++) {
      const b = snap + CHAMPS.dataOffset + i * CHAMPS.stride;
      const g = (o) => d2.getUint32(b + o, true);
      const gi = (o) => d2.getInt32(b + o, true);
      const idx = g(4);
      champs.push({
        index: idx, team: g(8), type: g(12), x: gi(20), y: gi(24), health: d2.getFloat32(b + 28, true),
        alive: !!g(224), gems: g(236), gold: g(232),
        earned: d2.getUint32(snap + 184248 + idx * 16, true),
        kda: [0, 1, 2].map((k) => d2.getUint32(snap + 184504 + idx * 12 + k * 4, true)),
        channel: g(440), channelTimer: gi(436),
      });
    }
    return {
      round: u(8), phase: u(24), outcome: u(28), awaiting: u(20), inputPos: u(56), substep: u(104),
      submitted: [Number(d2.getBigUint64(snap + 32, true)), Number(d2.getBigUint64(snap + 40, true))],
      stepKind: u(68), actorKind: u(72), actor: u(76), champs,
      drafts: [0, 1].map((t) => [0, 1, 2, 3, 4].map((k) => d2.getInt32(snap + 179516 + 12 + t * 20 + k * 4, true))),
    };
  }

  check(x.Game_Visualiser_Timeline_Seek(game, timeline, 0, 0));
  const rounds = [];
  let last = read();
  let lastRound = -1;
  const events = { deaths: [0, 0], carrierDeaths: [0, 0], gemsLostOnDeath: [0, 0], submissions: [[], []] };
  const profile = process.argv.includes('--profile');
  const profileKind = 1;  // actor kind of champions in step records
  const turnKinds = new Map(), roundState = new Map();
  let profRound = -1;
  let prevAlive = new Map(), prevGems = new Map(), prevChannel = new Map();
  for (let pos = 1; !last.outcome && !(last.awaiting && last.inputPos >= size); pos++) {
    // The main timeline extends as it is replayed; stop when stepping no longer works.
    const code = x.Game_Visualiser_Timeline_ReplayNext(game, 1);
    if (code !== 0) throw new Error(`replay step failed with engine error ${code} in round ${last.round}`);
    const s = read();
    if (s.inputPos === last.inputPos && s.substep === last.substep) throw new Error('timeline made no progress');
    if (profile && s.actorKind === profileKind) {
      const key = s.round + ':' + s.actor;
      if (!turnKinds.has(key)) turnKinds.set(key, new Set());
      turnKinds.get(key).add(s.stepKind);
    }
    if (profile && s.round !== profRound) {
      profRound = s.round;
      for (const c of s.champs) roundState.set(s.round + ':' + c.index, [c.alive, c.channel, c.gems, c.team]);
    }
    for (const c of s.champs) {
      const wasAlive = prevAlive.get(c.index);
      if (wasAlive && !c.alive) {
        events.deaths[c.team]++;
        const g = prevGems.get(c.index) || 0;
        if (g > 0) { events.carrierDeaths[c.team]++; events.gemsLostOnDeath[c.team] += g; }
      }
      prevAlive.set(c.index, c.alive); prevGems.set(c.index, c.gems);
    }
    if (s.submitted[0] !== last.submitted[0] || s.submitted[1] !== last.submitted[1]) {
      for (const t of [0, 1]) if (s.submitted[t] > last.submitted[t]) events.submissions[t].push([s.round, s.submitted[t] - last.submitted[t]]);
    }
    if (s.round !== lastRound && s.round % every === 0) {
      rounds.push({ r: s.round, sub: s.submitted, carried: [0, 1].map((t) => s.champs.filter((c) => c.team === t).reduce((a, c) => a + c.gems, 0)),
        earned: [0, 1].map((t) => s.champs.filter((c) => c.team === t).reduce((a, c) => a + c.earned, 0)) });
      if (process.argv.includes('--locks')) {
        const locks = [];
        for (let lx = 0; lx < 100; lx++) for (let ly = 0; ly < 100; ly++) for (const t of [0, 1]) {
          const d = dv(); d.setUint32(persp, 2, true); d.setUint32(persp + 4, 0xffffffff, true);
          if (x.Game_API_GetAltarLock(game, persp, lx, ly, t, args) === 0) locks.push([lx, ly, dv().getUint32(args + 8, true), dv().getUint32(args + 20, true)]);
        }
        rounds.at(-1).locks = locks;
      }
      if (process.argv.includes('--camps') && s.round === 1 || process.argv.includes('--camps-all')) {
        const d2 = dv(); const n = d2.getUint32(snap + CAMPS.countOffset, true); const camps = [];
        for (let i = 0; i < n; i++) { const b = snap + CAMPS.dataOffset + i * CAMPS.stride; camps.push([d2.getUint32(b + 12, true), d2.getInt32(b + 20, true), d2.getInt32(b + 24, true), Math.round(d2.getFloat32(b + 28, true)), d2.getUint32(b + 224, true)]); }
        rounds.at(-1).camps = camps;
      }
      if (process.argv.includes('--champs')) rounds.at(-1).champs = s.champs.map((c) => [c.index, c.team, c.type, c.x, c.y, Math.round(c.health), c.alive ? 1 : 0, c.gems, c.gold, c.channel, c.channelTimer]);
      lastRound = s.round;
    }
    last = s;
  }
  const final = last;
  let prof;
  if (profile) {
    prof = {};
    for (const [key, [alive, channel, gems, team]] of roundState) {
      const [round, index] = key.split(':');
      const kinds = turnKinds.get(round + ':' + index) || new Set();
      const cls = !alive ? 'dead' : kinds.has(12) ? 'tribute' : kinds.has(11) ? 'recall' : channel ? 'channel'
        : kinds.has(5) ? (gems ? 'attack_carrying' : 'attack') : kinds.has(4) ? (gems ? 'move_carrying' : 'move') : (gems ? 'idle_carrying' : 'idle');
      const p = prof[index] ??= { team, turns: 0 };
      p.turns++; p[cls] = (p[cls] || 0) + 1;
    }
  }
  console.log(JSON.stringify({
    steps: size, finalRound: final.round, outcome: final.outcome, submitted: final.submitted, drafts: final.drafts,
    champs: final.champs.map((c) => ({ index: c.index, team: c.team, type: c.type, kda: c.kda, earned: c.earned })),
    events, rounds, prof,
  }));
}

main().catch((e) => { console.error(e.stack || String(e)); process.exit(1); });
