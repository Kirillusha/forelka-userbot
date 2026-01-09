import os
from inline_core import gen_bot_username


def main():
    prefix = os.environ.get("FORELKA_BOT_PREFIX", "forelka_")
    n = int(os.environ.get("FORELKA_BOT_RAND", "5"))
    suffix = os.environ.get("FORELKA_BOT_SUFFIX", "_bot")
    print("@" + gen_bot_username(prefix=prefix, n=n, suffix=suffix))


if __name__ == "__main__":
    main()
