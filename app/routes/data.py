from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from ..services.data_service import fit_curve, propagate_error, analyze_experiment

data_bp = Blueprint("data", __name__, template_folder="../templates")

@data_bp.route("/", methods=["GET"])
@login_required
def data_home():
    return render_template("data.html")

@data_bp.route("/fit", methods=["POST"])
@login_required
def route_fit():
    payload = request.get_json() or {}
    return jsonify(fit_curve(payload))

@data_bp.route("/propagate", methods=["POST"])
@login_required
def route_prop():
    payload = request.get_json() or {}
    return jsonify(propagate_error(payload))

@data_bp.route("/analyze", methods=["POST"])
@login_required
def route_analyze():
    payload = request.get_json() or {}
    return jsonify(analyze_experiment(payload))
