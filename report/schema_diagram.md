# Database Schema Diagram (pd)

This diagram reflects the core tables and key foreign keys used by the pipeline.

```mermaid
erDiagram
    accounts {
        uuid account_id PK
        text account_type
        text name_canonical
        text industry_primary
        text website
        text linkedin_url
    }

    contacts {
        uuid contact_id PK
        text contact_type
        text first_name
        text last_name
        text email
        text phone
        text linkedin_url
        uuid primary_school_account_id FK
    }

    opportunities {
        uuid opportunity_id PK
        uuid parent_opportunity_id FK
        text name
        text season
        int year
        text program_track
        text level
        date start_date
        date end_date
    }

    applications {
        uuid application_id PK
        uuid contact_id FK
        uuid opportunity_id FK
        text status
        timestamp submitted_at
        timestamp created_at
        text source_system
    }

    experiences {
        uuid experience_id PK
        uuid contact_id FK
        uuid opportunity_id FK
        text status
        timestamp status_at
        text notes
    }

    work_experiences {
        uuid work_experience_id PK
        uuid contact_id FK
        uuid company_account_id FK
        text company_name_raw
        text title
        date start_date
        date end_date
        boolean is_current
        text location_city
        text location_state
        text description
        text source_system
        text source_profile_url
        text source_payload
        timestamp created_at
    }

    opportunity_sponsorships {
        uuid sponsorship_id PK
        uuid opportunity_id FK
        uuid sponsor_account_id FK NULLABLE
        text sponsor_display_name
        numeric sponsored_amount_usd
        timestamp created_at
    }

    partner_engagements {
        uuid engagement_id PK
        uuid sponsor_account_id FK
        date engagement_date
        text engagement_type
        text notes
        text outcome
        timestamp created_at
    }

    outreach_messages {
        uuid message_id PK
        uuid sponsor_account_id FK
        uuid contact_id FK
        text channel
        text subject NULLABLE
        text body
        timestamp sent_at
        timestamp created_at
    }

    account_aliases {
        uuid alias_id PK
        uuid account_id FK
        text alias_name UNIQUE
        text source_system
        timestamp created_at
    }

    etl_school_name_review_queue {
        uuid queue_id PK
        text raw_school_name
        uuid suggested_account_id FK NULLABLE
        float confidence_score NULLABLE
        text status
        text notes
        timestamp created_at
        timestamp decided_at NULLABLE
    }

    entity_embeddings {
        uuid embedding_id PK
        text entity_type
        uuid entity_id
        vector embedding -- pgvector
        timestamp created_at
    }

    query_audit_log {
        uuid audit_id PK
        text user_id
        text query_text
        timestamp executed_at
        text outcome
    }

    %% Relationships
    contacts }o--|| accounts : primary_school_account_id
    applications }o--|| contacts : contact_id
    applications }o--|| opportunities : opportunity_id
    experiences }o--|| contacts : contact_id
    experiences }o--|| opportunities : opportunity_id
    work_experiences }o--|| contacts : contact_id
    work_experiences }o--|| accounts : company_account_id
    opportunity_sponsorships }o--|| opportunities : opportunity_id
    opportunity_sponsorships }o--o{ accounts : sponsor_account_id
    partner_engagements }o--|| accounts : sponsor_account_id
    outreach_messages }o--|| accounts : sponsor_account_id
    outreach_messages }o--|| contacts : contact_id
    account_aliases }o--|| accounts : account_id
    etl_school_name_review_queue }o--o{ accounts : suggested_account_id
    opportunities }o--o{ opportunities : parent_opportunity_id
```

Notes:
- Some foreign keys are intentionally nullable (e.g., `sponsor_account_id` for PD-sponsored programs).
- The pipeline enforces key FK safety where required (e.g., `work_experiences.company_account_id`).
