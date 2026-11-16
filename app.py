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
import xml.etree.ElementTree as ET
from functools import wraps
from pathlib import Path, PurePosixPath, PureWindowsPath
from tempfile import mkdtemp
from typing import Any

import psutil
from flask import Flask, g, jsonify, render_template, request, send_file, session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

APP_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
IS_WINDOWS = os.name == "nt"
PLATFORM_LABEL = {"darwin": "macOS", "win32": "Windows"}.get(sys.platform, "Linux")
DEFAULT_NODE_NAME = f"Nexory {PLATFORM_LABEL} Node"


def default_data_directory() -> Path:
    if not getattr(sys, "frozen", False):
        return APP_ROOT / "data"
    if sys.platform == "win32":
        return Path(sys.executable).resolve().parent / "data"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "NexoryPanel"
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return data_home / "nexorypanel"


DATA_DEFAULT = default_data_directory()
DATA_DIR = Path(os.environ.get("NEXORY_DATA_DIR", DATA_DEFAULT)).expanduser().resolve()
SERVER_DIR = DATA_DIR / "servers"
DB_PATH = DATA_DIR / "nexory.sqlite3"
CONFIG_PATH = DATA_DIR / "secret.key"
SOFTWARE = {
    "paper": {"name": "PaperMC", "image": "/static/software/paper.png"},
    "folia": {"name": "FoliaMC", "image": "/static/software/folia.png"},
    "forge": {"name": "Forge", "image": "/static/software/forge.png"},
    "purpur": {"name": "PurpurMC", "image": "/static/software/purpur.png"},
    "mohist": {"name": "Mohist", "image": "/static/software/mohist.png"},
    "arclight": {"name": "Arclight", "image": "/static/software/arclight.png"},
    "neoforge": {"name": "NeoForge", "image": "/static/software/neoforge.png"},
    "vanilla": {"name": "Minecraft Vanilla", "image": "/static/software/vanilla.png"},
    "bedrock": {"name": "Minecraft Bedrock", "image": "/static/software/bedrock.png"},
    "fabric": {"name": "Fabric", "image": "/static/software/fabric.svg"},
}
VERSION_ID_PATTERN = re.compile(r"[A-Za-z0-9._+-]{1,32}")
BUILD_ID_PATTERN = re.compile(r"[A-Za-z0-9._+-]{1,128}")
NO_BUILD_SOFTWARE = {"vanilla", "bedrock"}
BEDROCK_DOWNLOAD_API = "https://net-secondary.web.minecraft-services.net/api/v1.0/download/links"
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
        "node_name": DEFAULT_NODE_NAME,
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
    is_bedrock = server["software"] == "bedrock"
    if is_bedrock:
        try:
            _, executable_name = bedrock_platform()
        except RuntimeError as error:
            return False, str(error)
        executable = root / executable_name
        if not executable.is_file():
            return False, "Instala primero Minecraft Bedrock desde Versiones."
    elif not (root / "server.jar").is_file():
        return False, "Instala primero server.jar desde Versiones."
    if not is_bedrock:
        eula = root / "eula.txt"
        if not eula.is_file() or "eula=true" not in eula.read_text(encoding="utf-8", errors="ignore").lower():
            return False, "Acepta el EULA oficial editando eula.txt y vuelve a iniciar."
    if folder_size(root) > server["disk_mb"] * 1024 * 1024:
        return False, "El servidor ya supera su límite de almacenamiento. Libera espacio antes de iniciar."
    process_environment = None
    if is_bedrock:
        launch_command = [str(executable)]
        if sys.platform.startswith("linux"):
            process_environment = os.environ.copy()
            library_paths = [str(root), process_environment.get("LD_LIBRARY_PATH", "")]
            process_environment["LD_LIBRARY_PATH"] = os.pathsep.join(
                path for path in library_paths if path
            )
    else:
        java = shutil.which("java")
        if not java:
            return False, "Java no está instalado o no aparece en PATH."
        launch_arguments = ["-jar", "server.jar", "nogui"]
        if server["software"] == "fabric":
            if not (root / "fabric-server-launch.jar").is_file():
                return False, "Instala primero Fabric desde Versiones."
            launch_arguments = ["-jar", "fabric-server-launch.jar", "nogui"]
        elif server["software"] in {"forge", "neoforge"}:
            argument_file = "win_args.txt" if os.name == "nt" else "unix_args.txt"
            if server["software"] == "forge":
                coordinate = f"{server['version']}-{server['build']}"
                argument_path = (
                    root / "libraries" / "net" / "minecraftforge" / "forge"
                    / coordinate / argument_file
                )
            else:
                coordinate = neoforge_coordinate(server["version"], server["build"])
                argument_path = (
                    root / "libraries" / "net" / "neoforged" / "neoforge"
                    / coordinate / argument_file
                )
            if not argument_path.is_file():
                return False, f"Instala primero {SOFTWARE[server['software']]['name']} desde Versiones."
            launch_arguments = [f"@{argument_path.relative_to(root).as_posix()}", "nogui"]
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
        launch_command = [java, *java_args, *launch_arguments]
    log_file = (root / "console.log").open("ab")
    try:
        new_process = subprocess.Popen(
            launch_command,
            cwd=root,
            stdin=subprocess.PIPE,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            env=process_environment,
        )
    except OSError as error:
        log_file.close()
        logging.exception("No se pudo iniciar el servidor %s", server_id)
        return False, f"No se pudo iniciar el servidor: {error}"
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


