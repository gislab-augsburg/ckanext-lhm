"""Tests for validators.py."""

import pytest

import ckan.plugins.toolkit as tk

from ckanext.lhm.logic import validators


def test_lhm_reauired_with_valid_value():
    assert validators.lhm_required("value") == "value"


def test_lhm_reauired_with_invalid_value():
    with pytest.raises(tk.Invalid):
        validators.lhm_required(None)
