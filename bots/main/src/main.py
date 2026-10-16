"""Dispatch draft and gameplay; a failed turn is logged and still yields."""
import cambc
import draft

# Fuel a normal Python turn starts with (2.5M less interpreter overhead).
FIRST_TURN_PLAY = 2_400_000


def main():
    bot = None
    while True:
        try:
            if cambc.is_draft():
                draft.play()
            else:
                # Loading the larger strategy during draft can exhaust the pick budget.
                # Draft and play run in separate processes, so draft-turn precompute
                # cannot reach here (beyond draft memory); the 2x first play turn is
                # where static caches are built.
                first = bot is None
                if first:
                    from bot import Bot
                    from planner.ledger import LEDGER
                    bot = Bot()
                    bot.warm(FIRST_TURN_PLAY)
                # The first turn also plays when a normal turn's worth of fuel remains.
                if not first or cambc.fuel_remaining() >= FIRST_TURN_PLAY:
                    started = cambc.round_number()
                    bot.play_turn()
                    bot.min_fuel = min(bot.min_fuel, cambc.fuel_remaining())
                    bot.suspended += cambc.round_number() != started
                    if started % 100 == 0:
                        print(f"v5d id={int(cambc.me())} plans={bot.plan_count} min_fuel={bot.min_fuel} "
                              f"suspensions={bot.suspended} aborts={LEDGER.aborts} cuts={bot.cuts}", flush=True)
        except Exception as error:
            trace = error.__traceback__
            frames = []
            while trace is not None:
                frames.append(f"{trace.tb_frame.f_code.co_filename}:{trace.tb_lineno}")
                trace = trace.tb_next
            print(f"bot error: {error} at {' > '.join(frames)}", flush=True)

        cambc.end_turn()


if __name__ == "__main__":
    main()
