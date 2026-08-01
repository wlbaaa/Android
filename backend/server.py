#!/usr/bin/env python3
"""
Android 12 Web Emulator - Backend API Server
Handles APK uploads, ADB commands, and emulator control.
"""

import argparse
import json
import os
import subprocess
import time
import shutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Configuration
UPLOAD_DIR = "/tmp/apk_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# CORS headers for all responses
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}


def run_adb(cmd, timeout=30):
    """Run an adb command and return output."""
    full_cmd = f"adb {cmd}"
    try:
        result = subprocess.run(
            full_cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def ensure_adb_connection():
    """Ensure adb is connected to the Redroid container."""
    ok, out, _ = run_adb("devices")
    if "localhost:5555" not in out:
        run_adb("connect localhost:5555")
        time.sleep(2)
    ok, out, _ = run_adb("devices")
    return "localhost:5555" in out


class APIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress default logging
        pass

    def send_cors(self):
        for key, value in CORS_HEADERS.items():
            self.send_header(key, value)

    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_cors()
        self.end_headers()
        self.wfile.write(body)

    def send_file_response(self, filepath, content_type, code=200):
        with open(filepath, "rb") as f:
            body = f.read()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/health":
            connected = ensure_adb_connection()
            self.send_json({
                "status": "ok",
                "service": "Android 12 Web Emulator API",
                "adb_connected": connected,
                "endpoints": [
                    "GET  /health - Health check",
                    "POST /install - Upload and install APK",
                    "GET  /apps - List installed apps",
                    "POST /launch - Launch an app by package name",
                    "POST /uninstall - Uninstall an app",
                    "GET  /screenshot - Capture screenshot",
                    "POST /adb - Run raw adb command",
                    "GET  /info - Get device info",
                ],
            })

        elif path == "/info":
            ensure_adb_connection()
            ok, out, err = run_adb("shell getprop")
            if ok:
                props = {}
                for line in out.split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        key = key.strip().strip("[]")
                        val = val.strip().strip("[]")
                        props[key] = val
                # Extract key info
                info = {
                    "model": props.get("ro.product.model", "Unknown"),
                    "brand": props.get("ro.product.brand", "Unknown"),
                    "android_version": props.get("ro.build.version.release", "Unknown"),
                    "sdk_version": props.get("ro.build.version.sdk", "Unknown"),
                    "abi": props.get("ro.product.cpu.abi", "Unknown"),
                    "resolution": props.get("ro.sf.lcd_density", "Unknown"),
                    "serial": props.get("ro.serialno", "Unknown"),
                }
                self.send_json({"status": "ok", "device": info})
            else:
                self.send_json({"status": "error", "message": err}, 500)

        elif path == "/apps":
            ensure_adb_connection()
            ok, out, err = run_adb("shell pm list packages -3")
            if ok:
                apps = []
                for line in out.strip().split("\n"):
                    pkg = line.replace("package:", "").strip()
                    if pkg:
                        apps.append({"package": pkg})
                self.send_json({"status": "ok", "apps": apps})
            else:
                self.send_json({"status": "error", "message": err}, 500)

        elif path == "/screenshot":
            ensure_adb_connection()
            ok, out, err = run_adb("shell screencap -p /sdcard/screenshot.png")
            err2 = ""
            if ok:
                ok2, _, err2 = run_adb("pull /sdcard/screenshot.png /tmp/screenshot.png")
                if ok2:
                    self.send_file_response("/tmp/screenshot.png", "image/png")
                    return
            self.send_json({"status": "error", "message": err or err2}, 500)

        else:
            self.send_json({"status": "error", "message": "Not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/install":
            self.handle_apk_upload()

        elif path == "/launch":
            self.handle_launch()

        elif path == "/uninstall":
            self.handle_uninstall()

        elif path == "/adb":
            self.handle_adb_command()

        else:
            self.send_json({"status": "error", "message": "Not found"}, 404)

    def handle_apk_upload(self):
        content_type = self.headers.get("Content-Type", "")

        if "multipart/form-data" not in content_type:
            self.send_json({"status": "error", "message": "Expected multipart/form-data"}, 400)
            return

        # Parse multipart form data
        boundary = content_type.split("boundary=")[1].strip()
        content_length = int(self.headers.get("Content-Length", 0))

        if content_length == 0:
            self.send_json({"status": "error", "message": "Empty request"}, 400)
            return

        body = self.rfile.read(content_length)

        # Extract file from multipart
        try:
            boundary_bytes = boundary.encode()
            parts = body.split(b"--" + boundary_bytes)

            apk_filename = None
            apk_data = None

            for part in parts:
                if b"filename=" in part:
                    # Parse filename
                    header_end = part.find(b"\r\n\r\n")
                    if header_end == -1:
                        continue
                    header = part[:header_end].decode("utf-8", errors="ignore")
                    file_data = part[header_end + 4:]

                    # Remove trailing \r\n
                    if file_data.endswith(b"\r\n"):
                        file_data = file_data[:-2]

                    # Extract filename
                    for h_line in header.split("\r\n"):
                        if "filename=" in h_line:
                            fname_start = h_line.find('filename="') + 10
                            fname_end = h_line.find('"', fname_start)
                            apk_filename = h_line[fname_start:fname_end]
                            break

                    apk_data = file_data
                    break

            if not apk_data or not apk_filename:
                self.send_json({"status": "error", "message": "No APK file found in request"}, 400)
                return

            # Save APK
            safe_name = os.path.basename(apk_filename)
            if not safe_name.endswith(".apk"):
                safe_name += ".apk"

            apk_path = os.path.join(UPLOAD_DIR, safe_name)
            with open(apk_path, "wb") as f:
                f.write(apk_data)

            file_size = len(apk_data)
            file_size_mb = round(file_size / (1024 * 1024), 2)

            # Install via adb
            ensure_adb_connection()
            ok, out, err = run_adb(f"install -r {apk_path}", timeout=120)

            if ok:
                # Try to get package name
                ok2, out2, _ = run_adb(f"shell pm list packages -3")
                self.send_json({
                    "status": "ok",
                    "message": "APK installed successfully",
                    "filename": safe_name,
                    "size": f"{file_size_mb} MB",
                    "output": out,
                })
            else:
                self.send_json({
                    "status": "error",
                    "message": f"Installation failed: {err or out}",
                    "filename": safe_name,
                }, 500)

        except Exception as e:
            self.send_json({"status": "error", "message": str(e)}, 500)

    def handle_launch(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        try:
            data = json.loads(body)
            package = data.get("package", "")

            if not package:
                self.send_json({"status": "error", "message": "Missing 'package' field"}, 400)
                return

            ensure_adb_connection()

            # Get main activity
            ok, out, err = run_adb(f"shell monkey -p {package} -c android.intent.category.LAUNCHER 1")

            if ok:
                self.send_json({"status": "ok", "message": f"App {package} launched"})
            else:
                self.send_json({"status": "error", "message": err or out}, 500)

        except json.JSONDecodeError:
            self.send_json({"status": "error", "message": "Invalid JSON"}, 400)

    def handle_uninstall(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        try:
            data = json.loads(body)
            package = data.get("package", "")

            if not package:
                self.send_json({"status": "error", "message": "Missing 'package' field"}, 400)
                return

            ensure_adb_connection()
            ok, out, err = run_adb(f"uninstall {package}")

            if ok:
                self.send_json({"status": "ok", "message": f"Uninstalled {package}"})
            else:
                self.send_json({"status": "error", "message": err or out}, 500)

        except json.JSONDecodeError:
            self.send_json({"status": "error", "message": "Invalid JSON"}, 400)

    def handle_adb_command(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        try:
            data = json.loads(body)
            command = data.get("command", "")

            if not command:
                self.send_json({"status": "error", "message": "Missing 'command' field"}, 400)
                return

            # Basic command injection protection
            dangerous = ["rm -rf", "shutdown", "reboot", "mkfs", "dd if="]
            for d in dangerous:
                if d in command.lower():
                    self.send_json({"status": "error", "message": f"Command not allowed"}, 403)
                    return

            ensure_adb_connection()
            ok, out, err = run_adb(command, timeout=10)

            self.send_json({
                "status": "ok" if ok else "error",
                "output": out,
                "error": err,
            })

        except json.JSONDecodeError:
            self.send_json({"status": "error", "message": "Invalid JSON"}, 400)


def main():
    parser = argparse.ArgumentParser(description="Android 12 Web Emulator API Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), APIHandler)
    print(f"Android 12 API Server running on http://{args.host}:{args.port}")
    print(f"Health check: http://{args.host}:{args.port}/health")
    print(f"Endpoints:")
    print(f"  GET  /health")
    print(f"  POST /install  - Upload and install APK")
    print(f"  GET  /apps     - List installed apps")
    print(f"  POST /launch   - Launch app by package")
    print(f"  GET  /screenshot - Capture screenshot")
    print(f"  GET  /info     - Get device info")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()


if __name__ == "__main__":
    main()
