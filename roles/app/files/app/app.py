"""MediQueue - minimal hospital appointment booking service.

Deployed by Ansible: Gunicorn runs this Flask app, Nginx proxies to it,
and appointments are stored in PostgreSQL.
"""
import os
import socket

import psycopg2
from flask import Flask, jsonify, redirect, render_template, request

app = Flask(__name__)

APP_NAME = os.getenv("APP_NAME", "MediQueue")
APP_VERSION = os.getenv("APP_VERSION", "dev")
APP_ENV = os.getenv("APP_ENV", "local")
DEPARTMENTS = ["General Medicine", "Cardiology", "Orthopaedics", "Paediatrics", "Dermatology"]


def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=3,
    )


def init_db():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id          SERIAL PRIMARY KEY,
                patient     VARCHAR(100) NOT NULL,
                department  VARCHAR(50)  NOT NULL,
                slot        DATE         NOT NULL,
                created_at  TIMESTAMP    DEFAULT NOW()
            )
            """
        )


def list_appointments():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, patient, department, slot FROM appointments ORDER BY slot, id")
        return [
            {"id": r[0], "patient": r[1], "department": r[2], "slot": r[3].isoformat()}
            for r in cur.fetchall()
        ]


@app.route("/")
def index():
    return render_template(
        "index.html",
        app_name=APP_NAME,
        version=APP_VERSION,
        env=APP_ENV,
        host=socket.gethostname(),
        departments=DEPARTMENTS,
        appointments=list_appointments(),
    )


@app.route("/book", methods=["POST"])
def book():
    patient = request.form.get("patient", "").strip()[:100]
    department = request.form.get("department", "")
    slot = request.form.get("slot", "")
    if patient and department in DEPARTMENTS and slot:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO appointments (patient, department, slot) VALUES (%s, %s, %s)",
                (patient, department, slot),
            )
    return redirect("/")


@app.route("/api/appointments")
def api_appointments():
    return jsonify(list_appointments())


@app.route("/health")
def health():
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
        db_state = "connected"
    except psycopg2.Error:
        db_state = "unreachable"
    status = "UP" if db_state == "connected" else "DEGRADED"
    return jsonify(
        status=status, database=db_state, version=APP_VERSION, host=socket.gethostname()
    ), (200 if status == "UP" else 503)


try:
    init_db()
except psycopg2.Error as exc:  # app still starts; /health will report the problem
    app.logger.error("Could not initialise database: %s", exc)
