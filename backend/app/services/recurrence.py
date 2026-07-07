from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

# Weekday: 0 = Monday ... 6 = Sunday (matches datetime.weekday()).


@dataclass
class RecurrenceRule:
    """Simple weekly recurrence.

    weekdays: list of ints (0=Mon..6=Sun)
    start_time: local time of day the session starts
    start_date / end_date: inclusive window to generate within
    """

    weekdays: list[int]
    start_time: time
    start_date: date
    end_date: date
    exceptions: set[date] | None = None


def expand_recurrence(rule: RecurrenceRule) -> list[datetime]:
    """Expand a weekly recurrence rule into a list of session start datetimes."""
    if rule.start_date > rule.end_date:
        return []

    exceptions = rule.exceptions or set()
    weekdays = set(rule.weekdays)
    occurrences: list[datetime] = []

    current = rule.start_date
    while current <= rule.end_date:
        if current.weekday() in weekdays and current not in exceptions:
            occurrences.append(datetime.combine(current, rule.start_time))
        current += timedelta(days=1)

    return occurrences
