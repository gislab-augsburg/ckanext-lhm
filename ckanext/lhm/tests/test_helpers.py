"""Tests for helpers.py."""

import ckanext.lhm.helpers as helpers


def test_lhm_config():

    usage = helpers.usage_info()
    email = helpers.contact_email()
    github = helpers.github()
    version = helpers.version_info()

    return usage, email, github, version
