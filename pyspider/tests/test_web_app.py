import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from pyspider.web import app as web_app


class _HtmlHandler(BaseHTTPRequestHandler):
    html = "<html><head><title>Py Demo</title></head><body>ok</body></html>"
    delay = 0.0

    def do_GET(self):  # noqa: N802
        if self.delay:
            time.sleep(self.delay)
        body = self.html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A003
        return


class WebAppTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = HTTPServer(("127.0.0.1", 0), _HtmlHandler)
        cls.server_thread = threading.Thread(
            target=cls.httpd.serve_forever, daemon=True
        )
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.httpd.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = Path(self.tempdir.name) / "spider.db"
        web_app.DATABASE = str(self.database)
        with web_app.TASK_STOPS_LOCK:
            web_app.TASK_STOPS.clear()
        web_app.init_db()
        self.client = web_app.app.test_client()

    def tearDown(self):
        with web_app.TASK_STOPS_LOCK:
            for stop_event in web_app.TASK_STOPS.values():
                stop_event.set()
        deadline = time.time() + 2.0
        while time.time() < deadline:
            with web_app.TASK_STOPS_LOCK:
                if not web_app.TASK_STOPS:
                    break
            time.sleep(0.05)
        for _ in range(20):
            try:
                self.tempdir.cleanup()
                return
            except PermissionError:
                time.sleep(0.05)
        self.tempdir.cleanup()

    def test_start_task_generates_result_and_logs(self):
        task_id = self._create_task(self.base_url)

        response = self.client.post(f"/api/tasks/{task_id}/start")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["message"], "Task started")

        task = self._wait_for_status(task_id, "completed")
        self.assertEqual(task["success_requests"], 1)

        results_payload = self.client.get(f"/api/tasks/{task_id}/results").get_json()
        self.assertEqual(len(results_payload["data"]), 1)
        result_data = results_payload["data"][0]
        self.assertEqual(result_data["title"], "Py Demo")
        self.assertEqual(result_data["status"], "completed")
        self.assertEqual(result_data["task_id"], task_id)
        self.assertIn("graph", result_data["artifacts"])
        self.assertIn("graph", result_data["artifact_refs"])
        self.assertEqual(result_data["artifacts"]["graph"]["kind"], "graph")
        self.assertTrue(Path(result_data["artifacts"]["graph"]["path"]).exists())
        artifacts_payload = self.client.get(
            f"/api/tasks/{task_id}/artifacts"
        ).get_json()
        self.assertIn("graph", artifacts_payload["data"])

        logs_payload = self.client.get(f"/api/tasks/{task_id}/logs").get_json()
        self.assertGreaterEqual(logs_payload["pagination"]["total"], 2)
        control_plane = Path(web_app.control_plane_dir())
        self.assertTrue((control_plane / "results.jsonl").exists())
        self.assertTrue((control_plane / "events.jsonl").exists())
        self.assertTrue((control_plane / "py-web-audit.jsonl").exists())
        self.assertIn(
            str(task_id), (control_plane / "results.jsonl").read_text(encoding="utf-8")
        )

    def test_graph_extract_endpoint_returns_nodes_edges_and_stats(self):
        response = self.client.post(
            "/api/graph/extract",
            json={
                "html": "<html><head><title>Py Graph</title></head><body><a href='https://example.com'>go</a></body></html>"
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["root_id"], "document")
        self.assertGreaterEqual(payload["data"]["stats"]["total_nodes"], 2)

    def test_stop_task_marks_task_stopped(self):
        _HtmlHandler.delay = 0.5
        try:
            task_id = self._create_task(self.base_url)
            self.client.post(f"/api/tasks/{task_id}/start")
            stop_response = self.client.post(f"/api/tasks/{task_id}/stop")
            self.assertEqual(stop_response.status_code, 200)
            self.assertEqual(
                stop_response.get_json()["data"]["message"], "Task stopped"
            )

            task = self._wait_for_status(task_id, "stopped")
            self.assertEqual(task["status"], "stopped")

            logs_payload = self.client.get(f"/api/tasks/{task_id}/logs").get_json()
            messages = [entry["message"] for entry in logs_payload["data"]]
            self.assertIn("task stop requested", messages)
            audit_path = Path(web_app.control_plane_dir()) / "py-web-audit.jsonl"
            events_path = Path(web_app.control_plane_dir()) / "events.jsonl"
            self.assertTrue(audit_path.exists())
            self.assertTrue(events_path.exists())
            self.assertIn(str(task_id), audit_path.read_text(encoding="utf-8"))
            self.assertIn(str(task_id), events_path.read_text(encoding="utf-8"))
        finally:
            _HtmlHandler.delay = 0.0

    def test_delete_task_supports_canonical_delete_endpoint(self):
        task_id = self._create_task(self.base_url)
        response = self.client.delete(f"/api/tasks/{task_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["message"], "Task deleted")
        missing = self.client.get(f"/api/tasks/{task_id}")
        self.assertEqual(missing.status_code, 404)

    def _create_task(self, url):
        list_payload = self.client.get("/api/tasks").get_json()
        self.assertIn("pagination", list_payload)
        response = self.client.post("/api/tasks", json={"name": "demo", "url": url})
        self.assertEqual(response.status_code, 200)
        return response.get_json()["data"]["id"]

    def _wait_for_status(self, task_id, expected_status):
        deadline = time.time() + 3
        while time.time() < deadline:
            payload = self.client.get(f"/api/tasks/{task_id}").get_json()
            task = payload["data"]
            if task["status"] == expected_status:
                return task
            time.sleep(0.05)
        self.fail(f"task {task_id} did not reach status {expected_status}")


if __name__ == "__main__":
    unittest.main()
