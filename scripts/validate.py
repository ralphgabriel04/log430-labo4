"""Validation: recoupe les chiffres du rapport avec les CSV bruts + valide le ZIP/PDF."""
import csv, os, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOC = os.path.join(ROOT, "locustfiles")

TESTS = ["test1_baseline","test2_nplus1fix","test3a_redis_naive","test3b_redis_cached","test4_loadbalanced"]

print("="*78)
print("1) DONNEES LOCUST REELLES (a comparer avec les tableaux du rapport)")
print("="*78)
for t in TESTS:
    p = os.path.join(LOC, f"{t}_stats.csv")
    print(f"\n--- {t} ---")
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            name = (r["Type"]+" "+r["Name"]).replace("/orders/reports/","")
            req=int(r["Request Count"]); fail=int(r["Failure Count"])
            pct = 100*fail/req if req else 0
            print(f"  {name:28} req={req:5} fail={fail:5} ({pct:5.1f}%) "
                  f"med={float(r['Median Response Time']):.0f}ms rps={float(r['Requests/s']):.1f}")

print("\n"+"="*78)
print("2) VALIDATION DU ZIP")
print("="*78)
zp = os.path.join(os.path.dirname(ROOT), "Labo04-livraison.zip")
must_have = [
    "Labo4/src/store_manager.py","Labo4/src/orders/commands/write_order.py",
    "Labo4/src/orders/queries/read_order.py","Labo4/src/orders/controllers/order_controller.py",
    "Labo4/RAPPORT.pdf","Labo4/RAPPORT.md","Labo4/.github/workflows/ci.yml",
    "Labo4/docker-compose.yml","Labo4/Dockerfile","Labo4/prometheus.yml","Labo4/nginx.conf",
    "Labo4/load-balancer-config/scenario_81/nginx.conf","Labo4/locustfiles/locustfile.py",
    "Labo4/generators/data_generator.py","Labo4/db-init/00_init.sql",
    "Labo4/docs/captures/ci_cd_pipeline.png",
]
with zipfile.ZipFile(zp) as z:
    names = set(z.namelist())
print(f"  Taille: {round(os.path.getsize(zp)/1024/1024,2)} MB   fichiers: {len(names)}")
ok = True
for m in must_have:
    present = m in names
    ok = ok and present
    print(f"  [{'OK' if present else 'MANQUE'}] {m}")
# verifier qu'aucune donnee lourde/secret n'est incluse
bad = [n for n in names if n.endswith(".env") or "redis_mock_data" in n
       or any(f"db-init/0{i}_" in n for i in range(1,7))]
print(f"  Fichiers indesirables (doit etre 0): {len(bad)}")
csvs = [n for n in names if n.startswith("Labo4/locustfiles/") and n.endswith("_stats.csv")]
print(f"  CSV de stats inclus: {len(csvs)} (attendu 5)")
print(f"\n  RESULTAT ZIP: {'VALIDE' if ok and not bad and len(csvs)==5 else 'A CORRIGER'}")

print("\n"+"="*78)
print("3) VALIDATION DU PDF")
print("="*78)
try:
    import pypdf
    r = pypdf.PdfReader(os.path.join(ROOT,"RAPPORT.pdf"))
    imgs = sum(len(list(p.images)) for p in r.pages)
    t0 = r.pages[0].extract_text()
    has_id = all(s in t0 for s in ["GABR77340401","Ralph Christian Gabriel","Ete 2026".replace("Ete","")])
    print(f"  pages={len(r.pages)} images={imgs}")
    print(f"  page-titre contient code permanent + nom: {('GABR77340401' in t0) and ('Ralph Christian Gabriel' in t0)}")
except Exception as e:
    print("  pypdf indisponible:", e)
