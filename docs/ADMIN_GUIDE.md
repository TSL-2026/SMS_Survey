# Admin Guide — The Safety Layer

## Onboarding a New Airline

Run in Supabase SQL Editor:
```sql
INSERT INTO airlines (name, name_local, slug, country, status)
VALUES ('Airline Name', 'Local Name', 'airline-slug', 'Country', 'invited');

SELECT name, slug, invite_code FROM airlines
WHERE slug = 'airline-slug';
```

Email the invite_code to the airline's safety manager.
Their survey URL: survey.thesafetylayer.xyz/airline-slug

## Suspending an Airline
```sql
UPDATE airlines SET status = 'suspended'
WHERE slug = 'airline-slug';
```

## Viewing All Airlines
```sql
SELECT
    name, slug, status, plan,
    created_at, activated_at,
    (SELECT COUNT(*) FROM responses r
     WHERE r.airline_id = a.id) as response_count
FROM airlines a
ORDER BY created_at DESC;
```

## Generating Test Data
```sql
SELECT generate_dummy_data('airline-slug', 100);
```

## Upgrading an Airline to Pro
```sql
UPDATE airlines SET plan = 'pro'
WHERE slug = 'airline-slug';
```
```

---

**GitHub Pages setting**

After all files are committed, go to **Settings → Pages**:
```
Source:  Deploy from a branch
Branch:  main
Folder:  / (root)
```

This serves `index.html` (survey) from root automatically. The `login.html` will be at `/login.html`. The `dashboard/` and `docs/` folders are not served as pages — they're just storage for your other files.

---

**Final URLs after custom domain setup:**
```
survey.thesafetylayer.xyz           → index.html       (survey form)
survey.thesafetylayer.xyz/login.html → login.html      (manager login)
app.thesafetylayer.xyz              → Streamlit on VPS  (dashboard)
