import os
import sqlite3
import json
from typing import Optional
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

app = FastAPI(title="Brand Knowledge Graph API & Observability Server", version="1.0.0")
DB_PATH = "brand_kg_mvp.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS crawler_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_id TEXT,
        crawler_name TEXT NOT NULL,
        ip_address TEXT NOT NULL,
        request_path TEXT NOT NULL,
        user_agent TEXT NOT NULL,
        referrer TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

init_db()

# List of known AI crawler User-Agents and identifiers
AI_CRAWLERS = {
    "gptbot": "ChatGPT (OpenAI)",
    "chatgpt-user": "ChatGPT (OpenAI)",
    "chatgpt": "ChatGPT (OpenAI)",
    "oai-searchbot": "SearchGPT (OpenAI)",
    "claudebot": "ClaudeBot (Anthropic)",
    "anthropic-ai": "ClaudeBot (Anthropic)",
    "google-extended": "Gemini (Google)",
    "googlebot": "Googlebot (Google)",
    "bingbot": "Bingbot (Microsoft)",
    "perplexitybot": "PerplexityBot",
    "applebot-extended": "Apple Intelligence",
    "facebookbot": "Meta AI",
    "cohere-ai": "Cohere Bot",
    "python-urllib": "AI Developer Bot",
    "curl": "AI Developer Bot"
}

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def log_crawler(request: Request, brand_id: Optional[str] = None):
    """Intercepts requests, identifies if they are AI crawlers, and logs them."""
    user_agent = request.headers.get("user-agent", "").lower()
    ip_address = request.client.host if request.client else "127.0.0.1"
    path = str(request.url.path)
    
    # Identify crawler
    detected_crawler = None
    for token, friendly_name in AI_CRAWLERS.items():
        if token in user_agent:
            detected_crawler = friendly_name
            break
            
    # For testing: if query param "mock_bot" is set, simulate that crawler
    mock_bot = request.query_params.get("mock_bot")
    if mock_bot and mock_bot.lower() in AI_CRAWLERS:
        detected_crawler = AI_CRAWLERS[mock_bot.lower()]
        user_agent = f"MockBot/{mock_bot}"
    elif mock_bot:
        detected_crawler = "Unknown AI Bot"
        user_agent = f"MockBot/{mock_bot}"

    # We log ALL traffic to brands, but tag AI bots specifically
    if detected_crawler or "bot" in user_agent or "crawler" in user_agent or "spider" in user_agent:
        crawler_name = detected_crawler or "Generic Bot"
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO crawler_logs (brand_id, crawler_name, ip_address, request_path, user_agent)
                VALUES (?, ?, ?, ?, ?)
                """,
                (brand_id, crawler_name, ip_address, path, user_agent)
            )
            conn.commit()
            conn.close()
            print(f"Logged AI Crawler hit: {crawler_name} visited {path}")
        except Exception as e:
            print(f"Failed to log crawler hit: {e}")

# HTML Sleek Layout Template
HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0b0f19;
            --card-bg: rgba(17, 24, 39, 0.7);
            --primary: #00f2fe;
            --primary-glow: rgba(0, 242, 254, 0.15);
            --secondary: #4facfe;
            --text-color: #f3f4f6;
            --text-muted: #9ca3af;
            --border: rgba(255, 255, 255, 0.08);
            --accent: #10b981;
        }}
        body {{
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: 'Plus Jakarta Sans', sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(79, 172, 254, 0.05) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(0, 242, 254, 0.05) 0%, transparent 40%);
        }}
        header {{
            border-bottom: 1px solid var(--border);
            backdrop-filter: blur(12px);
            position: sticky;
            top: 0;
            z-index: 50;
            background: rgba(11, 15, 25, 0.8);
        }}
        .nav-container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 1.25rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .logo a {{
            font-weight: 700;
            font-size: 1.5rem;
            color: #fff;
            text-decoration: none;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .logo a span {{
            font-size: 0.8rem;
            padding: 0.2rem 0.5rem;
            border: 1px solid var(--primary);
            border-radius: 4px;
            text-fill-color: initial;
            -webkit-text-fill-color: var(--primary);
        }}
        nav a {{
            color: var(--text-muted);
            text-decoration: none;
            margin-left: 2rem;
            font-size: 0.95rem;
            transition: color 0.2s;
            font-weight: 600;
        }}
        nav a:hover, nav a.active {{
            color: var(--primary);
        }}
        main {{
            flex: 1;
            max-width: 1200px;
            width: 100%;
            margin: 3rem auto;
            padding: 0 2rem;
            box-sizing: border-box;
        }}
        h1, h2, h3, h4 {{
            color: #fff;
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 2rem;
            backdrop-filter: blur(16px);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 2rem;
            margin-top: 2rem;
        }}
        .brand-card {{
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
        }}
        .brand-card:hover {{
            transform: translateY(-4px);
            border-color: var(--primary);
            box-shadow: 0 8px 24px var(--primary-glow);
        }}
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .badge-verified {{
            background: rgba(16, 185, 129, 0.1);
            color: var(--accent);
            border: 1px solid rgba(16, 185, 129, 0.2);
        }}
        .badge-unverified {{
            background: rgba(156, 163, 175, 0.1);
            color: var(--text-muted);
            border: 1px solid rgba(156, 163, 175, 0.2);
        }}
        footer {{
            border-top: 1px solid var(--border);
            padding: 2rem;
            text-align: center;
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-top: 5rem;
        }}
        code {{
            background: rgba(255, 255, 255, 0.05);
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            color: var(--secondary);
            font-family: monospace;
        }}
        a {{
            color: var(--primary);
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <header>
        <div class="nav-container">
            <div class="logo">
                <a href="/">BrandKG <span>Observability</span></a>
            </div>
            <nav>
                <a href="/" class="{home_active}">Directory</a>
                <a href="/campaigns" class="{camp_active}">Campaign Showcase</a>
                <a href="/dashboard" class="{dash_active}">AI Dashboard</a>
            </nav>
        </div>
    </header>
    <main>
        {content}
    </main>
    <footer>
        <p>&copy; 2026 BrandKG. Canonical machine-first structured knowledge graph for consumer brands.</p>
    </footer>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def directory_page(request: Request):
    """Renders the main directory page, showcasing brands and their award-winning campaigns."""
    conn = get_db_connection()
    cursor = conn.cursor()
    brands_rows = cursor.execute("SELECT slug, name, verification_status, description FROM brands").fetchall()
    
    # Fetch stats
    total_brands = len(brands_rows)
    total_campaigns = cursor.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
    total_awards = cursor.execute("SELECT COUNT(*) FROM award_winners").fetchone()[0]
    
    # Fetch recent campaigns with descriptions and video urls
    campaigns_rows = cursor.execute(
        """
        SELECT c.id as campaign_id, c.title, c.year, c.description, c.case_study_url, 
               b.name as brand_name, b.slug as brand_slug, a.name as agency_name
        FROM campaigns c
        JOIN brands b ON c.brand_id = b.id
        LEFT JOIN agencies a ON c.agency_id = a.id
        ORDER BY c.year DESC, c.title ASC
        LIMIT 9
        """
    ).fetchall()

    brands_html = ""
    for brand in brands_rows:
        badge_class = "badge-verified" if brand['verification_status'] == 'verified' else "badge-unverified"
        desc = brand['description'] or "No description provided."
        if len(desc) > 120:
            desc = desc[:120] + "..."
            
        brands_html += f"""
        <div class="card brand-card" onclick="window.location.href='/brands/{brand['slug']}'">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h3 style="margin: 0; font-size: 1.3rem;">{brand['name']}</h3>
                <span class="badge {badge_class}">{brand['verification_status']}</span>
            </div>
            <p style="color: var(--text-muted); font-size: 0.95rem; line-height: 1.5; height: 3rem; overflow: hidden; margin-bottom: 1.5rem;">{desc}</p>
            <div style="display: flex; gap: 0.5rem;">
                <a href="/brands/{brand['slug']}.json" style="font-size: 0.8rem; border: 1px solid var(--border); padding: 0.3rem 0.6rem; border-radius: 4px; color: var(--text-muted);">JSON-LD</a>
                <a href="/brands/{brand['slug']}.md" style="font-size: 0.8rem; border: 1px solid var(--border); padding: 0.3rem 0.6rem; border-radius: 4px; color: var(--text-muted);">Markdown</a>
            </div>
        </div>
        """
        
    campaigns_html = ""
    for camp in campaigns_rows:
        accolades = cursor.execute(
            """
            SELECT aw.prize_level, fc.name as category_name, f.name as festival_name
            FROM award_winners aw
            JOIN festival_categories fc ON aw.category_id = fc.id
            JOIN festivals f ON fc.festival_id = f.id
            WHERE aw.campaign_id = ?
            """,
            (camp['campaign_id'],)
        ).fetchall()
        
        acc_list = []
        for acc in accolades:
            acc_list.append(f"{acc['prize_level']} ({acc['festival_name']})")
        acc_text = ", ".join(acc_list) if acc_list else "Award Winner"
        
        video_embed = get_embed_html(camp['case_study_url'])
        agency_text = f"by {camp['agency_name']}" if camp['agency_name'] else "Direct / In-House"
        
        campaigns_html += f"""
        <div class="card" style="display: flex; flex-direction: column; gap: 1rem; position: relative;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem;">
                <div>
                    <h3 style="margin: 0; font-size: 1.25rem; color: #fff;">"{camp['title']}"</h3>
                    <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">
                        Brand: <a href="/brands/{camp['brand_slug']}" style="color: var(--primary); font-weight: 600;">{camp['brand_name']}</a> | {agency_text}
                    </div>
                </div>
                <span style="font-size: 0.75rem; background: rgba(0, 242, 254, 0.1); color: var(--primary); padding: 0.25rem 0.5rem; border-radius: 4px; font-weight: bold; border: 1px solid rgba(0, 242, 254, 0.2);">{camp['year']}</span>
            </div>
            
            <div style="font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; color: var(--accent); font-weight: bold;">
                🏆 {acc_text}
            </div>
            
            <p style="color: var(--text-muted); font-size: 0.95rem; line-height: 1.6; margin: 0; flex: 1;">
                {camp['description'] or 'No campaign summary description recorded.'}
            </p>
            
            {video_embed}
        </div>
        """
        
    conn.close()

    content = f"""
    <div style="text-align: center; margin-bottom: 4rem;">
        <h1 style="font-size: 3rem; margin-bottom: 1rem; font-weight: 700; background: linear-gradient(135deg, #fff 30%, var(--text-muted)); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">The Brand Reputational Graph</h1>
        <p style="color: var(--text-muted); font-size: 1.25rem; max-width: 700px; margin: 0 auto; line-height: 1.6;">
            The easiest place on the internet for AI search crawlers, agents, and local LLM clients to fetch verified records about brands.
        </p>
        <div style="display: flex; justify-content: center; gap: 4rem; margin-top: 3rem;">
            <div>
                <div style="font-size: 2.5rem; font-weight: 700; color: var(--primary);">{total_brands}</div>
                <div style="color: var(--text-muted); font-size: 0.9rem; text-transform: uppercase; margin-top: 0.5rem; letter-spacing: 1px;">Brands</div>
            </div>
            <div>
                <div style="font-size: 2.5rem; font-weight: 700; color: var(--secondary);">{total_campaigns}</div>
                <div style="color: var(--text-muted); font-size: 0.9rem; text-transform: uppercase; margin-top: 0.5rem; letter-spacing: 1px;">Creative Works</div>
            </div>
            <div>
                <div style="font-size: 2.5rem; font-weight: 700; color: var(--accent);">{total_awards}</div>
                <div style="color: var(--text-muted); font-size: 0.9rem; text-transform: uppercase; margin-top: 0.5rem; letter-spacing: 1px;">Trophies</div>
            </div>
        </div>
    </div>
    
    <div style="margin-bottom: 4rem;">
        <h2 style="margin-bottom: 1.5rem; font-size: 1.8rem; border-bottom: 2px solid var(--primary); display: inline-block; padding-bottom: 0.5rem;">Featured Campaign Masterpieces</h2>
        <div class="grid">
            {campaigns_html}
        </div>
    </div>

    <div style="margin-bottom: 4rem;">
        <h2 style="margin-bottom: 1.5rem; font-size: 1.8rem; border-bottom: 2px solid var(--secondary); display: inline-block; padding-bottom: 0.5rem;">Registered Brand Profiles</h2>
        <div class="grid">
            {brands_html}
        </div>
    </div>
    """
    
    return HTMLResponse(
        HTML_LAYOUT.format(
            title="Brand Knowledge Graph - Directory",
            home_active="active",
            camp_active="",
            dash_active="",
            content=content
        )
    )

@app.get("/brands/{slug}")
async def get_brand(
    request: Request, 
    slug: str, 
    accept: Optional[str] = Header(None)
):
    """
    Serves brand profiles. Detects content negotiation via Accept headers or path extensions.
    Logs crawler activity.
    """
    # Remove file extension suffix from slug if present (e.g. patagonia.md -> patagonia)
    is_markdown = False
    is_json = False
    
    if slug.endswith(".md"):
        slug = slug[:-3]
        is_markdown = True
    elif slug.endswith(".json"):
        slug = slug[:-5]
        is_json = True
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    brand = cursor.execute("SELECT * FROM brands WHERE slug = ?", (slug,)).fetchone()
    if not brand:
        conn.close()
        raise HTTPException(status_code=404, detail="Brand not found")
        
    brand_id = brand['id']
    log_crawler(request, brand_id)
    
    # Query campaigns and awards
    campaigns = cursor.execute(
        """
        SELECT c.id as campaign_id, c.title, c.year, c.description, c.case_study_url, a.name as agency_name
        FROM campaigns c
        LEFT JOIN agencies a ON c.agency_id = a.id
        WHERE c.brand_id = ?
        ORDER BY c.year DESC
        """,
        (brand_id,)
    ).fetchall()
    
    accolades_data = {}
    for camp in campaigns:
        accolades = cursor.execute(
            """
            SELECT aw.prize_level, fc.name as category_name, f.name as festival_name
            FROM award_winners aw
            JOIN festival_categories fc ON aw.category_id = fc.id
            JOIN festivals f ON fc.festival_id = f.id
            WHERE aw.campaign_id = ?
            """,
            (camp['campaign_id'],)
        ).fetchall()
        accolades_data[camp['campaign_id']] = accolades
        
    conn.close()

    # Determine response format based on Content-Negotiation or extension
    user_agent = request.headers.get("user-agent", "").lower()
    
    # If Accept header contains markdown, or URL ended in .md, serve Markdown
    if is_markdown or (accept and "text/markdown" in accept):
        return serve_markdown_representation(brand, campaigns, accolades_data)
        
    # If Accept contains json, or URL ended in .json, serve JSON-LD
    if is_json or (accept and "application/json" in accept):
        return serve_json_ld_representation(brand, campaigns, accolades_data)
        
    # Default: Browser HTML view
    return serve_html_representation(brand, campaigns, accolades_data)

def serve_markdown_representation(brand, campaigns, accolades_data):
    """Generates token-efficient, LLM-optimized Markdown representation of the brand profile."""
    md = f"# Brand Profile: {brand['name']}\n"
    md += f"**Canonical URI:** `https://brandkg.com/brands/{brand['slug']}`\n"
    md += f"**Verification Status:** {brand['verification_status'].upper()}\n"
    if brand['official_website']:
        md += f"**Official Website:** {brand['official_website']}\n"
    if brand['description']:
        md += f"\n## Description\n{brand['description']}\n"
        
    md += "\n## Creative Campaigns & Awards\n"
    if not campaigns:
        md += "No creative award history logged.\n"
    for camp in campaigns:
        agency = camp['agency_name'] or "Direct / In-House"
        md += f"\n### Campaign: \"{camp['title']}\" ({camp['year']})\n"
        md += f"*   **Creative Agency:** {agency}\n"
        if camp['description']:
            md += f"*   **Description:** {camp['description']}\n"
        if camp['case_study_url']:
            md += f"*   **Case Study Video:** {camp['case_study_url']}\n"
            
        accolades = accolades_data.get(camp['campaign_id'], [])
        if accolades:
            md += "*   **Trophies:**\n"
            for acc in accolades:
                md += f"    *   {acc['prize_level']} in *{acc['category_name']}* at **{acc['festival_name']}**\n"
                
    return PlainTextResponse(md, media_type="text/markdown")

def serve_json_ld_representation(brand, campaigns, accolades_data):
    """Generates schema.org-compliant JSON-LD data structures."""
    json_ld = {
        "@context": "https://schema.org",
        "@type": "Brand",
        "@id": f"https://brandkg.com/brands/{brand['slug']}",
        "name": brand['name'],
        "url": brand['official_website'],
        "description": brand['description'],
        "verificationStatus": brand['verification_status'],
        "knowsAbout": ["Advertising Excellence", "Creative Strategy"],
        "creativeWorks": []
    }
    
    for camp in campaigns:
        work = {
            "@type": "CreativeWork",
            "name": camp['title'],
            "dateCreated": str(camp['year']),
            "creator": {
                "@type": "Organization",
                "name": camp['agency_name'] if camp['agency_name'] else "Direct"
            },
            "award": [
                f"{acc['prize_level']} ({acc['festival_name']} - {acc['category_name']})"
                for acc in accolades_data.get(camp['campaign_id'], [])
            ]
        }
        json_ld["creativeWorks"].append(work)
        
    return JSONResponse(json_ld)

def get_embed_html(url: Optional[str]) -> str:
    if not url or url == 'null' or url == 'None':
        return ""
    # Convert watch link to embed link
    embed_url = url
    if "youtube.com/watch?v=" in url:
        video_id = url.split("watch?v=")[1].split("&")[0]
        embed_url = f"https://www.youtube.com/embed/{video_id}"
    elif "youtu.be/" in url:
        video_id = url.split("youtu.be/")[1].split("?")[0]
        embed_url = f"https://www.youtube.com/embed/{video_id}"
    elif "vimeo.com/" in url and "player.vimeo.com" not in url:
        video_id = url.split("vimeo.com/")[1].split("?")[0]
        embed_url = f"https://player.vimeo.com/video/{video_id}"
    
    if "youtube.com/embed/" in embed_url or "player.vimeo.com" in embed_url:
        return f"""
        <div style="margin-top: 1rem; position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 12px; border: 1px solid var(--border);">
            <iframe src="{embed_url}" 
                    style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0;" 
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                    allowfullscreen>
            </iframe>
        </div>
        """
    else:
        return f"""
        <div style="margin-top: 1rem;">
            <a href="{url}" target="_blank" style="font-size: 0.9rem; font-weight: 600; display: inline-flex; align-items: center; gap: 0.5rem; color: var(--primary);">
                🎥 View Case Study Video &rarr;
            </a>
        </div>
        """

def serve_html_representation(brand, campaigns, accolades_data):
    """Renders a beautiful premium dark-mode profile page containing embedded JSON-LD."""
    # Embedded JSON-LD script string
    json_ld_string = json.dumps({
        "@context": "https://schema.org",
        "@type": "Brand",
        "@id": f"https://brandkg.com/brands/{brand['slug']}",
        "name": brand['name'],
        "url": brand['official_website'],
        "description": brand['description']
    })
    
    badge_class = "badge-verified" if brand['verification_status'] == 'verified' else "badge-unverified"
    
    campaigns_html = ""
    for camp in campaigns:
        agency = camp['agency_name'] or "Direct / In-House"
        accolades = accolades_data.get(camp['campaign_id'], [])
        
        acc_html = ""
        for acc in accolades:
            acc_html += f"""
            <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border); padding: 0.75rem 1rem; border-radius: 8px; margin-top: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="color: #fff; font-weight: 600;">{acc['prize_level']}</span>
                    <span style="color: var(--text-muted); font-size: 0.85rem;"> in {acc['category_name']}</span>
                </div>
                <span style="color: var(--primary); font-size: 0.85rem; font-weight: 600;">{acc['festival_name']}</span>
            </div>
            """
            
        desc_html = ""
        if camp['description']:
            desc_html = f"""
            <p style="color: var(--text-muted); margin-top: 1rem; line-height: 1.6; font-size: 0.98rem;">
                {camp['description']}
            </p>
            """
            
        video_html = get_embed_html(camp['case_study_url'])
            
        campaigns_html += f"""
        <div style="border-bottom: 1px solid var(--border); padding: 1.5rem 0; margin-bottom: 1.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
                <h3 style="margin: 0; font-size: 1.25rem; color: #fff;">"{camp['title']}"</h3>
                <span style="color: var(--secondary); font-weight: 600;">{camp['year']}</span>
            </div>
            <div style="margin-top: 0.5rem; font-size: 0.9rem; color: var(--text-muted);">
                Produced by: <strong style="color: var(--text-color);">{agency}</strong>
            </div>
            {desc_html}
            {video_html}
            <div style="margin-top: 1rem;">
                {acc_html}
            </div>
        </div>
        """

    if not campaigns_html:
        campaigns_html = "<p style='color: var(--text-muted);'>No campaigns or accolades recorded.</p>"

    content = f"""
    <script type="application/ld+json">
    {json_ld_string}
    </script>
    
    <div style="display: flex; flex-direction: column; gap: 2rem;">
        <div class="card" style="position: relative; overflow: hidden;">
            <div style="position: absolute; top: 0; left: 0; width: 4px; height: 100%; background: linear-gradient(to bottom, var(--primary), var(--secondary));"></div>
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                <div>
                    <h1 style="margin: 0; font-size: 2.5rem; font-weight: 700;">{brand['name']}</h1>
                    {f'<a href="{brand["official_website"]}" target="_blank" style="font-size: 0.95rem; margin-top: 0.5rem; display: inline-block;">{brand["official_website"]}</a>' if brand["official_website"] else ''}
                </div>
                <span class="badge {badge_class}" style="font-size: 0.85rem; padding: 0.4rem 1rem;">{brand['verification_status']}</span>
            </div>
            <p style="margin-top: 1.5rem; line-height: 1.6; color: var(--text-muted); font-size: 1.1rem; max-width: 800px;">
                {brand['description'] or "This brand profile is registered on the Brand Knowledge Graph. Claim this profile to enrich sustainability data, product catalogs, and reputation indexes."}
            </p>
            
            <div style="display: flex; gap: 1rem; margin-top: 2rem; border-top: 1px solid var(--border); padding-top: 1.5rem;">
                <a href="/brands/{brand['slug']}.json" style="background: var(--primary-glow); border: 1px solid rgba(0, 242, 254, 0.3); padding: 0.5rem 1.25rem; border-radius: 8px; font-weight: 600;">View JSON-LD Schema</a>
                <a href="/brands/{brand['slug']}.md" style="background: rgba(255,255,255,0.05); border: 1px solid var(--border); color: #fff; padding: 0.5rem 1.25rem; border-radius: 8px; font-weight: 600;">View Markdown (LLM-Optimized)</a>
            </div>
        </div>
        
        <div class="card">
            <h2 style="margin-top: 0; border-bottom: 2px solid var(--primary); padding-bottom: 0.5rem; display: inline-block;">Creative & Reputational Accolades</h2>
            <div style="margin-top: 1.5rem;">
                {campaigns_html}
            </div>
        </div>
    </div>
    """
    
    return HTMLResponse(
        HTML_LAYOUT.format(
            title=f"BrandKG - {brand['name']}",
            home_active="active",
            camp_active="",
            dash_active="",
            content=content
        )
    )

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    """Renders the AI Consumption Observability (AICO) Dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Total hits
    total_hits = cursor.execute("SELECT COUNT(*) FROM crawler_logs").fetchone()[0]
    
    # 2. Breakdowns by crawler
    crawler_counts = cursor.execute(
        """
        SELECT crawler_name, COUNT(*) as count 
        FROM crawler_logs 
        GROUP BY crawler_name 
        ORDER BY count DESC
        """
    ).fetchall()
    
    # 3. Recent logs
    recent_logs = cursor.execute(
        """
        SELECT l.crawler_name, l.request_path, l.timestamp, b.name as brand_name
        FROM crawler_logs l
        LEFT JOIN brands b ON l.brand_id = b.id
        ORDER BY l.timestamp DESC
        LIMIT 10
        """
    ).fetchall()
    
    conn.close()

    # Formulate tables
    crawler_rows_html = ""
    for c in crawler_counts:
        crawler_rows_html += f"""
        <div style="display: flex; justify-content: space-between; padding: 0.75rem 0; border-bottom: 1px solid var(--border);">
            <span style="font-weight: 600;">{c['crawler_name']}</span>
            <span style="color: var(--primary); font-weight: bold;">{c['count']} hits</span>
        </div>
        """
        
    if not crawler_rows_html:
        crawler_rows_html = "<p style='color: var(--text-muted);'>No crawler activity logged yet.</p>"

    logs_rows_html = ""
    for log in recent_logs:
        brand = log['brand_name'] or "Index / Directory"
        logs_rows_html += f"""
        <tr>
            <td style="padding: 1rem; border-bottom: 1px solid var(--border); font-weight: 600; color: var(--primary);">{log['crawler_name']}</td>
            <td style="padding: 1rem; border-bottom: 1px solid var(--border); color: var(--secondary);">{brand}</td>
            <td style="padding: 1rem; border-bottom: 1px solid var(--border);"><code>{log['request_path']}</code></td>
            <td style="padding: 1rem; border-bottom: 1px solid var(--border); color: var(--text-muted); font-size: 0.85rem;">{log['timestamp']}</td>
        </tr>
        """
        
    if not logs_rows_html:
        logs_rows_html = "<tr><td colspan='4' style='padding: 2rem; text-align: center; color: var(--text-muted);'>No agent log records found. Try sending simulated AI crawler hits (e.g. visiting <code>/brands/apple?mock_bot=GPTBot</code>).</td></tr>"

    content = f"""
    <div style="margin-bottom: 3rem;">
        <h1 style="font-size: 2.5rem; margin-bottom: 0.5rem; font-weight: 700;">AI Consumption Observability Dashboard (AICO)</h1>
        <p style="color: var(--text-muted); font-size: 1.1rem; margin: 0;">
            Real-time analytics showing how AI agents, crawlers, and search engines synthesize your brand data.
        </p>
    </div>
    
    <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 2rem; flex-wrap: wrap;">
        <!-- Left Side: Recent logs -->
        <div class="card" style="overflow-x: auto;">
            <h2 style="margin-top: 0; border-bottom: 2px solid var(--primary); padding-bottom: 0.5rem; display: inline-block; font-size: 1.3rem;">Recent AI Crawler Activity</h2>
            <table style="width: 100%; border-collapse: collapse; margin-top: 1.5rem; text-align: left;">
                <thead>
                    <tr style="color: var(--text-muted); border-bottom: 1px solid var(--border);">
                        <th style="padding: 0.75rem 1rem;">Crawler Engine</th>
                        <th style="padding: 0.75rem 1rem;">Target Brand</th>
                        <th style="padding: 0.75rem 1rem;">Request Path</th>
                        <th style="padding: 0.75rem 1rem;">Timestamp</th>
                    </tr>
                </thead>
                <tbody>
                    {logs_rows_html}
                </tbody>
            </table>
        </div>
        
        <!-- Right Side: Stats -->
        <div style="display: flex; flex-direction: column; gap: 2rem;">
            <div class="card" style="text-align: center;">
                <h3 style="margin-top: 0; color: var(--text-muted); font-size: 1rem; text-transform: uppercase; letter-spacing: 1px;">Total AI Crawler Sessions</h3>
                <div style="font-size: 3.5rem; font-weight: 700; color: var(--primary); margin: 1rem 0;">{total_hits}</div>
                <p style="font-size: 0.85rem; color: var(--text-muted); margin: 0;">Unique context extractions logged by external engines</p>
            </div>
            
            <div class="card">
                <h3 style="margin-top: 0; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; font-size: 1.1rem;">Crawler Share</h3>
                <div style="margin-top: 1rem;">
                    {crawler_rows_html}
                </div>
            </div>
        </div>
    </div>
    """

    return HTMLResponse(
        HTML_LAYOUT.format(
            title="BrandKG - AI Observability Dashboard",
            home_active="",
            camp_active="",
            dash_active="active",
            content=content
        )
    )