def bedrock_platform() -> tuple[str, str]:
    if sys.platform == "win32":
        return "serverBedrockWindows", "bedrock_server.exe"
    if sys.platform.startswith("linux"):
        return "serverBedrockLinux", "bedrock_server"
    raise RuntimeError(
        "Minecraft Bedrock Dedicated Server oficial solo está disponible para Windows y Ubuntu Linux."
    )


def bedrock_server_downloads() -> dict[str, str]:
    download_type, _ = bedrock_platform()
    data = official_json(BEDROCK_DOWNLOAD_API)
    result = data.get("result") if isinstance(data, dict) else None
    links = result.get("links") if isinstance(result, dict) else None
    if not isinstance(links, list):
        raise ValueError("La API oficial no devolvió una lista de descargas Bedrock.")
    downloads: dict[str, str] = {}
    for item in links:
        if not isinstance(item, dict) or item.get("downloadType") != download_type:
            continue
        url = item.get("downloadUrl")
        parsed = urllib.parse.urlparse(url) if isinstance(url, str) else None
        match = re.fullmatch(
            r"/bedrockdedicatedserver/bin-(?:win|linux)/bedrock-server-(?P<version>\d+(?:\.\d+){2,3})\.zip",
            parsed.path if parsed else "",
        )
        if (
            not parsed
            or parsed.scheme != "https"
            or parsed.hostname != "www.minecraft.net"
            or not match
        ):
            raise ValueError("La API oficial devolvió un enlace Bedrock no válido.")
        downloads[match.group("version")] = url
    if not downloads:
        raise RuntimeError("La API oficial no publicó un paquete Bedrock para esta plataforma.")
    return downloads


def official_xml(url: str) -> ET.Element:
    if urllib.parse.urlparse(url).hostname not in {
        "maven.minecraftforge.net",
        "maven.neoforged.net",
    }:
        raise ValueError("La consulta XML no pertenece a un repositorio oficial permitido.")
    request_obj = urllib.request.Request(url, headers={"User-Agent": "NexoryPanel/1.0"})
    with urllib.request.urlopen(request_obj, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError(f"El servidor oficial respondió HTTP {response.status}.")
        content = response.read(4 * 1024 * 1024 + 1)
    if len(content) > 4 * 1024 * 1024:
        raise ValueError("Los metadatos oficiales superan el límite de lectura.")
    return ET.fromstring(content)


def version_sort_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version))


