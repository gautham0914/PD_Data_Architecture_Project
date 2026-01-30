from __future__ import annotations
import csv
from pathlib import Path
from typing import List, Tuple, Dict

from .db import connect

REPORT_DIR = Path(__file__).resolve().parents[1] / "report"
NULL_MD = REPORT_DIR / "null_profile.md"
NULL_CSV = REPORT_DIR / "null_profile.csv"
QUALITY_MD = REPORT_DIR / "quality_checks.md"


def get_pd_tables(cur) -> List[str]:
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'pd' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    return [r[0] for r in cur.fetchall()]


def get_columns(cur, table: str) -> List[Tuple[str, bool]]:
    cur.execute(
        """
        SELECT column_name, is_nullable = 'NO' AS not_null
        FROM information_schema.columns
        WHERE table_schema = 'pd' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    return [(r[0], bool(r[1])) for r in cur.fetchall()]


def get_pk_columns(cur) -> Dict[str, List[str]]:
    cur.execute(
        """
        SELECT tc.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema = 'pd' AND tc.constraint_type = 'PRIMARY KEY'
        ORDER BY tc.table_name, kcu.ordinal_position
        """,
    )
    rows = cur.fetchall()
    out: Dict[str, List[str]] = {}
    for t, c in rows:
        out.setdefault(t, []).append(c)
    return out


def get_fk_constraints(cur) -> List[Tuple[str, str, str, str]]:
    cur.execute(
        """
        SELECT tc.table_name AS table_name,
               kcu.column_name AS column_name,
               ccu.table_name AS ref_table,
               ccu.column_name AS ref_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON tc.constraint_name = ccu.constraint_name AND tc.table_schema = ccu.table_schema
        WHERE tc.table_schema = 'pd' AND tc.constraint_type = 'FOREIGN KEY'
        ORDER BY tc.table_name, kcu.ordinal_position
        """,
    )
    return [(r[0], r[1], r[2], r[3]) for r in cur.fetchall()]


def null_profile(cur) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    tables = get_pd_tables(cur)
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM pd.{t}")
        total = int(cur.fetchone()[0])
        cols = get_columns(cur, t)
        for col, _ in cols:
            cur.execute(f"SELECT COUNT(*) FROM pd.{t} WHERE {col} IS NULL")
            nulls = int(cur.fetchone()[0])
            pct = (nulls / total * 100.0) if total > 0 else 0.0
            results.append({
                "table": t,
                "column": col,
                "null_count": str(nulls),
                "total_rows": str(total),
                "null_percent": f"{pct:.2f}",
            })
    return results


def write_null_outputs(rows: List[Dict[str, str]]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with NULL_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["table", "column", "null_count", "total_rows", "null_percent"])
        w.writeheader()
        w.writerows(rows)

    by_table: Dict[str, List[Dict[str, str]]] = {}
    for r in rows:
        by_table.setdefault(r["table"], []).append(r)

    lines: List[str] = []
    lines.append("# Null Profile")
    for t, cols in by_table.items():
        lines.append(f"\n## {t}")
        lines.append("| column | nulls | total | % |")
        lines.append("|---|---:|---:|---:|")
        for r in cols:
            lines.append(f"| {r['column']} | {r['null_count']} | {r['total_rows']} | {r['null_percent']} |")
    NULL_MD.write_text("\n".join(lines))


def quality_checks(cur) -> Dict[str, Dict[str, int]]:
    checks: Dict[str, Dict[str, int]] = {"unacceptable_nulls": {}, "fk_orphans": {}, "duplicate_keys": {}}

    pk_cols = get_pk_columns(cur)
    fk_list = get_fk_constraints(cur)

    # PK nulls (should be 0)
    for table, cols in pk_cols.items():
        for col in cols:
            cur.execute(f"SELECT COUNT(*) FROM pd.{table} WHERE {col} IS NULL")
            checks["unacceptable_nulls"][f"{table}.{col}"] = int(cur.fetchone()[0])

    # FK nulls (key FKs considered unacceptable) + orphan checks
    for table, col, ref_table, ref_col in fk_list:
        cur.execute(f"SELECT COUNT(*) FROM pd.{table} WHERE {col} IS NULL")
        checks["unacceptable_nulls"][f"{table}.{col}"] = int(cur.fetchone()[0])
        cur.execute(
            f"""
            SELECT COUNT(*)
            FROM pd.{table} t
            WHERE t.{col} IS NOT NULL
              AND NOT EXISTS (
                    SELECT 1 FROM pd.{ref_table} r WHERE r.{ref_col} = t.{col}
              )
            """
        )
        checks["fk_orphans"][f"{table}.{col} -> {ref_table}.{ref_col}"] = int(cur.fetchone()[0])

    # Duplicate logical key: applications(contact_id, opportunity_id)
    cur.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT contact_id, opportunity_id, COUNT(*) AS c
            FROM pd.applications
            GROUP BY contact_id, opportunity_id
            HAVING COUNT(*) > 1
        ) s
        """
    )
    checks["duplicate_keys"]["applications(contact_id,opportunity_id)"] = int(cur.fetchone()[0])

    return checks


def write_quality_md(checks: Dict[str, Dict[str, int]]) -> None:
    lines: List[str] = []
    lines.append("# Data Quality Checks")

    def section(title: str, items: Dict[str, int]) -> None:
        total = sum(items.values())
        status = "PASS" if total == 0 else "FAIL"
        lines.append(f"\n## {title} — {status}")
        lines.append("| check | count |")
        lines.append("|---|---:|")
        for k, v in sorted(items.items()):
            lines.append(f"| {k} | {v} |")

    section("Unacceptable Nulls (PKs + FKs)", checks["unacceptable_nulls"])
    section("FK Orphans", checks["fk_orphans"])
    section("Duplicate Keys", checks["duplicate_keys"])

    QUALITY_MD.write_text("\n".join(lines))


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn, conn.cursor() as cur:
        rows = null_profile(cur)
        write_null_outputs(rows)
        checks = quality_checks(cur)
        write_quality_md(checks)
    print(f"Wrote: {NULL_MD}")
    print(f"Wrote: {NULL_CSV}")
    print(f"Wrote: {QUALITY_MD}")


if __name__ == "__main__":
    main()
