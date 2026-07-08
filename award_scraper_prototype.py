import os
import re
import json
import sqlite3
import urllib.request
import urllib.error
from typing import List, Optional
from pydantic import BaseModel, Field

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Define Pydantic structures for data verification
class AwardWinnerExtract(BaseModel):
    brand_name: str
    agency_name: Optional[str] = None
    campaign_title: str
    category: str
    prize_level: str
    year: int

class AwardsExtractionResult(BaseModel):
    festival_name: str
    winners: List[AwardWinnerExtract]

# Mock data representing copied text from Cannes Lions / D&AD Winners lists
SAMPLE_AWARDS_HTML_TEXT = """
D&AD Awards 2025 Winners Archive:
- Title: "The Last Photo" | Brand: ITV | Agency: adam&eveDDB | Award: Black Pencil | Category: Integrated
- Title: "R.I.P. Leon" | Brand: Apple | Agency: TBWA\\Media Arts Lab | Award: Yellow Pencil | Category: Film Advertising
- Title: "Sinyi Realty: In Love We Trust" | Brand: Sinyi Realty | Agency: Dentsu McGarryBowen | Award: Graphite Pencil | Category: Direct
- Title: "Real Beauty Sketches" | Brand: Dove | Agency: Ogilvy | Award: Yellow Pencil | Category: PR
"""

