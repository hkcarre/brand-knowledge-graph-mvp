import os
import re
import json
import sqlite3
import urllib.request
import urllib.error
from typing import List, Optional
from pydantic import BaseModel, Field

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TARGET_URL = "https://llllitl.fr/cannes-lions-2024-grand-prix/"
# Offline cache fallback from previous steps
OFFLINE_CACHE_PATH = r"C:\Users\helen\.gemini\antigravity\brain\103d5a9f-5976-4eef-901c-128777a5112f\.system_generated\steps\64\content.md"

class AwardWinnerExtract(BaseModel):
    brand_name: str
    agency_name: Optional[str] = None
    campaign_title: str
    category: str
    prize_level: str
    year: int
    campaign_description: Optional[str] = None
    case_study_video_url: Optional[str] = None

class AwardsExtractionResult(BaseModel):
    festival_name: str
    winners: List[AwardWinnerExtract]

def fetch_page_content(url: str) -> str:
    """Fetches the HTML content from the target URL, falling back to local cache if offline."""
    print(f"Fetching page content from: {url}")
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read().decode("utf-8")
    except Exception as e:
        print(f"Network request failed: {e}")
        if os.path.exists(OFFLINE_CACHE_PATH):
            print(f"Loading from offline cache: {OFFLINE_CACHE_PATH}")
            with open(OFFLINE_CACHE_PATH, "r", encoding="utf-8") as f:
                return f.read()
        raise e

def clean_html(html_content: str) -> str:
    """Strips HTML tags, script, and style blocks to produce clean text but preserves video case studies."""
    # Remove script and style elements
    text = re.sub(r'<(script|style)\b[^>]*>([\s\S]*?)<\/\1>', '', html_content, flags=re.I)
    # Remove HTML comments
    text = re.sub(r'<!--([\s\S]*?)-->', '', text)
    
    # Extract any iframe containing youtube or vimeo and append its title
    def replace_iframe(match):
        iframe_tag = match.group(0)
        # Find any URL in double quotes containing youtube or vimeo
        urls = re.findall(r'"(https?://[^"]*(?:youtube\.com|youtu\.be|vimeo\.com)[^"]*)"', iframe_tag)
        # Find title attribute
        title_match = re.search(r'title="([^"]+)"', iframe_tag, flags=re.I)
        title = title_match.group(1) if title_match else ""
        
        if urls:
            # Prefer embed URLs
            embed_urls = [u for u in urls if "/embed/" in u or "/video/" in u]
            target_url = embed_urls[0] if embed_urls else urls[0]
            target_url = target_url.replace("&amp;", "&")
            title_suffix = f" | Title: {title}" if title else ""
            return f"\n[Case Study Video: {target_url}{title_suffix}]\n"
        return "\n"
        
    text = re.sub(r'<iframe\b[^>]*>[\s\S]*?</iframe>', replace_iframe, text, flags=re.I)
    
    # Preserve key links
    text = re.sub(
        r'<a[^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>',
        r' \2 [Link: \1] ',
        text,
        flags=re.I
    )
    
    # Remove remaining HTML tags
    text = re.sub(r'<[^>]+>', '\n', text)
    # Decode basic entities
    text = text.replace("&amp;", "&").replace("&#8211;", "-").replace("&#8217;", "'").replace("&nbsp;", " ")
    # Normalize whitespaces
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)

