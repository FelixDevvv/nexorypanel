from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import re
import secrets
import shutil
import shlex
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
import zipfile
import webbrowser
from functools import wraps
from pathlib import Path
from typing import Any

import psutil
from flask import Flask, g, jsonify, render_template, request, send_file, session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

APP_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
DATA_DEFAULT = Path(sys.executable).resolve().parent / "data" if getattr(sys, "frozen", False) else APP_ROOT / "data"
DATA_DIR = Path(os.environ.get("NEXORY_DATA_DIR", DATA_DEFAULT)).resolve()
SERVER_DIR = DATA_DIR / "servers"
DB_PATH = DATA_DIR / "nexory.sqlite3"
CONFIG_PATH = DATA_DIR / "secret.key"
SOFTWARE = {
    "paper": {"name": "Paper", "image": "https://api.papermc.io/v2/projects/paper"},
    "purpur": {"name": "Purpur", "image": "https://api.purpurmc.org/v2/purpur"},
    "folia": {"name": "Folia", "image": "https://api.papermc.io/v2/projects/folia"},
    "vanilla": {"name": "Vanilla", "image": None},
}
THEMES = {"Default", "Purple", "Red", "Green", "Blue", "Pterodactyl", "Yellow", "Orange"}
MAX_EDIT_BYTES = 2 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 512 * 1024 * 1024
PROCESSES: dict[str, subprocess.Popen[bytes]] = {}
PROCESS_LOCK = threading.Lock()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
app = Flask(__name__, static_folder="static", template_folder="templates")
app.config.update(
    MAX_CONTENT_LENGTH=256 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)


