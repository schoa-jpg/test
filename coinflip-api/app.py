from flask import Flask, jsonify
import random
import json
import os

app = Flask(__name__)

STATS_FILE = os.environ.get("STATS_FILE", "/app/stats.json")


def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    return {"heads": 0, "tails": 0}


def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f)


@app.route("/")
def index():
    return {"service": "coin-flip", "endpoint": "/flip", "stats": "/stats"}


@app.route("/flip")
def flip():
    result = random.choice(["heads", "tails"])
    stats = load_stats()
    stats[result] += 1
    save_stats(stats)
    return jsonify({"result": result, "stats": stats})


@app.route("/stats")
def stats():
    return jsonify(load_stats())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
