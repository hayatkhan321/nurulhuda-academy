-- Classroom monitoring, code of conduct, learning choice, language checks, memberships, education support.
-- Additive only: new columns have defaults, nothing is dropped or rewritten. Safe to run twice.
alter table families add column if not exists membership varchar(10) not null default 'standard';
alter table families add column if not exists membership_since timestamptz;
alter table students add column if not exists lesson_format varchar(10) not null default 'academic';
alter table teachers add column if not exists conduct_version varchar(20);
alter table teachers add column if not exists conduct_accepted_at timestamptz;
alter table teachers add column if not exists tier varchar(10) not null default 'standard';
alter table teachers add column if not exists qualifications_verified boolean not null default false;
alter table teachers add column if not exists experience_years integer;
alter table teachers add column if not exists english_verified boolean not null default false;
alter table teachers add column if not exists urdu_verified boolean not null default false;
alter table teachers add column if not exists arabic_verified boolean not null default false;
alter table teachers add column if not exists lang_note varchar(200);
alter table promo_codes add column if not exists tiers varchar(40);
alter table invoices add column if not exists tier varchar(10) not null default 'standard';

create table if not exists classroom_events (
  id serial primary key,
  created_at timestamptz not null default now(),
  class_id integer not null references class_sessions(id),
  role varchar(10) not null,
  person varchar(120) not null,
  kind varchar(10) not null,
  started_at timestamptz not null,
  ended_at timestamptz,
  seconds integer,
  cause varchar(20),
  announced boolean not null default false
);
create index if not exists ix_classroom_events_class on classroom_events (class_id);

create table if not exists conduct_reports (
  id serial primary key,
  created_at timestamptz not null default now(),
  family_id integer not null references families(id),
  teacher_id integer not null references teachers(id),
  class_id integer references class_sessions(id),
  category varchar(20) not null,
  details text not null,
  status varchar(12) not null default 'open',
  admin_notes text,
  closed_at timestamptz
);
create index if not exists ix_conduct_reports_family on conduct_reports (family_id);
create index if not exists ix_conduct_reports_teacher on conduct_reports (teacher_id);

create table if not exists support_applications (
  id serial primary key,
  created_at timestamptz not null default now(),
  family_id integer not null references families(id),
  student_id integer not null references students(id),
  reason text not null,
  lessons_asked integer not null,
  status varchar(10) not null default 'pending',
  lessons_approved integer not null default 0,
  share integer not null default 100,
  admin_note varchar(500),
  decided_at timestamptz
);
create index if not exists ix_support_applications_family on support_applications (family_id);
create index if not exists ix_support_applications_student on support_applications (student_id);

create table if not exists sponsor_purchases (
  id serial primary key,
  created_at timestamptz not null default now(),
  number varchar(20) not null unique,
  family_id integer not null references families(id),
  coins integer not null,
  currency varchar(3) not null,
  unit_price numeric(10,2) not null,
  total numeric(10,2) not null,
  status varchar(12) not null default 'pending',
  method varchar(20),
  payer_reference varchar(200),
  reported_at timestamptz,
  paid_at timestamptz,
  amount_received numeric(10,2),
  credit_entry_id integer references credit_entries(id)
);
create index if not exists ix_sponsor_purchases_family on sponsor_purchases (family_id);

create table if not exists sponsor_entries (
  id serial primary key,
  created_at timestamptz not null default now(),
  family_id integer references families(id),
  coins integer not null,
  kind varchar(12) not null,
  purchase_id integer references sponsor_purchases(id),
  application_id integer references support_applications(id),
  note varchar(300)
);
create index if not exists ix_sponsor_entries_family on sponsor_entries (family_id);
create index if not exists ix_sponsor_entries_application on sponsor_entries (application_id);

alter table classroom_events enable row level security;
alter table conduct_reports enable row level security;
alter table support_applications enable row level security;
alter table sponsor_purchases enable row level security;
alter table sponsor_entries enable row level security;
