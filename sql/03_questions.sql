set search_path to pd, public;

-- Q1. How many Student Alumni completed Program X in Spring 2026?
select
    count(distinct e.contact_id) as completed_students,
    string_agg(
        distinct (c.first_name || ' ' || c.last_name),
        ', '
        order by (c.first_name || ' ' || c.last_name)
    ) as student_names
from pd.experiences e
join pd.opportunities o
  on o.opportunity_id = e.opportunity_id
join pd.opportunity_sponsorships os
  on os.opportunity_id = o.opportunity_id
join pd.contacts c
  on c.contact_id = e.contact_id
where o.season = 'Spring'
  and o.year = 2026
  and o.name ilike '%cre virtual internship%'
  and o.name ilike '%cbre%'
  and o.name ilike '%boston%'
  and os.sponsor_display_name ilike '%cbre%'
  and c.contact_type = 'student'
  and e.status = 'completed';

-- Q2) How many all time Student Applicants came from Hofstra University in 2024?
select
  count(distinct a.contact_id) as hofstra_applicants_2024
from pd.v_applications a
join pd.v_contacts c
  on c.contact_id = a.contact_id
join pd.v_accounts sch
  on sch.account_id = c.primary_school_account_id
where sch.name_canonical ilike '%hofstra%'
  and coalesce(a.submitted_at, a.created_at) >= date '2024-01-01'
  and coalesce(a.submitted_at, a.created_at) <  date '2025-01-01';


-- Q3) How many corporate partners sponsored programs in Fall 2025?
select
  count(distinct s.sponsor_account_id) as corporate_partners_fall_2025
from pd.v_opportunity_sponsorships s
join pd.v_opportunities o
  on o.opportunity_id = s.opportunity_id
where o.season = 'Fall'
  and o.year = 2025
  and s.sponsor_account_id is not null;

-- verify who sponsored Fall 2025
select
  o.name,
  o.season,
  o.year,
  s.sponsor_display_name,
  s.sponsor_account_id
from pd.v_opportunities o
left join pd.v_opportunity_sponsorships s
  on s.opportunity_id = o.opportunity_id
where o.season = 'Fall'
  and o.year = 2025
order by o.name, s.sponsor_display_name;

-- Checking who coorporate companies are in the data
select
  s.sponsor_display_name,
  a.account_type
from pd.v_opportunity_sponsorships s
join pd.accounts a
  on a.account_id = s.sponsor_account_id
group by 1,2
order by 2,1;

-- Q4) Can you tell me how many alumni from all Spring 2026 programs ended up at firms whose main focus in Real Estate development?
with spring_2026_alumni as (
  select distinct e.contact_id
  from pd.experiences e
  join pd.opportunities o
    on o.opportunity_id = e.opportunity_id
  join pd.contacts c
    on c.contact_id = e.contact_id
  where o.season = 'Spring'
    and o.year = 2026
    and e.status = 'completed'
    and c.contact_type = 'student'
),
latest_jobs as (
  select
    we.contact_id,
    we.company_account_id,
    row_number() over (
      partition by we.contact_id
      order by we.created_at desc
    ) as rn
  from pd.work_experiences we
)
select
  count(distinct lj.contact_id) as alumni_in_real_estate_development
from spring_2026_alumni a
join latest_jobs lj
  on lj.contact_id = a.contact_id
 and lj.rn = 1
join pd.accounts company
  on company.account_id = lj.company_account_id
where company.industry_primary = 'Real Estate Development';

-- Detail list: student → firm (Real Estate Development)
with spring_2026_alumni as (
  select distinct e.contact_id
  from pd.experiences e
  join pd.opportunities o
    on o.opportunity_id = e.opportunity_id
  join pd.contacts c
    on c.contact_id = e.contact_id
  where o.season = 'Spring'
    and o.year = 2026
    and e.status = 'completed'
    and c.contact_type = 'student'
),
latest_jobs as (
  select
    we.contact_id,
    we.company_account_id,
    row_number() over (
      partition by we.contact_id
      order by we.created_at desc
    ) as rn
  from pd.work_experiences we
)
select
  c.first_name,
  c.last_name,
  company.name_canonical as firm_name
from spring_2026_alumni a
join latest_jobs lj
  on lj.contact_id = a.contact_id
 and lj.rn = 1
join pd.contacts c
  on c.contact_id = a.contact_id
join pd.accounts company
  on company.account_id = lj.company_account_id
where company.industry_primary = 'Real Estate Development'
order by c.last_name, c.first_name;

-- Q5)What should the next corporate partner we re-engage with from the past (given we haven't done programs with them recently), and why? You may want to use an LLM.
select
  a.name_canonical as partner_name,
  max(o.year || ' ' || o.season) as last_program_term,
  count(distinct o.opportunity_id) as programs_sponsored
from pd.opportunity_sponsorships s
join pd.opportunities o
  on o.opportunity_id = s.opportunity_id
join pd.accounts a
  on a.account_id = s.sponsor_account_id
where a.account_type = 'company'
group by a.name_canonical
order by last_program_term asc;

-- Corporate partner outcome to strengthen the argument
select
  a.name_canonical as partner_name,
  count(*) filter (where e.status = 'completed') as completions,
  count(*) as total_participants
from pd.experiences e
join pd.opportunities o
  on o.opportunity_id = e.opportunity_id
join pd.opportunity_sponsorships s
  on s.opportunity_id = o.opportunity_id
join pd.accounts a
  on a.account_id = s.sponsor_account_id
where a.name_canonical = 'Hines'
group by a.name_canonical;