from flask import Blueprint


lhm_view = Blueprint('lhm_view', __name__)


def page():
    return "Hello, lhm!"

lhm_view.add_url_rule("/lhm_view/page", view_func=page)


def get_blueprints():
    return [lhm_view]