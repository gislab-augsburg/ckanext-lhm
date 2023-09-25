"""Tests for helpers.py."""

import ckanext.lhm.helpers as helpers


def test_lhm_hello():
    assert helpers.lhm_hello() == "Hello, lhm!"
