-- 1) Spring 2026: completed alumni for a specific program X
select count(distinct e.contact_id) as alumni_completed
from pd.v_experiences e
join pd.v_opportunities o
  on o.opportunity_id = e.opportunity_id
where o.season = 'Spring'
  and o.year = 2026
  and o.name = 'Spring 2026 CRE Virtual Internship (Team CBRE Boston)'
  and lower(e.status) = 'completed';


-- 2) Hofstra applicants in 2024 (school comes from contacts -> accounts)
select count(*) as hofstra_applicants_2024
from pd.v_applications a
join pd.v_contacts c
  on c.contact_id = a.contact_id
join pd.v_accounts sch
  on sch.account_id = c.primary_school_account_id
where lower(sch.name_canonical) like '%hofstra%'
  and coalesce(a.submitted_at, a.created_at) >= '2024-01-01'
  and coalesce(a.submitted_at, a.created_at) <  '2025-01-01';


-- 3) Corporate partners who sponsored Fall 2025 programs
select count(distinct s.sponsor_account_id) as corporate_partners_fall_2025
from pd.v_opportunity_sponsorships s
join pd.v_opportunities o
  on o.opportunity_id = s.opportunity_id
where o.season = 'Fall'
  and o.year = 2025
  and s.sponsor_account_id is not null;


-- 4) Spring 2026 completed alumni who ended up at Real Estate Development firms
select count(distinct e.contact_id) as spring_2026_alumni_in_re_dev
from pd.v_experiences e
join pd.v_opportunities o
  on o.opportunity_id = e.opportunity_id
join pd.v_work_experiences w
  on w.contact_id = e.contact_id
join pd.v_accounts comp
  on comp.account_id = w.company_account_id
where o.season = 'Spring'
  and o.year = 2026
  and lower(e.status) = 'completed'
  and lower(comp.industry_primary) like '%real estate development%';


-- 5) Next partner to re-engage: stale engagement + good outcomes (simple ranking)
with last_touch as (
  select sponsor_account_id, max(engagement_date) as last_engagement_date
  from pd.v_partner_engagements
  group by sponsor_account_id
),
outcomes as (
  select s.sponsor_account_id, count(distinct e.contact_id) as completions
  from pd.v_opportunity_sponsorships s
  join pd.v_opportunities o
    on o.opportunity_id = s.opportunity_id
  left join pd.v_experiences e
    on e.opportunity_id = o.opportunity_id
   and lower(e.status) = 'completed'
  where o.season = 'Spring'
    and o.year = 2026
    and s.sponsor_account_id is not null
  group by s.sponsor_account_id
)
select
  a.account_id,
  a.name_canonical as partner_name,
  lt.last_engagement_date,
  coalesce(o.completions, 0) as spring_2026_completions
from last_touch lt
join pd.v_accounts a
  on a.account_id = lt.sponsor_account_id
left join outcomes o
  on o.sponsor_account_id = lt.sponsor_account_id
where a.account_type = 'company'
  and lt.last_engagement_date < (current_date - interval '12 months')
order by coalesce(o.completions, 0) desc, lt.last_engagement_date asc
limit 10;
