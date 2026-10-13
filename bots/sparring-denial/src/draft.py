"""Fixed, deterministic combat draft (ChampionDraft IDs)."""
import cambc

D = cambc.ChampionDraft
# Denial: splash bruiser + ranged stun invade; stun-immune banker holds the economy.
ORDER = (D.VARG, D.TAVI, D.MARCELLA, D.VENDETTA, D.RYTH,
         D.STELLAR, D.REN, D.CASSI_AND_ISSAC, D.PRISM, D.VESPER_VALE, D.WILLOW)


def play():
    chosen = cambc.draft.current_draft(cambc.Team.ALLY)
    for pick in ORDER:
        if pick not in chosen:
            cambc.draft.pick(pick)
            return
