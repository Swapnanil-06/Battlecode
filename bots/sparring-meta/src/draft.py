"""Ladder-meta draft (docs/ladder-meta.md, Candidate A): Cassi & Issac first for the extra body."""
import cambc

D = cambc.ChampionDraft
ORDER = (D.CASSI_AND_ISSAC, D.VENDETTA, D.VARG, D.RYTH, D.TAVI,
         D.STELLAR, D.REN, D.MARCELLA, D.PRISM, D.VESPER_VALE, D.WILLOW)


def play():
    chosen = cambc.draft.current_draft(cambc.Team.ALLY)
    for pick in ORDER:
        if pick not in chosen:
            cambc.draft.pick(pick)
            return
