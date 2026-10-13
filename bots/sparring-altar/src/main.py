"""Dispatch draft and gameplay; a failed turn is logged and still yields."""
import cambc
import draft

TAG = "altar"


def main():
    bot = None
    while True:
        try:
            if cambc.is_draft():
                draft.play()
            else:
                # Loading the larger strategy during draft can exhaust the pick budget.
                if bot is None:
                    from policy import SparringBot
                    bot = SparringBot()
                else:
                    bot.play_turn()
                    import kit
                    kit.end_turn_bookkeeping()
                    now = cambc.round_number()
                    if now % 100 == 0 or now == cambc.constants.MAX_ROUNDS - 1:
                        print(kit.summary(TAG), flush=True)
        except Exception as error:
            frames = []
            trace = error.__traceback__
            while trace is not None:
                frames.append(f"{trace.tb_frame.f_code.co_filename.rsplit('/', 1)[-1]}:{trace.tb_lineno}")
                trace = trace.tb_next
            print(f"bot error: {type(error).__name__}: {error} at {' > '.join(frames)}"
                  f" (round {cambc.round_number()}, fuel {cambc.fuel_remaining()})", flush=True)

        cambc.end_turn()


if __name__ == "__main__":
    main()
