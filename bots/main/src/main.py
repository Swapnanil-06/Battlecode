"""Dispatch draft and gameplay; a failed turn is logged and still yields."""
import cambc
import draft


def main():
    bot = None
    while True:
        try:
            if cambc.is_draft():
                draft.play()
            else:
                # Loading the larger strategy during draft can exhaust the pick budget.
                if bot is None:
                    from bot import Bot
                    from planner.ledger import LEDGER
                    bot = Bot()
                    # Import may span fuel quanta. Start decisions with a fresh turn.
                else:
                    started = cambc.round_number()
                    bot.play_turn()
                    bot.min_fuel = min(bot.min_fuel, cambc.fuel_remaining())
                    bot.suspended += cambc.round_number() != started
                    if started % 100 == 0:
                        print(f"v5a id={int(cambc.me())} plans={bot.plan_count} min_fuel={bot.min_fuel} "
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
