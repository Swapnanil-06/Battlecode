"""The fuel ledger: the single owner of turn-budget decisions (docs/planner-spec.md §2).

Exhausting fuel suspends the turn mid-action and resumes next round on stale state, so
every expensive step asks the ledger first. A step may start only if, after its worst
measured cost, RESERVE_ACTION still remains for the actions and the yield behind it.
A refusal is an abort: the caller falls back to its cheapest safe action (usually
nothing) and the turn yields with fuel to spare.
"""
import cambc

RESERVE_ACTION = 250_000
# Optional depth (longer route scans, ward siting) stops here so ordinary turns end with
# room to spare; only mandatory steps may dig down to RESERVE_ACTION.
SOFT_FLOOR = 500_000

# Worst observed costs (fuel) of guarded steps, measured in local gate matches with
# headroom. They are area-scaled; recheck if maps grow or the SDK version changes.
COST_MOVE = 250_000      # move_towards_closest: field to goals, dash check, one step
COST_ATTACK = 60_000     # attack_if_in_range: checks, attack, attack reset
COST_SCAN = 400_000      # farm_camps tail after the route scan: attacks and one move
COST_CANDIDATE = 150_000  # scoring one more route candidate
COST_SETUP = 400_000     # farm_camps route setup: allies, bounded field, candidate sort
COST_FIELD = 300_000     # one full-map DistanceField (80x80 maps)
COST_BANK = 350_000      # bank: altar field and scoring, before its move
COST_RETREAT = 350_000   # retreat setup: sightings, camp threats, recall or casts
COST_DASH = 300_000      # retreat dash: landing scan and camp-pressure ties
COST_WALK = 500_000      # retreat walk: step scoring and the defending attack
COST_WARD = 650_000      # place_ward: candidate scoring is optional work


class Ledger:
    def __init__(self):
        self.aborts = 0  # guarded steps refused for lack of fuel

    def afford(self, cost):
        """True when a step costing up to `cost` still leaves RESERVE_ACTION; else abort."""
        if cambc.fuel_remaining() >= RESERVE_ACTION + cost:
            return True
        self.aborts += 1
        return False


    def optional(self, cost):
        """True when optional work costing up to `cost` still leaves SOFT_FLOOR."""
        return cambc.fuel_remaining() >= SOFT_FLOOR + cost


LEDGER = Ledger()