def db() -> sqlite3.Connection:
    if "db" not in g:
        connection = sqlite3.connect(DB_PATH, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


@app.teardown_appcontext
def close_db(_error: BaseException | None = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def setting(key: str, default: str) -> str:
    row = db().execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def server_setting(server_id: str, key: str, default: str = "") -> str:
    row = db().execute(
        "SELECT value FROM server_settings WHERE server_id = ? AND key = ?",
        (server_id, key),
    ).fetchone()
    return row["value"] if row else default


def save_server_settings(server_id: str, values: dict[str, str]) -> None:
    db().executemany(
        """INSERT INTO server_settings(server_id, key, value) VALUES(?, ?, ?)
           ON CONFLICT(server_id, key) DO UPDATE SET value = excluded.value""",
        ((server_id, key, value) for key, value in values.items()),
    )
    db().commit()


def log_activity(server_id: str, action: str, detail: str = "") -> None:
    user = getattr(g, "user", None)
    if user:
        db().execute(
            """INSERT INTO server_activity(id, server_id, user_id, username, action, detail, created_at)
               VALUES(?, ?, ?, ?, ?, ?, datetime('now'))""",
            (uuid.uuid4().hex, server_id, user["id"], user["username"], action, detail[:200]),
        )
        db().commit()


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SERVER_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=15)
    connection.executescript(
        """
        PRAGMA journal_mode = WAL;
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'user')), created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS servers (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, owner_id TEXT NOT NULL REFERENCES users(id),
            software TEXT NOT NULL, version TEXT NOT NULL, build TEXT NOT NULL DEFAULT '',
            ram_mb INTEGER NOT NULL, disk_mb INTEGER NOT NULL, port INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY, label TEXT NOT NULL, key_hash TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS server_members (
            server_id TEXT NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            PRIMARY KEY(server_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS server_settings (
            server_id TEXT NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
            key TEXT NOT NULL, value TEXT NOT NULL,
            PRIMARY KEY(server_id, key)
        );
        CREATE TABLE IF NOT EXISTS server_activity (
            id TEXT PRIMARY KEY, server_id TEXT NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
            user_id TEXT REFERENCES users(id) ON DELETE SET NULL, username TEXT NOT NULL,
            action TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS server_ports (
            id TEXT PRIMARY KEY, server_id TEXT NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
            port INTEGER NOT NULL, protocol TEXT NOT NULL CHECK(protocol IN ('TCP','UDP')),
            description TEXT NOT NULL, firewall_name TEXT NOT NULL UNIQUE,
            firewall_profile TEXT NOT NULL, created_at TEXT NOT NULL,
            UNIQUE(port, protocol)
        );
        CREATE TABLE IF NOT EXISTS server_backups (
            id TEXT PRIMARY KEY, server_id TEXT NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
            filename TEXT NOT NULL, size_bytes INTEGER NOT NULL, created_by TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS server_schedules (
            id TEXT PRIMARY KEY, server_id TEXT NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
            name TEXT NOT NULL, action TEXT NOT NULL CHECK(action IN ('start','stop','restart','command')),
            command TEXT NOT NULL DEFAULT '', interval_minutes INTEGER NOT NULL,
            next_run_at INTEGER NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS server_databases (
            id TEXT PRIMARY KEY, server_id TEXT NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
            database_name TEXT NOT NULL UNIQUE, username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL, created_at TEXT NOT NULL
        );
        """
    )
    defaults = {
        "enable_register": "true",
        "theme": "Purple",
        "accent_color": "",
        "button_style": "Gradient",
        "max_ram_mb": "8192",
        "max_disk_mb": "51200",
        "node_name": "Nexory Windows Node",
        "api_key_enabled": "false",
        "background_style": "Gradient",
        "announcement": "",
        "discord_url": "",
        "custom_links": "[]",
        "firewall_profile": "Any",
    }
    connection.executemany(
        "INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)", defaults.items()
    )
    connection.execute(
        "UPDATE settings SET value = 'Glassed' WHERE key = 'button_style' AND value = 'Glass'"
    )
    connection.commit()
    connection.close()
    if not CONFIG_PATH.exists():
        temporary = CONFIG_PATH.with_suffix(".tmp")
        temporary.write_text(secrets.token_urlsafe(48), encoding="utf-8")
        try:
            temporary.replace(CONFIG_PATH)
        except FileExistsError:
            temporary.unlink(missing_ok=True)
    app.secret_key = CONFIG_PATH.read_text(encoding="utf-8").strip()


def response_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


def json_body() -> dict[str, Any]:
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else {}


def csrf_valid() -> bool:
    token = session.get("csrf_token")
    return bool(token and secrets.compare_digest(token, request.headers.get("X-CSRF-Token", "")))


def login_required(admin: bool = False):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            user_id = session.get("user_id")
            if not user_id:
                return response_error("Inicia sesión para continuar.", 401)
            user = db().execute(
                "SELECT id, username, role FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if not user:
                session.clear()
                return response_error("La sesión ya no es válida.", 401)
            g.user = user
            if admin and user["role"] != "admin":
                return response_error("Se requieren permisos de administrador.", 403)
            if request.method not in {"GET", "HEAD", "OPTIONS"} and not csrf_valid():
                return response_error("Token CSRF inválido. Recarga la página.", 403)
            return function(*args, **kwargs)

        return wrapped

    return decorate


def api_key_required(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        candidate = request.headers.get("Authorization", "")
        if not candidate.startswith("Bearer "):
            return response_error("Falta la API key.", 401)
        digest = hashlib.sha256(candidate[7:].encode("utf-8")).hexdigest()
        row = db().execute("SELECT id FROM api_keys WHERE key_hash = ?", (digest,)).fetchone()
        if setting("api_key_enabled", "false") != "true" or not row:
            return response_error("API key no válida o desactivada.", 401)
        return function(*args, **kwargs)

    return wrapped


def to_server_path(server_id: str, relative: str = "") -> Path:
    root = (SERVER_DIR / server_id).resolve()
    if not root.is_relative_to(SERVER_DIR.resolve()):
        raise ValueError("Ruta de servidor no válida.")
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("La ruta sale de la carpeta del servidor.")
    return candidate


def get_server(server_id: str):
    row = db().execute(
        """SELECT s.*, u.username AS owner_name,
                  CASE WHEN s.owner_id = ? THEN 'owner' ELSE 'manager' END AS access_role
           FROM servers s JOIN users u ON u.id = s.owner_id
           WHERE s.id = ? AND (
               s.owner_id = ? OR ? = 'admin' OR EXISTS (
                   SELECT 1 FROM server_members m
                   WHERE m.server_id = s.id AND m.user_id = ?
               )
           )""",
        (g.user["id"], server_id, g.user["id"], g.user["role"], g.user["id"]),
    ).fetchone()
    return row


def folder_size(folder: Path) -> int:
    total = 0
    for path in folder.rglob("*"):
        if path.is_file():
            try:
                total += path.stat().st_size
            except OSError:
                logging.warning("No se pudo calcular tamaño de %s", path)
    return total


def used_allocations() -> tuple[int, int]:
    row = db().execute("SELECT COALESCE(SUM(ram_mb), 0), COALESCE(SUM(disk_mb), 0) FROM servers").fetchone()
    return int(row[0]), int(row[1])


def server_status(server_id: str) -> tuple[str, float, int]:
    with PROCESS_LOCK:
        process = PROCESSES.get(server_id)
    if not process:
        return "offline", 0.0, 0
    if process.poll() is not None:
        with PROCESS_LOCK:
            PROCESSES.pop(server_id, None)
        return "offline", 0.0, 0
    try:
        proc = psutil.Process(process.pid)
        return "online", proc.cpu_percent(interval=None), proc.memory_info().rss // (1024 * 1024)
    except psutil.Error:
        return "online", 0.0, 0


def start_server_process(server: Any) -> tuple[bool, str]:
    server_id = server["id"]
    root = to_server_path(server_id)
    with PROCESS_LOCK:
        process = PROCESSES.get(server_id)
    if process and process.poll() is None:
        return True, "online"
    jar = root / "server.jar"
    java = shutil.which("java")
    if not jar.is_file():
        return False, "Instala primero server.jar desde Versiones."
    eula = root / "eula.txt"
    if not eula.is_file() or "eula=true" not in eula.read_text(encoding="utf-8", errors="ignore").lower():
        return False, "Acepta el EULA oficial editando eula.txt y vuelve a iniciar."
    if folder_size(root) > server["disk_mb"] * 1024 * 1024:
        return False, "El servidor ya supera su límite de almacenamiento. Libera espacio antes de iniciar."
    if not java:
        return False, "Java no está instalado o no aparece en PATH."
    java_args_text = server_setting(server_id, "java_args", "-Xms256M -Xmx{ram}M")
    try:
        java_args = shlex.split(java_args_text.replace("{ram}", str(server["ram_mb"])))
    except ValueError:
        return False, "Los argumentos de Java tienen comillas sin cerrar."
    if len(java_args) > 24 or any(
        not argument.startswith("-") or any(char in argument for char in "\r\n\x00")
        for argument in java_args
    ):
        return False, "Los argumentos de inicio solo pueden contener opciones JVM válidas."
    log_file = (root / "console.log").open("ab")
    try:
        new_process = subprocess.Popen(
            [java, *java_args, "-jar", "server.jar", "nogui"],
            cwd=root,
            stdin=subprocess.PIPE,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError as error:
        log_file.close()
        logging.exception("No se pudo iniciar Java para %s", server_id)
        return False, f"No se pudo iniciar Java: {error}"
    log_file.close()
    with PROCESS_LOCK:
        PROCESSES[server_id] = new_process
    threading.Thread(
        target=monitor_disk_quota,
        args=(server_id, root, new_process, server["disk_mb"]),
        daemon=True,
    ).start()
    return True, "starting"


def stop_server_process(server_id: str) -> str:
    with PROCESS_LOCK:
        process = PROCESSES.get(server_id)
    if not process or process.poll() is not None:
        return "offline"
    if process.stdin:
        process.stdin.write(b"stop\n")
        process.stdin.flush()
    return "stopping"


def official_json(url: str) -> Any:
    request_obj = urllib.request.Request(url, headers={"User-Agent": "NexoryPanel/1.0"})
    with urllib.request.urlopen(request_obj, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError(f"El servidor oficial respondió HTTP {response.status}.")
        return json.loads(response.read(4 * 1024 * 1024).decode("utf-8"))


def official_download(url: str, target: Path) -> None:
    allowed_hosts = {
        "api.purpurmc.org", "fill.papermc.io", "fill-data.papermc.io",
        "piston-data.mojang.com", "cdn.modrinth.com",
    }
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
        raise ValueError("El enlace de descarga no pertenece a un host oficial permitido.")
    target.parent.mkdir(parents=True, exist_ok=True)
    request_obj = urllib.request.Request(url, headers={"User-Agent": "NexoryPanel/1.0"})
    written = 0
    temporary = target.with_suffix(target.suffix + ".download")
    try:
        with urllib.request.urlopen(request_obj, timeout=30) as response, temporary.open("wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_DOWNLOAD_BYTES:
                    raise ValueError("El archivo supera el límite de descarga de 512 MiB.")
                out.write(chunk)
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


@app.errorhandler(413)
def request_too_large(_error):
    return response_error("El archivo supera el límite de subida de 256 MiB.", 413)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/branding/icon")
def branding_icon():
    path = DATA_DIR / "custom_icon.png"
    if not path.is_file():
        path = APP_ROOT / "static" / "icon.png"
    return send_file(path, mimetype="image/png", max_age=0)


@app.get("/api/bootstrap")
def bootstrap():
    session.setdefault("csrf_token", secrets.token_urlsafe(32))
    count = db().execute("SELECT COUNT(*) FROM users").fetchone()[0]
    custom_links = json.loads(setting("custom_links", "[]"))
    return jsonify(
        {
            "csrfToken": session["csrf_token"],
            "setupRequired": count == 0,
            "registrationEnabled": setting("enable_register", "true") == "true",
            "theme": setting("theme", "Purple"),
            "accentColor": setting("accent_color", ""),
            "buttonStyle": setting("button_style", "Gradient"),
            "backgroundStyle": setting("background_style", "Gradient"),
            "backgroundStart": setting("background_start", "#151027"),
            "backgroundEnd": setting("background_end", "#211644"),
            "announcement": setting("announcement", ""),
            "discordUrl": setting("discord_url", ""),
            "customLinks": custom_links,
            "hasCustomIcon": (DATA_DIR / "custom_icon.png").is_file(),
            "nodeName": setting("node_name", "Nexory Windows Node"),
            "user": (
                dict(db().execute(
                    "SELECT id, username, role FROM users WHERE id = ?", (session.get("user_id"),)
                ).fetchone())
                if session.get("user_id")
                and db().execute("SELECT 1 FROM users WHERE id = ?", (session.get("user_id"),)).fetchone()
                else None
            ),
        }
    )


@app.post("/api/register")
def register():
    if not csrf_valid():
        return response_error("Token CSRF inválido. Recarga la página.", 403)
    body = json_body()
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))
    if not re.fullmatch(r"[A-Za-z0-9_]{3,24}", username):
        return response_error("El usuario debe tener 3–24 caracteres: letras, números o _.")
    if len(password) < 10 or len(password) > 256:
        return response_error("La contraseña debe tener entre 10 y 256 caracteres.")
    connection = db()
    try:
        connection.execute("BEGIN IMMEDIATE")
        count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count and setting("enable_register", "true") != "true":
            connection.rollback()
            return response_error("El registro está desactivado.", 403)
        user_id = uuid.uuid4().hex
        role = "admin" if count == 0 else "user"
        connection.execute(
            "INSERT INTO users(id, username, password_hash, role, created_at) VALUES(?, ?, ?, ?, datetime('now'))",
            (user_id, username, generate_password_hash(password), role),
        )
        connection.commit()
    except sqlite3.IntegrityError:
        connection.rollback()
        return response_error("Ese nombre de usuario ya está registrado.", 409)
    session.clear()
    session["user_id"] = user_id
    session["csrf_token"] = secrets.token_urlsafe(32)
    return jsonify({"user": {"id": user_id, "username": username, "role": role}, "csrfToken": session["csrf_token"]})


@app.post("/api/login")
def login():
    if not csrf_valid():
        return response_error("Token CSRF inválido. Recarga la página.", 403)
    body = json_body()
    user = db().execute(
        "SELECT id, username, role, password_hash FROM users WHERE username = ?",
        (str(body.get("username", "")).strip(),),
    ).fetchone()
    if not user or not check_password_hash(user["password_hash"], str(body.get("password", ""))):
        return response_error("Usuario o contraseña incorrectos.", 401)
    session.clear()
    session["user_id"] = user["id"]
    session["csrf_token"] = secrets.token_urlsafe(32)
    return jsonify({"user": {"id": user["id"], "username": user["username"], "role": user["role"]}, "csrfToken": session["csrf_token"]})


@app.post("/api/logout")
@login_required()
def logout():
    session.clear()
    session["csrf_token"] = secrets.token_urlsafe(32)
    return jsonify({"ok": True, "csrfToken": session["csrf_token"]})


@app.get("/api/servers")
@login_required()
def servers():
    if g.user["role"] == "admin":
        rows = db().execute(
            """SELECT s.*, u.username AS owner_name, 'admin' AS access_role FROM servers s
               JOIN users u ON u.id = s.owner_id ORDER BY s.created_at DESC"""
        ).fetchall()
    else:
        rows = db().execute(
            """SELECT s.*, u.username AS owner_name,
                      CASE WHEN s.owner_id = ? THEN 'owner' ELSE 'manager' END AS access_role
               FROM servers s JOIN users u ON u.id = s.owner_id
               WHERE s.owner_id = ? OR EXISTS (
                   SELECT 1 FROM server_members m
                   WHERE m.server_id = s.id AND m.user_id = ?
               ) ORDER BY s.created_at DESC""",
            (g.user["id"], g.user["id"], g.user["id"]),
        ).fetchall()
    result = []
    for row in rows:
        status, cpu, memory = server_status(row["id"])
        result.append({**dict(row), "status": status, "cpu": cpu, "memory": memory,
                       "diskUsed": folder_size(SERVER_DIR / row["id"]) // (1024 * 1024),
                       "description": server_setting(row["id"], "description"),
                       "icon": f"/api/servers/{row['id']}/icon" if (SERVER_DIR / row["id"] / "server-icon.png").is_file() else ""})
    return jsonify(result)


@app.post("/api/servers")
@login_required(admin=True)
def create_server():
    body = json_body()
    name = str(body.get("name", "")).strip()
    software = str(body.get("software", "")).lower()
    version = str(body.get("version", "")).strip()
    build = str(body.get("build", "")).strip()
    owner_id = str(body.get("ownerId", ""))
    try:
        ram = int(body.get("ramMb", 0))
        disk = int(body.get("diskMb", 0))
        port = int(body.get("port", 25565))
    except (TypeError, ValueError):
        return response_error("RAM, almacenamiento y puerto deben ser números.")
    if not name or len(name) > 48:
        return response_error("El nombre debe tener entre 1 y 48 caracteres.")
    if software not in SOFTWARE:
        return response_error("Software no admitido.")
    if not re.fullmatch(r"[A-Za-z0-9._+-]{1,32}", version):
        return response_error("Versión no válida.")
    if build and not re.fullmatch(r"[0-9]{1,9}", build):
        return response_error("Build no válida.")
    if not 512 <= ram <= 131072 or not 1024 <= disk <= 1048576:
        return response_error("RAM (512–131072 MiB) o disco (1024–1048576 MiB) fuera de rango.")
    if not 1024 <= port <= 65535:
        return response_error("El puerto debe estar entre 1024 y 65535.")
    owner = db().execute("SELECT id FROM users WHERE id = ?", (owner_id,)).fetchone()
    if not owner:
        return response_error("El usuario asignado no existe.")
    used_ram, used_disk = used_allocations()
    max_ram = int(setting("max_ram_mb", "8192"))
    max_disk = int(setting("max_disk_mb", "51200"))
    if used_ram + ram > max_ram or used_disk + disk > max_disk:
        return response_error("La asignación supera la capacidad configurada del nodo.", 409)
    if db().execute("SELECT 1 FROM servers WHERE port = ?", (port,)).fetchone():
        return response_error("Ese puerto ya está asignado.", 409)
    server_id = uuid.uuid4().hex[:12]
    db().execute(
        """INSERT INTO servers(id, name, owner_id, software, version, build, ram_mb, disk_mb, port, created_at)
           VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        (server_id, name, owner_id, software, version, build, ram, disk, port),
    )
    db().commit()
    server_root = SERVER_DIR / server_id
    server_root.mkdir(parents=True, exist_ok=False)
    (server_root / "eula.txt").write_text("# Acepta el EULA de Minecraft antes de iniciar.\neula=false\n", encoding="utf-8")
    log_activity(server_id, "server.create", name)
    return jsonify({"id": server_id}), 201


@app.delete("/api/servers/<server_id>")
@login_required(admin=True)
def delete_server(server_id: str):
    row = db().execute("SELECT id FROM servers WHERE id = ?", (server_id,)).fetchone()
    if not row:
        return response_error("Servidor no encontrado.", 404)
    if db().execute("SELECT 1 FROM server_databases WHERE server_id = ? LIMIT 1", (server_id,)).fetchone():
        return response_error("Elimina primero las bases de datos MySQL asociadas desde la pestaña Base de datos.", 409)
    ports = db().execute(
        "SELECT port, protocol, firewall_name, firewall_profile FROM server_ports WHERE server_id = ?",
        (server_id,),
    ).fetchall()
    try:
        for port in ports:
            run_firewall_rule(port["firewall_name"], port["port"], port["protocol"], port["firewall_profile"], remove=True)
    except RuntimeError as error:
        return response_error(f"No se pudo cerrar el puerto {port['port']}: {error}", 503)
    with PROCESS_LOCK:
        process = PROCESSES.pop(server_id, None)
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
    shutil.rmtree(to_server_path(server_id))
    backup_dir = DATA_DIR / "backups" / server_id
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    db().execute("DELETE FROM servers WHERE id = ?", (server_id,))
    db().commit()
    return jsonify({"ok": True})


@app.get("/api/software/<software>/versions")
@login_required()
def software_versions(software: str):
    if software not in SOFTWARE:
        return response_error("Software no admitido.")
    try:
        if software in {"paper", "folia"}:
            data = official_json(f"https://fill.papermc.io/v3/projects/{software}/versions")
            entries = data.get("versions", []) if isinstance(data, dict) else data
            versions = [
                (item.get("version", {}).get("id") if isinstance(item.get("version"), dict)
                 else item.get("version") or item.get("id"))
                for item in entries
                if isinstance(item, dict)
            ]
            versions = [version for version in versions if isinstance(version, str)]
            return jsonify({"versions": versions})
        if software == "purpur":
            data = official_json("https://api.purpurmc.org/v2/purpur")
            return jsonify({"versions": data.get("versions", [])})
        manifest = official_json("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
        return jsonify({"versions": [item["id"] for item in manifest.get("versions", []) if item.get("type") == "release"]})
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        logging.exception("Fallo al consultar versiones de %s", software)
        return response_error(f"No se pudo consultar la API oficial: {error}", 502)


@app.get("/api/software/<software>/versions/<version>/builds")
@login_required()
def software_builds(software: str, version: str):
    if software not in {"paper", "folia", "purpur"}:
        return jsonify({"builds": []})
    if not re.fullmatch(r"[A-Za-z0-9._+-]{1,32}", version):
        return response_error("Versión no válida.")
    try:
        if software == "purpur":
            data = official_json(f"https://api.purpurmc.org/v2/purpur/{urllib.parse.quote(version, safe='')}")
            builds = data.get("builds", {}).get("all", [])
        else:
            data = official_json(f"https://fill.papermc.io/v3/projects/{software}/versions/{urllib.parse.quote(version, safe='')}/builds")
            builds = data.get("builds", []) if isinstance(data, dict) else data
        return jsonify({"builds": builds})
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        logging.exception("Fallo al consultar builds de %s %s", software, version)
        return response_error(f"No se pudieron consultar las builds: {error}", 502)


@app.post("/api/servers/<server_id>/install")
@login_required()
def install_server(server_id: str):
    server = get_server(server_id)
    if not server:
        return response_error("Servidor no encontrado.", 404)
    body = json_body()
    software = str(body.get("software", server["software"])).lower()
    if software not in SOFTWARE:
        return response_error("Software no admitido.")
    version = str(body.get("version", server["version"]))
    build = str(body.get("build", server["build"]))
    root = to_server_path(server_id)
    jar = root / "server.jar"
    try:
        if software == "purpur":
            url = f"https://api.purpurmc.org/v2/purpur/{urllib.parse.quote(version, safe='')}/{urllib.parse.quote(build, safe='')}/download"
        elif software in {"paper", "folia"}:
            if not build:
                return response_error("Selecciona una build antes de instalar.")
            build_data = official_json(
                f"https://fill.papermc.io/v3/projects/{software}/versions/{urllib.parse.quote(version, safe='')}/builds"
            )
            builds = build_data.get("builds", []) if isinstance(build_data, dict) else build_data
            build_data = next(
                (item for item in builds if str(item.get("id", "")) == build),
                None,
            )
            if not build_data:
                return response_error("No se encontró esa build en la API oficial.", 404)
            downloads = build_data.get("downloads", {})
            server_download = downloads.get("server:default") or downloads.get("server")
            if not isinstance(server_download, dict):
                return response_error("La build oficial no contiene un archivo de servidor.")
            url = server_download.get("url") or server_download.get("downloadUrl")
            if not url:
                return response_error("La API oficial no proporcionó un enlace de descarga.")
        else:
            manifest = official_json("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
            entry = next(item for item in manifest["versions"] if item["id"] == version)
            version_data = official_json(entry["url"])
            url = version_data["downloads"]["server"]["url"]
        allowed = {
            "api.purpurmc.org", "fill.papermc.io", "fill-data.papermc.io",
            "piston-data.mojang.com",
        }
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in allowed:
            raise ValueError("El enlace no coincide con los dominios oficiales.")
        official_download(url, jar)
        db().execute(
            "UPDATE servers SET software = ?, version = ?, build = ? WHERE id = ?",
            (software, version, build, server_id),
        )
        db().commit()
        return jsonify({"ok": True, "file": "server.jar"})
    except StopIteration:
        return response_error("No se encontró esa versión oficial de Minecraft.", 404)
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        logging.exception("Fallo al instalar servidor %s", server_id)
        return response_error(f"No se pudo instalar el servidor: {error}", 502)


@app.post("/api/servers/<server_id>/power/<action>")
@login_required()
def server_power(server_id: str, action: str):
    server = get_server(server_id)
    if not server:
        return response_error("Servidor no encontrado.", 404)
    if action == "start":
        succeeded, result = start_server_process(server)
        if not succeeded:
            return response_error(result, 503)
    elif action == "stop":
        result = stop_server_process(server_id)
    else:
        return response_error("Acción no válida.", 404)
    log_activity(server_id, f"server.power.{action}")
    return jsonify({"ok": True, "status": result})


def monitor_disk_quota(server_id: str, root: Path, process: subprocess.Popen[bytes], disk_mb: int) -> None:
    limit = disk_mb * 1024 * 1024
    while process.poll() is None:
        time.sleep(2)
        try:
            if folder_size(root) > limit:
                with (root / "console.log").open("ab") as log:
                    log.write(b"\r\n[NexoryPanel] Limite de almacenamiento superado; se detiene el proceso.\r\n")
                process.terminate()
                logging.warning("Servidor %s detenido por superar la cuota de disco", server_id)
                return
        except OSError:
            logging.exception("No se pudo verificar la cuota del servidor %s", server_id)
            process.terminate()
            return


@app.post("/api/servers/<server_id>/command")
@login_required()
def server_command(server_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    command = str(json_body().get("command", "")).strip()
    if not command or len(command) > 256 or "\n" in command or "\r" in command:
        return response_error("Comando no válido.")
    with PROCESS_LOCK:
        process = PROCESSES.get(server_id)
    if not process or process.poll() is not None or not process.stdin:
        return response_error("El servidor está apagado.", 409)
    process.stdin.write(command.encode("utf-8") + b"\n")
    process.stdin.flush()
    log_activity(server_id, "server.command")
    return jsonify({"ok": True})


@app.get("/api/servers/<server_id>/console")
@login_required()
def server_console(server_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    path = to_server_path(server_id, "console.log")
    if not path.exists():
        return jsonify({"lines": []})
    with path.open("rb") as log:
        log.seek(max(0, path.stat().st_size - 40000))
        text = log.read().decode("utf-8", errors="replace")
    return jsonify({"lines": text.splitlines()[-300:]})


def is_server_owner(server: Any) -> bool:
    return g.user["role"] == "admin" or server["owner_id"] == g.user["id"]


def store_uploaded_icon(uploaded: Any, target: Path) -> None:
    from PIL import Image

    raw = uploaded.stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("El PNG supera el límite de 1 MiB.")
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.format != "PNG" or image.width > 512 or image.height > 512:
                raise ValueError("El icono debe ser PNG y no superar 512×512 píxeles.")
            image.verify()
    except Image.DecompressionBombError as error:
        raise ValueError("El PNG tiene dimensiones excesivas.") from error
    with Image.open(io.BytesIO(raw)) as image:
        target.parent.mkdir(parents=True, exist_ok=True)
        image.convert("RGBA").save(target, format="PNG")


@app.get("/api/servers/<server_id>/activity")
@login_required()
def server_activity(server_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    rows = db().execute(
        """SELECT username, action, detail, created_at FROM server_activity
           WHERE server_id = ? ORDER BY created_at DESC LIMIT 200""",
        (server_id,),
    )
    return jsonify([dict(row) for row in rows])


@app.route("/api/servers/<server_id>/settings", methods=["GET", "PUT"])
@login_required()
def server_settings_api(server_id: str):
    server = get_server(server_id)
    if not server:
        return response_error("Servidor no encontrado.", 404)
    if request.method == "GET":
        return jsonify({
            "name": server["name"],
            "description": server_setting(server_id, "description"),
            "javaArgs": server_setting(server_id, "java_args", "-Xms256M -Xmx{ram}M"),
            "icon": f"/api/servers/{server_id}/icon" if (SERVER_DIR / server_id / "server-icon.png").is_file() else "",
        })
    body = json_body()
    name = str(body.get("name", server["name"])).strip()
    description = str(body.get("description", "")).strip()[:500]
    java_args = str(body.get("javaArgs", server_setting(server_id, "java_args", "-Xms256M -Xmx{ram}M"))).strip()
    if not name or len(name) > 48:
        return response_error("El nombre debe tener entre 1 y 48 caracteres.")
    if len(java_args) > 400 or "\n" in java_args or "\r" in java_args or "\x00" in java_args:
        return response_error("Los argumentos de Java deben ser una sola línea de hasta 400 caracteres.")
    try:
        args = shlex.split(java_args.replace("{ram}", str(server["ram_mb"])), posix=False)
    except ValueError:
        return response_error("Los argumentos de Java tienen comillas sin cerrar.")
    if len(args) > 24 or any(not item.startswith("-") or item in {"-jar", "-cp", "-classpath"} for item in args):
        return response_error("Usa únicamente opciones de JVM; el JAR y su ruta son administrados por NexoryPanel.")
    db().execute("UPDATE servers SET name = ? WHERE id = ?", (name, server_id))
    save_server_settings(server_id, {"description": description, "java_args": java_args})
    log_activity(server_id, "server.settings.update", "Nombre, descripción o argumentos de inicio")
    return jsonify({"ok": True})


@app.get("/api/servers/<server_id>/icon")
@login_required()
def server_icon(server_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    path = SERVER_DIR / server_id / "server-icon.png"
    if not path.is_file():
        return response_error("Este servidor no tiene un icono personalizado.", 404)
    return send_file(path, mimetype="image/png", max_age=0)


@app.post("/api/servers/<server_id>/icon")
@login_required()
def upload_server_icon(server_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    uploaded = request.files.get("icon")
    if not uploaded or not uploaded.filename:
        return response_error("Selecciona una imagen PNG.")
    try:
        store_uploaded_icon(uploaded, SERVER_DIR / server_id / "server-icon.png")
    except (OSError, ValueError) as error:
        return response_error(f"No se pudo guardar el icono: {error}")
    log_activity(server_id, "server.settings.icon")
    return jsonify({"ok": True, "icon": f"/api/servers/{server_id}/icon?t={int(time.time())}"})


@app.get("/api/servers/<server_id>/members")
@login_required()
def server_members(server_id: str):
    server = get_server(server_id)
    if not server:
        return response_error("Servidor no encontrado.", 404)
    rows = db().execute(
        """SELECT u.id, u.username, m.created_at FROM server_members m
           JOIN users u ON u.id = m.user_id WHERE m.server_id = ? ORDER BY u.username""",
        (server_id,),
    )
    return jsonify({
        "members": [dict(row) for row in rows],
        "canManage": is_server_owner(server),
    })


@app.get("/api/servers/<server_id>/members/candidates")
@login_required()
def server_member_candidates(server_id: str):
    server = get_server(server_id)
    if not server:
        return response_error("Servidor no encontrado.", 404)
    if not is_server_owner(server):
        return response_error("Solo el propietario o un administrador puede conceder acceso.", 403)
    rows = db().execute(
        "SELECT id, username FROM users WHERE id != ? ORDER BY username",
        (server["owner_id"],),
    )
    return jsonify([dict(row) for row in rows])


@app.post("/api/servers/<server_id>/members")
@login_required()
def add_server_member(server_id: str):
    server = get_server(server_id)
    if not server:
        return response_error("Servidor no encontrado.", 404)
    if not is_server_owner(server):
        return response_error("Solo el propietario o un administrador puede conceder acceso.", 403)
    user_id = str(json_body().get("userId", ""))
    if user_id == server["owner_id"]:
        return response_error("El propietario ya tiene acceso al servidor.")
    user = db().execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return response_error("La cuenta seleccionada no existe.")
    try:
        db().execute(
            "INSERT INTO server_members(server_id, user_id, created_at) VALUES(?, ?, datetime('now'))",
            (server_id, user_id),
        )
        db().commit()
    except sqlite3.IntegrityError:
        return response_error("Esa cuenta ya tiene acceso al servidor.", 409)
    log_activity(server_id, "server.users.add", user_id)
    return jsonify({"ok": True})


@app.delete("/api/servers/<server_id>/members/<user_id>")
@login_required()
def remove_server_member(server_id: str, user_id: str):
    server = get_server(server_id)
    if not server:
        return response_error("Servidor no encontrado.", 404)
    if not is_server_owner(server):
        return response_error("Solo el propietario o un administrador puede revocar acceso.", 403)
    db().execute("DELETE FROM server_members WHERE server_id = ? AND user_id = ?", (server_id, user_id))
    db().commit()
    log_activity(server_id, "server.users.remove", user_id)
    return jsonify({"ok": True})


@app.get("/api/servers/<server_id>/backups")
@login_required()
def list_server_backups(server_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    rows = db().execute(
        "SELECT id, filename, size_bytes, created_by, created_at FROM server_backups WHERE server_id = ? ORDER BY created_at DESC",
        (server_id,),
    )
    return jsonify([dict(row) for row in rows])


@app.post("/api/servers/<server_id>/backups")
@login_required()
def create_server_backup(server_id: str):
    server = get_server(server_id)
    if not server:
        return response_error("Servidor no encontrado.", 404)
    status, _, _ = server_status(server_id)
    if status != "offline":
        return response_error("Detén el servidor antes de crear un backup consistente.", 409)
    root = to_server_path(server_id)
    backup_dir = DATA_DIR / "backups" / server_id
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_id = uuid.uuid4().hex
    filename = f"{backup_id}.zip"
    target = backup_dir / filename
    temporary = backup_dir / f"{backup_id}.tmp"
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in root.rglob("*"):
                if path.is_symlink() or not path.is_file():
                    continue
                archive.write(path, path.relative_to(root).as_posix())
        temporary.replace(target)
    except (OSError, zipfile.BadZipFile) as error:
        temporary.unlink(missing_ok=True)
        logging.exception("No se pudo respaldar el servidor %s", server_id)
        return response_error(f"No se pudo crear el backup: {error}", 500)
    size = target.stat().st_size
    db().execute(
        """INSERT INTO server_backups(id, server_id, filename, size_bytes, created_by, created_at)
           VALUES(?, ?, ?, ?, ?, datetime('now'))""",
        (backup_id, server_id, filename, size, g.user["username"]),
    )
    db().commit()
    log_activity(server_id, "server.backup.create", filename)
    return jsonify({"id": backup_id, "filename": filename, "sizeBytes": size}), 201


@app.get("/api/servers/<server_id>/backups/<backup_id>")
@login_required()
def download_server_backup(server_id: str, backup_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    row = db().execute(
        "SELECT filename FROM server_backups WHERE id = ? AND server_id = ?",
        (backup_id, server_id),
    ).fetchone()
    if not row:
        return response_error("Backup no encontrado.", 404)
    path = DATA_DIR / "backups" / server_id / row["filename"]
    if not path.is_file():
        return response_error("El archivo de backup no está disponible.", 404)
    return send_file(path, mimetype="application/zip", as_attachment=True, download_name=f"{server_id}-{backup_id}.zip")


@app.delete("/api/servers/<server_id>/backups/<backup_id>")
@login_required()
def delete_server_backup(server_id: str, backup_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    row = db().execute(
        "SELECT filename FROM server_backups WHERE id = ? AND server_id = ?",
        (backup_id, server_id),
    ).fetchone()
    if not row:
        return response_error("Backup no encontrado.", 404)
    (DATA_DIR / "backups" / server_id / row["filename"]).unlink(missing_ok=True)
    db().execute("DELETE FROM server_backups WHERE id = ?", (backup_id,))
    db().commit()
    log_activity(server_id, "server.backup.delete", row["filename"])
    return jsonify({"ok": True})


def run_firewall_rule(rule_name: str, port: int, protocol: str, profile: str, remove: bool = False) -> None:
    if os.name != "nt":
        raise RuntimeError("La administración del Firewall solo está disponible en Windows.")
    verb = "delete" if remove else "add"
    arguments = ["netsh", "advfirewall", "firewall", verb, "rule", f"name={rule_name}"]
    if not remove:
        arguments.extend([
            "dir=in", "action=allow", f"protocol={protocol}",
            f"localport={port}", f"profile={profile}",
        ])
    try:
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"No se pudo modificar Windows Firewall: {error}") from error
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(detail or "Windows rechazó la regla; ejecuta el panel con permisos de administrador.")


@app.get("/api/servers/<server_id>/network")
@login_required()
def list_server_ports(server_id: str):
    server = get_server(server_id)
    if not server:
        return response_error("Servidor no encontrado.", 404)
    rows = db().execute(
        "SELECT id, port, protocol, description, firewall_profile, created_at FROM server_ports WHERE server_id = ? ORDER BY port, protocol",
        (server_id,),
    )
    primary = {
        "id": "primary", "port": server["port"], "protocol": "TCP",
        "description": "Puerto principal de Minecraft", "primary": True,
    }
    return jsonify({"ports": [primary, *[dict(row) for row in rows]], "firewallProfile": setting("firewall_profile", "Any")})


@app.post("/api/servers/<server_id>/network")
@login_required()
def add_server_port(server_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    body = json_body()
    try:
        port = int(body.get("port", 0))
    except (ValueError, TypeError):
        return response_error("El puerto debe ser un número.")
    protocol = str(body.get("protocol", "TCP")).upper()
    description = str(body.get("description", "Puerto adicional")).strip()[:80] or "Puerto adicional"
    if not 1024 <= port <= 65535 or protocol not in {"TCP", "UDP"}:
        return response_error("Usa un puerto entre 1024 y 65535 y protocolo TCP o UDP.")
    collision = db().execute(
        """SELECT 1 FROM servers WHERE port = ? UNION ALL
           SELECT 1 FROM server_ports WHERE port = ? AND protocol = ? LIMIT 1""",
        (port, port, protocol),
    ).fetchone()
    if collision:
        return response_error("Ese puerto ya está asignado.", 409)
    profile = setting("firewall_profile", "Any")
    port_id = uuid.uuid4().hex[:12]
    firewall_name = f"NexoryPanel-{server_id}-{port_id}"
    try:
        run_firewall_rule(firewall_name, port, protocol, profile)
    except RuntimeError as error:
        logging.warning("No se pudo abrir %s/%s en el Firewall: %s", port, protocol, error)
        return response_error(str(error), 503)
    try:
        db().execute(
            """INSERT INTO server_ports(id, server_id, port, protocol, description, firewall_name, firewall_profile, created_at)
               VALUES(?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (port_id, server_id, port, protocol, description, firewall_name, profile),
        )
        db().commit()
    except sqlite3.IntegrityError:
        db().rollback()
        try:
            run_firewall_rule(firewall_name, port, protocol, profile, remove=True)
        except RuntimeError:
            logging.exception("No se pudo revertir una regla de Firewall huérfana %s", firewall_name)
        return response_error("Ese puerto ya está asignado.", 409)
    log_activity(server_id, "server.network.add", f"{port}/{protocol} ({profile})")
    return jsonify({"ok": True, "id": port_id, "firewallProfile": profile}), 201


@app.delete("/api/servers/<server_id>/network/<port_id>")
@login_required()
def delete_server_port(server_id: str, port_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    row = db().execute(
        "SELECT port, protocol, firewall_name, firewall_profile FROM server_ports WHERE id = ? AND server_id = ?",
        (port_id, server_id),
    ).fetchone()
    if not row:
        return response_error("Asignación no encontrada.", 404)
    try:
        run_firewall_rule(row["firewall_name"], row["port"], row["protocol"], row["firewall_profile"], remove=True)
    except RuntimeError as error:
        logging.warning("No se pudo cerrar %s/%s en el Firewall: %s", row["port"], row["protocol"], error)
        return response_error(str(error), 503)
    db().execute("DELETE FROM server_ports WHERE id = ?", (port_id,))
    db().commit()
    log_activity(server_id, "server.network.remove", f"{row['port']}/{row['protocol']}")
    return jsonify({"ok": True})


def mysql_binary() -> Path | None:
    found = shutil.which("mysql")
    candidates = [Path(found)] if found else []
    for root in (Path(os.environ.get("ProgramFiles", r"C:\Program Files")), Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))):
        candidates.extend(root.glob("MySQL/MySQL Server */bin/mysql.exe"))
    return next((candidate for candidate in candidates if candidate.is_file()), None)


@app.get("/api/servers/<server_id>/databases")
@login_required()
def list_server_databases(server_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    rows = db().execute(
        "SELECT id, database_name, username, created_at FROM server_databases WHERE server_id = ? ORDER BY created_at DESC",
        (server_id,),
    )
    return jsonify({"available": mysql_binary() is not None, "databases": [dict(row) for row in rows]})


@app.post("/api/servers/<server_id>/databases")
@login_required()
def create_server_database(server_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    if not mysql_binary():
        return response_error("MySQL Server no está instalado. Un administrador puede instalarlo desde Administración.", 503)
    body = json_body()
    root_user = str(body.get("adminUser", "root")).strip()
    root_password = str(body.get("adminPassword", ""))
    label = str(body.get("name", "plugin")).strip().lower()
    slug = re.sub(r"[^a-z0-9_]+", "_", label).strip("_")[:20] or "plugin"
    if not re.fullmatch(r"[A-Za-z0-9_]{1,32}", root_user) or not root_password:
        return response_error("Introduce el usuario y la contraseña de MySQL.")
    database_name = f"nexory_{server_id[:8]}_{slug}_{secrets.token_hex(3)}"
    username = f"nx_{secrets.token_hex(6)}"
    password = secrets.token_urlsafe(24)
    database_id = uuid.uuid4().hex
    try:
        import pymysql
    except ImportError:
        return response_error("El controlador MySQL no está instalado. Actualiza NexoryPanel.", 503)
    try:
        connection = pymysql.connect(
            host="127.0.0.1", port=3306, user=root_user, password=root_password,
            connect_timeout=5, charset="utf8mb4", autocommit=False,
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                cursor.execute(f"CREATE USER '{username}'@'localhost' IDENTIFIED BY %s", (password,))
                cursor.execute(f"GRANT ALL PRIVILEGES ON `{database_name}`.* TO '{username}'@'localhost'")
            connection.commit()
        finally:
            connection.close()
    except pymysql.MySQLError as error:
        logging.warning("No se pudo crear una base MySQL para %s: %s", server_id, error)
        return response_error("MySQL rechazó la conexión o la creación. Comprueba el servicio y las credenciales.", 502)
    db().execute(
        """INSERT INTO server_databases(id, server_id, database_name, username, password_hash, created_at)
           VALUES(?, ?, ?, ?, ?, datetime('now'))""",
        (database_id, server_id, database_name, username, generate_password_hash(password)),
    )
    db().commit()
    log_activity(server_id, "server.database.create", database_name)
    return jsonify({
        "id": database_id, "database": database_name, "username": username,
        "password": password, "host": "127.0.0.1", "port": 3306,
    }), 201


@app.delete("/api/servers/<server_id>/databases/<database_id>")
@login_required()
def delete_server_database(server_id: str, database_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    if not mysql_binary():
        return response_error("MySQL Server no está disponible.", 503)
    body = json_body()
    root_user = str(body.get("adminUser", "root")).strip()
    root_password = str(body.get("adminPassword", ""))
    row = db().execute(
        "SELECT database_name, username FROM server_databases WHERE id = ? AND server_id = ?",
        (database_id, server_id),
    ).fetchone()
    if not row:
        return response_error("Base de datos no encontrada.", 404)
    try:
        import pymysql
    except ImportError:
        return response_error("El controlador MySQL no está instalado. Actualiza NexoryPanel.", 503)
    try:
        connection = pymysql.connect(host="127.0.0.1", port=3306, user=root_user, password=root_password, connect_timeout=5, autocommit=True)
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"DROP DATABASE `{row['database_name']}`")
                cursor.execute(f"DROP USER '{row['username']}'@'localhost'")
        finally:
            connection.close()
    except pymysql.MySQLError as error:
        logging.warning("No se pudo eliminar una base MySQL de %s: %s", server_id, error)
        return response_error("No se pudo eliminar; comprueba el servicio y las credenciales de administrador MySQL.", 502)
    db().execute("DELETE FROM server_databases WHERE id = ?", (database_id,))
    db().commit()
    log_activity(server_id, "server.database.delete", row["database_name"])
    return jsonify({"ok": True})


MYSQL_INSTALL_PROCESS: subprocess.Popen[bytes] | None = None


@app.get("/api/admin/database/status")
@login_required(admin=True)
def mysql_install_status():
    binary = mysql_binary()
    process = MYSQL_INSTALL_PROCESS
    return jsonify({
        "installed": binary is not None,
        "binary": str(binary) if binary else "",
        "installRunning": bool(process and process.poll() is None),
        "installExitCode": process.returncode if process and process.poll() is not None else None,
    })


@app.post("/api/admin/database/install")
@login_required(admin=True)
def install_mysql_server():
    global MYSQL_INSTALL_PROCESS
    if mysql_binary():
        return jsonify({"ok": True, "installed": True})
    if MYSQL_INSTALL_PROCESS and MYSQL_INSTALL_PROCESS.poll() is None:
        return response_error("La instalación de MySQL ya está en curso.", 409)
    winget = shutil.which("winget")
    if not winget:
        return response_error("winget no está disponible. Instala MySQL Server 8.4 desde la página oficial de MySQL.", 503)
    arguments = [
        winget, "install", "--id", "Oracle.MySQL", "--exact",
        "--interactive", "--accept-source-agreements",
    ]
    try:
        MYSQL_INSTALL_PROCESS = subprocess.Popen(
            arguments,
            cwd=DATA_DIR,
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        )
    except OSError as error:
        logging.exception("No se pudo iniciar winget para MySQL")
        return response_error(f"No se pudo iniciar la instalación de MySQL: {error}", 500)
    logging.info("Administrador %s inició el instalador interactivo Oracle.MySQL.", g.user["username"])
    return jsonify({"ok": True, "started": True}), 202


@app.get("/api/servers/<server_id>/schedules")
@login_required()
def list_server_schedules(server_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    rows = db().execute(
        """SELECT id, name, action, command, interval_minutes, next_run_at, enabled, created_at
           FROM server_schedules WHERE server_id = ? ORDER BY created_at DESC""",
        (server_id,),
    )
    return jsonify([dict(row) for row in rows])


@app.post("/api/servers/<server_id>/schedules")
@login_required()
def create_server_schedule(server_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    body = json_body()
    name = str(body.get("name", "")).strip()[:60]
    action = str(body.get("action", ""))
    command = str(body.get("command", "")).strip()
    try:
        interval = int(body.get("intervalMinutes", 60))
    except (TypeError, ValueError):
        return response_error("El intervalo debe ser un número.")
    if not name or action not in {"start", "stop", "restart", "command"} or not 1 <= interval <= 525600:
        return response_error("Revisa el nombre, la acción y el intervalo (1–525600 minutos).")
    if action == "command" and (not command or len(command) > 256 or "\n" in command or "\r" in command):
        return response_error("El comando debe tener entre 1 y 256 caracteres en una línea.")
    if action != "command":
        command = ""
    schedule_id = uuid.uuid4().hex
    next_run = int(time.time()) + interval * 60
    db().execute(
        """INSERT INTO server_schedules(id, server_id, name, action, command, interval_minutes, next_run_at, created_at)
           VALUES(?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        (schedule_id, server_id, name, action, command, interval, next_run),
    )
    db().commit()
    log_activity(server_id, "server.schedule.create", name)
    return jsonify({"ok": True, "id": schedule_id, "nextRunAt": next_run}), 201


@app.delete("/api/servers/<server_id>/schedules/<schedule_id>")
@login_required()
def delete_server_schedule(server_id: str, schedule_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    db().execute("DELETE FROM server_schedules WHERE id = ? AND server_id = ?", (schedule_id, server_id))
    db().commit()
    log_activity(server_id, "server.schedule.delete", schedule_id)
    return jsonify({"ok": True})


def schedule_worker() -> None:
    while True:
        try:
            with app.app_context():
                now = int(time.time())
                due = db().execute(
                    """SELECT sc.*, s.name AS server_name, s.ram_mb, s.disk_mb
                       FROM server_schedules sc JOIN servers s ON s.id = sc.server_id
                       WHERE sc.enabled = 1 AND sc.next_run_at <= ?""",
                    (now,),
                ).fetchall()
                for schedule in due:
                    db().execute(
                        "UPDATE server_schedules SET next_run_at = ? WHERE id = ? AND next_run_at <= ?",
                        (now + schedule["interval_minutes"] * 60, schedule["id"], now),
                    )
                    db().commit()
                    try:
                        execute_schedule(schedule)
                    except (OSError, RuntimeError, ValueError):
                        logging.exception("No se pudo ejecutar el schedule %s", schedule["id"])
        except sqlite3.Error:
            logging.exception("No se pudo comprobar la cola de schedules")
        time.sleep(5)


def execute_schedule(schedule: Any) -> None:
    server_id = schedule["server_id"]
    if schedule["action"] == "start":
        server = db().execute("SELECT * FROM servers WHERE id = ?", (server_id,)).fetchone()
        if server:
            success, result = start_server_process(server)
            if not success:
                raise RuntimeError(result)
    elif schedule["action"] == "stop":
        stop_server_process(server_id)
    elif schedule["action"] == "command":
        with PROCESS_LOCK:
            process = PROCESSES.get(server_id)
        if not process or process.poll() is not None or not process.stdin:
            raise RuntimeError("No se puede enviar el comando: el servidor está apagado.")
        process.stdin.write(schedule["command"].encode("utf-8") + b"\n")
        process.stdin.flush()
    elif schedule["action"] == "restart":
        process = threading.Thread(target=scheduled_restart, args=(server_id,), daemon=True)
        process.start()
    db().execute(
        """INSERT INTO server_activity(id, server_id, username, action, detail, created_at)
           VALUES(?, ?, 'Nexory Scheduler', ?, ?, datetime('now'))""",
        (uuid.uuid4().hex, server_id, f"server.schedule.{schedule['action']}", schedule["name"]),
    )
    db().commit()


def scheduled_restart(server_id: str) -> None:
    stop_server_process(server_id)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        status, _, _ = server_status(server_id)
        if status == "offline":
            with app.app_context():
                server = db().execute("SELECT * FROM servers WHERE id = ?", (server_id,)).fetchone()
                if server:
                    started, message = start_server_process(server)
                    if not started:
                        logging.error("No se pudo completar el reinicio programado: %s", message)
            return
        time.sleep(1)
    logging.error("El servidor %s no se apagó para el reinicio programado.", server_id)


@app.get("/api/servers/<server_id>/files")
@login_required()
def list_files(server_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    relative = request.args.get("path", "")
    try:
        folder = to_server_path(server_id, relative)
        if not folder.is_dir():
            return response_error("La carpeta no existe.", 404)
        entries = []
        for item in sorted(folder.iterdir(), key=lambda entry: (not entry.is_dir(), entry.name.lower())):
            if item.is_symlink() or not item.resolve().is_relative_to((SERVER_DIR / server_id).resolve()):
                continue
            entries.append({"name": item.name, "directory": item.is_dir(),
                            "size": item.stat().st_size if item.is_file() else 0})
        return jsonify({"path": relative, "entries": entries,
                        "usedMb": folder_size(SERVER_DIR / server_id) // (1024 * 1024),
                        "limitMb": get_server(server_id)["disk_mb"]})
    except ValueError as error:
        return response_error(str(error), 403)


@app.post("/api/servers/<server_id>/files/folder")
@login_required()
def create_folder(server_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    body = json_body()
    name = str(body.get("name", ""))
    try:
        folder = to_server_path(server_id, body.get("path", ""))
        if not re.fullmatch(r"[^<>:\"/\\|?*\x00-\x1f]{1,100}", name) or name in {".", ".."}:
            return response_error("Nombre de carpeta no válido.")
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).mkdir(exist_ok=False)
        log_activity(server_id, "server.file.mkdir", str(Path(body.get("path", "")) / name))
        return jsonify({"ok": True})
    except FileExistsError:
        return response_error("Ya existe una carpeta con ese nombre.", 409)
    except (OSError, ValueError) as error:
        return response_error(str(error), 400)


@app.post("/api/servers/<server_id>/files/file")
@login_required()
def create_file(server_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    body = json_body()
    name = str(body.get("name", ""))
    content = str(body.get("content", ""))
    try:
        folder = to_server_path(server_id, body.get("path", ""))
        target = to_server_path(server_id, str(Path(body.get("path", "")) / name))
        if not re.fullmatch(r"[^<>:\"/\\|?*\x00-\x1f]{1,100}", name) or name in {".", ".."}:
            return response_error("Nombre de archivo no válido.")
        if len(content.encode("utf-8")) > MAX_EDIT_BYTES:
            return response_error("El editor admite archivos de hasta 2 MiB.")
        folder.mkdir(parents=True, exist_ok=True)
        if target.exists():
            return response_error("El archivo ya existe.", 409)
        if folder_size(to_server_path(server_id)) + len(content.encode("utf-8")) > get_server(server_id)["disk_mb"] * 1024 * 1024:
            return response_error("La operación supera el almacenamiento asignado.", 413)
        target.write_text(content, encoding="utf-8")
        log_activity(server_id, "server.file.create", str(target.relative_to(to_server_path(server_id))))
        return jsonify({"ok": True})
    except (OSError, ValueError) as error:
        return response_error(str(error), 400)


@app.get("/api/servers/<server_id>/files/content")
@login_required()
def file_content(server_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    try:
        target = to_server_path(server_id, request.args.get("path", ""))
        if not target.is_file() or target.stat().st_size > MAX_EDIT_BYTES:
            return response_error("Archivo no encontrado o supera el límite del editor de 2 MiB.", 413)
        return jsonify({"content": target.read_text(encoding="utf-8")})
    except (OSError, UnicodeError, ValueError) as error:
        return response_error(f"No se pudo leer el archivo de texto: {error}", 400)


@app.put("/api/servers/<server_id>/files/content")
@login_required()
def save_file(server_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    body = json_body()
    content = str(body.get("content", ""))
    try:
        target = to_server_path(server_id, body.get("path", ""))
        if not target.is_file():
            return response_error("El archivo no existe.", 404)
        if len(content.encode("utf-8")) > MAX_EDIT_BYTES:
            return response_error("El editor admite archivos de hasta 2 MiB.", 413)
        current_size = target.stat().st_size
        if folder_size(to_server_path(server_id)) - current_size + len(content.encode("utf-8")) > get_server(server_id)["disk_mb"] * 1024 * 1024:
            return response_error("El archivo superaría el almacenamiento asignado.", 413)
        target.write_text(content, encoding="utf-8")
        log_activity(server_id, "server.file.write", str(body.get("path", "")))
        return jsonify({"ok": True})
    except (OSError, ValueError) as error:
        return response_error(str(error), 400)


@app.post("/api/servers/<server_id>/files/rename")
@login_required()
def rename_file(server_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    body = json_body()
    relative = str(body.get("path", ""))
    new_name = str(body.get("newName", "")).strip()
    if not re.fullmatch(r"[^<>:\"/\\|?*\x00-\x1f]{1,100}", new_name) or new_name in {".", ".."}:
        return response_error("Nombre no válido.")
    try:
        source = to_server_path(server_id, relative)
        if source == to_server_path(server_id) or not source.exists():
            return response_error("No se encontró el archivo o carpeta.", 404)
        if source.is_symlink():
            return response_error("No se permiten enlaces simbólicos.")
        target = to_server_path(server_id, str(Path(relative).parent / new_name))
        if target.exists():
            return response_error("Ya existe un elemento con ese nombre.", 409)
        source.rename(target)
        log_activity(server_id, "server.file.rename", f"{relative} -> {new_name}")
        return jsonify({"ok": True, "name": new_name})
    except (OSError, ValueError) as error:
        return response_error(str(error), 400)


@app.delete("/api/servers/<server_id>/files")
@login_required()
def delete_file(server_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    try:
        target = to_server_path(server_id, request.args.get("path", ""))
        if target == to_server_path(server_id):
            return response_error("No se puede eliminar la raíz del servidor.", 400)
        if target.is_dir():
            shutil.rmtree(target)
        elif target.is_file():
            target.unlink()
        else:
            return response_error("El archivo no existe.", 404)
        log_activity(server_id, "server.file.delete", request.args.get("path", ""))
        return jsonify({"ok": True})
    except (OSError, ValueError) as error:
        return response_error(str(error), 400)


@app.post("/api/servers/<server_id>/files/upload")
@login_required()
def upload_files(server_id: str):
    server = get_server(server_id)
    if not server:
        return response_error("Servidor no encontrado.", 404)
    files = request.files.getlist("files")
    if not files:
        return response_error("Selecciona al menos un archivo.")
    try:
        destination = to_server_path(server_id, request.form.get("path", ""))
        destination.mkdir(parents=True, exist_ok=True)
        root = to_server_path(server_id)
        current = folder_size(root)
        total = 0
        for file in files:
            position = file.stream.tell()
            file.stream.seek(0, os.SEEK_END)
            total += file.stream.tell()
            file.stream.seek(position)
        if current + total > server["disk_mb"] * 1024 * 1024:
            return response_error("La subida supera el límite de almacenamiento del servidor.", 413)
        for file in files:
            relative = file.filename or ""
            if "\x00" in relative or Path(relative).is_absolute():
                return response_error("Nombre de archivo no válido.")
            parts = [secure_filename(part) for part in relative.replace("\\", "/").split("/") if part not in {"", ".", ".."}]
            if not parts:
                continue
            target = to_server_path(server_id, str(Path(request.form.get("path", "")) / Path(*parts)))
            target.parent.mkdir(parents=True, exist_ok=True)
            file.save(target)
        log_activity(server_id, "server.file.upload", f"{len(files)} archivo(s)")
        return jsonify({"ok": True})
    except (OSError, ValueError) as error:
        return response_error(str(error), 400)


@app.post("/api/servers/<server_id>/files/archive")
@login_required()
def archive_files(server_id: str):
    if not get_server(server_id):
        return response_error("Servidor no encontrado.", 404)
    body = json_body()
    action = body.get("action")
    try:
        source = to_server_path(server_id, body.get("path", ""))
        root = to_server_path(server_id)
        if action == "zip":
            if not source.exists() or source == root:
                return response_error("Selecciona un archivo o carpeta para comprimir.")
            target = source.with_suffix(source.suffix + ".zip") if source.is_file() else source.parent / f"{source.name}.zip"
            if target.exists():
                return response_error("Ya existe el archivo ZIP de destino.", 409)
            with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
                if source.is_file():
                    archive.write(source, source.name)
                else:
                    for child in source.rglob("*"):
                        if child.is_file() and not child.is_symlink():
                            archive.write(child, child.relative_to(source.parent))
            if folder_size(root) > get_server(server_id)["disk_mb"] * 1024 * 1024:
                target.unlink(missing_ok=True)
                return response_error("La compresión superaría el límite de almacenamiento.", 413)
            log_activity(server_id, "server.file.archive", str(source.relative_to(root)))
        elif action == "unzip":
            if not source.is_file() or source.suffix.lower() != ".zip":
                return response_error("Selecciona un archivo .zip.")
            with zipfile.ZipFile(source) as archive:
                total_uncompressed = 0
                for item in archive.infolist():
                    total_uncompressed += item.file_size
                    if total_uncompressed > get_server(server_id)["disk_mb"] * 1024 * 1024:
                        return response_error("El ZIP supera la cuota de almacenamiento al descomprimir.", 413)
                    mode = item.external_attr >> 16
                    if (mode & 0o170000) == 0o120000:
                        return response_error("El ZIP contiene enlaces simbólicos y no se puede extraer.", 400)
                    candidate = (source.parent / item.filename).resolve()
                    if not candidate.is_relative_to(root):
                        return response_error("El ZIP intenta extraer archivos fuera del servidor.", 400)
                if folder_size(root) + total_uncompressed > get_server(server_id)["disk_mb"] * 1024 * 1024:
                    return response_error("La extracción superaría el límite de almacenamiento.", 413)
                archive.extractall(source.parent)
                log_activity(server_id, "server.file.extract", str(source.relative_to(root)))
        else:
            return response_error("Acción de archivo no válida.")
        return jsonify({"ok": True})
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        return response_error(str(error), 400)


@app.get("/api/admin/overview")
@login_required(admin=True)
def admin_overview():
    users = [dict(row) for row in db().execute("SELECT id, username, role, created_at FROM users ORDER BY created_at")]
    ram, disk = used_allocations()
    keys = [dict(row) for row in db().execute("SELECT id, label, created_at FROM api_keys ORDER BY created_at DESC")]
    return jsonify({
        "users": users,
        "servers": [dict(row) for row in db().execute(
            "SELECT s.id, s.name, s.software, s.version, s.ram_mb, s.disk_mb, u.username AS owner_name FROM servers s JOIN users u ON u.id = s.owner_id"
        )],
        "settings": {
            "enableRegister": setting("enable_register", "true") == "true",
            "theme": setting("theme", "Purple"),
            "accentColor": setting("accent_color", ""),
            "buttonStyle": setting("button_style", "Gradient"),
            "backgroundStyle": setting("background_style", "Gradient"),
            "backgroundStart": setting("background_start", "#151027"),
            "backgroundEnd": setting("background_end", "#211644"),
            "maxRamMb": int(setting("max_ram_mb", "8192")),
            "maxDiskMb": int(setting("max_disk_mb", "51200")),
            "nodeName": setting("node_name", "Nexory Windows Node"),
            "apiKeyEnabled": setting("api_key_enabled", "false") == "true",
            "announcement": setting("announcement", ""),
            "discordUrl": setting("discord_url", ""),
            "customLinks": json.loads(setting("custom_links", "[]")),
            "hasCustomIcon": (DATA_DIR / "custom_icon.png").is_file(),
            "firewallProfile": setting("firewall_profile", "Any"),
        },
        "allocation": {"ramMb": ram, "diskMb": disk},
        "apiKeys": keys,
        "themes": sorted(THEMES),
    })


@app.put("/api/admin/settings")
@login_required(admin=True)
def update_settings():
    body = json_body()
    try:
        max_ram = int(body.get("maxRamMb", setting("max_ram_mb", "8192")))
        max_disk = int(body.get("maxDiskMb", setting("max_disk_mb", "51200")))
    except (TypeError, ValueError):
        return response_error("Los límites de recursos deben ser números.")
    if not 512 <= max_ram <= 1048576 or not 1024 <= max_disk <= 10485760:
        return response_error("Límites fuera de rango (RAM 512–1048576 MiB, disco 1024–10485760 MiB).")
    ram, disk = used_allocations()
    if max_ram < ram or max_disk < disk:
        return response_error("No puedes fijar un límite inferior a las asignaciones actuales.", 409)
    theme = str(body.get("theme", setting("theme", "Purple")))
    if theme not in THEMES:
        return response_error("Tema no válido.")
    accent_color = str(body.get("accentColor", setting("accent_color", ""))).strip().lower()
    if accent_color and not re.fullmatch(r"#[0-9a-f]{6}", accent_color):
        return response_error("El color personalizado debe ser hexadecimal #RRGGBB.")
    button_style = str(body.get("buttonStyle", setting("button_style", "Gradient")))
    if button_style not in {"Gradient", "Solid", "Outline", "Glass", "Glassed"}:
        return response_error("Estilo de botones no válido.")
    background_style = str(body.get("backgroundStyle", setting("background_style", "Gradient")))
    if background_style not in {"Gradient", "Glassed", "Solid"}:
        return response_error("Estilo de fondo no válido.")
    background_start = str(body.get("backgroundStart", setting("background_start", "#151027"))).lower()
    background_end = str(body.get("backgroundEnd", setting("background_end", "#211644"))).lower()
    if not re.fullmatch(r"#[0-9a-f]{6}", background_start) or not re.fullmatch(r"#[0-9a-f]{6}", background_end):
        return response_error("Los colores del fondo deben usar el formato #RRGGBB.")
    announcement = str(body.get("announcement", setting("announcement", ""))).strip()[:300]
    discord_url = str(body.get("discordUrl", setting("discord_url", ""))).strip()
    firewall_profile = str(body.get("firewallProfile", setting("firewall_profile", "Any")))
    if firewall_profile not in {"Any", "Private", "Domain", "Public"}:
        return response_error("Perfil de Firewall no válido.")
    custom_links = body.get("customLinks", json.loads(setting("custom_links", "[]")))
    if not isinstance(custom_links, list) or len(custom_links) > 8:
        return response_error("Puedes configurar hasta 8 enlaces personalizados.")
    validated_links = []
    for link in custom_links:
        if not isinstance(link, dict):
            return response_error("Formato de enlace personalizado no válido.")
        label = str(link.get("label", "")).strip()[:32]
        url = str(link.get("url", "")).strip()
        parsed_url = urllib.parse.urlparse(url)
        if not label or parsed_url.scheme != "https" or not parsed_url.hostname or parsed_url.username or parsed_url.password:
            return response_error("Cada enlace personalizado debe tener etiqueta y una URL HTTPS válida.")
        validated_links.append({"label": label, "url": url[:500]})
    if discord_url:
        parsed_discord = urllib.parse.urlparse(discord_url)
        if parsed_discord.scheme != "https" or not parsed_discord.hostname:
            return response_error("La URL de Discord debe comenzar por https://.")
    enable_register = bool(body.get("enableRegister", True))
    api_enabled = bool(body.get("apiKeyEnabled", False))
    node_name = str(body.get("nodeName", "Nexory Windows Node")).strip()[:60] or "Nexory Windows Node"
    values = {
        "max_ram_mb": str(max_ram), "max_disk_mb": str(max_disk), "theme": theme,
        "enable_register": str(enable_register).lower(), "api_key_enabled": str(api_enabled).lower(),
        "node_name": node_name, "accent_color": accent_color, "button_style": button_style,
        "background_style": background_style, "background_start": background_start,
        "background_end": background_end, "announcement": announcement,
        "discord_url": discord_url, "custom_links": json.dumps(validated_links),
        "firewall_profile": firewall_profile,
    }
    db().executemany("INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", values.items())
    db().commit()
    return jsonify({"ok": True})


@app.post("/api/admin/branding/icon")
@login_required(admin=True)
def upload_branding_icon():
    uploaded = request.files.get("icon")
    if not uploaded or not uploaded.filename:
        return response_error("Selecciona una imagen PNG.")
    try:
        store_uploaded_icon(uploaded, DATA_DIR / "custom_icon.png")
    except (OSError, ValueError) as error:
        return response_error(f"No se pudo guardar el icono: {error}")
    return jsonify({"ok": True, "icon": f"/api/branding/icon?t={int(time.time())}"})


@app.delete("/api/admin/branding/icon")
@login_required(admin=True)
def reset_branding_icon():
    (DATA_DIR / "custom_icon.png").unlink(missing_ok=True)
    return jsonify({"ok": True})


@app.post("/api/admin/api-keys")
@login_required(admin=True)
def create_api_key():
    label = str(json_body().get("label", "Dashboard")).strip()[:50] or "Dashboard"
    key = "nex_" + secrets.token_urlsafe(36)
    db().execute(
        "INSERT INTO api_keys(id, label, key_hash, created_at) VALUES(?, ?, ?, datetime('now'))",
        (uuid.uuid4().hex, label, hashlib.sha256(key.encode("utf-8")).hexdigest()),
    )
    db().commit()
    return jsonify({"key": key})


@app.delete("/api/admin/api-keys/<key_id>")
@login_required(admin=True)
def delete_api_key(key_id: str):
    db().execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
    db().commit()
    return jsonify({"ok": True})


@app.get("/api/dashboard")
@api_key_required
def dashboard_api():
    rows = db().execute(
        """SELECT s.id, s.name, s.software, s.version, s.port, s.ram_mb, s.disk_mb,
                  u.username AS owner FROM servers s JOIN users u ON u.id = s.owner_id"""
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/users")
@login_required()
def user_list():
    if g.user["role"] != "admin":
        return jsonify([{"id": g.user["id"], "username": g.user["username"]}])
    return jsonify([dict(row) for row in db().execute("SELECT id, username FROM users ORDER BY username")])


@app.get("/api/plugins/search")
@login_required()
def search_plugins():
    query = request.args.get("q", "").strip()[:100]
    if not query:
        return jsonify({"hits": []})
    facets = json.dumps([["project_type:plugin"]], separators=(",", ":"))
    url = "https://api.modrinth.com/v2/search?" + urllib.parse.urlencode({"query": query, "facets": facets, "limit": 12})
    try:
        data = official_json(url)
        return jsonify({"hits": data.get("hits", [])})
    except (OSError, ValueError, RuntimeError) as error:
        logging.exception("Fallo al buscar plugins en Modrinth")
        return response_error(f"No se pudo consultar Modrinth: {error}", 502)


@app.get("/api/plugins/<project_id>/versions")
@login_required()
def plugin_versions(project_id: str):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", project_id):
        return response_error("ID de plugin no válido.")
    game_version = request.args.get("gameVersion", "")
    loaders = json.dumps(["paper", "purpur", "folia", "spigot"])
    url = f"https://api.modrinth.com/v2/project/{project_id}/version?" + urllib.parse.urlencode({"loaders": loaders})
    try:
        versions = official_json(url)
        if game_version:
            versions = [item for item in versions if game_version in item.get("game_versions", [])]
        return jsonify({"versions": versions[:30]})
    except (OSError, ValueError, RuntimeError) as error:
        logging.exception("Fallo al consultar versiones de plugin")
        return response_error(f"No se pudieron consultar las versiones: {error}", 502)


@app.post("/api/servers/<server_id>/plugins/install")
@login_required()
def install_plugin(server_id: str):
    server = get_server(server_id)
    if not server:
        return response_error("Servidor no encontrado.", 404)
    if server["software"] == "vanilla":
        return response_error("Los plugins requieren Paper, Purpur o Folia.")
    body = json_body()
    url = str(body.get("url", ""))
    file_name = secure_filename(str(body.get("fileName", "")))
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "cdn.modrinth.com" or not file_name.lower().endswith(".jar"):
        return response_error("Archivo de plugin no válido.")
    target = to_server_path(server_id, str(Path("plugins") / file_name))
    try:
        target.parent.mkdir(exist_ok=True)
        official_download(url, target)
        if folder_size(to_server_path(server_id)) > server["disk_mb"] * 1024 * 1024:
            target.unlink(missing_ok=True)
            return response_error("El plugin supera el almacenamiento asignado.", 413)
        return jsonify({"ok": True, "file": file_name})
    except (OSError, ValueError) as error:
        logging.exception("Fallo al instalar plugin")
        return response_error(f"No se pudo instalar el plugin: {error}", 502)


@app.post("/api/plugin-projects/template")
@login_required()
def plugin_template():
    body = json_body()
    name = str(body.get("name", "")).strip()
    package_name = str(body.get("package", "")).strip()
    main_class = str(body.get("mainClass", "Main")).strip()
    mc_version = str(body.get("minecraftVersion", "1.21.8")).strip()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9 _-]{1,39}", name):
        return response_error("El nombre admite 2–40 letras, números, espacios, guiones o _.")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*", package_name):
        return response_error("El paquete Java debe tener formato válido, por ejemplo com.ejemplo.miplugin.")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,40}", main_class):
        return response_error("El nombre de clase Java no es válido.")
    if not re.fullmatch(r"\d{1,2}\.\d{1,2}(?:\.\d{1,2})?", mc_version):
        return response_error("La versión de Minecraft debe tener formato 1.21 o 1.21.8.")

    artifact = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "plugin"
    api_version = ".".join(mc_version.split(".")[:2])
    java_path = Path(*package_name.split(".")) / f"{main_class}.java"
    source = f"""package {package_name};

import org.bukkit.plugin.java.JavaPlugin;

public final class {main_class} extends JavaPlugin {{
    @Override
    public void onEnable() {{
        getLogger().info("{name} enabled.");
    }}

    @Override
    public void onDisable() {{
        getLogger().info("{name} disabled.");
    }}
}}
"""
    plugin_yml = f"""name: {name}
version: 0.1.0
main: {package_name}.{main_class}
api-version: '{api_version}'
description: A starter plugin for Minecraft {mc_version}
"""
    pom = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>{package_name}</groupId>
  <artifactId>{artifact}</artifactId>
  <version>0.1.0-SNAPSHOT</version>
  <properties>
    <maven.compiler.release>21</maven.compiler.release>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
  </properties>
  <repositories>
    <repository><id>spigotmc-repo</id><url>https://hub.spigotmc.org/nexus/content/repositories/snapshots/</url></repository>
  </repositories>
  <dependencies>
    <dependency>
      <groupId>org.spigotmc</groupId><artifactId>spigot-api</artifactId>
      <version>{mc_version}-R0.1-SNAPSHOT</version><scope>provided</scope>
    </dependency>
  </dependencies>
  <build>
    <finalName>{artifact}</finalName>
    <resources><resource><directory>src/main/resources</directory><filtering>true</filtering></resource></resources>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId><artifactId>maven-compiler-plugin</artifactId><version>3.13.0</version>
      </plugin>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId><artifactId>maven-jar-plugin</artifactId><version>3.4.2</version>
      </plugin>
    </plugins>
  </build>
</project>
"""
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        output.writestr(f"{artifact}/pom.xml", pom)
        output.writestr(f"{artifact}/src/main/resources/plugin.yml", plugin_yml)
        output.writestr(f"{artifact}/src/main/java/{java_path.as_posix()}", source)
        output.writestr(
            f"{artifact}/README.txt",
            "Maven project starter for a Paper/Purpur/Folia-compatible Bukkit plugin.\n"
            "Build with: mvn package\n"
            f"Install target/{artifact}.jar into the server plugins/ folder.\n",
        )
    archive.seek(0)
    return send_file(
        archive,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{artifact}-plugin-template.zip",
    )


if __name__ == "__main__":
    init_db()
    threading.Thread(target=schedule_worker, name="NexoryScheduler", daemon=True).start()
    port = int(os.environ.get("NEXORY_PORT", "5000"))
    url = f"http://127.0.0.1:{port}"
    if os.environ.get("NEXORY_OPEN_BROWSER", "true" if getattr(sys, "frozen", False) else "false").lower() == "true":
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    print(f"NexoryPanel disponible en {url}. Pulsa Ctrl+C para detenerlo.")
    app.run(host="127.0.0.1", port=port, debug=False)
