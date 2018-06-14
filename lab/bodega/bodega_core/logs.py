"""Logging functionality."""
import logging
import re


class NumericThresholdFilter(logging.Filter):
    """Filter log records according to a numeric value meeting a threshold.

    Python's log filtering focuses on which records to exclude: when multiple
    filters are involved, if any one of them excludes a record then it will
    not be sent to the log handler. So, this filter excludes all records
    under the specified logger name that match the specified regular expression
    pattern and have their numeric value below the specified threshold.
    """

    def __init__(self, name='', pattern='^(.*)$', threshold=1.0):
        """Create a NumericThresholdFilter."""
        self.name_filter = logging.Filter(name=name)
        self.pattern = pattern
        self.threshold = threshold

    def filter(self, record):
        if not self.name_filter.filter(record):
            return True

        message = record.getMessage()
        match = re.match(self.pattern, message)
        if not match:
            return True

        try:
            value = float(match.group(1))
        except ValueError:
            return True

        return (value >= self.threshold)
