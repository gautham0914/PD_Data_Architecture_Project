import pandas as pd
from pathlib import Path
from src.db import connect

# Output paths
REPORT_DIR = Path("report")
EXCEL_PATH = REPORT_DIR / "data_export.xlsx"
CSV_DIR = REPORT_DIR / "csv"

TABLES = [
    "accounts",
    "account_aliases",
    "contacts",
    "opportunities",
    "opportunity_sponsorships",
    "applications",
    "experiences",
    "work_experiences",
    "partner_engagements",
    "outreach_messages",
    "etl_school_name_review_queue",
]

def export_excel_and_csv():
    REPORT_DIR.mkdir(exist_ok=True)
    CSV_DIR.mkdir(exist_ok=True)

    with connect() as conn:
        # ---- Excel export (single writer, clean close) ----
        writer = pd.ExcelWriter(EXCEL_PATH, engine="openpyxl")
        try:
            for table in TABLES:
                print(f"Exporting {table}...")
                df = pd.read_sql(f"SELECT * FROM pd.{table}", conn)

                # Excel cannot handle timezone-aware datetimes; drop tz info
                for col in df.columns:
                    try:
                        if pd.api.types.is_datetime64tz_dtype(df[col]):
                            df[col] = df[col].dt.tz_localize(None)
                    except Exception:
                        pass

                # Excel sheet name must be <= 31 chars
                sheet_name = table[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)

                # CSV backup (readable in VS Code)
                df.to_csv(CSV_DIR / f"{table}.csv", index=False)
        finally:
            writer.close()

    print("\n✅ Export complete")
    print(f"📘 Excel: {EXCEL_PATH}")
    print(f"📄 CSVs:  {CSV_DIR}/")

if __name__ == "__main__":
    export_excel_and_csv()

