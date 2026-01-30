# Null Profile

## account_aliases
| column | nulls | total | % |
|---|---:|---:|---:|
| alias_id | 0 | 53 | 0.00 |
| account_id | 0 | 53 | 0.00 |
| alias_name | 0 | 53 | 0.00 |
| source_system | 0 | 53 | 0.00 |
| created_at | 0 | 53 | 0.00 |

## accounts
| column | nulls | total | % |
|---|---:|---:|---:|
| account_id | 0 | 34 | 0.00 |
| account_type | 0 | 34 | 0.00 |
| name_canonical | 0 | 34 | 0.00 |
| website | 0 | 34 | 0.00 |
| linkedin_url | 34 | 34 | 100.00 |
| industry_primary | 0 | 34 | 0.00 |
| created_at | 0 | 34 | 0.00 |

## applications
| column | nulls | total | % |
|---|---:|---:|---:|
| application_id | 0 | 230 | 0.00 |
| contact_id | 0 | 230 | 0.00 |
| opportunity_id | 0 | 230 | 0.00 |
| status | 0 | 230 | 0.00 |
| submitted_at | 0 | 230 | 0.00 |
| created_at | 0 | 230 | 0.00 |
| source_system | 0 | 230 | 0.00 |

## contacts
| column | nulls | total | % |
|---|---:|---:|---:|
| contact_id | 0 | 200 | 0.00 |
| contact_type | 0 | 200 | 0.00 |
| first_name | 0 | 200 | 0.00 |
| last_name | 0 | 200 | 0.00 |
| email | 16 | 200 | 8.00 |
| phone | 67 | 200 | 33.50 |
| linkedin_url | 95 | 200 | 47.50 |
| primary_school_account_id | 38 | 200 | 19.00 |
| created_at | 0 | 200 | 0.00 |

## entity_embeddings
| column | nulls | total | % |
|---|---:|---:|---:|
| embedding_id | 0 | 0 | 0.00 |
| entity_type | 0 | 0 | 0.00 |
| entity_id | 0 | 0 | 0.00 |
| content | 0 | 0 | 0.00 |
| embedding | 0 | 0 | 0.00 |
| created_at | 0 | 0 | 0.00 |

## etl_school_name_review_queue
| column | nulls | total | % |
|---|---:|---:|---:|
| queue_id | 0 | 8 | 0.00 |
| raw_school_name | 0 | 8 | 0.00 |
| suggested_account_id | 8 | 8 | 100.00 |
| confidence_score | 8 | 8 | 100.00 |
| status | 0 | 8 | 0.00 |
| notes | 0 | 8 | 0.00 |
| created_at | 0 | 8 | 0.00 |
| decided_at | 8 | 8 | 100.00 |

## experiences
| column | nulls | total | % |
|---|---:|---:|---:|
| experience_id | 0 | 180 | 0.00 |
| contact_id | 0 | 180 | 0.00 |
| opportunity_id | 0 | 180 | 0.00 |
| status | 0 | 180 | 0.00 |
| status_at | 0 | 180 | 0.00 |
| notes | 0 | 180 | 0.00 |

## opportunities
| column | nulls | total | % |
|---|---:|---:|---:|
| opportunity_id | 0 | 10 | 0.00 |
| parent_opportunity_id | 7 | 10 | 70.00 |
| name | 0 | 10 | 0.00 |
| season | 0 | 10 | 0.00 |
| year | 0 | 10 | 0.00 |
| program_track | 0 | 10 | 0.00 |
| level | 7 | 10 | 70.00 |
| start_date | 0 | 10 | 0.00 |
| end_date | 0 | 10 | 0.00 |
| created_at | 0 | 10 | 0.00 |

## opportunity_sponsorships
| column | nulls | total | % |
|---|---:|---:|---:|
| sponsorship_id | 0 | 7 | 0.00 |
| opportunity_id | 0 | 7 | 0.00 |
| sponsor_account_id | 3 | 7 | 42.86 |
| sponsor_display_name | 0 | 7 | 0.00 |
| sponsored_amount_usd | 0 | 7 | 0.00 |
| created_at | 0 | 7 | 0.00 |

## outreach_messages
| column | nulls | total | % |
|---|---:|---:|---:|
| message_id | 0 | 120 | 0.00 |
| sponsor_account_id | 0 | 120 | 0.00 |
| contact_id | 0 | 120 | 0.00 |
| channel | 0 | 120 | 0.00 |
| subject | 41 | 120 | 34.17 |
| body | 0 | 120 | 0.00 |
| sent_at | 0 | 120 | 0.00 |
| created_at | 0 | 120 | 0.00 |

## partner_engagements
| column | nulls | total | % |
|---|---:|---:|---:|
| engagement_id | 0 | 122 | 0.00 |
| sponsor_account_id | 0 | 122 | 0.00 |
| engagement_date | 0 | 122 | 0.00 |
| engagement_type | 0 | 122 | 0.00 |
| notes | 0 | 122 | 0.00 |
| outcome | 0 | 122 | 0.00 |
| created_at | 0 | 122 | 0.00 |

## query_audit_log
| column | nulls | total | % |
|---|---:|---:|---:|
| query_id | 0 | 0 | 0.00 |
| user_question | 0 | 0 | 0.00 |
| generated_sql | 0 | 0 | 0.00 |
| is_validated | 0 | 0 | 0.00 |
| validation_notes | 0 | 0 | 0.00 |
| executed_at | 0 | 0 | 0.00 |
| created_at | 0 | 0 | 0.00 |

## work_experiences
| column | nulls | total | % |
|---|---:|---:|---:|
| work_experience_id | 0 | 180 | 0.00 |
| contact_id | 0 | 180 | 0.00 |
| company_account_id | 0 | 180 | 0.00 |
| company_name_raw | 0 | 180 | 0.00 |
| title | 0 | 180 | 0.00 |
| start_date | 0 | 180 | 0.00 |
| end_date | 77 | 180 | 42.78 |
| is_current | 0 | 180 | 0.00 |
| location_city | 0 | 180 | 0.00 |
| location_state | 0 | 180 | 0.00 |
| description | 0 | 180 | 0.00 |
| source_system | 0 | 180 | 0.00 |
| source_profile_url | 180 | 180 | 100.00 |
| source_payload | 180 | 180 | 100.00 |
| created_at | 0 | 180 | 0.00 |