"""Fixed, deterministic combat draft (ChampionDraft IDs)."""
import cambc

D = cambc.ChampionDraft
# Altar: stun-immune banker, then the two range-4 stunners that camp altars.
ORDER = (D.MARCELLA, D.TAVI, D.RYTH, D.VARG, D.VENDETTA,
         D.STELLAR, D.REN, D.CASSI_AND_ISSAC, D.PRISM, D.VESPER_VALE, D.WILLOW)


def play():
    chosen = cambc.draft.current_draft(cambc.Team.ALLY)
    for pick in ORDER:
        if pick not in chosen:
            cambc.draft.pick(pick)
            return