@app.get("/campaigns", response_class=HTMLResponse)
async def campaigns_page(request: Request):
    """Renders a page displaying ALL creative campaigns and their case study videos."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query all campaigns
    campaigns_rows = cursor.execute(
        """
        SELECT c.id as campaign_id, c.title, c.year, c.description, c.case_study_url, 
               b.name as brand_name, b.slug as brand_slug, a.name as agency_name
        FROM campaigns c
        JOIN brands b ON c.brand_id = b.id
        LEFT JOIN agencies a ON c.agency_id = a.id
        ORDER BY c.year DESC, c.title ASC
        """
    ).fetchall()
    
    campaigns_html = ""
    for camp in campaigns_rows:
        accolades = cursor.execute(
            """
            SELECT aw.prize_level, fc.name as category_name, f.name as festival_name
            FROM award_winners aw
            JOIN festival_categories fc ON aw.category_id = fc.id
            JOIN festivals f ON fc.festival_id = f.id
            WHERE aw.campaign_id = ?
            """,
            (camp['campaign_id'],)
        ).fetchall()
        
        acc_list = []
        for acc in accolades:
            acc_list.append(f"{acc['prize_level']} ({acc['festival_name']})")
        acc_text = ", ".join(acc_list) if acc_list else "Award Winner"
        
        video_embed = get_embed_html(camp['case_study_url'])
        agency_text = f"by {camp['agency_name']}" if camp['agency_name'] else "Direct / In-House"
        
        campaigns_html += f"""
        <div class="card" style="display: flex; flex-direction: column; gap: 1rem; position: relative;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem;">
                <div>
                    <h3 style="margin: 0; font-size: 1.25rem; color: #fff;">"{camp['title']}"</h3>
                    <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">
                        Brand: <a href="/brands/{camp['brand_slug']}" style="color: var(--primary); font-weight: 600;">{camp['brand_name']}</a> | {agency_text}
                    </div>
                </div>
                <span style="font-size: 0.75rem; background: rgba(0, 242, 254, 0.1); color: var(--primary); padding: 0.25rem 0.5rem; border-radius: 4px; font-weight: bold; border: 1px solid rgba(0, 242, 254, 0.2);">{camp['year']}</span>
            </div>
            
            <div style="font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; color: var(--accent); font-weight: bold;">
                🏆 {acc_text}
            </div>
            
            <p style="color: var(--text-muted); font-size: 0.95rem; line-height: 1.6; margin: 0; flex: 1;">
                {camp['description'] or 'No campaign description available.'}
            </p>
            
            {video_embed}
        </div>
        """
        
    conn.close()

    content = f"""
    <div style="margin-bottom: 3rem;">
        <h1 style="font-size: 2.5rem; margin-bottom: 0.5rem; font-weight: 700;">Creative Campaigns & Case Studies Showcase</h1>
        <p style="color: var(--text-muted); font-size: 1.1rem; margin: 0;">
            A complete canonical registry of creative works, brand descriptions, and video case studies.
        </p>
    </div>
    
    <div class="grid" style="grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));">
        {campaigns_html}
    </div>
    """

    return HTMLResponse(
        HTML_LAYOUT.format(
            title="BrandKG - Creative Campaigns",
            home_active="",
            camp_active="active",
            dash_active="",
            content=content
        )
    )
