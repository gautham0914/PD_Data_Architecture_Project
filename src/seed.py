from __future__ import annotations
import random
import uuid
from dataclasses import dataclass
import os
from datetime import date, datetime, timedelta, timezone
from faker import Faker
# psycopg v3: use cursor.executemany for batch inserts
from .db import connect
fake = Faker()
random.seed(42)
from .etl import canonicalize_raw_name
# -------------------------
# Scale (simple + strong but not massive)
# -------------------------
N_CONTACTS = 200
N_APPLICATIONS = 230
N_EXPERIENCES = 180
N_WORK_EXPERIENCES = 180
N_OUTREACH = 120
N_ENGAGEMENTS = 90

# Allow overriding via environment for faster runs
N_CONTACTS = int(os.getenv("N_CONTACTS", N_CONTACTS))
N_APPLICATIONS = int(os.getenv("N_APPLICATIONS", N_APPLICATIONS))
N_EXPERIENCES = int(os.getenv("N_EXPERIENCES", N_EXPERIENCES))
N_WORK_EXPERIENCES = int(os.getenv("N_WORK_EXPERIENCES", N_WORK_EXPERIENCES))
N_OUTREACH = int(os.getenv("N_OUTREACH", N_OUTREACH))
N_ENGAGEMENTS = int(os.getenv("N_ENGAGEMENTS", N_ENGAGEMENTS))


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def rand_dt(start: datetime, end: datetime) -> datetime:
    seconds = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, max(1, seconds)))


def rand_date(start: date, end: date) -> date:
    days = (end - start).days
    return start + timedelta(days=random.randint(0, max(1, days)))


@dataclass(frozen=True)
class Opp:
    opportunity_id: uuid.UUID
    name: str
    season: str
    year: int


# -------------------------
# Canonicalization helpers (simple + realistic)
# -------------------------
def slug_domain(name: str, tld: str) -> str:
    slug = "".join(ch for ch in name.lower() if ch.isalnum())
    return f"https://{slug}.{tld}"


def main() -> None:
    """
    FK-safe order:
      accounts -> aliases/review -> opportunities -> contacts -> applications -> experiences ->
      work_experiences -> sponsorships -> partner_engagements -> outreach_messages
    """
    with connect() as conn, conn.cursor() as cur:
        cur.execute("set search_path to pd, public;")

        # Reset (optional). Helps while iterating.
        for tbl in [
            "outreach_messages",
            "partner_engagements",
            "opportunity_sponsorships",
            "work_experiences",
            "experiences",
            "applications",
            "contacts",
            "opportunities",
            "account_aliases",
            "etl_school_name_review_queue",
            "accounts",
        ]:
            cur.execute(f"delete from pd.{tbl};")
        conn.commit()

        ids = seed_accounts(cur)
        seed_aliases_and_review_queue(
            cur,
            school_ids_by_name=ids["school_ids_by_name"],
            company_ids_by_name=ids["company_ids_by_name"],
        )
        opps = seed_opportunities(cur)

        contacts = seed_contacts(
            cur,
            school_ids=list(ids["school_ids_by_name"].values()),
            hofstra_id=ids["school_ids_by_name"]["Hofstra University"],
        )

        app_pairs = seed_applications(
            cur,
            all_contacts=contacts["all_contacts"],
            hofstra_students=contacts["hofstra_students"],
            opp_map=opps,
        )

        completed_spring_2026 = seed_experiences(cur, app_pairs=app_pairs, opp_map=opps)

        seed_work_experiences(
            cur,
            all_contacts=contacts["all_contacts"],
            completed_spring_2026=completed_spring_2026,
            redev_company_ids=ids["redev_company_ids"],
            other_company_ids=ids["other_company_ids"],
            company_id_to_canonical=ids["company_id_to_canonical"],
        )

        seed_sponsorships(cur, opp_map=opps, sponsor_ids=ids["sponsor_ids"])
        seed_partner_engagements(cur, sponsor_ids=ids["sponsor_ids"])
        seed_outreach(cur, sponsor_ids=ids["sponsor_ids"], contact_ids=contacts["all_contacts"])

        conn.commit()

    print("✅ Done: seeded Neon with instructor-aligned synthetic data (canonical + aliases + realistic raw inputs).")


