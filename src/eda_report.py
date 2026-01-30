from __future__ import annotations
import csv
from pathlib import Path
from typing import List, Tuple

from .db import connect

REPORT_DIR = Path(__file__).resolve().parents[1] / "report"
EDA_MD = REPORT_DIR / "eda_report.md"
EDA_DIR = REPORT_DIR / "eda_csv"


def write_csv(path: Path, headers: List[str], rows: List[Tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for r in rows:
            w.writerow(list(r))


def top_table_md(title: str, headers: List[str], rows: List[Tuple], limit: int = 20) -> List[str]:
    lines: List[str] = []
    lines.append(f"\n## {title}")
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---" for _ in headers]) + "|")
    for r in rows[:limit]:
        lines.append("| " + " | ".join([str(x) for x in r]) + " |")
    return lines


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    EDA_DIR.mkdir(parents=True, exist_ok=True)

    lines: List[str] = []
    lines.append("# EDA Report")

    with connect() as conn, conn.cursor() as cur:
        # Contact type distribution
        cur.execute("""
            SELECT contact_type, COUNT(*) AS n
            FROM pd.contacts
            GROUP BY contact_type
            ORDER BY n DESC
        """)
        rows = cur.fetchall()
        write_csv(EDA_DIR / "contact_types.csv", ["contact_type", "count"], rows)
        lines += top_table_md("Contact Types", ["contact_type", "count"], rows)

        # Applications by status
        cur.execute("""
            SELECT status, COUNT(*) AS n
            FROM pd.applications
            GROUP BY status
            ORDER BY n DESC
        """)
        rows = cur.fetchall()
        write_csv(EDA_DIR / "applications_by_status.csv", ["status", "count"], rows)
        lines += top_table_md("Applications by Status", ["status", "count"], rows)

        # Experiences by status
        cur.execute("""
            SELECT status, COUNT(*) AS n
            FROM pd.experiences
            GROUP BY status
            ORDER BY n DESC
        """)
        rows = cur.fetchall()
        write_csv(EDA_DIR / "experiences_by_status.csv", ["status", "count"], rows)
        lines += top_table_md("Experiences by Status", ["status", "count"], rows)

        # Top schools by applicant count
        cur.execute("""
            SELECT a.name_canonical AS school, COUNT(*) AS applicants
            FROM pd.applications ap
            JOIN pd.contacts c ON c.contact_id = ap.contact_id
            LEFT JOIN pd.accounts a ON a.account_id = c.primary_school_account_id
            WHERE a.account_type = 'academic_institution'
            GROUP BY a.name_canonical
            ORDER BY applicants DESC
        """)
        rows = cur.fetchall()
        write_csv(EDA_DIR / "top_schools_applicants.csv", ["school", "applicants"], rows)
        lines += top_table_md("Top Schools by Applicants", ["school", "applicants"], rows)

        # Placements by industry (work experiences)
        cur.execute("""
            SELECT COALESCE(acc.industry_primary, 'Unknown') AS industry, COUNT(*) AS n
            FROM pd.work_experiences we
            LEFT JOIN pd.accounts acc ON acc.account_id = we.company_account_id
            GROUP BY industry
            ORDER BY n DESC
        """)
        rows = cur.fetchall()
        write_csv(EDA_DIR / "placements_by_industry.csv", ["industry", "count"], rows)
        lines += top_table_md("Placements by Industry", ["industry", "count"], rows)

        # Sponsor funding totals
        cur.execute("""
            SELECT COALESCE(a.name_canonical, os.sponsor_display_name) AS sponsor, SUM(os.sponsored_amount_usd) AS total_usd
            FROM pd.opportunity_sponsorships os
            LEFT JOIN pd.accounts a ON a.account_id = os.sponsor_account_id
            GROUP BY COALESCE(a.name_canonical, os.sponsor_display_name)
            ORDER BY total_usd DESC
        """)
        rows = cur.fetchall()
        write_csv(EDA_DIR / "sponsor_funding_totals.csv", ["sponsor", "total_usd"], rows)
        lines += top_table_md("Sponsor Funding Totals", ["sponsor", "total_usd"], rows)

    EDA_MD.write_text("\n".join(lines))
    print(f"Wrote: {EDA_MD}")
    print(f"Wrote CSVs to: {EDA_DIR}")


if __name__ == "__main__":
    main()
