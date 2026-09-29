from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory

from src.api import database, history_store
from src.api.recovery_service import RecoveryService

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "web"

app = Flask(__name__, static_folder=str(WEB_ROOT), static_url_path="")
recovery_service = RecoveryService(database.DATABASE_PATH)


@app.get("/")
def index() -> Any:
    return send_from_directory(WEB_ROOT, "index.html")


@app.get("/api/health")
def health() -> Any:
    return jsonify({"status": "ok", "database": "read-only"})


@app.get("/api/dashboard")
def dashboard() -> Any:
    return jsonify({
        "counts": database.get_dashboard_data(),
        "recent_operations": history_store.list_operations(limit=5),
    })


@app.get("/api/stations")
def stations() -> Any:
    return jsonify({"stations": database.get_stations()})


@app.get("/api/stations/<station_code>/resources")
def station_resources(station_code: str) -> Any:
    return jsonify({"resources": database.get_station_resources(station_code)})


@app.get("/api/trains")
def trains() -> Any:
    day = request.args.get("day", type=int)
    platform = request.args.get("platform", type=int)
    return jsonify({
        "trains": database.search_trains(
            query=request.args.get("q", "").strip(),
            station_code=request.args.get("station", "").strip(),
            day=day,
            platform_number=platform,
        )
    })


@app.get("/api/trains/<train_number>")
def train_details(train_number: str) -> Any:
    return jsonify({"stops": database.get_train_timetable(train_number)})


@app.post("/api/disruptions/detect")
def detect_disruption() -> Any:
    try:
        payload = _validated_disruption(request.get_json(silent=True) or {})
        return jsonify(recovery_service.detect_affected(payload))
    except (KeyError, TypeError, ValueError) as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/recovery/<recovery_id>/optimize")
def optimize_recovery(recovery_id: str) -> Any:
    try:
        iterations = (request.get_json(silent=True) or {}).get("iterations", 10)
        return jsonify(recovery_service.optimize(recovery_id, int(iterations)))
    except KeyError:
        return jsonify({"error": "Recovery operation was not found."}), 404
    except Exception:
        app.logger.exception("Recovery optimization failed")
        return jsonify({"error": "Optimization could not be completed."}), 500


@app.get("/api/recovery/<recovery_id>")
def recovery_details(recovery_id: str) -> Any:
    try:
        return jsonify(recovery_service.get_result(recovery_id))
    except KeyError:
        return jsonify({"error": "Recovery operation was not found."}), 404


@app.post("/api/recovery/<recovery_id>/select")
def select_recovery(recovery_id: str) -> Any:
    try:
        payload = request.get_json(silent=True) or {}
        selected_option = int(payload["option"])
        result = recovery_service.get_result(recovery_id)
        options = result["options"]
        if selected_option < 1 or selected_option > len(options):
            raise ValueError("Selected recovery option is unavailable.")
        operation = history_store.record_operation(
            operation_id=recovery_id,
            disruption=result["disruption"],
            affected_trains=len({
                record["train_number"] for record in result["affected_records"]
            }),
            options=options,
            metrics={**result["metrics"], "selected_option": selected_option},
            selected_option=selected_option,
        )
        return jsonify(operation)
    except KeyError:
        return jsonify({"error": "Recovery operation was not found."}), 404
    except (TypeError, ValueError) as error:
        return jsonify({"error": str(error)}), 400


@app.get("/api/history")
def history() -> Any:
    return jsonify({"operations": history_store.list_operations()})


def _validated_disruption(payload: dict[str, Any]) -> dict[str, Any]:
    fields = [
        "disruption_type",
        "station_code",
        "resource_id",
        "day",
        "start_time",
        "end_time",
    ]
    missing = [field for field in fields if not payload.get(field)]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    if payload["end_time"] <= payload["start_time"]:
        raise ValueError("End time must be after start time.")
    resource_ids = {
        item["resource_id"]
        for item in database.get_station_resources(payload["station_code"])
    }
    if payload["resource_id"] not in resource_ids:
        raise ValueError("Resource does not belong to the selected station.")
    return {
        **payload,
        "day": int(payload["day"]),
        "description": payload.get("description", "").strip(),
    }


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
