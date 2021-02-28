# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import contextlib
import sys

import six
from six.moves.urllib.parse import urljoin
from six.moves.urllib.request import urlopen
from yaml import safe_load


TIMEOUT_SEC = 1


def wrap_exception(method):
    def wrapper(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except Exception as e:
            six.reraise(
                SwaggerValidationError,
                SwaggerValidationError(str(e), e),
                sys.exc_info()[2])
    return wrapper


def read_file(file_path):
    """
    Utility method for reading a JSON/YAML file and converting it to a Python dictionary
    :param file_path: path of the file to read

    :return: Python dictionary representation of the JSON file
    :rtype: dict
    """
    return read_url(urljoin('file://', file_path))


def read_url(url, timeout=TIMEOUT_SEC):
    with contextlib.closing(urlopen(url, timeout=timeout)) as fh:
        # NOTE: JSON is a subset of YAML so it is safe to read JSON as it is YAML
        return safe_load(fh.read().decode('utf-8'))


class SwaggerValidationError(Exception):
    """Exception raised in case of a validation error."""
    pass
