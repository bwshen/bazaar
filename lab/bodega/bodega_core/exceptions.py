"""Bodega-specific exceptions and helper functions."""

from django.core.exceptions import ValidationError


class BodegaException(Exception):
    pass


class BodegaTypeError(TypeError, BodegaException):
    pass


class BodegaValueError(ValueError, BodegaException):
    pass


class BodegaValidationError(ValidationError, BodegaException):
    pass


class BodegaNoMatch(BodegaException):
    pass


def bodega_error(log, msg):
    log.error(msg)
    raise BodegaException(msg)


def bodega_type_error(log, msg):
    log.error(msg)
    raise BodegaTypeError(msg)


def bodega_value_error(log, msg):
    log.error(msg)
    raise BodegaValueError(msg)


def bodega_validation_error(log, msg):
    log.error(msg, exc_info=True)
    raise BodegaValidationError(msg)


def bodega_no_match(log, msg):
    log.error(msg)
    raise BodegaNoMatch(msg)


def verify_type(log, actual_obj, expected_type, msg=''):
    if not isinstance(actual_obj, expected_type):
        error_msg = 'Wrong type: %s (expected %s)%s' % (
            type(actual_obj),
            expected_type,
            ' [%s]' % msg if msg else '')
        bodega_type_error(log, error_msg)


def verify_dictionary_and_keys(log, var, expected_keys, optional_keys):
    """Verify that 'var' is a dictionary with the provided keys.

    Input:
      - 'var': a variable to be verified.
      - 'expected_keys': a set of keys expected in 'var'.
      - 'optional_keys': a set of keys which may be in 'var'.

    Throws a BodegaTypeError exception if 'var' is not a dictionary with
    the passed keys.
    """
    verify_type(log, var, dict)
    actual_non_optional_keys = set(var.keys()).difference(optional_keys)
    missing_keys = expected_keys.difference(actual_non_optional_keys)
    if missing_keys:
        bodega_type_error(log, 'Missing keys: %s' % list(missing_keys))
    superfluous_keys = actual_non_optional_keys.difference(expected_keys)
    if superfluous_keys:
        bodega_type_error(log, 'Superfluous keys: %s' % list(superfluous_keys))
