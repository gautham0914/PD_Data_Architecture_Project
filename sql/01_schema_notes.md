# Schema Notes (pd)

This schema maps the Round 2 objects to tables:

- Applications → pd.applications: student applications to programs/opportunities
- Opportunities → pd.opportunities: distinct programs; include term (e.g., Spring 2026), sponsor info
- Contacts → pd.contacts: students, academic contacts, etc. (use `type` for role)
- Accounts → pd.accounts: schools, companies (use `type` to distinguish)
- Experiences → pd.experiences: outcomes per contact per opportunity (e.g., Completed, Rejected)
- Work Experiences → pd.work_experiences: LinkedIn-like job history for contacts
- Opportunity Sponsorships → pd.opportunity_sponsorships: link opportunities to sponsoring accounts
- Partner Engagements → pd.partner_engagements: history (dates, touchpoints, outcomes)
- Account Aliases → pd.account_aliases: alias mapping (raw variant → canonical account)
- Entity Embeddings → pd.entity_embeddings: pgvector for AI similarity (entities + embeddings)
- Query Audit Log → pd.query_audit_log: logs safe SQL usage
- ETL Review Queue → pd.etl_school_name_review_queue: human review backlog for school names
- Outreach Messages → pd.outreach_messages: messages for AI tools and engagement workflows

ETL canonicalization: we normalize raw `school_name` in applications, fuzzy-match to `accounts`,
upsert aliases, and queue unsure cases for review.

AI-ready features: expose read-only views `pd.v_*` and use pgvector in `pd.entity_embeddings`.