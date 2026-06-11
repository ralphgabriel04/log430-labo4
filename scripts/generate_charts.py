"""
Génère les graphiques du RAPPORT à partir des CSV Locust et de l'API Prometheus.
Usage: python scripts/generate_charts.py
"""
import csv, os, time, json, urllib.request
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCUST = os.path.join(ROOT, "locustfiles")
OUT = os.path.join(ROOT, "docs", "captures")
os.makedirs(OUT, exist_ok=True)

TESTS = [
    ("test1_baseline",       "1. Baseline\n(MySQL + N+1)"),
    ("test2_nplus1fix",      "2. N+1 corrigé\n(MySQL)"),
    ("test3a_redis_naive",   "3a. Redis naïf\n(sans cache)"),
    ("test3b_redis_cached",  "3b. Redis caché"),
    ("test4_loadbalanced",   "4. Load balancing\n(2 replicas)"),
]
ENDPOINTS = {
    "POST/orders": "POST",
    "GET/best-sellers": "best-sellers",
    "GET/highest-spenders": "highest-spenders",
}

def read_stats(prefix):
    """Retourne {row_name: dict} depuis <prefix>_stats.csv"""
    path = os.path.join(LOCUST, f"{prefix}_stats.csv")
    rows = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (r["Type"] + r["Name"]).replace("/orders/reports", "")
            rows[key] = r
    return rows

data = {p: read_stats(p) for p, _ in TESTS}
labels = [lbl for _, lbl in TESTS]
COL = {"POST": "#c0392b", "best-sellers": "#2980b9", "highest-spenders": "#27ae60"}

def metric(prefix, contains, field, default=0.0):
    for key, r in data[prefix].items():
        if contains in key:
            try:
                return float(r[field])
            except Exception:
                return default
    return default

# ---- Chart 1: taux d'échec (%) par endpoint et par test ----
fig, ax = plt.subplots(figsize=(11, 5.5))
x = range(len(TESTS)); w = 0.26
for i, (disp, contains) in enumerate([("POST /orders","POST"),
                                       ("GET best-sellers","best-sellers"),
                                       ("GET highest-spenders","highest-spenders")]):
    vals = []
    for p, _ in TESTS:
        req = metric(p, contains, "Request Count")
        fail = metric(p, contains, "Failure Count")
        vals.append(100*fail/req if req else 0)
    ax.bar([xx + (i-1)*w for xx in x], vals, w, label=disp, color=list(COL.values())[i])
ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=9)
ax.set_ylabel("Taux d'échec (%)"); ax.set_ylim(0, 105)
ax.set_title("Taux d'échec par endpoint - 150 utilisateurs, 120 s")
ax.legend(); ax.grid(axis="y", alpha=0.3)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "chart_failure_rate.png"), dpi=130); plt.close()

# ---- Chart 2: débit agrégé (req/s) ----
fig, ax = plt.subplots(figsize=(9, 5))
rps = [metric(p, "Aggregated", "Requests/s") for p, _ in TESTS]
fps = [metric(p, "Aggregated", "Failures/s") for p, _ in TESTS]
ax.bar([xx-0.2 for xx in x], rps, 0.4, label="Requêtes/s (total)", color="#16a085")
ax.bar([xx+0.2 for xx in x], fps, 0.4, label="Échecs/s", color="#c0392b")
ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=9)
ax.set_ylabel("Requêtes par seconde"); ax.set_title("Débit agrégé et échecs par seconde")
ax.legend(); ax.grid(axis="y", alpha=0.3)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "chart_rps.png"), dpi=130); plt.close()

# ---- Chart 3: temps de réponse médian des lectures (échelle log) ----
fig, ax = plt.subplots(figsize=(9, 5))
for contains, color in [("best-sellers", "#2980b9"), ("highest-spenders", "#27ae60")]:
    med = [metric(p, contains, "Median Response Time") for p, _ in TESTS]
    ax.plot(range(len(TESTS)), med, "o-", label=f"GET {contains}", color=color, linewidth=2)
ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=9)
ax.set_yscale("log"); ax.set_ylabel("Temps de réponse médian (ms, log)")
ax.set_title("Temps de réponse médian des rapports (lecture)")
ax.legend(); ax.grid(alpha=0.3, which="both")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "chart_read_latency.png"), dpi=130); plt.close()

# ---- Chart 4: Q1 - échecs vs utilisateurs (baseline timeline) ----
hist = os.path.join(LOCUST, "test1_baseline_stats_history.csv")
t0=None; ts=[]; users=[]; fps=[]
with open(hist, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["Name"] != "Aggregated": continue
        tt = float(r["Timestamp"]);  t0 = t0 if t0 else tt
        ts.append(tt-t0); users.append(float(r["User Count"]))
        fps.append(float(r.get("Failures/s", 0) or 0))
fig, ax1 = plt.subplots(figsize=(10, 5))
ax1.plot(ts, users, color="#2980b9", linewidth=2, label="Utilisateurs")
ax1.set_xlabel("Temps (s)"); ax1.set_ylabel("Utilisateurs simultanés", color="#2980b9")
ax2 = ax1.twinx()
ax2.plot(ts, fps, color="#c0392b", linewidth=2, label="Échecs/s")
ax2.set_ylabel("Échecs par seconde", color="#c0392b")
# ligne au point de rupture (~122 users)
for i,u in enumerate(users):
    if fps[i] > 0:
        ax1.axvline(ts[i], color="gray", linestyle="--", alpha=0.7)
        ax1.annotate(f"1ers échecs\n~{int(u)} users", (ts[i], u),
                     textcoords="offset points", xytext=(-65,-10), fontsize=9, color="gray")
        break
ax1.set_title("Q1 - Apparition des échecs vs nombre d'utilisateurs (baseline)")
plt.tight_layout(); plt.savefig(os.path.join(OUT, "chart_q1_failures_vs_users.png"), dpi=130); plt.close()

# ---- Chart 5: compteurs Prometheus (query_range) ----
try:
    end = int(time.time()); start = end - 2400
    fig, ax = plt.subplots(figsize=(10, 5))
    for m, color in [("orders_total","#c0392b"),
                     ("highest_spenders_total","#27ae60"),
                     ("best_sellers_total","#2980b9")]:
        url = (f"http://localhost:9190/api/v1/query_range?query={m}"
               f"&start={start}&end={end}&step=15")
        with urllib.request.urlopen(url, timeout=10) as resp:
            js = json.load(resp)
        for series in js["data"]["result"]:
            xs = [float(v[0]) - start for v in series["values"]]
            ys = [float(v[1]) for v in series["values"]]
            ax.plot(xs, ys, label=m, color=color, linewidth=1.8)
            break
    ax.set_xlabel("Temps (s)"); ax.set_ylabel("Valeur du compteur (cumulatif)")
    ax.set_title("Compteurs Prometheus pendant les tests de charge\n"
                 "(remise à zéro = redémarrage du store_manager entre les tests)")
    ax.legend(); ax.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, "chart_prometheus_counters.png"), dpi=130); plt.close()
    print("Prometheus chart OK")
except Exception as e:
    print(f"Prometheus chart skipped: {e}")

print("Charts written to", OUT)
for f in sorted(os.listdir(OUT)):
    print("  ", f)
