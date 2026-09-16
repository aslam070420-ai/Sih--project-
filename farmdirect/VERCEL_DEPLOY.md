# 🚀 FarmDirect on Vercel — 5 easy steps

## 1. GitHub
Extract the FarmDirect ZIP and upload the **contents of the `farmdirect` folder** to one GitHub repository.

You should see `app.py`, `requirements.txt`, `templates`, `static`, etc. directly in the repo.

## 2. Vercel
Vercel Dashboard → **Add New → Project** → select the FarmDirect GitHub repo → **Import**.

Keep the root directory as `./` when `app.py` is at the repo root.

## 3. First deploy
Press **Deploy**. V16 can boot in temporary cloud demo mode even before a permanent DB is attached.

## 4. Permanent database
Create a free Supabase (or Neon) PostgreSQL database. Copy its **pooled/serverless connection string**.

Vercel → FarmDirect project → **Settings → Environment Variables**:

```text
DATABASE_URL = your pooled postgres URL
FD_SECRET    = a long random secret
CRON_SECRET  = another long random secret
```

Save and **Redeploy**.

## 5. Verify
Open:

```text
https://YOUR-PROJECT.vercel.app/api/system/health
```

For the final persistent setup it should report:

```json
"backend": "postgres"
```

Then open `/marketplace`, `/market-intelligence` and `/ivr/simulator`.

## Custom domain
Vercel project → **Settings → Domains → Add Domain**. Follow the DNS values Vercel shows. HTTPS is handled automatically after verification.

## Free-plan market sync
The included Vercel cron runs once daily, which matches the Hobby plan's minimum cron interval. The Live Mandi screen also supports an explicit manual refresh for a selected crop.

## If Vercel warns that the Python function is larger than the standard package limit
V16 includes NumPy, pandas and scikit-learn for the AI modules. New Vercel projects can use Large Functions; if the dashboard asks you to opt in, add `VERCEL_SUPPORT_LARGE_FUNCTIONS=1` and redeploy.
