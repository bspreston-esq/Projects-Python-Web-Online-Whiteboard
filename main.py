#!/usr/bin/env python3
"""A collaborative whiteboard: canvas front end, JSON stroke API behind it."""
import argparse
import http.server
import json
import threading
import urllib.parse

STROKES = {}
LOCK = threading.Lock()

PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Online Whiteboard</title>
<style>
  body { margin:0; font-family: system-ui, sans-serif; background:#1b1f24; color:#eee; }
  header { display:flex; gap:.75rem; align-items:center; padding:.6rem 1rem; background:#12161a; }
  canvas { display:block; background:#fff; margin:1rem auto; border-radius:8px; cursor:crosshair; touch-action:none; }
  button, input { font: inherit; }
</style></head><body>
<header>
  <strong>Whiteboard</strong>
  <label>Room <input id="room" value="default" size="10"></label>
  <label>Colour <input id="colour" type="color" value="#1d4ed8"></label>
  <label>Width <input id="width" type="range" min="1" max="20" value="3"></label>
  <button id="clear">Clear</button>
  <span id="status">connecting...</span>
</header>
<canvas id="board" width="960" height="600"></canvas>
<script>
const canvas = document.getElementById('board'), ctx = canvas.getContext('2d');
const status = document.getElementById('status'), roomInput = document.getElementById('room');
let drawing = false, current = [];

function room() { return roomInput.value.trim() || 'default'; }
function drawStroke(stroke) {
  if (!stroke.points.length) return;
  ctx.strokeStyle = stroke.colour; ctx.lineWidth = stroke.width;
  ctx.lineCap = 'round'; ctx.beginPath();
  ctx.moveTo(stroke.points[0][0], stroke.points[0][1]);
  for (const [x, y] of stroke.points.slice(1)) ctx.lineTo(x, y);
  ctx.stroke();
}
async function refresh() {
  const response = await fetch('/api/strokes?room=' + encodeURIComponent(room()));
  const data = await response.json();
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  data.strokes.forEach(drawStroke);
  status.textContent = data.strokes.length + ' strokes';
}
canvas.addEventListener('pointerdown', event => {
  drawing = true;
  const rect = canvas.getBoundingClientRect();
  current = [[(event.clientX - rect.left) * canvas.width / rect.width,
              (event.clientY - rect.top) * canvas.height / rect.height]];
});
canvas.addEventListener('pointermove', event => {
  if (!drawing) return;
  const rect = canvas.getBoundingClientRect();
  current.push([(event.clientX - rect.left) * canvas.width / rect.width,
                (event.clientY - rect.top) * canvas.height / rect.height]);
  drawStroke({points: current, colour: document.getElementById('colour').value,
              width: Number(document.getElementById('width').value)});
});
canvas.addEventListener('pointerup', async () => {
  if (!drawing || current.length < 2) { drawing = false; return; }
  drawing = false;
  await fetch('/api/strokes', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({room: room(), points: current,
      colour: document.getElementById('colour').value,
      width: Number(document.getElementById('width').value)})});
  current = []; refresh();
});
document.getElementById('clear').onclick = async () => {
  await fetch('/api/strokes?room=' + encodeURIComponent(room()), {method: 'DELETE'});
  refresh();
};
setInterval(refresh, 2000);
refresh();
</script></body></html>"""

class WhiteboardHandler(http.server.BaseHTTPRequestHandler):
    server_version = "MiniWhiteboard/1.0"

    def _send(self, body: bytes, content_type="application/json", status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _room(self):
        return urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("room", ["default"])[0]

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            self._send(PAGE.encode(), "text/html; charset=utf-8")
        elif self.path.startswith("/api/strokes"):
            with LOCK:
                strokes = list(STROKES.get(self._room(), []))
            self._send(json.dumps({"strokes": strokes}).encode())
        else:
            self._send(b'{"error":"not found"}', status=404)

    def do_POST(self):
        if not self.path.startswith("/api/strokes"):
            self._send(b'{"error":"not found"}', status=404); return
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            stroke = {"points": [[float(x), float(y)] for x, y in payload["points"]],
                      "colour": str(payload.get("colour", "#000000")),
                      "width": float(payload.get("width", 3))}
            if not stroke["points"]:
                raise ValueError("empty stroke")
            room = str(payload.get("room") or self._room())
        except (ValueError, KeyError, TypeError) as exc:
            self._send(json.dumps({"error": str(exc)}).encode(), status=400); return
        with LOCK:
            STROKES.setdefault(room, []).append(stroke)
            total = len(STROKES[room])
        self._send(json.dumps({"ok": True, "strokes": total}).encode())

    def do_DELETE(self):
        if not self.path.startswith("/api/strokes"):
            self._send(b'{"error":"not found"}', status=404); return
        with LOCK:
            STROKES.pop(self._room(), None)
        self._send(b'{"ok":true}')

    def log_message(self, *args):
        pass

def demo() -> None:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), WhiteboardHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        import urllib.request
        with urllib.request.urlopen(base + "/") as response:
            page = response.read().decode()
        print("canvas page:", "canvas" in page, "| bytes:", len(page))
        stroke = json.dumps({"room": "demo", "points": [[10, 10], [50, 40], [90, 20]],
                             "colour": "#1d4ed8", "width": 3}).encode()
        request = urllib.request.Request(base + "/api/strokes", data=stroke,
                                         headers={"Content-Type": "application/json"})
        print("post:", json.load(urllib.request.urlopen(request)))
        with urllib.request.urlopen(base + "/api/strokes?room=demo") as response:
            data = json.load(response)
        print(f"strokes stored: {len(data['strokes'])}, points: {len(data['strokes'][0]['points'])}")
        delete = urllib.request.Request(base + "/api/strokes?room=demo", method="DELETE")
        urllib.request.urlopen(delete).read()
        with urllib.request.urlopen(base + "/api/strokes?room=demo") as response:
            print("after clear:", len(json.load(response)["strokes"]))
    finally:
        server.shutdown(); server.server_close()

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    if args.demo:
        demo(); return
    server = http.server.ThreadingHTTPServer((args.host, args.port), WhiteboardHandler)
    print(f"whiteboard on http://{args.host}:{args.port}/  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
