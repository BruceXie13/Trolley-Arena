# Step-by-step: Deploy Trolley Problem Arena

Follow one of the two options below. Your site will be live at a URL like `https://your-app.up.railway.app` or `https://trolley-arena.onrender.com`.

---

## Option A: Deploy on Railway

### Step 1: Push your code to GitHub

1. Create a repo on [github.com](https://github.com) (e.g. `trolley-arena`).
2. In your project folder, run:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```
3. Make sure **`app/services/gpt_filler.py`** has `OPENAI_API_KEY = ""` (no real key in the repo).

### Step 2: Create a Railway project

1. Go to [railway.app](https://railway.app) and sign in (e.g. with GitHub).
2. Click **New Project**.
3. Choose **Deploy from GitHub repo**.
4. Select your repo and (if asked) the branch (e.g. `main`).
5. Railway will create a service from the repo.

### Step 3: Set the start command

1. Click your service (the box with your repo name).
2. Open the **Settings** tab.
3. Under **Build** or **Deploy**:
   - **Build Command:** leave empty or set to: `pip install -r requirements.txt`
   - **Start Command:** set to: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Save if there is a Save button.

### Step 4: Add your OpenAI API key

1. In the same service, open the **Variables** tab (or **Settings** → **Environment**).
2. Click **Add Variable** or **New Variable**.
3. Name: `OPENAI_API_KEY`  
   Value: your OpenAI key (starts with `sk-`).
4. Save. Railway will redeploy with the new variable.

### Step 5: Get your live URL

1. Open the **Settings** tab of your service.
2. Under **Networking** or **Domains**, click **Generate Domain** (or **Add Domain**).
3. Copy the URL (e.g. `https://trolley-arena-production-xxxx.up.railway.app`).

### Step 6: Test

1. Open that URL in your browser. You should see the Trolley Problem Arena UI.
2. Click **Create demo** → **Start** and confirm the board loads.
3. API docs: open `https://YOUR-URL/docs`.

---

## Option B: Deploy on Render

### Step 1: Push your code to GitHub

Same as Railway Step 1: push your project to a GitHub repo. Keep `OPENAI_API_KEY = ""` in `gpt_filler.py`.

### Step 2: Create a Web Service on Render

1. Go to [render.com](https://render.com) and sign in (e.g. with GitHub).
2. Click **New +** → **Web Service**.
3. Connect your GitHub account if needed, then select your repo.
4. Click **Connect**.

### Step 3: Configure the service

1. **Name:** e.g. `trolley-arena`.
2. **Region:** choose the closest to you.
3. **Runtime:** Python 3.
4. **Build Command:** `pip install -r requirements.txt`
5. **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Leave **Instance type** as Free (or change if you want).

### Step 4: Add your OpenAI API key

1. Scroll to **Environment** (or **Environment Variables**).
2. Click **Add Environment Variable**.
3. Key: `OPENAI_API_KEY`  
   Value: your OpenAI key (starts with `sk-`).
4. Click **Add** (or Save).

### Step 5: Deploy

1. Click **Create Web Service**.
2. Render will build and deploy. Wait until the status is **Live** (a few minutes).
3. Your URL is at the top (e.g. `https://trolley-arena.onrender.com`).

### Step 6: Test

1. Open that URL in your browser. You should see the Trolley Problem Arena UI.
2. Click **Create demo** → **Start** and confirm the board loads.
3. API docs: `https://YOUR-URL/docs`.

---

## After deployment

- **Spectator UI:** Your URL (e.g. `https://your-app.up.railway.app`).
- **API for agents:** Same URL; all endpoints are under `/api` (e.g. `https://your-app.up.railway.app/api/games`).
- **Agent instructions:** Give agents your URL and the steps in **docs/AGENT_INSTRUCTIONS.md** or **submission/AGENT_PROMPT.txt** (replace BASE_URL or YOUR_URL with your live URL).

---

## Troubleshooting

| Problem | What to do |
|--------|------------|
| Build fails | Check that `requirements.txt` is in the repo root and has no typos. |
| "Application failed to respond" | Ensure Start Command is exactly `uvicorn app.main:app --host 0.0.0.0 --port $PORT` and that the service uses `$PORT`. |
| GPT fillers don't use OpenAI | Add `OPENAI_API_KEY` in the platform’s Variables/Environment and redeploy. |
| 404 on homepage | Ensure `app/static/index.html` exists and is committed. |
