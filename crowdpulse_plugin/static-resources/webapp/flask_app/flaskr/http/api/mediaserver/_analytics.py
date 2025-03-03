import json
import logging
import os
from collections.abc import Mapping
from datetime import datetime, timezone, timedelta
from math import isclose
from typing import Optional, Sequence

from ....common import format_uuid

_logger = logging.getLogger(__name__)


class AnalyticsTrack:

    def __init__(self, raw_track: Mapping):
        self._raw_track = raw_track

    def track_id(self):
        return format_uuid(self._raw_track['id'])

    def type_id(self):
        return self._raw_track['objectTypeId']

    def time_period(self):
        start_ms = int(self._raw_track['firstAppearanceTimeUs']) // 1000
        end_ms = int(self._raw_track['lastAppearanceTimeUs']) // 1000
        return TimePeriod.from_start_and_end_ms(start_ms=start_ms, end_ms=end_ms)

    def attributes(self):
        return self._raw_track['attributes']

    def position_sequence(self):
        positions = []
        for position in self._raw_track['objectPositionSequence']:
            positions.append(BoundingBox.from_box_data(**position['boundingBox']))
        return positions

    def to_json(self):
        return json.dumps({
            'id': self.track_id(),
            'objectTypeId': self.type_id(),
            'firstAppearanceTimeUs': self.time_period().start_ms,
            'lastAppearanceTimeUs': self.time_period().end_ms if self.time_period().complete else None,
            'attributes': self.attributes(),
            # TODO: Add position sequence
            })


class TimePeriod:

    def __init__(self, start_ms: int, duration_ms: Optional[int] = None):
        self.start_ms = start_ms
        self.start = datetime.fromtimestamp(start_ms / 1000, timezone.utc)
        if duration_ms is None:
            self.complete = False
        else:
            self.complete = True
            self._duration_ms = duration_ms
            self._duration_timedelta = timedelta(milliseconds=duration_ms)
            self.duration_sec = self._duration_timedelta.total_seconds()
            self.end_ms = self.start_ms + self._duration_ms
            self.end = self.start + self._duration_timedelta

    def __repr__(self):
        duration = f'duration_ms={self._duration_ms}' if self.complete else 'incomplete'
        return f'TimePeriod(start_ms={self.start_ms}, {duration})'

    def __eq__(self, other):
        if not isinstance(other, TimePeriod):
            return NotImplemented
        if self.start_ms != other.start_ms:
            return False
        if not self.complete and not other.complete:
            return True
        if not self.complete or not other.complete:
            return False
        return self._duration_ms == other._duration_ms

    def __hash__(self):
        if not self.complete:
            return hash(self.start_ms)
        return hash((self.start_ms, self._duration_ms))

    @classmethod
    def _from_filename(cls, filename):
        [stem, _] = os.path.splitext(filename)
        try:
            [start_ms_str, duration_ms_str] = stem.split('_')
        except ValueError:  # Incomplete time period
            start_ms_str = stem
            duration_ms = None
        else:
            duration_ms = int(duration_ms_str)
        return cls(int(start_ms_str), duration_ms)

    def join(self, other):
        if not isinstance(other, TimePeriod):
            raise TypeError(f"Cannot concatenate TimePeriod with {type(other)}")
        if not other.complete:
            duration_ms = None
        else:
            duration_ms = self._duration_ms + other._duration_ms
        return TimePeriod(self.start_ms, duration_ms)

    def is_among(self, periods_list, tolerance_sec=1):
        trimmed = self.trim_left(tolerance_sec * 1000).trim_right(tolerance_sec * 1000)
        log_lines = [f"Compare period {trimmed!r} with:", *(repr(period) for period in periods_list)]
        _logger.debug("    \n".join(log_lines))
        return any([period.contains(trimmed) for period in periods_list])

    @staticmethod
    def consolidate(periods_list, tolerance_sec=0) -> Sequence['TimePeriod']:
        tolerance = timedelta(seconds=tolerance_sec)
        try:
            [first, *others] = periods_list
        except ValueError:
            return []
        consolidated = [first]
        for period in others:
            gap_length = period.start - consolidated[-1].end
            if gap_length <= tolerance:
                consolidated[-1] = consolidated[-1].extend(gap_length).join(period)
            else:
                consolidated.append(period)
        return consolidated

    @classmethod
    def list_from_filenames(cls, filename_list):
        chunk_periods = [cls._from_filename(filename) for filename in filename_list]
        return cls.consolidate(chunk_periods)

    def extend(self, delta: timedelta):
        if not self.complete:
            raise RuntimeError("Can't extend incomplete period")
        delta_ms = int(delta.total_seconds() * 1000)
        return TimePeriod(self.start_ms, self._duration_ms + delta_ms)

    @staticmethod
    def calculate_gaps(periods_list):
        gaps_list = []
        for previous, current in zip(periods_list, periods_list[1:]):
            gap_timedelta = current.start - previous.end
            gaps_list.append(gap_timedelta.total_seconds())
        return gaps_list

    @classmethod
    def from_datetime(cls, start: datetime, duration: Optional[timedelta] = None):
        start_ms = int(start.timestamp() * 1000)
        if duration is None:
            duration_ms = None
        else:
            duration_ms = int(duration.total_seconds() * 1000)
        return TimePeriod(start_ms, duration_ms)

    @classmethod
    def from_start_and_end_ms(cls, start_ms, end_ms):
        return cls(start_ms=start_ms, duration_ms=end_ms - start_ms)

    def trim_right(self, ms: int) -> 'TimePeriod':
        if not self.complete:
            raise RuntimeError("Non-finished time period could not be shrank")
        if ms > self._duration_ms:
            return TimePeriod(start_ms=self.start_ms, duration_ms=0)
        return TimePeriod(self.start_ms, self._duration_ms - ms)

    def trim_left(self, ms: int) -> 'TimePeriod':
        if not self.complete:
            return TimePeriod(start_ms=self.start_ms + ms, duration_ms=None)
        if ms > self._duration_ms:
            return TimePeriod(start_ms=self.start_ms + self._duration_ms, duration_ms=0)
        return TimePeriod(start_ms=self.start_ms + ms, duration_ms=self._duration_ms - ms)

    def contains(self, other: 'TimePeriod') -> bool:
        if not self.complete:
            raise RuntimeError(f"Non-finished {self} could not be compared")
        elif not other.complete:
            raise RuntimeError(f"Non-finished {other} could not be compared")
        if self.start_ms > other.start_ms:
            return False
        if self.end < other.end:
            return False
        return True


