"""
Seed script (skeleton): generate synthetic data and load into Neon.

Constraints:
- Respect FK insert order
- Generate data to answer 5 questions
- Use Faker for realistic text; keep beginner-readable

TODOs:
- Define minimal column sets for each pd.* table (align with your actual schema)
- Implement generators: accounts (schools, companies), contacts, applications, opportunities,
  experiences, work_experiences, opportunity_sponsorships, partner_engagements
- Insert in order: accounts -> contacts -> opportunities -> applications -> experiences ->
  work_experiences -> opportunity_sponsorships/partner_engagements -> outreach_messages
- Include messy variants (e.g., Hofstra Univ., Hofstra University, Hofstra College) to test ETL
- Ensure Spring 2026 alumni outcomes include Real Estate Development firms
- Add stale engagements and strong past outcomes to support re-engagement recommendation
"""
from __future__ import annotations

from typing import Iterable

from faker import Faker

from .db import connect

fake = Faker()

# NOTE: Without exact column names, we provide function shapes and TODOs.


def insert_accounts() -> None:
    """Insert academic institutions and companies; include messy school variants."""
    # TODO: Adjust columns to match pd.accounts (e.g., id serial, name text, type text)
    schools = [
        "Hofstra University",
        "Hofstra Univ.",
        "Hofstra College",
        "University of Hofstra",  # intentionally messy
    ]
    companies = [
        "CBRE", "JLL", "Boston Properties", "Related Companies", "Hines"
    ]
    with connect() as conn, conn.cursor() as cur:
        for s in set(schools):
            cur.execute("insert into pd.accounts (name, type) values (%s, %s)", (s, "academic"))
        for c in companies:
            cur.execute("insert into pd.accounts (name, type) values (%s, %s)", (c, "company"))
        conn.commit()


def insert_opportunities() -> None:
    """Create opportunities across terms (Fall 2025, Spring 2026) with sponsors."""
    # TODO: Align with pd.opportunities schema (e.g., id, name, term, sponsor_type, sponsor_account_id)
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "insert into pd.opportunities (name, term, sponsor_type) values (%s, %s, %s)",
            ("Spring 2026 CRE Virtual Internship (Team CBRE Boston)", "Spring 2026", "company"),
        )
        cur.execute(
            "insert into pd.opportunities (name, term, sponsor_type) values (%s, %s, %s)",
            ("Spring 2026 CRE Virtual Internship (Team JLL LA)", "Spring 2026", "company"),
        )
        cur.execute(
            "insert into pd.opportunities (name, term, sponsor_type) values (%s, %s, %s)",
            ("CRE Fundamentals (Level 1)", "Fall 2025", "pd"),
        )
        conn.commit()


def insert_contacts_and_applications() -> None:
    """Create student contacts and applications, including Hofstra 2024 applicants."""
    # TODO: Align with pd.contacts, pd.applications schema
    with connect() as conn, conn.cursor() as cur:
        for _ in range(50):
            name = fake.name()
            email = fake.email()
            # Randomly assign a school (including messy variants)
            school = fake.random_element(elements=(
                "Hofstra University", "Hofstra Univ.", "University of Hofstra", "Boston University"
            ))
            cur.execute(
                "insert into pd.contacts (name, email, type) values (%s, %s, %s) returning id",
                (name, email, "student"),
            )
            contact_id = cur.fetchone()[0]
            cur.execute(
                "insert into pd.applications (contact_id, school_name, year) values (%s, %s, %s)",
                (contact_id, school, 2024),
            )
        conn.commit()


def insert_experiences_and_outcomes() -> None:
    """Create experiences (completed/alumni) and work outcomes for Spring 2026 alumni."""
    # TODO: Align with pd.experiences, pd.work_experiences schema
    # Ensure some alumni ended up at Real Estate Development firms
    pass  # TODO


def insert_partnerships_and_engagements() -> None:
    """Create sponsorships and partner engagement history to support re-engagement recommendations."""
    # TODO: Align with pd.opportunity_sponsorships, pd.partner_engagements schema
    pass  # TODO


def insert_outreach_messages() -> None:
    """Optional: seed outreach messages for future AI tooling demos."""
    # TODO: Align with pd.outreach_messages schema (to be added)
    pass  # TODO


def main() -> None:
    """Run all seed steps in FK-safe order."""
    insert_accounts()
    insert_opportunities()
    insert_contacts_and_applications()
    insert_experiences_and_outcomes()
    insert_partnerships_and_engagements()
    insert_outreach_messages()


if __name__ == "__main__":
    main()