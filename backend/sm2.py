from datetime import datetime, timedelta, timezone
from models import Card

# SM-2 algorithm ratings: 0=Again, 1=Hard, 2=Good, 3=Easy
# Maps to q values: Again=1, Hard=2, Good=4, Easy=5
RATING_TO_Q = {0: 1, 1: 2, 2: 4, 3: 5}


def apply_sm2(card: Card, rating: int) -> Card:
    """
    Update card SM-2 fields based on a 0-3 rating (Again/Hard/Good/Easy).
    Mutates and returns the card; caller must commit to DB.
    """
    q = RATING_TO_Q[rating]
    ef = card.easiness
    reps = card.repetitions

    if q >= 3:  # correct response
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = round(card.interval * ef)
        reps += 1
    else:  # incorrect — reset
        reps = 0
        interval = 1

    # Update ease factor (clamped to minimum 1.3)
    ef = ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    ef = max(1.3, ef)

    card.easiness = ef
    card.interval = interval
    card.repetitions = reps
    card.last_reviewed = datetime.now(timezone.utc)
    card.due_date = datetime.now(timezone.utc) + timedelta(days=interval)

    return card
