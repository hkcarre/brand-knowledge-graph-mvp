# Deploying to Render

Your codebase has been successfully pushed to your GitHub repository:
**[https://github.com/hkcarre/brand-knowledge-graph-mvp](https://github.com/hkcarre/brand-knowledge-graph-mvp)**

Follow these simple steps to deploy it live to the public internet for free:

---

## Step 1: Create a Render Web Service
1.  Log in to [Render](https://dashboard.render.com/) (you can sign in with your GitHub account).
2.  Click the blue **New** button in the top right, and select **Web Service**.
3.  Select **Build and deploy from a Git repository**.
4.  You will see your list of repositories. Find **`brand-knowledge-graph-mvp`** and click **Connect**.

---

## Step 2: Configure Deployment Settings
In the configuration screen, set the following:
*   **Name:** `brand-knowledge-graph-mvp` (or any name you prefer)
*   **Region:** Select the closest region (e.g., Oregon, Frankfurt)
*   **Branch:** `master`
*   **Runtime:** `Python`
*   **Build Command:** `pip install -r requirements.txt`
*   **Start Command:** `python -m uvicorn server:app --host 0.0.0.0 --port $PORT`
*   **Instance Type:** `Free`

---

## Step 3: Add environment variable
1.  Scroll down to the **Advanced** section or go to the **Environment** tab on Render.
2.  Add a new environment variable:
    *   **Key:** `GEMINI_API_KEY`
    *   **Value:** `(Your Gemini API Key)` (Paste your Gemini API key here)
3.  Click **Create Web Service**.

---

## Step 4: Access your Live URL!
Render will build the dependencies and spin up your FastAPI server. Within 1–2 minutes, it will provide you with a permanent public URL (e.g. `https://brand-knowledge-graph-mvp.onrender.com`).

*   **Public Directory:** `https://brand-knowledge-graph-mvp.onrender.com/`
*   **AI Observability Dashboard:** `https://brand-knowledge-graph-mvp.onrender.com/dashboard`
*   **Markdown representation for bots:** `https://brand-knowledge-graph-mvp.onrender.com/brands/heinz.md`
