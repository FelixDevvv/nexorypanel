import os
import tempfile
import unittest
from unittest.mock import patch

TEMP_STORAGE = tempfile.TemporaryDirectory(prefix="nexory-tests-")
os.environ["NEXORY_DATA_DIR"] = TEMP_STORAGE.name

import app as panel


class PanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        panel.init_db()

    @classmethod
    def tearDownClass(cls):
        TEMP_STORAGE.cleanup()

    def setUp(self):
        connection = panel.sqlite3.connect(panel.DB_PATH)
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.executescript(
            "DELETE FROM api_keys; DELETE FROM servers; DELETE FROM users; DELETE FROM settings;"
        )
        connection.commit()
        connection.close()
        panel.init_db()
        for child in panel.SERVER_DIR.iterdir():
            if child.is_dir():
                panel.shutil.rmtree(child)
            else:
                child.unlink()
        with panel.PROCESS_LOCK:
            panel.PROCESSES.clear()
        self.client = panel.app.test_client()
        bootstrap = self.client.get("/api/bootstrap").get_json()
        self.csrf = bootstrap["csrfToken"]

    def post(self, url, body):
        return self.client.post(
            url, json=body, headers={"X-CSRF-Token": self.csrf}
        )

    def test_first_account_admin_and_user_registration(self):
        first = self.post(
            "/api/register", {"username": "root_user", "password": "secure-password-1"}
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json()["user"]["role"], "admin")
        self.csrf = first.get_json()["csrfToken"]
        second = self.post(
            "/api/register", {"username": "player_01", "password": "another-password-1"}
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.get_json()["user"]["role"], "user")

    def test_server_quotas_file_sandbox_and_dashboard_key(self):
        created = self.post(
            "/api/register", {"username": "root_user", "password": "secure-password-1"}
        )
        self.csrf = created.get_json()["csrfToken"]
        admin_id = created.get_json()["user"]["id"]
        regular_user = self.post(
            "/api/register", {"username": "player_01", "password": "another-password-1"}
        )
        self.assertEqual(regular_user.get_json()["user"]["role"], "user")
        self.csrf = regular_user.get_json()["csrfToken"]
        denied = self.post(
            "/api/servers",
            {"name": "Nope", "ownerId": regular_user.get_json()["user"]["id"],
             "software": "paper", "version": "1.21.1", "build": "1",
             "ramMb": 2048, "diskMb": 10240, "port": 25565},
        )
        self.assertEqual(denied.status_code, 403)

        logout = self.client.post(
            "/api/logout", json={}, headers={"X-CSRF-Token": self.csrf}
        )
        self.csrf = logout.get_json()["csrfToken"]
        login = self.client.post(
            "/api/login",
            json={"username": "root_user", "password": "secure-password-1"},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(login.status_code, 200)
        self.csrf = login.get_json()["csrfToken"]
        server = self.post(
            "/api/servers",
            {"name": "Survival", "ownerId": admin_id, "software": "paper",
             "version": "1.21.1", "build": "123", "ramMb": 2048,
             "diskMb": 1024, "port": 25565},
        )
        self.assertEqual(server.status_code, 201)
        server_id = server.get_json()["id"]
        self.assertTrue((panel.SERVER_DIR / server_id / "eula.txt").is_file())

        with patch.object(
            panel,
            "official_json",
            return_value={"versions": [{"version": {"id": "1.21.8"}}]},
        ):
            versions = self.client.get("/api/software/paper/versions")
        self.assertEqual(versions.get_json()["versions"], ["1.21.8"])

        with patch.object(
            panel,
            "official_json",
            return_value={
                "builds": [
                    {
                        "id": 123,
                        "downloads": {
                            "server:default": {
                                "url": "https://fill-data.papermc.io/v1/objects/test/paper.jar"
                            }
                        },
                    }
                ]
            },
        ), patch.object(panel, "official_download") as download:
            install = self.post(f"/api/servers/{server_id}/install", {})
        self.assertEqual(install.status_code, 200)
        self.assertEqual(download.call_args.args[0], "https://fill-data.papermc.io/v1/objects/test/paper.jar")

        template = self.post(
            "/api/plugin-projects/template",
            {"name": "Mi Plugin", "package": "com.ejemplo.miplugin",
             "mainClass": "Main", "minecraftVersion": "1.21.8"},
        )
        self.assertEqual(template.status_code, 200)
        with panel.zipfile.ZipFile(panel.io.BytesIO(template.data)) as archive:
            files = archive.namelist()
            self.assertIn("mi-plugin/pom.xml", files)
            java_source = archive.read(
                "mi-plugin/src/main/java/com/ejemplo/miplugin/Main.java"
            ).decode("utf-8")
            self.assertIn("extends JavaPlugin", java_source)

        traversal = self.client.get(f"/api/servers/{server_id}/files?path=..%2F..")
        self.assertEqual(traversal.status_code, 403)
        create_folder = self.post(
            f"/api/servers/{server_id}/files/folder", {"path": "", "name": "plugins"}
        )
        self.assertEqual(create_folder.status_code, 200)
        create_file = self.post(
            f"/api/servers/{server_id}/files/file",
            {"path": "plugins", "name": "config.yml", "content": "enabled: true\n"},
        )
        self.assertEqual(create_file.status_code, 200)
        rename = self.post(
            f"/api/servers/{server_id}/files/rename",
            {"path": "plugins/config.yml", "newName": "settings.yml"},
        )
        self.assertEqual(rename.status_code, 200)
        self.assertTrue((panel.SERVER_DIR / server_id / "plugins" / "settings.yml").is_file())

        connection = panel.sqlite3.connect(panel.DB_PATH)
        connection.execute("UPDATE servers SET disk_mb = 1 WHERE id = ?", (server_id,))
        connection.commit()
        connection.close()
        payload = self.post(
            f"/api/servers/{server_id}/files/file",
            {"path": "", "name": "too-large.txt", "content": "x" * (1024 * 1024)},
        )
        self.assertEqual(payload.status_code, 413)

        self.client.put(
            "/api/admin/settings",
            json={"maxRamMb": 8192, "maxDiskMb": 51200, "theme": "Purple",
                  "enableRegister": True, "apiKeyEnabled": True, "nodeName": "Test node",
                  "accentColor": "#12abef", "buttonStyle": "Outline"},
            headers={"X-CSRF-Token": self.csrf},
        )
        settings = self.client.get("/api/admin/overview").get_json()["settings"]
        self.assertEqual(settings["accentColor"], "#12abef")
        self.assertEqual(settings["buttonStyle"], "Outline")
        key_response = self.post("/api/admin/api-keys", {"label": "test"})
        self.assertEqual(key_response.status_code, 200)
        key = key_response.get_json()["key"]
        dashboard = self.client.get(
            "/api/dashboard", headers={"Authorization": f"Bearer {key}"}
        )
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.get_json()[0]["id"], server_id)

    def test_server_modules_members_backups_schedules_and_customization(self):
        created = self.post(
            "/api/register", {"username": "root_user", "password": "secure-password-1"}
        )
        self.csrf = created.get_json()["csrfToken"]
        admin_id = created.get_json()["user"]["id"]
        server = self.post(
            "/api/servers",
            {"name": "Module test", "ownerId": admin_id, "software": "paper",
             "version": "1.21.8", "build": "123", "ramMb": 2048,
             "diskMb": 10240, "port": 25565},
        ).get_json()
        server_id = server["id"]
        user = self.post(
            "/api/register", {"username": "server_user", "password": "secure-password-2"}
        )
        user_id = user.get_json()["user"]["id"]
        self.csrf = user.get_json()["csrfToken"]
        logout = self.client.post("/api/logout", json={}, headers={"X-CSRF-Token": self.csrf})
        self.csrf = logout.get_json()["csrfToken"]
        login = self.client.post(
            "/api/login",
            json={"username": "root_user", "password": "secure-password-1"},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.csrf = login.get_json()["csrfToken"]

        member = self.post(f"/api/servers/{server_id}/members", {"userId": user_id})
        self.assertEqual(member.status_code, 200)
        settings = self.client.put(
            f"/api/servers/{server_id}/settings",
            json={"name": "Managed server", "description": "shared access",
                  "javaArgs": "-Xms512M -Xmx{ram}M"},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(settings.status_code, 200)

        schedule = self.post(
            f"/api/servers/{server_id}/schedules",
            {"name": "Hourly announcement", "action": "command",
             "command": "say hello", "intervalMinutes": 60},
        )
        self.assertEqual(schedule.status_code, 201)
        self.assertEqual(len(self.client.get(f"/api/servers/{server_id}/schedules").get_json()), 1)

        with patch.object(panel, "IS_WINDOWS", True), patch.object(panel, "run_firewall_rule") as firewall:
            port = self.post(
                f"/api/servers/{server_id}/network",
                {"port": 25575, "protocol": "TCP", "description": "RCON"},
            )
            self.assertEqual(port.status_code, 201)
            self.assertEqual(firewall.call_args.args[3], "Any")
            removed = self.client.delete(
                f"/api/servers/{server_id}/network/{port.get_json()['id']}",
                headers={"X-CSRF-Token": self.csrf},
            )
            self.assertEqual(removed.status_code, 200)
            self.assertTrue(firewall.call_args.kwargs["remove"])

        backup = self.client.post(
            f"/api/servers/{server_id}/backups", json={},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(backup.status_code, 201)
        downloaded = self.client.get(
            f"/api/servers/{server_id}/backups/{backup.get_json()['id']}"
        )
        self.assertEqual(downloaded.status_code, 200)
        with panel.zipfile.ZipFile(panel.io.BytesIO(downloaded.data)) as archive:
            self.assertIn("eula.txt", archive.namelist())
        downloaded.close()

        activity = self.client.get(f"/api/servers/{server_id}/activity").get_json()
        self.assertTrue(any(event["action"] == "server.backup.create" for event in activity))
        with patch.object(panel, "mysql_binary", return_value=None):
            self.assertFalse(self.client.get(f"/api/servers/{server_id}/databases").get_json()["available"])

        logout = self.client.post("/api/logout", json={}, headers={"X-CSRF-Token": self.csrf})
        self.csrf = logout.get_json()["csrfToken"]
        login_user = self.client.post(
            "/api/login",
            json={"username": "server_user", "password": "secure-password-2"},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.csrf = login_user.get_json()["csrfToken"]
        self.assertEqual(self.client.get("/api/servers").get_json()[0]["id"], server_id)
        self.assertEqual(self.client.get(f"/api/servers/{server_id}/settings").status_code, 200)

    def test_non_windows_ports_are_recorded_without_firewall_changes(self):
        created = self.post(
            "/api/register", {"username": "root_user", "password": "secure-password-1"}
        )
        self.csrf = created.get_json()["csrfToken"]
        server = self.post(
            "/api/servers",
            {"name": "Cross-platform server", "ownerId": created.get_json()["user"]["id"],
             "software": "paper", "version": "1.21.8", "build": "123",
             "ramMb": 2048, "diskMb": 10240, "port": 25565},
        ).get_json()

        with patch.object(panel, "IS_WINDOWS", False), patch.object(panel, "run_firewall_rule") as firewall:
            network = self.client.get(f"/api/servers/{server['id']}/network").get_json()
            self.assertFalse(network["firewallManaged"])
            port = self.post(
                f"/api/servers/{server['id']}/network",
                {"port": 25575, "protocol": "TCP", "description": "RCON"},
            )
            self.assertEqual(port.status_code, 201)
            self.assertEqual(port.get_json()["firewallProfile"], "Manual")
            removed = self.client.delete(
                f"/api/servers/{server['id']}/network/{port.get_json()['id']}",
                headers={"X-CSRF-Token": self.csrf},
            )
            self.assertEqual(removed.status_code, 200)
            firewall.assert_not_called()

            status = self.client.get("/api/admin/database/status").get_json()
            self.assertFalse(status["installSupported"])
            install = self.post("/api/admin/database/install", {})
            self.assertEqual(install.status_code, 501)

    def test_frozen_data_directory_uses_native_user_location(self):
        home = panel.Path.home() / "nexory-home"
        with patch.object(panel.sys, "frozen", True, create=True), patch.object(panel.sys, "platform", "darwin"), patch.object(panel.Path, "home", return_value=home):
            self.assertEqual(
                panel.default_data_directory(),
                home / "Library" / "Application Support" / "NexoryPanel",
            )
        with patch.object(panel.sys, "frozen", True, create=True), patch.object(panel.sys, "platform", "linux"), patch.object(panel.Path, "home", return_value=home), patch.dict(panel.os.environ, {"XDG_DATA_HOME": str(home / ".local" / "share")}):
            self.assertEqual(
                panel.default_data_directory(),
                home / ".local" / "share" / "nexorypanel",
            )

    def test_custom_admin_branding_and_background_settings(self):
        registered = self.post(
            "/api/register", {"username": "root_user", "password": "secure-password-1"}
        )
        self.csrf = registered.get_json()["csrfToken"]
        response = self.client.put(
            "/api/admin/settings",
            json={"maxRamMb": 8192, "maxDiskMb": 51200, "theme": "Purple",
                  "enableRegister": True, "apiKeyEnabled": False, "nodeName": "Test",
                  "buttonStyle": "Glassed", "backgroundStyle": "Glassed",
                  "backgroundStart": "#101020", "backgroundEnd": "#302050",
                  "announcement": "Maintenance notice",
                  "discordUrl": "https://discord.gg/example",
                  "customLinks": [{"label": "Docs", "url": "https://example.com/docs"}],
                  "firewallProfile": "Private"},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(response.status_code, 200)
        settings = self.client.get("/api/admin/overview").get_json()["settings"]
        self.assertEqual(settings["backgroundStyle"], "Glassed")
        self.assertEqual(settings["firewallProfile"], "Private")
        self.assertEqual(settings["customLinks"][0]["label"], "Docs")
        self.assertEqual(self.client.get("/api/bootstrap").get_json()["announcement"], "Maintenance notice")

        from PIL import Image

        image_data = panel.io.BytesIO()
        Image.new("RGBA", (32, 32), (100, 40, 220, 255)).save(image_data, format="PNG")
        image_data.seek(0)
        uploaded = self.client.post(
            "/api/admin/branding/icon",
            data={"icon": (image_data, "brand.png")},
            headers={"X-CSRF-Token": self.csrf},
        )
        self.assertEqual(uploaded.status_code, 200)
        icon_response = self.client.get("/api/branding/icon")
        self.assertEqual(icon_response.mimetype, "image/png")
        icon_response.close()
        self.assertTrue(self.client.delete(
            "/api/admin/branding/icon", headers={"X-CSRF-Token": self.csrf}
        ).get_json()["ok"])


if __name__ == "__main__":
    unittest.main()
