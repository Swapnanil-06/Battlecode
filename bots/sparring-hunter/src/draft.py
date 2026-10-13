"""Fixed, deterministic combat draft (ChampionDraft IDs)."""
import cambc

D = cambc.ChampionDraft
# Hunter: ranged stun + dash finisher first, then the stun-immune banker.
ORDER = (D.TAVI, D.VENDETTA, D.MARCELLA, D.VARG, D.RYTH,
         D.STELLAR, D.REN, D.CASSI_AND_ISSAC, D.PRISM, D.VESPER_VALE, D.WILLOW)


def play():
    chosen = cambc.draft.current_draft(cambc.Team.ALLY)
    for pick in ORDER:
        if pick not in chosen:
            cambc.draft.pick(pick)
            return
