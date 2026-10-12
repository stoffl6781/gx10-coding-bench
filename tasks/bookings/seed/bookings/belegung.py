import calendar
from dataclasses import dataclass
from datetime import date, timedelta

from .dates import parse_date
from .overlap import overlaps


@dataclass
class Booking:
    id: int
    guest: str
    start: date
    end: date


class Belegung:
    def __init__(self):
        self._bookings = {}
        self._next_id = 1

    def add(self, guest: str, arrival: str, departure: str) -> Booking:
        start, end = parse_date(arrival), parse_date(departure)
        if end < start:
            raise ValueError("Abreise vor Anreise")
        for b in self._bookings.values():
            if overlaps(start, end, b.start, b.end):
                raise ValueError("Zeitraum belegt")
        booking = Booking(self._next_id, guest, start, end)
        self._bookings[booking.id] = booking
        self._next_id += 1
        return booking

    def free_nights(self, year: int, month: int) -> int:
        days = calendar.monthrange(year, month)[1]
        first = date(year, month, 1)
        busy = 0
        for i in range(days):
            night = first + timedelta(days=i)
            if any(b.start <= night <= b.end for b in self._bookings.values()):
                busy += 1
        return days - busy
