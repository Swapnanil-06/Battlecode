"""SDK-free starting point for objective allocation; not enabled in main yet.

Inputs must come from each champion's legal observations and a versioned draft
plan. Scores are hypotheses to calibrate with paired replays, not win chances.
Keep at most 8 jobs and 6 bodies; snapshot SDK data before calling this module.
"""


def objective_rate(gems, denied, bag, survival, seconds, recovery=0,
                   gold=0, gold_value=0.0):
    """Expected gem swing / rounds, accounting for loss of the current bag.

    `seconds` is rounds through completed tribute, including travel, clear,
    capture and channel resolution. `survival` includes successful delivery.
    `denied` must be incremental prevented ENEMY score, not kill reward or gems
    already counted in `gems`. Recovery is full death/recall downtime on failure.
    Gold has zero default value until a measured conversion value is supplied.
    """
    if not 0 <= survival <= 1 or seconds < 1 or recovery < 0:
        raise ValueError('invalid probability or duration')
    if min(gems, denied, bag, gold, gold_value) < 0:
        raise ValueError('negative reward')
    swing = survival * (gems + denied + gold * gold_value)
    swing -= (1 - survival) * bag
    return swing / (seconds + (1 - survival) * recovery)


def assign_jobs(offers, fixed=()):
    """Greedy, deterministic exclusive jobs for idle bodies.

    offers: (body_id, job_id, marginal_rate), already including route/risk cost.
    fixed: (body_id, job_id) for existing capture/tribute commitments. A job is
    exclusive; use one composite squad job for a contested camp requiring two
    bodies and let the caller reserve both. Do not give a shared job two IDs.

    Greedy matching is deliberately small, not a globally optimal solver.
    Returning no job is safer than taking a negative marginal-rate job.
    """
    result = dict(fixed)
    if len(result) != len(fixed) or len(set(result.values())) != len(result):
        raise ValueError('conflicting fixed commitments')
    busy = set(result.values())
    for body, job, rate in sorted(offers, key=lambda x: (-x[2], x[0], x[1])):
        if rate > 0 and body not in result and job not in busy:
            result[body] = job
            busy.add(job)
    return result


def bank_now(bag, bank_rounds, bank_survival, next_gems, cycle_rounds,
             cycle_survival, recovery=60):
    """Compare banking now with ONE more complete camp-to-tribute cycle.

    cycle_rounds includes delivery of both bags. Probabilities are conservative
    estimates; unknown enemy positions do not imply safety. Apply lethal-risk,
    winning-bag and match-horizon overrides before this economic comparison.
    """
    if bag <= 0:
        return False
    now = objective_rate(bag, 0, bag, bank_survival, bank_rounds, recovery)
    later = objective_rate(bag + next_gems, 0, bag, cycle_survival,
                           cycle_rounds, recovery)
    return now >= later
