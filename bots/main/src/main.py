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
                    bot = Bot()
                    # Import may span fuel quanta. Start decisions with a fresh turn.
                else:
                    bot.play_turn()
        except Exception as error:
            print(f"bot error: {error}", flush=True)

        cambc.end_turn()


if __name__ == "__main__":
    main()