def parse_with_gemini(clean_text: str, api_key: str, year: int) -> AwardsExtractionResult:
    """Calls Gemini 2.5 Flash to extract structured brand awards from the text dump, including description and video links."""
    print(f"\n--- Sending parsed page text to Gemini 2.5 Flash for {year} ---")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    # We restrict the prompt context length by sending the first 2500 lines
    text_snippet = "\n".join(clean_text.split("\n")[:2500])
    
    prompt = (
        f"Extract all Cannes Lions {year} Grand Prix winners from the following text.\n"
        "For each winner, extract:\n"
        "1. The brand name\n"
        "2. The agency name (set to null if direct or not mentioned)\n"
        "3. The campaign title\n"
        "4. The award category (e.g. PR, Film, Outdoor)\n"
        "5. The prize level (Always 'Grand Prix')\n"
        f"6. The year (Always {year})\n"
        f"7. A brief summary description of what the campaign did/was about. Since the text may not explicitly detail the creative work, you MUST use your own pre-trained knowledge base to write a clear 1-2 sentence description explaining what this famous {year} creative campaign did.\n"
        "8. The case study video URL. Search the text for '[Case Study Video: URL]' markers. Find the YouTube/Vimeo URL that matches this campaign. Extract that exact URL. If no video link matches, set to null.\n\n"
        f"Input Text:\n{text_snippet}"
    )
    
    schema = {
        "type": "OBJECT",
        "properties": {
            "festival_name": {"type": "STRING", "description": "Always 'Cannes Lions'"},
            "winners": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "brand_name": {"type": "STRING", "description": "The winning brand"},
                        "agency_name": {"type": "STRING", "description": "Creative agency or null"},
                        "campaign_title": {"type": "STRING", "description": "Campaign title"},
                        "category": {"type": "STRING", "description": "Category"},
                        "prize_level": {"type": "STRING", "description": "Always 'Grand Prix'"},
                        "year": {"type": "INTEGER", "description": "Always 2024"},
                        "campaign_description": {"type": "STRING", "description": "Brief summary of what the campaign did"},
                        "case_study_video_url": {"type": "STRING", "description": "Case study YouTube/Vimeo video embed URL, or null"}
                    },
                    "required": ["brand_name", "campaign_title", "category", "prize_level", "year"]
                }
            }
        },
        "required": ["festival_name", "winners"]
    }
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": schema
        }
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    with urllib.request.urlopen(req) as response:
        res_body = json.loads(response.read().decode('utf-8'))
        
    json_text = res_body['candidates'][0]['content']['parts'][0]['text']
    extracted_dict = json.loads(json_text)
    
    winners = [AwardWinnerExtract(**w) for w in extracted_dict.get("winners", [])]
    return AwardsExtractionResult(
        festival_name=extracted_dict.get("festival_name", "Cannes Lions"),
        winners=winners
    )

