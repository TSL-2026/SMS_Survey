-- ============================================================
-- The Safety Layer — Multi-Tenant Schema v2.0
-- Run this entire file in Supabase SQL Editor
-- WARNING: If upgrading from v1, see migration notes at bottom
-- ============================================================

-- ============================================================
-- 1. AIRLINES
-- ============================================================
CREATE TABLE IF NOT EXISTS airlines (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT NOT NULL,                    -- "SITA AIR"
    name_local   TEXT,                             -- "सिता एयर" (local language)
    slug         TEXT NOT NULL UNIQUE,             -- "sita-air" → survey URL
    logo_url     TEXT,                             -- hosted image URL
    country      TEXT,
    icao_code    TEXT,                             -- e.g. "SNY"
    iata_code    TEXT,                             -- e.g. "S7"
    invite_code  TEXT NOT NULL UNIQUE DEFAULT substring(gen_random_uuid()::text, 1, 8),
    status       TEXT NOT NULL DEFAULT 'invited'   -- invited | active | suspended
                 CHECK (status IN ('invited','active','suspended')),
    plan         TEXT NOT NULL DEFAULT 'free'      -- free | pro
                 CHECK (plan IN ('free','pro')),
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    activated_at TIMESTAMPTZ
);

-- ============================================================
-- 2. AIRLINE USERS (Safety Managers)
-- ============================================================
-- Links Supabase Auth users to their airline
CREATE TABLE IF NOT EXISTS airline_users (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    airline_id   UUID NOT NULL REFERENCES airlines(id) ON DELETE CASCADE,
    role         TEXT NOT NULL DEFAULT 'admin'
                 CHECK (role IN ('admin','viewer')),
    full_name    TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 3. SURVEY VERSIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS survey_versions (
    id          SERIAL PRIMARY KEY,
    version     TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO survey_versions (version, description)
VALUES ('v2.0', 'Multi-tenant launch — ICAO Annex 19 aligned, revised Q9/Q10, new SPI/risk/peer questions')
ON CONFLICT (version) DO NOTHING;

-- ============================================================
-- 4. OPTIONAL QUESTIONS (per-airline extras)
-- ============================================================
CREATE TABLE IF NOT EXISTS optional_questions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    airline_id    UUID NOT NULL REFERENCES airlines(id) ON DELETE CASCADE,
    section       TEXT NOT NULL CHECK (section IN ('A','B','C','D')),
    question_text TEXT NOT NULL,
    question_local TEXT,                           -- local language version
    is_active     BOOLEAN DEFAULT true,
    sort_order    INTEGER DEFAULT 99,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 5. RESPONSES (multi-tenant version)
-- ============================================================
CREATE TABLE IF NOT EXISTS responses (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    airline_id           UUID NOT NULL REFERENCES airlines(id),
    version_id           INTEGER REFERENCES survey_versions(id) DEFAULT 1,
    submitted_at         TIMESTAMPTZ DEFAULT NOW(),

    -- Demographics (fully anonymous — no identity fields)
    department           TEXT NOT NULL,
    employee_category    TEXT NOT NULL,
    years_experience     TEXT NOT NULL,
    language_used        TEXT NOT NULL DEFAULT 'en',  -- 'en' | 'ne'

    -- PILLAR 1: Safety Policy & Objectives
    q1_aware             BOOLEAN NOT NULL,
    q2                   SMALLINT CHECK (q2 BETWEEN 1 AND 5),
    q3                   SMALLINT CHECK (q3 BETWEEN 1 AND 5),
    q4                   SMALLINT CHECK (q4 BETWEEN 1 AND 5),
    q5_spi               SMALLINT CHECK (q5_spi BETWEEN 1 AND 5),

    -- PILLAR 2: Safety Risk Management
    q6                   SMALLINT CHECK (q6 BETWEEN 1 AND 5),
    q7                   SMALLINT CHECK (q7 BETWEEN 1 AND 5),
    q8                   SMALLINT CHECK (q8 BETWEEN 1 AND 5),
    q9                   SMALLINT CHECK (q9 BETWEEN 1 AND 5),
    q10                  SMALLINT CHECK (q10 BETWEEN 1 AND 5),
    q11                  SMALLINT CHECK (q11 BETWEEN 1 AND 5),
    q12_risk_assess      SMALLINT CHECK (q12_risk_assess BETWEEN 1 AND 5),
    q13_action_inform    SMALLINT CHECK (q13_action_inform BETWEEN 1 AND 5),

    -- PILLAR 3: Safety Assurance
    q14                  SMALLINT CHECK (q14 BETWEEN 1 AND 5),
    q15                  SMALLINT CHECK (q15 BETWEEN 1 AND 5),
    q16                  SMALLINT CHECK (q16 BETWEEN 1 AND 5),
    q19_invest_outcome   SMALLINT CHECK (q19_invest_outcome BETWEEN 1 AND 5),
    q20_corrective       SMALLINT CHECK (q20_corrective BETWEEN 1 AND 5),

    -- PILLAR 4: Safety Promotion
    q17                  SMALLINT CHECK (q17 BETWEEN 1 AND 5),
    q18                  SMALLINT CHECK (q18 BETWEEN 1 AND 5),
    q21                  SMALLINT CHECK (q21 BETWEEN 1 AND 5),
    q22                  SMALLINT CHECK (q22 BETWEEN 1 AND 5),
    q23_peer             SMALLINT CHECK (q23_peer BETWEEN 1 AND 5),

    -- Open feedback
    q24_comments         TEXT
);

-- ============================================================
-- 6. ROW LEVEL SECURITY
-- ============================================================
ALTER TABLE airlines          ENABLE ROW LEVEL SECURITY;
ALTER TABLE airline_users     ENABLE ROW LEVEL SECURITY;
ALTER TABLE survey_versions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE optional_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE responses         ENABLE ROW LEVEL SECURITY;

-- Helper function: get airline_id for the logged-in user
CREATE OR REPLACE FUNCTION get_my_airline_id()
RETURNS UUID AS $$
    SELECT airline_id FROM airline_users
    WHERE auth_user_id = auth.uid()
    LIMIT 1;
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- Helper function: check if user is platform admin
-- Add your Supabase auth user UUID here after first login
CREATE OR REPLACE FUNCTION is_platform_admin()
RETURNS BOOLEAN AS $$
    SELECT auth.uid() IN (
        'REPLACE-WITH-YOUR-SUPABASE-AUTH-USER-UUID'::uuid
    );
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- ── AIRLINES ──
-- Public can read airline by slug (needed for survey branding)
CREATE POLICY "Public can read active airlines by slug"
    ON airlines FOR SELECT TO anon
    USING (status = 'active');

-- Authenticated managers can read their own airline
CREATE POLICY "Managers read own airline"
    ON airlines FOR SELECT TO authenticated
    USING (id = get_my_airline_id() OR is_platform_admin());

-- Platform admin can do everything
CREATE POLICY "Admin full access airlines"
    ON airlines FOR ALL TO authenticated
    USING (is_platform_admin())
    WITH CHECK (is_platform_admin());

-- ── AIRLINE USERS ──
CREATE POLICY "Users read own record"
    ON airline_users FOR SELECT TO authenticated
    USING (auth_user_id = auth.uid() OR is_platform_admin());

CREATE POLICY "Admin full access airline_users"
    ON airline_users FOR ALL TO authenticated
    USING (is_platform_admin())
    WITH CHECK (is_platform_admin());

-- ── SURVEY VERSIONS ──
CREATE POLICY "Anyone can read versions"
    ON survey_versions FOR SELECT
    USING (true);

-- ── OPTIONAL QUESTIONS ──
-- Public can read active optional questions for a given airline
CREATE POLICY "Public read active optional questions"
    ON optional_questions FOR SELECT TO anon
    USING (is_active = true);

CREATE POLICY "Managers read own optional questions"
    ON optional_questions FOR SELECT TO authenticated
    USING (airline_id = get_my_airline_id() OR is_platform_admin());

CREATE POLICY "Admin full access optional_questions"
    ON optional_questions FOR ALL TO authenticated
    USING (is_platform_admin())
    WITH CHECK (is_platform_admin());

-- ── RESPONSES ──
-- Anonymous employees can INSERT only (never read)
CREATE POLICY "Anon can submit responses"
    ON responses FOR INSERT TO anon
    WITH CHECK (
        airline_id IN (
            SELECT id FROM airlines WHERE status = 'active'
        )
    );

-- Managers can only read their own airline's responses
CREATE POLICY "Managers read own airline responses"
    ON responses FOR SELECT TO authenticated
    USING (airline_id = get_my_airline_id() OR is_platform_admin());

-- Nobody can update or delete responses — ever
-- (No UPDATE or DELETE policies = those operations are blocked)

-- ============================================================
-- 7. INDEXES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_responses_airline_id   ON responses (airline_id);
CREATE INDEX IF NOT EXISTS idx_responses_submitted_at ON responses (submitted_at);
CREATE INDEX IF NOT EXISTS idx_responses_department   ON responses (department);
CREATE INDEX IF NOT EXISTS idx_responses_category     ON responses (employee_category);
CREATE INDEX IF NOT EXISTS idx_airline_users_auth_id  ON airline_users (auth_user_id);
CREATE INDEX IF NOT EXISTS idx_airlines_slug          ON airlines (slug);
CREATE INDEX IF NOT EXISTS idx_airlines_invite_code   ON airlines (invite_code);

-- ============================================================
-- 8. REGISTRATION FUNCTION
-- Called when a safety manager registers with an invite code.
-- Links their Supabase Auth user to the correct airline.
-- ============================================================
CREATE OR REPLACE FUNCTION register_with_invite(
    p_invite_code TEXT,
    p_full_name   TEXT
)
RETURNS JSON AS $$
DECLARE
    v_airline airlines%ROWTYPE;
BEGIN
    -- Find airline by invite code
    SELECT * INTO v_airline
    FROM airlines
    WHERE invite_code = p_invite_code
      AND status = 'invited';

    IF NOT FOUND THEN
        RETURN json_build_object(
            'success', false,
            'error', 'Invalid or already used invite code'
        );
    END IF;

    -- Create airline_user record
    INSERT INTO airline_users (auth_user_id, airline_id, full_name)
    VALUES (auth.uid(), v_airline.id, p_full_name)
    ON CONFLICT (auth_user_id) DO NOTHING;

    -- Activate the airline
    UPDATE airlines
    SET status = 'active', activated_at = NOW()
    WHERE id = v_airline.id;

    RETURN json_build_object(
        'success', true,
        'airline_id', v_airline.id,
        'airline_name', v_airline.name,
        'slug', v_airline.slug
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================
-- 9. DUMMY DATA GENERATOR
-- SELECT generate_dummy_data('sita-air', 150);
-- ============================================================
CREATE OR REPLACE FUNCTION generate_dummy_data(
    p_slug TEXT,
    n      INTEGER DEFAULT 50
)
RETURNS TEXT AS $$
DECLARE
    v_airline_id UUID;
    departments  TEXT[] := ARRAY[
        'Flight Operations','Maintenance & Engineering',
        'Ground Operations','Administration & Finance','Corporate Safety'
    ];
    categories   TEXT[] := ARRAY[
        'Flight Crew (Pilot/Co-pilot)','Licensed Engineer / Technician',
        'Ground Staff / Handling','Manager / Head of Department','Flight Dispatcher'
    ];
    experience   TEXT[] := ARRAY['<1','1-3','3-5','5+'];
    languages    TEXT[] := ARRAY['en','ne'];
    i            INTEGER;
BEGIN
    SELECT id INTO v_airline_id FROM airlines WHERE slug = p_slug;
    IF NOT FOUND THEN
        RETURN 'ERROR: Airline with slug "' || p_slug || '" not found.';
    END IF;

    FOR i IN 1..n LOOP
        INSERT INTO responses (
            airline_id, department, employee_category, years_experience, language_used,
            q1_aware, q2, q3, q4, q5_spi,
            q6, q7, q8, q9, q10, q11, q12_risk_assess, q13_action_inform,
            q14, q15, q16, q19_invest_outcome, q20_corrective,
            q17, q18, q21, q22, q23_peer,
            q24_comments, submitted_at
        ) VALUES (
            v_airline_id,
            departments[1 + floor(random() * 5)::int],
            categories[1 + floor(random() * 5)::int],
            experience[1 + floor(random() * 4)::int],
            languages[1 + floor(random() * 2)::int],
            random() > 0.1,
            1 + floor(random() * 5)::int, 1 + floor(random() * 5)::int,
            1 + floor(random() * 5)::int, 1 + floor(random() * 5)::int,
            1 + floor(random() * 5)::int, 1 + floor(random() * 5)::int,
            1 + floor(random() * 5)::int, 1 + floor(random() * 5)::int,
            1 + floor(random() * 5)::int, 1 + floor(random() * 5)::int,
            1 + floor(random() * 5)::int, 1 + floor(random() * 5)::int,
            1 + floor(random() * 5)::int, 1 + floor(random() * 5)::int,
            1 + floor(random() * 5)::int, 1 + floor(random() * 5)::int,
            1 + floor(random() * 5)::int, 1 + floor(random() * 5)::int,
            1 + floor(random() * 5)::int, 1 + floor(random() * 5)::int,
            1 + floor(random() * 5)::int, 1 + floor(random() * 5)::int,
            CASE WHEN random() > 0.7 THEN 'Test feedback ' || i ELSE NULL END,
            NOW() - (random() * INTERVAL '180 days')
        );
    END LOOP;

    RETURN 'Generated ' || n || ' responses for airline: ' || p_slug;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================
-- 10. SEED: CREATE SITA AIR AS FIRST AIRLINE
-- After running, use the invite_code to register your first
-- safety manager account.
-- ============================================================
INSERT INTO airlines (name, name_local, slug, country, icao_code, iata_code, status)
VALUES ('SITA AIR', 'सिता एयर', 'sita-air', 'Nepal', 'SNY', 'S7', 'invited')
ON CONFLICT (slug) DO NOTHING;

-- View your invite code:
-- SELECT name, slug, invite_code FROM airlines WHERE slug = 'sita-air';

-- ============================================================
-- MIGRATION NOTE (upgrading from schema v1)
-- If you ran the previous schema, run this first:
--   DROP TABLE IF EXISTS responses CASCADE;
--   DROP TABLE IF EXISTS survey_versions CASCADE;
-- Then run this entire file fresh.
-- ============================================================
