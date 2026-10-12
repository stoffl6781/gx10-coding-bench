from datetime import date, datetime


def parse_date(s: str) -> date:
    return datetime.strptime(s.strip(), "%m.%d.%Y").date()
