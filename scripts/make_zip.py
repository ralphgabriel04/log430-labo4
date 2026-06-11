"""Cree Labo04-livraison.zip avec le code source + preuves, sans .git ni donnees lourdes."""
import os, zipfile, fnmatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(ROOT), "Labo04-livraison.zip")

EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", ".code-review-graph",
                ".cto-toolkit", ".remember", "redis_mock_data", ".ruff_cache"}
EXCLUDE_FILE_GLOBS = [".env", "db-init/00_post_init.sql", "db-init/01_*", "db-init/02_*",
                      "db-init/03_*", "db-init/04_*", "db-init/05_*", "db-init/06_*",
                      "*.pyc"]

def excluded_file(rel):
    rel = rel.replace("\\", "/")
    return any(fnmatch.fnmatch(rel, g) for g in EXCLUDE_FILE_GLOBS)

count = 0
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ROOT)
            if excluded_file(rel):
                continue
            z.write(full, os.path.join("Labo4", rel))
            count += 1

print(f"Zip cree: {OUT}")
print(f"Fichiers: {count}  Taille: {round(os.path.getsize(OUT)/1024/1024, 2)} MB")