def minecraft_release_versions() -> set[str]:
    manifest = official_json("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
    return {
        str(item["id"])
        for item in manifest.get("versions", [])
        if item.get("type") == "release" and VERSION_ID_PATTERN.fullmatch(str(item.get("id", "")))
    }


def forge_build_index() -> dict[str, list[str]]:
    metadata = official_xml(
        "https://maven.minecraftforge.net/net/minecraftforge/forge/maven-metadata.xml"
    )
    releases = minecraft_release_versions()
    builds: dict[str, set[str]] = {}
    for item in metadata.findall("./versioning/versions/version"):
        coordinate = item.text or ""
        minecraft_version, separator, build = coordinate.partition("-")
        if separator and build and minecraft_version in releases:
            builds.setdefault(minecraft_version, set()).add(build)
    return {
        version: sorted(items, key=version_sort_key, reverse=True)
        for version, items in builds.items()
    }


def neoforge_version_info() -> dict[str, list[tuple[str, str]]]:
    metadata = official_xml(
        "https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml"
    )
    releases = minecraft_release_versions()
    versions: dict[str, set[tuple[str, str]]] = {}
    for item in metadata.findall("./versioning/versions/version"):
        coordinate = item.text or ""
        numeric = coordinate.split("-", 1)[0].split(".")
        if len(numeric) < 3 or not all(part.isdigit() for part in numeric):
            continue
        if numeric[0] in {"20", "21"}:
            minecraft_version = (
                f"1.{numeric[0]}" if numeric[1] == "0" else f"1.{numeric[0]}.{numeric[1]}"
            )
            prefix = f"{numeric[0]}.{numeric[1]}."
        elif len(numeric) >= 4:
            minecraft_version = ".".join(numeric[:3])
            prefix = f"{minecraft_version}."
        else:
            continue
        if minecraft_version not in releases or not coordinate.startswith(prefix):
            continue
        build = coordinate[len(prefix):]
        if build:
            versions.setdefault(minecraft_version, set()).add((build, coordinate))
    return {
        version: sorted(
            builds,
            key=lambda item: version_sort_key(item[1]),
            reverse=True,
        )
        for version, builds in versions.items()
    }


def neoforge_coordinate(minecraft_version: str, build: str) -> str:
    if minecraft_version.startswith("1."):
        parts = minecraft_version.split(".")
        base_version = f"{parts[1]}.{parts[2]}" if len(parts) > 2 else f"{parts[1]}.0"
    else:
        base_version = minecraft_version
    return f"{base_version}.{build}"


def arclight_builds(minecraft_version: str | None = None) -> list[dict[str, str]]:
    releases = official_json("https://api.github.com/repos/IzzelAliz/Arclight/releases?per_page=100")
    pattern = re.compile(
        r"^arclight-(?P<loader>fabric|forge|neoforge)-(?P<version>[0-9.]+)-(?P<build>.+)\.jar$"
    )
    builds = []
    for release in releases:
        for asset in release.get("assets", []):
            name = str(asset.get("name", ""))
            match = pattern.fullmatch(name)
            if not match or (minecraft_version and match.group("version") != minecraft_version):
                continue
            url = asset.get("browser_download_url", "")
            if urllib.parse.urlparse(url).hostname != "github.com":
                continue
            builds.append({
                "id": name,
                "label": f"{match.group('loader').capitalize()} · {release.get('tag_name', 'Arclight')}",
                "url": url,
            })
    return builds


def official_download(url: str, target: Path) -> None:
    allowed_hosts = {
        "api.purpurmc.org", "fill.papermc.io", "fill-data.papermc.io",
        "piston-data.mojang.com", "cdn.modrinth.com", "meta.fabricmc.net",
        "maven.minecraftforge.net", "maven.neoforged.net", "api.mohistmc.com",
        "github.com", "mohistmc.com", "www.minecraft.net",
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
            "nodeName": setting("node_name", DEFAULT_NODE_NAME),
            "platformLabel": PLATFORM_LABEL,
            "firewallManaged": IS_WINDOWS,
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
                       "protocol": "UDP" if row["software"] == "bedrock" else "TCP",
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
        port = int(body.get("port", 19132 if software == "bedrock" else 25565))
    except (TypeError, ValueError):
        return response_error("RAM, almacenamiento y puerto deben ser números.")
    if not name or len(name) > 48:
        return response_error("El nombre debe tener entre 1 y 48 caracteres.")
    if software not in SOFTWARE:
        return response_error("Software no admitido.")
    if software == "bedrock":
        try:
            bedrock_platform()
        except RuntimeError as error:
            return response_error(str(error), 400)
    if not VERSION_ID_PATTERN.fullmatch(version):
        return response_error("Versión no válida.")
    if build and not BUILD_ID_PATTERN.fullmatch(build):
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


def run_server_installer(
    software: str,
    installer_name: str,
    install_flag: str,
    staging: Path,
    server_root: Path,
    disk_limit: int,
) -> None:
    java = shutil.which("java")
    if not java:
        raise RuntimeError("Java no está instalado o no aparece en PATH.")
    log_path = staging / "nexory-install.log"
    with log_path.open("wb") as output:
        process = subprocess.Popen(
            [java, "-Djava.awt.headless=true", "-jar", installer_name, install_flag],
            cwd=staging,
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        deadline = time.monotonic() + 600
        try:
            while process.poll() is None:
                if folder_size(server_root) + folder_size(staging) > disk_limit:
                    raise RuntimeError("La instalación superó el límite de almacenamiento del servidor.")
                if time.monotonic() >= deadline:
                    raise RuntimeError("La instalación superó el tiempo máximo de 10 minutos.")
                time.sleep(1)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
    if process.returncode:
        output_text = log_path.read_text(encoding="utf-8", errors="replace")[-3000:]
        raise RuntimeError(f"El instalador de {SOFTWARE[software]['name']} falló: {output_text}")


def merge_server_installation(staging: Path, server_root: Path) -> None:
    for source in staging.rglob("*"):
        if source.is_symlink():
            raise RuntimeError("El instalador creó un enlace simbólico; se canceló la instalación.")
    for source in staging.iterdir():
        if source.name in {"eula.txt", "nexory-install.log"}:
            continue
        target = server_root / source.name
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)


def extract_bedrock_archive(
    archive_path: Path,
    destination: Path,
    current_size: int,
    disk_limit: int,
) -> None:
    root = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        entries = archive.infolist()
        if len(entries) > 10000:
            raise ValueError("El paquete Bedrock contiene demasiados archivos.")
        unpacked_size = sum(entry.file_size for entry in entries if not entry.is_dir())
        if current_size + unpacked_size > disk_limit:
            raise RuntimeError("La instalación Bedrock superaría el límite de almacenamiento.")
        extracted_files: set[str] = set()
        for entry in entries:
            name = entry.filename
            relative = PurePosixPath(name)
            windows_path = PureWindowsPath(name)
            if (
                not name
                or "\\" in name
                or relative.is_absolute()
                or windows_path.is_absolute()
                or windows_path.drive
                or ".." in relative.parts
            ):
                raise ValueError("El paquete Bedrock contiene una ruta no permitida.")
            target = (destination / Path(*relative.parts)).resolve()
            if not target.is_relative_to(root):
                raise ValueError("El paquete Bedrock intenta escribir fuera del servidor.")
            mode = entry.external_attr >> 16
            if mode & 0o170000 == 0o120000:
                raise ValueError("El paquete Bedrock contiene un enlace simbólico.")
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            normalized_target = os.path.normcase(str(target))
            if normalized_target in extracted_files:
                raise ValueError("El paquete Bedrock contiene rutas duplicadas.")
            extracted_files.add(normalized_target)
            target.parent.mkdir(parents=True, exist_ok=True)
            written = 0
            with archive.open(entry) as source, target.open("xb") as output:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > entry.file_size:
                        raise ValueError("Un archivo del paquete Bedrock supera el tamaño anunciado.")
                    output.write(chunk)
            if written != entry.file_size:
                raise ValueError("Un archivo del paquete Bedrock está incompleto.")
            if sys.platform.startswith("linux") and mode & 0o111:
                target.chmod((mode & 0o777) | 0o111)


def configure_bedrock_server_port(server_root: Path, port: int) -> None:
    properties = server_root / "server.properties"
    if not properties.is_file():
        raise RuntimeError("El paquete Bedrock no contiene server.properties.")
    values = {"server-port": str(port), "server-portv6": str(port)}
    lines = properties.read_text(encoding="utf-8-sig").splitlines()
    written: set[str] = set()
    for index, line in enumerate(lines):
        key, separator, _ = line.partition("=")
        key = key.strip()
        if separator and key in values:
            lines[index] = f"{key}={values[key]}"
            written.add(key)
    for key, value in values.items():
        if key not in written:
            lines.append(f"{key}={value}")
    properties.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        if software == "forge":
            versions = forge_build_index()
            return jsonify({"versions": sorted(versions, key=version_sort_key, reverse=True)})
        if software == "neoforge":
            versions = neoforge_version_info()
            return jsonify({"versions": sorted(versions, key=version_sort_key, reverse=True)})
        if software == "fabric":
            data = official_json("https://meta.fabricmc.net/v2/versions/game")
            return jsonify({
                "versions": [
                    item["version"]
                    for item in data
                    if item.get("stable") and VERSION_ID_PATTERN.fullmatch(str(item.get("version", "")))
                ]
            })
        if software == "mohist":
            data = official_json("https://api.mohistmc.com/project/mohist/versions")
            return jsonify({
                "versions": [
                    item["name"]
                    for item in data
                    if isinstance(item, dict) and VERSION_ID_PATTERN.fullmatch(str(item.get("name", "")))
                ]
            })
        if software == "arclight":
            versions = {
                match.group("version")
                for item in arclight_builds()
                if (match := re.fullmatch(
                    r"arclight-(?:fabric|forge|neoforge)-(?P<version>[0-9.]+)-.+\.jar",
                    item["id"],
                ))
            }
            return jsonify({"versions": sorted(versions, key=version_sort_key, reverse=True)})
        if software == "bedrock":
            versions = bedrock_server_downloads()
            return jsonify({"versions": sorted(versions, key=version_sort_key, reverse=True)})
        data = official_json("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
        return jsonify({
            "versions": [
                item["id"]
                for item in data.get("versions", [])
                if item.get("type") == "release"
            ]
        })
    except (OSError, ValueError, KeyError, RuntimeError, ET.ParseError) as error:
        logging.exception("Fallo al consultar versiones de %s", software)
        return response_error(f"No se pudo consultar la API oficial: {error}", 502)


@app.get("/api/software/<software>/versions/<version>/builds")
@login_required()
def software_builds(software: str, version: str):
    if software not in SOFTWARE:
        return response_error("Software no admitido.")
    if not VERSION_ID_PATTERN.fullmatch(version):
        return response_error("Versión no válida.")
    try:
        if software == "purpur":
            data = official_json(f"https://api.purpurmc.org/v2/purpur/{urllib.parse.quote(version, safe='')}")
            builds = list(reversed(data.get("builds", {}).get("all", [])))
            return jsonify({"builds": builds})
        if software in {"paper", "folia"}:
            data = official_json(f"https://fill.papermc.io/v3/projects/{software}/versions/{urllib.parse.quote(version, safe='')}/builds")
            builds = data.get("builds", []) if isinstance(data, dict) else data
            return jsonify({"builds": builds})
        if software == "forge":
            return jsonify({"builds": forge_build_index().get(version, [])})
        if software == "neoforge":
            builds = [
                {"id": build, "label": coordinate}
                for build, coordinate in neoforge_version_info().get(version, [])
            ]
            return jsonify({"builds": builds})
        if software == "fabric":
            data = official_json(
                f"https://meta.fabricmc.net/v2/versions/loader/{urllib.parse.quote(version, safe='')}"
            )
            return jsonify({
                "builds": [
                    {"id": item["loader"]["version"], "label": f"Loader {item['loader']['version']}"}
                    for item in data
                    if item.get("loader", {}).get("stable")
                    and BUILD_ID_PATTERN.fullmatch(str(item.get("loader", {}).get("version", "")))
                ]
            })
        if software == "mohist":
            data = official_json(
                f"https://api.mohistmc.com/project/mohist/{urllib.parse.quote(version, safe='')}/builds"
            )
            return jsonify({
                "builds": [
                    {"id": str(item["id"]), "label": f"Build {item['id']}"}
                    for item in data
                    if isinstance(item, dict) and str(item.get("id", "")).isdigit()
                ]
            })
        if software == "arclight":
            return jsonify({"builds": arclight_builds(version)})
        if software == "bedrock":
            return jsonify({"builds": []})
        return jsonify({"builds": []})
    except (OSError, ValueError, KeyError, RuntimeError, ET.ParseError) as error:
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
    if not VERSION_ID_PATTERN.fullmatch(version):
        return response_error("Versión no válida.")
    if software not in NO_BUILD_SOFTWARE and not BUILD_ID_PATTERN.fullmatch(build):
        return response_error("Selecciona una build válida antes de instalar.")
    with PROCESS_LOCK:
        process = PROCESSES.get(server_id)
    if process and process.poll() is None:
        return response_error("Detén el servidor antes de cambiar su software o versión.", 409)
    root = to_server_path(server_id)
    SERVER_DIR.mkdir(parents=True, exist_ok=True)
    staging = Path(mkdtemp(prefix=f"nexory-install-{server_id}-", dir=SERVER_DIR))
    try:
        if software == "purpur":
            url = f"https://api.purpurmc.org/v2/purpur/{urllib.parse.quote(version, safe='')}/{urllib.parse.quote(build, safe='')}/download"
            official_download(url, staging / "server.jar")
        elif software in {"paper", "folia"}:
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
            official_download(url, staging / "server.jar")
        elif software == "forge":
            if build not in forge_build_index().get(version, []):
                return response_error("No se encontró esa build de Forge en el repositorio oficial.", 404)
            coordinate = f"{version}-{build}"
            installer_name = f"forge-{coordinate}-installer.jar"
            url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{coordinate}/{installer_name}"
            official_download(url, staging / installer_name)
            run_server_installer(
                software, installer_name, "--installServer", staging, root,
                server["disk_mb"] * 1024 * 1024,
            )
            (staging / installer_name).unlink()
            argument_file = "win_args.txt" if os.name == "nt" else "unix_args.txt"
            if not (
                staging / "libraries" / "net" / "minecraftforge" / "forge"
                / coordinate / argument_file
            ).is_file():
                raise RuntimeError("Forge terminó sin generar sus argumentos de inicio.")
        elif software == "neoforge":
            available_builds = dict(neoforge_version_info().get(version, []))
            coordinate = available_builds.get(build)
            if not coordinate:
                return response_error("No se encontró esa build de NeoForge en el repositorio oficial.", 404)
            installer_name = f"neoforge-{coordinate}-installer.jar"
            url = (
                f"https://maven.neoforged.net/releases/net/neoforged/neoforge/"
                f"{coordinate}/{installer_name}"
            )
            official_download(url, staging / installer_name)
            run_server_installer(
                software, installer_name, "--install-server", staging, root,
                server["disk_mb"] * 1024 * 1024,
            )
            (staging / installer_name).unlink()
            argument_file = "win_args.txt" if os.name == "nt" else "unix_args.txt"
            if not (
                staging / "libraries" / "net" / "neoforged" / "neoforge"
                / coordinate / argument_file
            ).is_file():
                raise RuntimeError("NeoForge terminó sin generar sus argumentos de inicio.")
        elif software == "fabric":
            loaders = official_json(
                f"https://meta.fabricmc.net/v2/versions/loader/{urllib.parse.quote(version, safe='')}"
            )
            if not any(
                item.get("loader", {}).get("version") == build and item.get("loader", {}).get("stable")
                for item in loaders
            ):
                return response_error("No se encontró esa build estable de Fabric.", 404)
            installers = official_json("https://meta.fabricmc.net/v2/versions/installer")
            installer_version = next(
                item["version"] for item in installers if item.get("stable")
            )
            fabric_url = (
                f"https://meta.fabricmc.net/v2/versions/loader/"
                f"{urllib.parse.quote(version, safe='')}/{urllib.parse.quote(build, safe='')}/"
                f"{urllib.parse.quote(installer_version, safe='')}/server/jar"
            )
            official_download(fabric_url, staging / "fabric-server-launch.jar")
            manifest = official_json("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
            entry = next(item for item in manifest["versions"] if item["id"] == version)
            version_data = official_json(entry["url"])
            url = version_data["downloads"]["server"]["url"]
            official_download(url, staging / "server.jar")
        elif software == "mohist":
            builds = official_json(
                f"https://api.mohistmc.com/project/mohist/{urllib.parse.quote(version, safe='')}/builds"
            )
            if not any(str(item.get("id", "")) == build for item in builds if isinstance(item, dict)):
                return response_error("No se encontró esa build de Mohist.", 404)
            url = (
                f"https://api.mohistmc.com/project/mohist/{urllib.parse.quote(version, safe='')}"
                f"/builds/{urllib.parse.quote(build, safe='')}/download"
            )
            official_download(url, staging / "server.jar")
        elif software == "arclight":
            build_data = next(
                (item for item in arclight_builds(version) if item["id"] == build),
                None,
            )
            if not build_data:
                return response_error("No se encontró esa build de Arclight.", 404)
            official_download(build_data["url"], staging / "server.jar")
        elif software == "bedrock":
            _, executable_name = bedrock_platform()
            download_url = bedrock_server_downloads().get(version)
            if not download_url:
                return response_error("La versión Bedrock ya no está disponible en la fuente oficial.", 404)
            archive_path = staging / "bedrock-server.zip"
            official_download(download_url, archive_path)
            extract_bedrock_archive(
                archive_path,
                staging,
                folder_size(root) + folder_size(staging),
                server["disk_mb"] * 1024 * 1024,
            )
            archive_path.unlink()
            executable = staging / executable_name
            if not executable.is_file():
                raise RuntimeError("El paquete oficial no contiene el ejecutable Bedrock esperado.")
            if sys.platform.startswith("linux"):
                executable.chmod(executable.stat().st_mode | 0o111)
            configure_bedrock_server_port(staging, server["port"])
        else:
            manifest = official_json("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
            entry = next(item for item in manifest["versions"] if item["id"] == version)
            version_data = official_json(entry["url"])
            url = version_data["downloads"]["server"]["url"]
            official_download(url, staging / "server.jar")

        expected_file = (
            bedrock_platform()[1] if software == "bedrock" else "server.jar"
        )
        if not (staging / expected_file).is_file():
            raise RuntimeError(f"La instalación no generó el archivo {expected_file} esperado.")
        if software == "fabric" and not (staging / "fabric-server-launch.jar").is_file():
            raise RuntimeError("Fabric no generó su launcher de servidor.")
        if folder_size(root) + folder_size(staging) > server["disk_mb"] * 1024 * 1024:
            raise RuntimeError("La instalación superaría el límite de almacenamiento del servidor.")
        merge_server_installation(staging, root)
        if folder_size(root) > server["disk_mb"] * 1024 * 1024:
            raise RuntimeError("La instalación superó el límite de almacenamiento del servidor.")
        db().execute(
            "UPDATE servers SET software = ?, version = ?, build = ? WHERE id = ?",
            (software, version, build, server_id),
        )
        db().commit()
        return jsonify({"ok": True, "file": expected_file})
    except StopIteration:
        return response_error("No se encontró esa versión oficial de Minecraft.", 404)
    except (OSError, ValueError, KeyError, RuntimeError, ET.ParseError, zipfile.BadZipFile) as error:
        logging.exception("Fallo al instalar servidor %s", server_id)
        return response_error(f"No se pudo instalar el servidor: {error}", 502)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


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
    if not IS_WINDOWS:
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
        "id": "primary", "port": server["port"],
        "protocol": "UDP" if server["software"] == "bedrock" else "TCP",
        "description": "Puerto principal de Minecraft", "primary": True,
    }
    return jsonify({
        "ports": [primary, *[dict(row) for row in rows]],
        "firewallProfile": setting("firewall_profile", "Any"),
        "firewallManaged": IS_WINDOWS,
    })


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
    profile = setting("firewall_profile", "Any") if IS_WINDOWS else "Manual"
    port_id = uuid.uuid4().hex[:12]
    firewall_name = f"NexoryPanel-{server_id}-{port_id}"
    if IS_WINDOWS:
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
        if IS_WINDOWS:
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
    if IS_WINDOWS and row["firewall_profile"] != "Manual":
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
    if IS_WINDOWS:
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
        "installSupported": IS_WINDOWS,
        "installRunning": bool(process and process.poll() is None),
        "installExitCode": process.returncode if process and process.poll() is not None else None,
    })


@app.post("/api/admin/database/install")
@login_required(admin=True)
def install_mysql_server():
    global MYSQL_INSTALL_PROCESS
    if not IS_WINDOWS:
        return response_error(
            "La instalación automática de MySQL solo está disponible en Windows. "
            "Instala MySQL Server y el cliente mysql desde el gestor de paquetes de tu sistema.",
            501,
        )
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
            "nodeName": setting("node_name", DEFAULT_NODE_NAME),
            "platformLabel": PLATFORM_LABEL,
            "firewallManaged": IS_WINDOWS,
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
    node_name = str(body.get("nodeName", DEFAULT_NODE_NAME)).strip()[:60] or DEFAULT_NODE_NAME
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
    if server["software"] in {"vanilla", "forge", "neoforge", "fabric", "bedrock"}:
        return response_error("Este software no admite la instalación de plugins Bukkit.")
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