def init_sqlite_db(db_path: str = "brand_kg_mvp.db"):
    """Initializes local SQLite database matching schema.sql specifications."""
    print(f"Initializing SQLite database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
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
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agencies (
        id TEXT PRIMARY KEY,
        slug TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        website TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS festivals (
        id TEXT PRIMARY KEY,
        slug TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        website TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS festival_categories (
        id TEXT PRIMARY KEY,
        festival_id TEXT,
        name TEXT NOT NULL,
        UNIQUE(festival_id, name),
        FOREIGN KEY(festival_id) REFERENCES festivals(id) ON DELETE CASCADE
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS campaigns (
        id TEXT PRIMARY KEY,
        brand_id TEXT,
        agency_id TEXT,
        title TEXT NOT NULL,
        slug TEXT NOT NULL,
        year INTEGER NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(brand_id, title, year),
        FOREIGN KEY(brand_id) REFERENCES brands(id) ON DELETE CASCADE,
        FOREIGN KEY(agency_id) REFERENCES agencies(id) ON DELETE SET NULL
    )""")
    
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

def make_slug(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text

def parse_with_gemini(raw_text: str, api_key: str) -> AwardsExtractionResult:
    """
    Calls the Gemini API using native HTTP requests to extract structured award data
    using Gemini's native JSON Schema mode.
    """
    print(f"\n--- Calling Gemini API (gemini-2.5-flash) ---")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    prompt = (
        "Extract all advertising, design, and brand award winners from the following text. "
        "Create entries for each winner. If an agency is not mentioned, set agency_name to null.\n\n"
        f"Input Text:\n{raw_text}"
    )
    
    # JSON schema for Gemini structured output
    schema = {
        "type": "OBJECT",
        "properties": {
            "festival_name": {
                "type": "STRING", 
                "description": "Name of the award festival (e.g., D&AD, Cannes Lions, Clio Awards)"
            },
            "winners": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "brand_name": {"type": "STRING", "description": "The brand that won (e.g. Nike, ITV, Apple)"},
                        "agency_name": {"type": "STRING", "description": "Creative agency name (null if not specified)"},
                        "campaign_title": {"type": "STRING", "description": "Name of the campaign or work"},
                        "category": {"type": "STRING", "description": "Award category (e.g., PR, Film Advertising)"},
                        "prize_level": {"type": "STRING", "description": "Pencil/Award level won (e.g. Yellow Pencil, Wood Pencil)"},
                        "year": {"type": "INTEGER", "description": "The year of the award ceremony"}
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
    
    try:
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
        
        # Parse into pydantic validation models
        winners = [AwardWinnerExtract(**w) for w in extracted_dict.get("winners", [])]
        return AwardsExtractionResult(
            festival_name=extracted_dict.get("festival_name", "Unknown Festival"),
            winners=winners
        )
        
    except urllib.error.HTTPError as e:
        print(f"Gemini API HTTP Error: {e.code} - {e.read().decode('utf-8')}")
        raise e
    except Exception as e:
        print(f"Failed to call Gemini API: {e}")
        raise e

def parse_with_fallback(raw_text: str) -> AwardsExtractionResult:
    """Fallback local regex parser if Gemini call fails or no key is provided."""
    print("\n--- Running Fallback Local Regex Extraction ---")
    winners = []
    lines = [line.strip() for line in raw_text.split("\n") if line.strip() and line.startswith("-")]
    for line in lines:
        title_match = re.search(r'Title:\s*"([^"]+)"', line)
        brand_match = re.search(r'Brand:\s*([^|]+)', line)
        agency_match = re.search(r'Agency:\s*([^|]+)', line)
        award_match = re.search(r'Award:\s*([^|]+)', line)
        category_match = re.search(r'Category:\s*(.+)$', line)
        
        if title_match and brand_match and award_match and category_match:
            winners.append(AwardWinnerExtract(
                brand_name=brand_match.group(1).strip(),
                agency_name=agency_match.group(1).strip() if agency_match else None,
                campaign_title=title_match.group(1).strip(),
                category=category_match.group(1).strip(),
                prize_level=award_match.group(1).strip(),
                year=2025
            ))
    return AwardsExtractionResult(festival_name="D&AD", winners=winners)

def save_to_kb(conn: sqlite3.Connection, result: AwardsExtractionResult):
    cursor = conn.cursor()
    import uuid
    
    # 1. Festival
    fest_slug = make_slug(result.festival_name)
    fest_id = f"fest-{fest_slug}"
    cursor.execute(
        "INSERT OR IGNORE INTO festivals (id, slug, name) VALUES (?, ?, ?)",
        (fest_id, fest_slug, result.festival_name)
    )
    
    for winner in result.winners:
        # 2. Brand
        brand_slug = make_slug(winner.brand_name)
        brand_id = f"brand-{brand_slug}"
        cursor.execute(
            "INSERT OR IGNORE INTO brands (id, slug, name) VALUES (?, ?, ?)",
            (brand_id, brand_slug, winner.brand_name)
        )
        
        # 3. Agency
        agency_id = None
        if winner.agency_name:
            agency_slug = make_slug(winner.agency_name)
            agency_id = f"agency-{agency_slug}"
            cursor.execute(
                "INSERT OR IGNORE INTO agencies (id, slug, name) VALUES (?, ?, ?)",
                (agency_id, agency_slug, winner.agency_name)
            )
            
        # 4. Festival Category
        cat_slug = make_slug(winner.category)
        cat_id = f"cat-{fest_slug}-{cat_slug}"
        cursor.execute(
            "INSERT OR IGNORE INTO festival_categories (id, festival_id, name) VALUES (?, ?, ?)",
            (cat_id, fest_id, winner.category)
        )
        
        # 5. Campaign
        camp_slug = make_slug(winner.campaign_title)
        camp_id = f"camp-{brand_slug}-{camp_slug}-{winner.year}"
        cursor.execute(
            """
            INSERT OR IGNORE INTO campaigns (id, brand_id, agency_id, title, slug, year) 
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (camp_id, brand_id, agency_id, winner.campaign_title, camp_slug, winner.year)
        )
        
        # 6. Award Winner Entry
        award_win_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT OR IGNORE INTO award_winners (id, campaign_id, category_id, year, prize_level, confidence_score)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (award_win_id, camp_id, cat_id, winner.year, winner.prize_level, 1.0)
        )
        
    conn.commit()
    print("Database sync complete.")

def print_summary_reports(conn: sqlite3.Connection):
    cursor = conn.cursor()
    print("\n--- Verified Knowledge Graph Entities ---")
    
    print("\n[Brands]:")
    for r in cursor.execute("SELECT id, name, verification_status FROM brands"):
        print(f"  ID: {r[0]} | Name: {r[1]} | Status: {r[2]}")
        
    print("\n[Campaigns & Agency Relationships]:")
    query = """
        SELECT c.title, b.name, COALESCE(a.name, 'Direct/None') as agency, c.year
        FROM campaigns c
        JOIN brands b ON c.brand_id = b.id
        LEFT JOIN agencies a ON c.agency_id = a.id
    """
    for r in cursor.execute(query):
        print(f"  Campaign: '{r[0]}' | Brand: {r[1]} | Produced by: {r[2]} ({r[3]})")
        
    print("\n[Accolades]:")
    query = """
        SELECT c.title, f.name, fc.name, aw.prize_level, aw.year
        FROM award_winners aw
        JOIN campaigns c ON aw.campaign_id = c.id
        JOIN festival_categories fc ON aw.category_id = fc.id
        JOIN festivals f ON fc.festival_id = f.id
    """
    for r in cursor.execute(query):
        print(f"  Accolade: '{r[0]}' won {r[3]} in '{r[2]}' at {r[1]} ({r[4]})")

if __name__ == "__main__":
    db_conn = init_sqlite_db()
    
    # Attempt to use the live Gemini API first
    if GEMINI_API_KEY and not GEMINI_API_KEY.startswith("YOUR_"):
        try:
            extracted_data = parse_with_gemini(SAMPLE_AWARDS_HTML_TEXT, GEMINI_API_KEY)
            print(f"Successfully parsed {len(extracted_data.winners)} awards from {extracted_data.festival_name} winners list using Gemini API.")
        except Exception as e:
            print(f"Gemini API failed, falling back to local extractor. Error: {e}")
            extracted_data = parse_with_fallback(SAMPLE_AWARDS_HTML_TEXT)
    else:
        print("No valid Gemini API key found. Using fallback local extractor.")
        extracted_data = parse_with_fallback(SAMPLE_AWARDS_HTML_TEXT)
        
    # Save to SQLite db
    save_to_kb(db_conn, extracted_data)
    
    # Print results
    print_summary_reports(db_conn)
    db_conn.close()
