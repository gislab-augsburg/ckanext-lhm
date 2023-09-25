from flask import Blueprint


lhm = Blueprint(
    "lhm", __name__)


def page():
    return "Hello, lhm!"


lhm.add_url_rule(
    "/lhm/page", view_func=page)


def get_blueprints():
    return [lhm]
