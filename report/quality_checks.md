# Data Quality Checks

## Unacceptable Nulls (PKs + FKs) — FAIL
| check | count |
|---|---:|
| account_aliases.account_id | 0 |
| account_aliases.alias_id | 0 |
| accounts.account_id | 0 |
| applications.application_id | 0 |
| applications.contact_id | 0 |
| applications.opportunity_id | 0 |
| contacts.contact_id | 0 |
| contacts.primary_school_account_id | 38 |
| entity_embeddings.embedding_id | 0 |
| etl_school_name_review_queue.queue_id | 0 |
| etl_school_name_review_queue.suggested_account_id | 8 |
| experiences.contact_id | 0 |
| experiences.experience_id | 0 |
| experiences.opportunity_id | 0 |
| opportunities.opportunity_id | 0 |
| opportunities.parent_opportunity_id | 7 |
| opportunity_sponsorships.opportunity_id | 0 |
| opportunity_sponsorships.sponsor_account_id | 3 |
| opportunity_sponsorships.sponsorship_id | 0 |
| outreach_messages.contact_id | 0 |
| outreach_messages.message_id | 0 |
| outreach_messages.sponsor_account_id | 0 |
| partner_engagements.engagement_id | 0 |
| partner_engagements.sponsor_account_id | 0 |
| query_audit_log.query_id | 0 |
| work_experiences.company_account_id | 0 |
| work_experiences.contact_id | 0 |
| work_experiences.work_experience_id | 0 |

## FK Orphans — PASS
| check | count |
|---|---:|
| account_aliases.account_id -> accounts.account_id | 0 |
| applications.contact_id -> contacts.contact_id | 0 |
| applications.opportunity_id -> opportunities.opportunity_id | 0 |
| contacts.primary_school_account_id -> accounts.account_id | 0 |
| etl_school_name_review_queue.suggested_account_id -> accounts.account_id | 0 |
| experiences.contact_id -> contacts.contact_id | 0 |
| experiences.opportunity_id -> opportunities.opportunity_id | 0 |
| opportunities.parent_opportunity_id -> opportunities.opportunity_id | 0 |
| opportunity_sponsorships.opportunity_id -> opportunities.opportunity_id | 0 |
| opportunity_sponsorships.sponsor_account_id -> accounts.account_id | 0 |
| outreach_messages.contact_id -> contacts.contact_id | 0 |
| outreach_messages.sponsor_account_id -> accounts.account_id | 0 |
| partner_engagements.sponsor_account_id -> accounts.account_id | 0 |
| work_experiences.company_account_id -> accounts.account_id | 0 |
| work_experiences.contact_id -> contacts.contact_id | 0 |

## Duplicate Keys — PASS
| check | count |
|---|---:|
| applications(contact_id,opportunity_id) | 0 |