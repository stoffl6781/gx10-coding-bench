# Ferienwohnung: Belegung

Regeln:

- Datumsangaben kommen als `TT.MM.JJJJ`, Leerzeichen am Rand sind erlaubt.
- Eine Buchung belegt die Nächte von der Anreise bis zum Tag vor der Abreise. Der Abreisetag ist wieder frei, am selben Tag darf der nächste Gast anreisen.
- Eine Buchung hat mindestens eine Nacht. Abreise am Anreisetag oder davor ist ein ValueError.
- Überschneidet sich eine neue Buchung mit einer bestehenden, ist das ein ValueError.
- `free_nights(jahr, monat)` zählt die freien Nächte des Monats. Eine Nacht gehört zu dem Datum, an dem sie beginnt.

Tests: `python3 -m unittest discover -s tests -t .`
