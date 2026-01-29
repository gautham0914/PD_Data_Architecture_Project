-- Required questions as SQL (skeletons using pd.v_* views)
-- Adjust column names to your actual schema; these are illustrative.

-- 1) How many Student Alumni have completed the X program in Spring 2026?
-- Assumes experiences has status and links contact_id + opportunity_id; opportunities has term/name
select count(*) as alumni_completed
from pd.v_experiences e
join pd.v_opportunities o on o.id = e.opportunity_id
where o.term = 'Spring 2026'
  and e.status = 'Completed';

-- 2) How many all-time Student Applicants came from Hofstra University in 2024?
-- Uses applications.year and applications.school_name after ETL canonicalization.
select count(*) as hofstra_applicants_2024
from pd.v_applications a
where a.year = 2024
  and lower(a.school_name) like '%hofstra%';

-- 3) How many corporate partners sponsored programs in Fall 2025?
select count(distinct s.sponsor_account_id) as partners_fall_2025
from pd.v_opportunity_sponsorships s
join pd.v_opportunities o on o.id = s.opportunity_id
where o.term = 'Fall 2025';

-- 4) How many alumni from all Spring 2026 programs ended up at Real Estate Development firms?
-- Assumes work_experiences has employer_account_id + industry/category
select count(distinct e.contact_id) as spring_2026_alumni_in_re_dev
from pd.v_experiences e
join pd.v_opportunities o on o.id = e.opportunity_id
join pd.v_work_experiences w on w.contact_id = e.contact_id
join pd.v_accounts acc on acc.id = w.employer_account_id
where o.term = 'Spring 2026'
  and e.status = 'Completed'
  and lower(acc.industry) like '%real estate development%';

-- 5) Recommend next corporate partner to re-engage
-- Placeholder for LLM reasoning: rank by stale engagement + strong past outcomes
select acc.id as partner_id,
       acc.name as partner_name,
       max(pe.last_engaged_at) as last_engaged,
       sum(case when e.status = 'Completed' then 1 else 0 end) as alumni_outcomes
from pd.v_partner_engagements pe
join pd.v_accounts acc on acc.id = pe.account_id
left join pd.v_opportunity_sponsorships s on s.sponsor_account_id = acc.id
left join pd.v_experiences e on e.opportunity_id = s.opportunity_id
where acc.type = 'company'
  and (pe.last_engaged_at < (now() - interval '12 months'))
group by acc.id, acc.name
order by alumni_outcomes desc nulls last, last_engaged asc
limit 10;