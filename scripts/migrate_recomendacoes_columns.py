#!/usr/bin/env python3
"""
Migration helper: add 'subtitulo' and 'grau_evidencia' columns to 'recomendacoes'.

This script uses only the Python standard library (sqlite3) and can run on any
Python 3.x without installing project dependencies. It is safe to run multiple
times—columns will only be created if missing.

Usage (from repo root):
  python scripts/migrate_recomendacoes_columns.py
"""
import os
import sqlite3


def main():
    repo_root = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(repo_root, '..', 'src', 'database', 'app.db')
    db_path = os.path.normpath(db_path)

    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found: {db_path}\nRun the app once to create it or ensure the path is correct.")
        return 1

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()

        # Check if table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='recomendacoes';")
        row = cur.fetchone()
        if not row:
            print("[ERROR] Table 'recomendacoes' does not exist yet. Run the app/init to create tables first.")
            return 2

        # Inspect columns
        cur.execute("PRAGMA table_info(recomendacoes);")
        cols = [r[1] for r in cur.fetchall()]  # r[1] is the column name

        to_add = []
        if 'subtitulo' not in cols:
            to_add.append(("subtitulo", "VARCHAR(200)"))
        if 'grau_evidencia' not in cols:
            to_add.append(("grau_evidencia", "VARCHAR(20)"))

        if not to_add:
            print("[OK] Columns already present: 'subtitulo', 'grau_evidencia'. Nothing to do.")
            return 0

        for name, sql_type in to_add:
            alter = f"ALTER TABLE recomendacoes ADD COLUMN {name} {sql_type};"
            print(f"[MIGRATE] Executing: {alter}")
            cur.execute(alter)

        conn.commit()
        print("[DONE] Migration completed successfully.")
        return 0
    finally:
        conn.close()


if __name__ == '__main__':
    raise SystemExit(main())
