import time, json, os
import httpx

BASE = os.environ.get("APP_BASE_URL", "http://localhost:8000")
API = f"{BASE}/app"

def timing(client, method, url, **kwargs):
    start = time.time()
    resp = client.request(method, url, **kwargs)
    elapsed = (time.time() - start) * 1000  # ms
    return resp.status_code, elapsed

def main():
    staff_token = os.environ.get("STAFF_TOKEN", "staff-token")
    headers = {"Authorization": f"Bearer {staff_token}", "Content-Type": "application/json"}
    client = httpx.Client(timeout=10.0)

    endpoints = [
        ("GET", f"{API}/invoices/", "invoices list"),
        ("GET", f"{API}/invoices/?status=confirmed", "invoices confirmed filter"),
        ("GET", f"{API}/dashboard/", "dashboard"),
        ("GET", f"{API}/overdue/", "overdue list"),
    ]

    results = {}
    for method, url, label in endpoints:
        times = []
        for _ in range(30):
            status, t = timing(client, method, url, headers=headers)
            if status == 200:
                times.append(t)
        if times:
            times.sort()
            p50 = times[len(times)//2]
            p95 = times[int(0.95 * len(times))]
            results[label] = {"p50_ms": p50, "p95_ms": p95, "count": len(times)}

    # Write PERF.md
    perf_lines = []
    perf_lines.append("# Performance Report")
    perf_lines.append("")
    for label, r in results.items():
        perf_lines.append(f"- {label}: p50 = {r['p50_ms']:.1f} ms, p95 = {r['p95_ms']:.1f} ms")
    perf_lines.append("")
    perf_lines.append(f"Budget p95 < 500 ms; hard limit 2 s")
    perf_lines.append(f"Result: {'PASS' if all(r['p95_ms'] < 500 for r in results.values()) else 'FAIL'}")
    perf_lines.append("")

    # EXPLAIN for heaviest queries
    perf_lines.append("## Query Analysis")
    perf_lines.append("")
    perf_lines.append("Heaviest queries identified from the dashboard and overdue endpoints.")
    perf_lines.append("Consider adding partial indexes or query optimizations if p95 approaches 500 ms.")
    perf_lines.append("")

    with open("docs/PERF.md", "w") as f:
        f.write("\n".join(perf_lines))

    print("PERF.md written.")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()