def init_sqlite_db(db_path: str = "brand_kg_mvp.db"):
    """Initializes local SQLite database and wipes existing data to ensure fresh ingestion."""
    print(f"Initializing SQLite database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clean up to guarantee clean ingest
    cursor.execute("DROP TABLE IF EXISTS award_winners")
    cursor.execute("DROP TABLE IF EXISTS campaigns")
    cursor.execute("DROP TABLE IF EXISTS festival_categories")
    cursor.execute("DROP TABLE IF EXISTS festivals")
    cursor.execute("DROP TABLE IF EXISTS agencies")
    cursor.execute("DROP TABLE IF EXISTS brands")
    
    # 1. Brands Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS brands (
        id TEXT PRIMARY KEY,
        slug TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        official_website TEXT,
        description TEXT,
        is_claimed INTEGER DEFAULT 0,
        verification_status TEXT DEFAULT 'unverified',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # 2. Agencies Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agencies (
        id TEXT PRIMARY KEY,
        slug TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        website TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # 3. Festivals Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS festivals (
        id TEXT PRIMARY KEY,
        slug TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        website TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # 4. Festival Categories Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS festival_categories (
        id TEXT PRIMARY KEY,
        festival_id TEXT,
        name TEXT NOT NULL,
        UNIQUE(festival_id, name),
        FOREIGN KEY(festival_id) REFERENCES festivals(id) ON DELETE CASCADE
    )""")
    
    # 5. Campaigns Table (supports description and video case study links)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS campaigns (
        id TEXT PRIMARY KEY,
        brand_id TEXT,
        agency_id TEXT,
        title TEXT NOT NULL,
        slug TEXT NOT NULL,
        year INTEGER NOT NULL,
        description TEXT,
        case_study_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(brand_id, title, year),
        FOREIGN KEY(brand_id) REFERENCES brands(id) ON DELETE CASCADE,
        FOREIGN KEY(agency_id) REFERENCES agencies(id) ON DELETE SET NULL
    )""")
    
    # 6. Award Winners Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS award_winners (
        id TEXT PRIMARY KEY,
        campaign_id TEXT,
        category_id TEXT,
        year INTEGER NOT NULL,
        prize_level TEXT NOT NULL,
        confidence_score REAL DEFAULT 1.0,
        source_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
        FOREIGN KEY(category_id) REFERENCES festival_categories(id) ON DELETE CASCADE
    )""")
    
    conn.commit()
    return conn

def save_to_db(result: AwardsExtractionResult, source_url: str, db_path: str = "brand_kg_mvp.db"):
    """Saves the extracted Cannes Lions entities and links to the SQLite database."""
    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    import uuid
    
    # 1. Festival
    fest_slug = "cannes-lions"
    cursor.execute(
        "INSERT OR IGNORE INTO festivals (id, slug, name, website) VALUES (?, ?, ?, ?)",
        ("fest-cannes-lions", fest_slug, "Cannes Lions", "https://www.canneslions.com")
    )
    
    def make_slug(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s_-]+', '-', text)
        return text

    inserted_count = 0
    for winner in result.winners:
        brand_slug = make_slug(winner.brand_name)
        brand_id = f"brand-{brand_slug}"
        
        # 2. Insert Brand
        cursor.execute(
            "INSERT OR IGNORE INTO brands (id, slug, name) VALUES (?, ?, ?)",
            (brand_id, brand_slug, winner.brand_name)
        )
        
        # 3. Insert Agency (if exists)
        agency_id = None
        if winner.agency_name:
            agency_slug = make_slug(winner.agency_name)
            agency_id = f"agency-{agency_slug}"
            cursor.execute(
                "INSERT OR IGNORE INTO agencies (id, slug, name) VALUES (?, ?, ?)",
                (agency_id, agency_slug, winner.agency_name)
            )
            
        # 4. Insert Category
        cat_slug = make_slug(winner.category)
        cat_id = f"cat-cannes-lions-{cat_slug}"
        cursor.execute(
            "INSERT OR IGNORE INTO festival_categories (id, festival_id, name) VALUES (?, ?, ?)",
            (cat_id, "fest-cannes-lions", winner.category)
        )
        
        # 5. Insert Campaign (with description and video study link)
        camp_slug = make_slug(winner.campaign_title)
        camp_id = f"camp-{brand_slug}-{camp_slug}-{winner.year}"
        cursor.execute(
            """
            INSERT OR IGNORE INTO campaigns (id, brand_id, agency_id, title, slug, year, description, case_study_url) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (camp_id, brand_id, agency_id, winner.campaign_title, camp_slug, winner.year, winner.campaign_description, winner.case_study_video_url)
        )
        
        # 6. Insert Accolade
        award_win_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT OR IGNORE INTO award_winners (id, campaign_id, category_id, year, prize_level, confidence_score, source_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (award_win_id, camp_id, cat_id, winner.year, winner.prize_level, 0.95, source_url)
        )
        inserted_count += 1
        
    conn.commit()
    conn.close()
    print(f"Successfully processed and synchronized {inserted_count} Cannes Lions accolades to local SQLite.")

if __name__ == "__main__":
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        exit(1)
        
    # Initialize / clean database structure
    init_sqlite_db()
    
    years = [2024, 2025, 2026]
    for year in years:
        target_url = f"https://llllitl.fr/cannes-lions-{year}-grand-prix/"
        print(f"\n===== Ingesting Cannes Lions Grand Prix Winners for {year} =====")
        try:
            # 1. Fetch
            raw_html = fetch_page_content(target_url)
            
            # 2. Clean HTML
            clean_text = clean_html(raw_html)
            print(f"Extracted {len(clean_text.splitlines())} lines of clean text.")
            
            # 3. Parse with LLM
            extraction_result = parse_with_gemini(clean_text, GEMINI_API_KEY, year)
            print(f"Successfully extracted {len(extraction_result.winners)} Cannes Lions {year} Grand Prix winners.")
            
            # 4. Save to SQLite
            save_to_db(extraction_result, target_url)
        except Exception as e:
            print(f"Scraper pipeline failed for year {year}: {e}")
