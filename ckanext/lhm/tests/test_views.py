"""Tests for views.py."""

import pytest

import ckanext.lhm.validators as validators


import ckan.plugins.toolkit as tk


@pytest.mark.ckan_config("ckan.plugins", "lhm")
@pytest.mark.usefixtures("with_plugins")
def test_lhm_blueprint(app, reset_db):
    resp = app.get(tk.h.url_for("lhm.page"))
    assert resp.status_code == 200
    assert resp.body == "Hello, lhm!"
