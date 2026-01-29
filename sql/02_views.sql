-- Read-only reporting views (pd.v_*)
-- Keep beginner-friendly: select * passthroughs as a starting point.

create schema if not exists pd;

create or replace view pd.v_accounts as
select * from pd.accounts;

create or replace view pd.v_contacts as
select * from pd.contacts;

create or replace view pd.v_opportunities as
select * from pd.opportunities;

create or replace view pd.v_applications as
select * from pd.applications;

create or replace view pd.v_experiences as
select * from pd.experiences;

create or replace view pd.v_work_experiences as
select * from pd.work_experiences;

create or replace view pd.v_opportunity_sponsorships as
select * from pd.opportunity_sponsorships;

create or replace view pd.v_partner_engagements as
select * from pd.partner_engagements;

create or replace view pd.v_account_aliases as
select * from pd.account_aliases;

create or replace view pd.v_entity_embeddings as
select * from pd.entity_embeddings;

create or replace view pd.v_query_audit_log as
select * from pd.query_audit_log;

create or replace view pd.v_outreach_messages as
select * from pd.outreach_messages;