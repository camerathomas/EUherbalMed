import json
import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), "ema_herbal_medicines.json")


def load_data():
    """Laad het JSON-bestand en retourneer de records."""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        payload = json.load(f)
    # Ondersteun zowel {"data": [...]} als een platte lijst
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


@app.route("/")
def index():
    records = load_data()
    # Unieke waarden voor de filters
    statuses = sorted({r.get("ema_status", "") for r in records if r.get("ema_status")})
    outcomes = sorted({r.get("ema_outcome", "") for r in records if r.get("ema_outcome")})
    areas = sorted({
        area
        for r in records
        for area in (r.get("therapeutic_area") or [])
        if area
    })
    return render_template(
        "index.html",
        records=records,
        statuses=statuses,
        outcomes=outcomes,
        areas=areas,
        total=len(records),
    )


@app.route("/api/records")
def api_records():
    """Optioneel: JSON-endpoint voor toekomstige AI-app of andere clients."""
    return jsonify(load_data())


if __name__ == "__main__":
    app.run(debug=True, port=5000)
