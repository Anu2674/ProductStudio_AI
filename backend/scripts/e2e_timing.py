"""Phase 4 - real end-to-end timing of the full user flow.

Drives the running backend over HTTP exactly like the frontend would:
register/login -> create project -> upload image -> POST generate -> poll until
the generation row is completed -> download the result.

Reports the real wall-clock time from "clicked generate" to "result ready", and
(with --concurrency N) real job-queue throughput for N simultaneous requests.

Nothing here is estimated - every number is measured on your stack. For the
numbers to mean anything the AI service must be in real mode
(PIPELINE_MODE=real) on a GPU; against the mock pipeline you are only timing the
API + queue overhead, which is still a useful separate measurement.

Usage:
    python scripts/e2e_timing.py --base-url http://localhost:8001 \
        --image ../ai-service/eval/test_images/sneaker_white.jpg \
        --prompt "a white sneaker on a marble shelf, soft daylight" \
        --concurrency 1 --repeats 5
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import statistics
import time
import uuid
from pathlib import Path

import httpx


def _client(base_url: str) -> httpx.Client:
    return httpx.Client(base_url=base_url, timeout=600)


def _auth(c: httpx.Client) -> str:
    email = f"e2e_{uuid.uuid4().hex[:10]}@example.com"
    password = "e2e-passw0rd!"
    c.post("/api/v1/auth/register", json={"email": email, "password": password})
    r = c.post("/api/v1/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def one_run(base_url: str, image: Path, prompt: str, poll_interval: float) -> dict:
    with _client(base_url) as c:
        token = _auth(c)
        h = {"Authorization": f"Bearer {token}"}

        pr = c.post("/api/v1/projects", json={"name": f"e2e {uuid.uuid4().hex[:6]}"}, headers=h)
        pr.raise_for_status()
        project_id = pr.json()["id"]

        with image.open("rb") as f:
            up = c.post(
                f"/api/v1/projects/{project_id}/images",
                files={"file": (image.name, f, "image/jpeg")},
                headers=h,
            )
        up.raise_for_status()
        image_id = up.json()["id"]

        t0 = time.perf_counter()
        gen = c.post(
            f"/api/v1/projects/{project_id}/images/{image_id}/generate",
            json={"prompt": prompt, "scene_type": "studio_white", "lighting": "soft", "camera_angle": "front"},
            headers=h,
        )
        gen.raise_for_status()
        generation_id = gen.json()["id"]
        submit_s = time.perf_counter() - t0

        status = gen.json()["status"]
        while status in {"pending", "processing"}:
            time.sleep(poll_interval)
            g = c.get(f"/api/v1/generations/{generation_id}", headers=h)
            g.raise_for_status()
            status = g.json()["status"]
        total_s = time.perf_counter() - t0

        return {"generation_id": generation_id, "status": status, "submit_s": submit_s, "total_s": total_s}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8001")
    ap.add_argument("--image", required=True, type=Path)
    ap.add_argument("--prompt", default="a product on a clean studio background, soft light")
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--poll-interval", type=float, default=0.5)
    args = ap.parse_args()

    if not args.image.exists():
        raise SystemExit(f"image not found: {args.image}")

    print(f"e2e timing: {args.repeats} batch(es) of {args.concurrency} concurrent request(s)")
    all_results = []
    batch_walls = []
    for b in range(args.repeats):
        t0 = time.perf_counter()
        with cf.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            futs = [
                ex.submit(one_run, args.base_url, args.image, args.prompt, args.poll_interval)
                for _ in range(args.concurrency)
            ]
            batch = [f.result() for f in futs]
        wall = time.perf_counter() - t0
        batch_walls.append(wall)
        all_results.extend(batch)
        ok = sum(1 for r in batch if r["status"] == "completed")
        print(f"  batch {b + 1}: wall {wall:.2f}s  completed {ok}/{len(batch)}  "
              f"throughput {len(batch) / wall:.2f} gen/s")

    totals = [r["total_s"] for r in all_results if r["status"] == "completed"]
    fails = [r for r in all_results if r["status"] != "completed"]
    print("\n=== Phase 4 end-to-end result (REAL) ===")
    print(f"runs                 : {len(all_results)}  (failed: {len(fails)})")
    if totals:
        print(f"end-to-end p50       : {statistics.median(totals):.2f} s")
        print(f"end-to-end mean      : {statistics.mean(totals):.2f} s")
        print(f"end-to-end min / max : {min(totals):.2f} / {max(totals):.2f} s")
    if args.concurrency > 1:
        agg = len(totals) / sum(batch_walls) if batch_walls else 0.0
        print(f"throughput (agg)     : {agg:.2f} completed generations / s "
              f"at concurrency {args.concurrency}")


if __name__ == "__main__":
    main()
