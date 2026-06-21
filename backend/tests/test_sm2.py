"""
Unit tests for the SM-2 spaced repetition math.

These exist because SM-2 is deceptively subtle: the slow drift of the easiness
factor (EF) over many reviews is what makes scheduling feel "intelligent," and a
small sign/coefficient error is silent — the app still works, it just schedules
badly forever. We verify EF drift, interval progression, and reset-on-failure
independently of the UI and DB.
"""
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from sm2 import apply_sm2, RATING_TO_Q  # noqa: E402

# Rating constants (mirror the UI): 0=Again, 1=Hard, 2=Good, 3=Easy
AGAIN, HARD, GOOD, EASY = 0, 1, 2, 3


def make_card(easiness=2.5, interval=1, repetitions=0):
    """A minimal stand-in for the SQLAlchemy Card model (no DB needed)."""
    return SimpleNamespace(
        easiness=easiness,
        interval=interval,
        repetitions=repetitions,
        due_date=None,
        last_reviewed=None,
    )


# --- Interval progression on repeated correct answers ----------------------

def test_first_correct_sets_interval_1():
    card = make_card()
    apply_sm2(card, GOOD)
    assert card.interval == 1
    assert card.repetitions == 1


def test_second_correct_sets_interval_6():
    card = make_card()
    apply_sm2(card, GOOD)  # rep 1 -> interval 1
    apply_sm2(card, GOOD)  # rep 2 -> interval 6
    assert card.interval == 6
    assert card.repetitions == 2


def test_third_correct_uses_ef_multiplier():
    card = make_card()
    apply_sm2(card, GOOD)  # interval 1
    apply_sm2(card, GOOD)  # interval 6
    ef_before = card.easiness
    apply_sm2(card, GOOD)  # interval = round(6 * EF)
    assert card.interval == round(6 * ef_before)
    assert card.repetitions == 3


def test_intervals_grow_monotonically_with_good():
    card = make_card()
    prev = 0
    for _ in range(8):
        apply_sm2(card, GOOD)
        assert card.interval >= prev
        prev = card.interval
    assert card.interval > 6  # has compounded beyond the seed intervals


# --- Easiness factor drift -------------------------------------------------

def test_good_keeps_ef_stable():
    # q=4 (Good): delta = 0.1 - 1*(0.08 + 1*0.02) = 0.1 - 0.1 = 0.0
    card = make_card(easiness=2.5)
    apply_sm2(card, GOOD)
    assert card.easiness == pytest.approx(2.5)


def test_easy_increases_ef():
    # q=5 (Easy): delta = 0.1 - 0 = +0.1
    card = make_card(easiness=2.5)
    apply_sm2(card, EASY)
    assert card.easiness == pytest.approx(2.6)


def test_hard_decreases_ef():
    # q=2 (Hard): delta = 0.1 - 3*(0.08 + 3*0.02) = 0.1 - 3*0.14 = -0.32
    card = make_card(easiness=2.5)
    apply_sm2(card, HARD)
    assert card.easiness == pytest.approx(2.18)


def test_again_decreases_ef():
    # q=1 (Again): delta = 0.1 - 4*(0.08 + 4*0.02) = 0.1 - 4*0.16 = -0.54
    card = make_card(easiness=2.5)
    apply_sm2(card, AGAIN)
    assert card.easiness == pytest.approx(1.96)


def test_ef_clamped_at_minimum_1_3():
    # Repeated failures must never drag EF below 1.3
    card = make_card(easiness=1.3)
    for _ in range(10):
        apply_sm2(card, AGAIN)
        assert card.easiness >= 1.3
    assert card.easiness == pytest.approx(1.3)


def test_ef_drift_over_mixed_session():
    # A realistic mix should leave EF meaningfully below the 2.5 start.
    card = make_card(easiness=2.5)
    for rating in [GOOD, HARD, GOOD, AGAIN, GOOD, HARD]:
        apply_sm2(card, rating)
    assert card.easiness < 2.5
    assert card.easiness >= 1.3


# --- Reset on failure ------------------------------------------------------

def test_again_resets_repetitions_and_interval():
    card = make_card()
    apply_sm2(card, GOOD)
    apply_sm2(card, GOOD)
    apply_sm2(card, GOOD)  # built-up interval & reps
    assert card.repetitions == 3
    apply_sm2(card, AGAIN)
    assert card.repetitions == 0
    assert card.interval == 1


def test_failure_resets_interval_but_ef_persists():
    # EF is the "long memory" — it should keep its accumulated drift across a lapse.
    card = make_card()
    apply_sm2(card, GOOD)
    apply_sm2(card, GOOD)
    apply_sm2(card, EASY)  # bump EF up
    ef_after_easy = card.easiness
    apply_sm2(card, AGAIN)  # lapse resets interval/reps...
    assert card.interval == 1
    assert card.repetitions == 0
    # ...but EF only takes the q=1 penalty from its current value, not a full reset.
    expected = max(1.3, ef_after_easy + (0.1 - 4 * (0.08 + 4 * 0.02)))
    assert card.easiness == pytest.approx(expected)


# --- Bookkeeping fields ----------------------------------------------------

def test_due_date_advances_by_interval():
    card = make_card()
    before = datetime.now(timezone.utc)
    apply_sm2(card, GOOD)  # interval 1
    delta = card.due_date - before
    # ~1 day out, allow a little slack for execution time
    assert timedelta(hours=23) < delta < timedelta(hours=25)


def test_last_reviewed_is_set():
    card = make_card()
    apply_sm2(card, GOOD)
    assert card.last_reviewed is not None


def test_rating_to_q_mapping():
    assert RATING_TO_Q == {0: 1, 1: 2, 2: 4, 3: 5}