# -------------------------
# ACCOUNTS (schools + companies + sponsors + employers)
# -------------------------
def seed_accounts(cur) -> dict:
    """
    accounts schema (after dropping name_raw):
      account_type: academic_institution | company | nonprofit | other
      name_canonical required
      industry_primary used for Q4 (Real Estate Development)
    """
    now = utcnow()

    # --- Schools (canonical names only) ---
    # Use official-ish canonicals (no short forms like NYU/UCLA/USC)
    schools_canonical = [
        "Hofstra University",
        "Boston University",
        "Rutgers University",
        "New York University",
        "Temple University",
        "Drexel University",
        "The Pennsylvania State University",
        "University of California, Los Angeles",
        "University of Southern California",
    ]

    # Expand to 25 institutions with realistic names
    while len(schools_canonical) < 25:
        schools_canonical.append(f"{fake.city()} {random.choice(['University', 'College'])}")

    school_ids_by_name: dict[str, uuid.UUID] = {}
    for nm in schools_canonical:
        aid = uuid.uuid4()
        school_ids_by_name[nm] = aid
        cur.execute(
            """
            insert into pd.accounts
              (account_id, account_type, name_canonical, website, linkedin_url, industry_primary, created_at)
            values (%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                aid,
                "academic_institution",
                nm,
                slug_domain(nm, "edu"),
                None,
                "Education",
                now,
            ),
        )

    # --- Sponsor companies (corporate partners) ---
    sponsor_specs = [
        ("CBRE", "Commercial Real Estate"),
        ("JLL", "Commercial Real Estate"),
        ("Related Companies", "Real Estate Development"),
        ("Hines", "Real Estate Development"),
    ]

    sponsor_ids: dict[str, uuid.UUID] = {}
    company_ids_by_name: dict[str, uuid.UUID] = {}
    company_id_to_canonical: dict[uuid.UUID, str] = {}

    redev_company_ids: list[uuid.UUID] = []
    other_company_ids: list[uuid.UUID] = []

    for name, industry in sponsor_specs:
        aid = uuid.uuid4()
        sponsor_ids[name] = aid
        company_ids_by_name[name] = aid
        company_id_to_canonical[aid] = name
        cur.execute(
            """
            insert into pd.accounts
              (account_id, account_type, name_canonical, website, linkedin_url, industry_primary, created_at)
            values (%s,%s,%s,%s,%s,%s,%s)
            """,
            (aid, "company", name, slug_domain(name, "com"), None, industry, now),
        )
        if industry == "Real Estate Development":
            redev_company_ids.append(aid)
        else:
            other_company_ids.append(aid)

    # --- Extra employers (richer work histories) ---
    extra_employers = [
        ("Boston Properties", "Real Estate Development"),
        ("Greystar", "Real Estate Development"),
        ("Deloitte", "Consulting"),
        ("Goldman Sachs", "Finance"),
        ("Blackstone", "Investment Management"),
    ]

    for name, industry in extra_employers:
        aid = uuid.uuid4()
        company_ids_by_name[name] = aid
        company_id_to_canonical[aid] = name
        cur.execute(
            """
            insert into pd.accounts
              (account_id, account_type, name_canonical, website, linkedin_url, industry_primary, created_at)
            values (%s,%s,%s,%s,%s,%s,%s)
            """,
            (aid, "company", name, slug_domain(name, "com"), None, industry, now),
        )
        if industry == "Real Estate Development":
            redev_company_ids.append(aid)
        else:
            other_company_ids.append(aid)

    return {
        "school_ids_by_name": school_ids_by_name,
        "company_ids_by_name": company_ids_by_name,
        "company_id_to_canonical": company_id_to_canonical,
        "sponsor_ids": sponsor_ids,
        "redev_company_ids": redev_company_ids,
        "other_company_ids": other_company_ids,
    }


# -------------------------
# ETL CLEANLINESS: ALIASES + REVIEW QUEUE (schools + companies)
# -------------------------
def seed_aliases_and_review_queue(cur, school_ids_by_name: dict[str, uuid.UUID], company_ids_by_name: dict[str, uuid.UUID]) -> None:
    """
    account_aliases has UNIQUE(alias_name) so don't repeat alias strings.
    review queue status default is 'pending' per schema.
    """
    now = utcnow()

    def add_alias(account_id: uuid.UUID, alias: str) -> None:
        cur.execute(
            """
            insert into pd.account_aliases (alias_id, account_id, alias_name, source_system, created_at)
            values (%s,%s,%s,%s,%s)
            """,
            (uuid.uuid4(), account_id, alias, "etl", now),
        )

    # --- School aliases (prove standardization beyond Hofstra) ---
    hofstra_id = school_ids_by_name["Hofstra University"]
    for a in ["Hofstra Univ.", "Hofstra College", "University of Hofstra", "HOFSTRA UNIVERSITY", "Hofstra U"]:
        add_alias(hofstra_id, a)

    nyu_id = school_ids_by_name["New York University"]
    for a in ["NYU", "New York Univ", "N.Y. University", "New York University (NY)"]:
        add_alias(nyu_id, a)

    psu_id = school_ids_by_name["The Pennsylvania State University"]
    for a in ["Penn State", "PSU", "PennSt", "Pennsylvania State University"]:
        add_alias(psu_id, a)

    ucla_id = school_ids_by_name["University of California, Los Angeles"]
    for a in ["UCLA", "UC Los Angeles", "University of California LA", "U.C.L.A."]:
        add_alias(ucla_id, a)

    usc_id = school_ids_by_name["University of Southern California"]
    for a in ["USC", "Southern Cal", "Univ of Southern California", "U.S.C."]:
        add_alias(usc_id, a)

    rutgers_id = school_ids_by_name["Rutgers University"]
    for a in ["Rutgers", "Rutgers - NB", "Rutgers Univ", "Rutgers University (New Brunswick)"]:
        add_alias(rutgers_id, a)

    # --- Company aliases (Clay / LinkedIn style messy names) ---
    cbre_id = company_ids_by_name["CBRE"]
    for a in ["CBRE Group", "CBRE Inc", "C.B.R.E.", "CBRE Group, Inc."]:
        add_alias(cbre_id, a)

    jll_id = company_ids_by_name["JLL"]
    for a in ["Jones Lang LaSalle", "Jones Lang LaSalle Inc", "JLL (US)", "J.L.L."]:
        add_alias(jll_id, a)

    hines_id = company_ids_by_name["Hines"]
    for a in ["Hines Interests", "Hines Real Estate", "Hines (Houston)"]:
        add_alias(hines_id, a)

    related_id = company_ids_by_name["Related Companies"]
    for a in ["Related", "The Related Companies", "Related Co."]:
        add_alias(related_id, a)

    # --- Review queue (unknown / ambiguous raw inputs) ---
    uncertain = [
        ("Hofstra Univrsity", "typo likely Hofstra"),
        ("Penn State - Main", "could be PSU main campus"),
        ("NYU Tandon", "sub-school; decide mapping policy"),
        ("Rutgers Newark", "campus variant; needs policy"),
        ("UCLA Extension", "extension program; confirm mapping policy"),
        ("CBRE Boston Office", "location noise; should map to CBRE"),
        ("JLL - LA", "location noise; should map to JLL"),
    ]
    for raw, note in uncertain:
        cur.execute(
            """
            insert into pd.etl_school_name_review_queue
              (queue_id, raw_school_name, suggested_account_id, confidence_score, status, notes, created_at, decided_at)
            values (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (uuid.uuid4(), raw, None, None, "pending", f"Needs human review: {note}", now, None),
        )


# -------------------------
# OPPORTUNITIES (parent-child + required names + patch)
# -------------------------
def seed_opportunities(cur) -> dict[str, Opp]:
    now = utcnow()
    opps: dict[str, Opp] = {}

    # Parent for Fundamentals
    fundamentals_parent_id = uuid.uuid4()
    cur.execute(
        """
        insert into pd.opportunities
          (opportunity_id, parent_opportunity_id, name, season, year, program_track, level, start_date, end_date, created_at)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            fundamentals_parent_id,
            None,
            "CRE Fundamentals",
            "Fall",
            2025,
            "CRE Fundamentals",
            None,
            date(2025, 9, 1),
            date(2025, 12, 15),
            now,
        ),
    )

    # Required child opportunities: Level 1/2/3
    for lvl in ["Level 1", "Level 2", "Level 3"]:
        oid = uuid.uuid4()
        name = f"CRE Fundamentals ({lvl})"
        cur.execute(
            """
            insert into pd.opportunities
              (opportunity_id, parent_opportunity_id, name, season, year, program_track, level, start_date, end_date, created_at)
            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (oid, fundamentals_parent_id, name, "Fall", 2025, "CRE Fundamentals", lvl, date(2025, 9, 10), date(2025, 12, 5), now),
        )
        opps[name] = Opp(oid, name, "Fall", 2025)

    # Required Spring 2026 internships
    required = [
        "Spring 2026 CRE Virtual Internship (Team CBRE Boston)",
        "Spring 2026 CRE Virtual Internship (Team JLL LA)",
    ]
    for nm in required:
        oid = uuid.uuid4()
        cur.execute(
            """
            insert into pd.opportunities
              (opportunity_id, parent_opportunity_id, name, season, year, program_track, level, start_date, end_date, created_at)
            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (oid, None, nm, "Spring", 2026, "CRE Virtual Internship", None, date(2026, 1, 20), date(2026, 5, 10), now),
        )
        opps[nm] = Opp(oid, nm, "Spring", 2026)

    # Extra programs (allowed)
    extras = [
        ("Spring 2026 CRE Virtual Internship (Team Related NYC)", "Spring", 2026),
        ("Fall 2025 Career Prep (Bootcamp)", "Fall", 2025),
        ("Spring 2026 Mentorship Program", "Spring", 2026),
    ]
    for nm, season, year in extras:
        oid = uuid.uuid4()
        start = date(year, 1, 15) if season == "Spring" else date(year, 9, 1)
        end = start + timedelta(days=90)
        cur.execute(
            """
            insert into pd.opportunities
              (opportunity_id, parent_opportunity_id, name, season, year, program_track, level, start_date, end_date, created_at)
            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (oid, None, nm, season, year, "Program", None, start, end, now),
        )
        opps[nm] = Opp(oid, nm, season, year)

    # ✅ Patch: old program for "not recent" proof
    old_name = "Fall 2024 CRE Virtual Internship (Team Hines Chicago)"
    old_id = uuid.uuid4()
    cur.execute(
        """
        insert into pd.opportunities
          (opportunity_id, parent_opportunity_id, name, season, year, program_track, level, start_date, end_date, created_at)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (old_id, None, old_name, "Fall", 2024, "CRE Virtual Internship", None, date(2024, 9, 10), date(2024, 12, 5), now),
    )
    opps[old_name] = Opp(old_id, old_name, "Fall", 2024)

    return opps


# -------------------------
# CONTACTS (students + academic)
# -------------------------
def seed_contacts(cur, school_ids: list[uuid.UUID], hofstra_id: uuid.UUID) -> dict:
    now = utcnow()
    all_contacts: list[uuid.UUID] = []
    hofstra_students: list[uuid.UUID] = []

    # Cache canonicalization for repeated raw school variants
    school_cache: dict[str, uuid.UUID] = {}
    rows: list[tuple] = []
    raw_variants = [
        "NYU",
        "Rutgers - NB",
        "Penn State",
        "Hofstra Univ.",
        "Temple Univ",
        "UCLA",
    ]

    for i in range(N_CONTACTS):
        cid = uuid.uuid4()
        is_student = i < int(N_CONTACTS * 0.88)
        contact_type = "student" if is_student else random.choice(["academic", "other"])

        first = fake.first_name()
        last = fake.last_name()
        raw_school = random.choice(raw_variants)

        if raw_school in school_cache:
            school_id = school_cache[raw_school]
        else:
            res = canonicalize_raw_name(
                cur,
                raw_school,
                account_type_hint="academic_institution",
                source_system="typeform",
            )
            school_id = res.account_id
            school_cache[raw_school] = school_id

        email = fake.email() if random.random() < 0.92 else None
        phone = fake.phone_number() if random.random() < 0.65 else None
        linkedin = (
            f"https://linkedin.com/in/{first.lower()}-{last.lower()}-{random.randint(100,999)}"
            if random.random() < 0.55 else None
        )

        rows.append(
            (
                cid,
                contact_type,
                first,
                last,
                email,
                phone,
                linkedin,
                school_id,
                now,
            )
        )

        all_contacts.append(cid)
        if is_student and school_id == hofstra_id:
            hofstra_students.append(cid)

    # Batch insert for speed
        cur.executemany(
                """
                insert into pd.contacts (
                    contact_id, contact_type, first_name, last_name,
                    email, phone, linkedin_url, primary_school_account_id, created_at
                ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                on conflict (contact_id) do nothing
                """,
                rows,
        )

    return {"all_contacts": all_contacts, "hofstra_students": hofstra_students}


# -------------------------
# APPLICATIONS (avoid UNIQUE(contact_id, opportunity_id) violation)
# -------------------------
def seed_applications(cur, all_contacts: list[uuid.UUID], hofstra_students: list[uuid.UUID], opp_map: dict[str, Opp]) -> list[tuple[uuid.UUID, uuid.UUID]]:
    now = utcnow()
    used_pairs: set[tuple[uuid.UUID, uuid.UUID]] = set()
    pairs: list[tuple[uuid.UUID, uuid.UUID]] = []
    opp_list = list(opp_map.values())

    statuses = ["started", "submitted", "reviewed", "accepted", "rejected", "waitlisted"]
    start_2024 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end_2024 = datetime(2024, 12, 31, 23, 59, tzinfo=timezone.utc)
    start_2025 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end_2026 = datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc)

    rows: list[tuple] = []
    # Guarantee Hofstra applicants in 2024
    for cid in hofstra_students:
        opp = random.choice(opp_list)
        key = (cid, opp.opportunity_id)
        if key in used_pairs:
            continue
        used_pairs.add(key)
        rows.append(
            (
                uuid.uuid4(), cid, opp.opportunity_id, random.choice(statuses), rand_dt(start_2024, end_2024), now, "webform"
            )
        )
        pairs.append(key)

    # Fill remaining random apps
    while len(pairs) < N_APPLICATIONS:
        cid = random.choice(all_contacts)
        opp = random.choice(opp_list)
        key = (cid, opp.opportunity_id)
        if key in used_pairs:
            continue
        used_pairs.add(key)

        rows.append(
            (
                uuid.uuid4(), cid, opp.opportunity_id, random.choice(statuses), rand_dt(start_2025, end_2026), now, "webform"
            )
        )
        pairs.append(key)

        cur.executemany(
                """
                insert into pd.applications (
                    application_id, contact_id, opportunity_id, status, submitted_at, created_at, source_system
                ) values (%s,%s,%s,%s,%s,%s,%s)
                on conflict (application_id) do nothing
                """,
                rows,
        )

    return pairs


# -------------------------
# EXPERIENCES (force Spring 2026 completions + old Hines completions)
# -------------------------
def seed_experiences(cur, app_pairs: list[tuple[uuid.UUID, uuid.UUID]], opp_map: dict[str, Opp]) -> list[uuid.UUID]:
    spring_ids = {
        opp_map["Spring 2026 CRE Virtual Internship (Team CBRE Boston)"].opportunity_id,
        opp_map["Spring 2026 CRE Virtual Internship (Team JLL LA)"].opportunity_id,
    }
    old_hines_id = opp_map["Fall 2024 CRE Virtual Internship (Team Hines Chicago)"].opportunity_id

    completed_spring: set[uuid.UUID] = set()
    forced_old_hines = 0

    statuses = ["intern", "completed", "interview_rejected", "dropped"]
    weights = [35, 40, 15, 10]

    random.shuffle(app_pairs)
    rows: list[tuple] = []
    for cid, oid in app_pairs[:N_EXPERIENCES]:
        if oid in spring_ids and len(completed_spring) < 25:
            status = "completed"
        elif oid == old_hines_id and forced_old_hines < 18:
            status = "completed"
            forced_old_hines += 1
        else:
            status = random.choices(statuses, weights=weights, k=1)[0]

        if oid in spring_ids and status == "completed":
            completed_spring.add(cid)

        rows.append(
            (
                uuid.uuid4(), cid, oid, status, utcnow() - timedelta(days=random.randint(10, 900)), "Seeded outcome."
            )
        )

        cur.executemany(
                """
                insert into pd.experiences (
                    experience_id, contact_id, opportunity_id, status, status_at, notes
                ) values (%s,%s,%s,%s,%s,%s)
                on conflict (experience_id) do nothing
                """,
                rows,
        )

    return list(completed_spring)


# -------------------------
# WORK EXPERIENCES (ensure Spring 2026 completers go to RE Dev)
# -------------------------
def seed_work_experiences(
    cur,
    all_contacts: list[uuid.UUID],
    completed_spring_2026: list[uuid.UUID],
    redev_company_ids: list[uuid.UUID],
    other_company_ids: list[uuid.UUID],
    company_id_to_canonical: dict[uuid.UUID, str],
) -> None:
    now = utcnow()

    # Raw variants (Clay / LinkedIn style) for canonical companies
    raw_company_variants: dict[str, list[str]] = {
        "CBRE": ["CBRE", "CBRE Group", "CBRE Inc", "C.B.R.E.", "CBRE Group, Inc."],
        "JLL": ["JLL", "Jones Lang LaSalle", "Jones Lang LaSalle Inc", "J.L.L.", "JLL (US)"],
        "Related Companies": ["Related", "Related Companies", "The Related Companies", "Related Co."],
        "Hines": ["Hines", "Hines Interests", "Hines Real Estate", "Hines (Houston)"],
        "Boston Properties": ["Boston Properties", "BXP", "Boston Props"],
        "Greystar Development": ["Greystar", "Greystar Real Estate", "Greystar Development"],
        "Deloitte": ["Deloitte", "Deloitte LLP"],
        "Goldman Sachs": ["Goldman Sachs", "Goldman Sachs Group"],
        "Blackstone": ["Blackstone", "Blackstone Group"],
    }

    def raw_variant_for_company(company_id: uuid.UUID) -> str:
        canonical = company_id_to_canonical.get(company_id, "Unknown")
        variants = raw_company_variants.get(canonical)
        return random.choice(variants) if variants else canonical

    def insert_one_work_exp(
        contact_id: uuid.UUID,
        comp_id: uuid.UUID,
        title: str,
        start_dt: date,
        end_dt: date | None,
        is_current: bool,
        city: str,
        state: str,
        description: str,
    ) -> None:
        raw_company = raw_variant_for_company(comp_id)

        # ✅ Canonicalization step: raw -> canonical account_id
        # NOTE: canonicalize_raw_name must return an object with .account_id (UUID)
        res = canonicalize_raw_name(
            cur,
            raw_company,
            account_type_hint="company",
            source_system="clay",
        )

        cur.execute(
            """
            insert into pd.work_experiences
              (work_experience_id, contact_id, company_account_id, company_name_raw, title,
               start_date, end_date, is_current, location_city, location_state,
               description, source_system, source_profile_url, source_payload, created_at)
            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                uuid.uuid4(),
                contact_id,
                res.account_id,   # ✅ canonical FK from canonicalizer
                raw_company,      # ✅ messy raw text
                title,
                start_dt,
                end_dt,
                is_current,
                city,
                state,
                description,
                "clay",
                None,
                None,
                now,
            ),
        )

    # Create a cache for company canonicalization to avoid repeated DB lookups
    company_cache: dict[str, uuid.UUID] = {}

    def canonical_company_id(raw_company: str) -> uuid.UUID:
        if raw_company in company_cache:
            return company_cache[raw_company]
        res = canonicalize_raw_name(
            cur,
            raw_company,
            account_type_hint="company",
            source_system="clay",
        )
        company_cache[raw_company] = res.account_id
        return res.account_id

    rows: list[tuple] = []

    # Force Spring 2026 completers into RE Dev firms
    for cid in completed_spring_2026:
        comp_id = random.choice(redev_company_ids)
        raw_company = raw_variant_for_company(comp_id)
        canon_id = canonical_company_id(raw_company)
        rows.append(
            (
                uuid.uuid4(),
                cid,
                canon_id,
                raw_company,
                random.choice(["Development Analyst", "Real Estate Analyst", "Analyst"]),
                date(2026, 6, 1),
                None,
                True,
                random.choice(["New York", "Boston", "Los Angeles"]),
                random.choice(["NY", "MA", "CA"]),
                "Post-program placement into Real Estate Development (seed).",
                "clay",
                None,
                None,
                now,
            )
        )

    remaining = max(0, N_WORK_EXPERIENCES - len(completed_spring_2026))
    for _ in range(remaining):
        cid = random.choice(all_contacts)
        comp_id = random.choice(redev_company_ids + other_company_ids)

        start_dt = rand_date(date(2022, 1, 1), date(2026, 1, 1))
        is_current = random.random() < 0.35
        end_dt = None if is_current else start_dt + timedelta(days=random.randint(60, 900))

        raw_company = raw_variant_for_company(comp_id)
        canon_id = canonical_company_id(raw_company)
        rows.append(
            (
                uuid.uuid4(),
                cid,
                canon_id,
                raw_company,
                random.choice(["Intern", "Analyst", "Associate", "Coordinator"]),
                start_dt,
                end_dt,
                is_current,
                fake.city(),
                fake.state_abbr(),
                fake.sentence(nb_words=14),
                "clay",
                None,
                None,
                now,
            )
        )

        cur.executemany(
                """
                insert into pd.work_experiences (
                    work_experience_id, contact_id, company_account_id, company_name_raw, title,
                    start_date, end_date, is_current, location_city, location_state,
                    description, source_system, source_profile_url, source_payload, created_at
                ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                on conflict (work_experience_id) do nothing
                """,
                rows,
        )

# -------------------------
# SPONSORSHIPS (PD = sponsor_account_id NULL)
# -------------------------
def seed_sponsorships(cur, opp_map: dict[str, Opp], sponsor_ids: dict[str, uuid.UUID]) -> None:
    now = utcnow()

    def ins(opp_name: str, sponsor_display: str, sponsor_account_id, amount: float) -> None:
        cur.execute(
            """
            insert into pd.opportunity_sponsorships
              (sponsorship_id, opportunity_id, sponsor_account_id, sponsor_display_name, sponsored_amount_usd, created_at)
            values (%s,%s,%s,%s,%s,%s)
            """,
            (uuid.uuid4(), opp_map[opp_name].opportunity_id, sponsor_account_id, sponsor_display, round(amount, 2), now),
        )

    # Required sponsor mapping:
    ins("Spring 2026 CRE Virtual Internship (Team CBRE Boston)", "CBRE", sponsor_ids["CBRE"], 85000)
    ins("Spring 2026 CRE Virtual Internship (Team JLL LA)", "JLL", sponsor_ids["JLL"], 80000)

    # Sponsor NOT in name -> PD sponsored
    for lvl in ["Level 1", "Level 2", "Level 3"]:
        ins(f"CRE Fundamentals ({lvl})", "Project Destined", None, 40000 + random.randint(0, 15000))

    # Sponsor appears in name (Related)
    if "Spring 2026 CRE Virtual Internship (Team Related NYC)" in opp_map:
        ins("Spring 2026 CRE Virtual Internship (Team Related NYC)", "Related Companies", sponsor_ids["Related Companies"], 90000)

    # Old Hines sponsorship
    ins("Fall 2024 CRE Virtual Internship (Team Hines Chicago)", "Hines", sponsor_ids["Hines"], 75000)


# -------------------------
# PARTNER ENGAGEMENTS (helps Q5)
# -------------------------
def seed_partner_engagements(cur, sponsor_ids: dict[str, uuid.UUID]) -> None:
    now = utcnow()
    types = ["program_sponsorship", "meeting", "outreach"]
    outcomes = ["positive", "no_response", "interested", "declined", "follow_up_needed"]

    stale_rows: list[tuple] = []
    for name in ["Hines", "Related Companies"]:
        for _ in range(8):
            stale_rows.append(
                (
                    uuid.uuid4(), sponsor_ids[name], rand_date(date(2023, 1, 1), date(2024, 12, 31)),
                    random.choice(types), "Stale but historically valuable partner.", random.choice(outcomes), now
                )
            )
        cur.executemany(
                """
                insert into pd.partner_engagements (
                    engagement_id, sponsor_account_id, engagement_date, engagement_type, notes, outcome, created_at
                ) values (%s,%s,%s,%s,%s,%s,%s)
                on conflict (engagement_id) do nothing
                """,
                stale_rows,
        )

    sponsor_list = list(sponsor_ids.values())
    rows: list[tuple] = []
    for _ in range(N_ENGAGEMENTS):
        rows.append(
            (
                uuid.uuid4(), random.choice(sponsor_list), rand_date(date(2024, 1, 1), date(2026, 1, 1)),
                random.choice(types), fake.sentence(nb_words=10), random.choice(outcomes), now
            )
        )
        cur.executemany(
                """
                insert into pd.partner_engagements (
                    engagement_id, sponsor_account_id, engagement_date, engagement_type, notes, outcome, created_at
                ) values (%s,%s,%s,%s,%s,%s,%s)
                on conflict (engagement_id) do nothing
                """,
                rows,
        )


# -------------------------
# OUTREACH MESSAGES (bonus CRM-like)
# -------------------------
def seed_outreach(cur, sponsor_ids: dict[str, uuid.UUID], contact_ids: list[uuid.UUID]) -> None:
    now = utcnow()
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = utcnow()
    sponsors = list(sponsor_ids.values())
    channels = ["email", "linkedin", "phone"]

    rows: list[tuple] = []
    for _ in range(N_OUTREACH):
        channel = random.choice(channels)
        subject = fake.sentence(nb_words=6) if channel != "phone" else None
        rows.append(
            (
                uuid.uuid4(), random.choice(sponsors), random.choice(contact_ids), channel, subject,
                fake.paragraph(nb_sentences=3), rand_dt(start, end), now
            )
        )
        cur.executemany(
                """
                insert into pd.outreach_messages (
                    message_id, sponsor_account_id, contact_id, channel, subject, body, sent_at, created_at
                ) values (%s,%s,%s,%s,%s,%s,%s,%s)
                on conflict (message_id) do nothing
                """,
                rows,
        )
if __name__ == "__main__":
    main()
    

