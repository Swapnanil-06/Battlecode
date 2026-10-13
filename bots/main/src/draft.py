import cambc
from randomness import below


def play():
    # Choose randomly from the champions our team has not picked.
    chosen = cambc.draft.current_draft(cambc.Team.ALLY)
    # These are ChampionDraft IDs, not ChampionType IDs (Cassi/Issac share a pick).
    available = [pick for pick in range(11) if pick not in chosen]

    cambc.draft.pick(available[below(len(available))])
