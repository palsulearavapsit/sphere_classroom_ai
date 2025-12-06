from flask import Blueprint, jsonify

api_bp = Blueprint("api", __name__)

@api_bp.route("/", methods=["GET"])
def api_root():
    return jsonify({"name":"Project Galileo API","version":"1.0"})