class _Interval:

    def __init__(self, start, end):
        self.start = start
        self.end = end

    def contains(self, number):
        return self.start <= number <= self.end

    def expanded(self, accuracy):
        return _Interval(self.start - accuracy, self.end + accuracy)

    def overlaps(self, other, accuracy):
        expanded = other.expanded(accuracy)
        return expanded.contains(self.start) or self.contains(expanded.start)

    @property
    def size(self):
        return self.end - self.start

    def calc_rel_coordinate(self, abs_coordinate: float):
        return self.size - abs(self.size - abs_coordinate % (2 * self.size))


class Rectangle:

    def __init__(self, x1, y1, x2, y2):
        self.x = _Interval(x1, x2)
        self.y = _Interval(y1, y2)
        _logger.debug("Create %r", self)
        self.coordinates_dict = {
            'x1': self.x.start,
            'y1': self.y.start,
            'x2': self.x.end,
            'y2': self.y.end,
            }

    def __repr__(self):
        return (
            f'Rectangle(x1={self.x.start}, y1={self.y.start}, x2={self.x.end}, y2={self.y.end})')

    @classmethod
    def from_box_data(cls, x, y, width, height):
        return cls(x1=x, x2=x + width, y1=y, y2=y + height)

    def overlaps(self, other, x_accuracy, y_accuracy):
        return self.x.overlaps(other.x, x_accuracy) and self.y.overlaps(other.y, y_accuracy)


class NormalizedRectangle(Rectangle):

    def __init__(self, x, y, width, height):
        super().__init__(x, y, x + width, y + height)
        if not self._is_valid():
            raise ValueError(f"{self} has invalid coordinates")

    def _is_valid(self):
        values_ok = all(
            0 <= value <= 1 for value in (self.x.start, self.x.end, self.y.start, self.y.end))
        dimensions_ok = all((self.x.end >= self.x.start, self.y.end >= self.y.start))
        return values_ok and dimensions_ok

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(x={self.x.start}, y={self.y.start}, "
            f"width={self.x.size}, height={self.y.size})"
            )

    def is_close_to(self, other, rel_tolerance=0.001):
        return all([
            isclose(self.x.start, other.x.start, rel_tol=rel_tolerance),
            isclose(self.y.start, other.y.start, rel_tol=rel_tolerance),
            isclose(self.x.end, other.x.end, rel_tol=rel_tolerance),
            isclose(self.y.end, other.y.end, rel_tol=rel_tolerance),
            ])


class BoundingBox(NormalizedRectangle):

    def __init__(self, x1, y1, x2, y2, precision=3):
        self._precision = precision
        super(BoundingBox, self).__init__(
            round(x1, self._precision),
            round(y1, self._precision),
            round(x2 - x1, self._precision),
            round(y2 - y1, self._precision),
            )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(x={self.x.start}, y={self.y.start}, "
            f"width={self.x.size}, height={self.y.size}, precision={self._precision})"
            )

    def as_bounding_box_dict(self):
        return {
            'x': self.x.start,
            'y': self.y.start,
            'width': round(self.x.size, self._precision),
            'height': round(self.y.size, self._precision),
            }
