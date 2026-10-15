# Experimental map-aware draft

`bots/topteam` is an uploadable alternative to `bots/main`. It keeps the
incumbent gameplay policy and changes only the draft. The original team
remains available as the fallback on every unrecognised map profile.

The draft identifies three published map profiles from dimensions and camp
group counts, all visible through the official draft API:

| Profile | Roster |
| --- | --- |
| Corners, packs | Varg, Cassi & Issac, Stellar, Ryth, Ren |
| Lanes | Vendetta, Cassi & Issac, Varg, Ryth, Tavi |
| All other profiles | Vendetta, Tavi, Marcella, Varg, Ryth |

On 15 October 2026, the first candidate combined the leader-observed roster
with route ownership, a changed camp scoring formula, and earlier banking. It
lost **0/12** against `bots/main` over elkring, expanse, collision, corners,
packs and lanes, each side. Controlled follow-ups kept the incumbent gameplay:
the leader-observed roster won **6/12**, a hybrid six-body roster **5/12**,
and a banking-only gameplay change **5/12**. Those results rejected the first
implementation and the banking change.

The final selected draft won **8/12** against `bots/main` on the same six-map,
two-side panel. The choice of map profiles used the prior tests on these same
maps, so **8/12 is an in-sample result**, not an unbiased estimate of its win
rate or proof it will beat top ladder teams. Match seed variation was visible
between repeat panels; the two-map sweeps are too small to guarantee a gain.
The bot built successfully against CAMBC 2.1.6 and all 12 final matches
completed with no logged bot exceptions or fuel suspensions. No ladder match
or submission was performed.

The source ZIP can be produced from the repository root with
`cambc bundle bots/topteam --output topteam.zip`. Use `bots/main` as the
conservative choice until a larger independent panel or ladder trial confirms
the draft change. The original design and platform checks are in
`top-team-strategy.md` and `strategy-validation.md`.
