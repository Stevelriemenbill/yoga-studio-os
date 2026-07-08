from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

# Weekday: 0 = Monday ... 6 = Sunday (matches datetime.weekday()).


@dataclass
class RecurrenceRule:
    """Simple weekly recurrence.

    weekdays: list of ints (0=Mon..6=Sun)
    start_time: local time of day the session starts
    start_date: inclusive date to start generating from
    end_date: inclusive last date to generate within (or None if count-bound)
    count: maximum number of occurrences to generate (or None if date-bound)
    exceptions: dates to skip
    """

    weekdays: list[int]
    start_time: time
    start_date: date
    end_date: date | None = None
    count: int | None = None
    exceptions: set[date] | None = None
    #: Repeat every N weeks (1 = weekly, 6 = every six weeks). Weeks are counted
    #: from the Monday of ``start_date``'s week.
    interval_weeks: int = 1


#: Absolute safety limit on occurrences, even when only a count is given but
#: something goes wrong, to bound work.
_MAX_DAYS_SCANNED = 366 * 5


def expand_recurrence(rule: RecurrenceRule) -> list[datetime]:
    """Expand a weekly recurrence rule into a list of session start datetimes.

    Generation stops at ``end_date`` (if given) or once ``count`` occurrences
    have been produced (if given). At least one bound must be set.
    """
    if rule.end_date is not None and rule.start_date > rule.end_date:
        return []

    exceptions = rule.exceptions or set()
    weekdays = set(rule.weekdays)
    occurrences: list[datetime] = []

    interval = max(1, rule.interval_weeks)
    # Monday of the week containing start_date; used as the anchor for the
    # every-N-weeks filter.
    anchor_monday = rule.start_date - timedelta(days=rule.start_date.weekday())

    current = rule.start_date
    scanned = 0
    while scanned < _MAX_DAYS_SCANNED:
        if rule.end_date is not None and current > rule.end_date:
            break
        if rule.count is not None and len(occurrences) >= rule.count:
            break
        if current.weekday() in weekdays and current not in exceptions:
            if interval == 1:
                occurrences.append(datetime.combine(current, rule.start_time))
            else:
                cur_monday = current - timedelta(days=current.weekday())
                weeks_since = (cur_monday - anchor_monday).days // 7
                if weeks_since % interval == 0:
                    occurrences.append(
                        datetime.combine(current, rule.start_time)
                    )
        current += timedelta(days=1)
        scanned += 1

    return occurrences
