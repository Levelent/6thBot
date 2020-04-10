from datetime import timedelta
from typing import Union


def highest_denom(time: Union[timedelta, int]):
    """Converts to highest time denomination, rounded down.
    :param time: Either a timedelta or the total number of seconds.
    :return: the value of the highest time denomination, rounded down.
    :rtype: str
    """
    multipliers = [60, 60, 24, 7, 52]
    denominations = ["seconds", "minutes", "hours", "days", "weeks", "years"]

    if isinstance(time, timedelta):
        seconds = time.total_seconds()
    else:  # is an integer
        seconds = time

    mp = 1
    for num in range(6):
        diff = seconds // mp
        if num < 5 and diff >= multipliers[num]:
            mp *= multipliers[num]
        else:
            diff_round = int(abs(diff))
            if diff_round == 1:
                denominations[num] = denominations[num][:-1]
            return f"{diff_round} {denominations[num]}"
