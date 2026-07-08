import os
import sqlite3
import re
from typing import List, Optional
from fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("Brand Knowledge Graph & Accolades")
DB_PATH = "brand_kg_mvp.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@mcp.tool()
def search_brands(query: str) -> str:
    """
    Search for consumer brands in the database.
    Use this to resolve brand names and get their slugs.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    rows = cursor.execute(
        "SELECT slug, name, verification_status, description FROM brands WHERE name LIKE ? OR slug LIKE ?",
        (f"%{query}%", f"%{query}%")
    ).fetchall()
    conn.close()
    
    if not rows:
        return f"No brands found matching: {query}"
        
    result = []
    for r in rows:
        desc = r['description'] or "No description available."
        if len(desc) > 100:
            desc = desc[:100] + "..."
        result.append(f"- Name: {r['name']} (slug: {r['slug']}) | Status: {r['verification_status']}\n  Description: {desc}")
    return "\n".join(result)

@mcp.tool()
def get_brand_profile(brand_slug: str) -> str:
    """
    Retrieve the detailed creative profile, agency partners, and awards won for a specific brand slug.
    Verify the slug first using search_brands if you are not sure.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    brand = cursor.execute("SELECT * FROM brands WHERE slug = ?", (brand_slug,)).fetchone()
    if not brand:
        conn.close()
        return f"Brand slug '{brand_slug}' not found. Try searching for it first using search_brands."
        
    campaigns = cursor.execute(
        """
        SELECT c.id as campaign_id, c.title, c.year, c.description, c.case_study_url, a.name as agency_name
        FROM campaigns c
        LEFT JOIN agencies a ON c.agency_id = a.id
        WHERE c.brand_id = ?
        ORDER BY c.year DESC
        """,
        (brand['id'],)
    ).fetchall()
    
    profile = f"# Brand Profile: {brand['name']}\n"
    if brand['official_website']:
        profile += f"Website: {brand['official_website']}\n"
    profile += f"Verification Status: {brand['verification_status'].upper()}\n"
    profile += f"Description: {brand['description'] or 'No description available.'}\n\n"
    profile += "## Creative Campaigns & Award Accolades:\n"
    
    if not campaigns:
        profile += "No logged campaigns or awards found for this brand.\n"
        
    for camp in campaigns:
        agency = camp['agency_name'] or "Direct / In-House"
        profile += f"\n- **\"{camp['title']}\" ({camp['year']})**\n"
        profile += f"  Agency Partner: {agency}\n"
        if camp['description']:
            profile += f"  Summary: {camp['description']}\n"
        if camp['case_study_url']:
            profile += f"  Case Study Video: {camp['case_study_url']}\n"
            
        # Fetch awards
        awards = cursor.execute(
            """
            SELECT aw.prize_level, fc.name as category_name, f.name as festival_name
            FROM award_winners aw
            JOIN festival_categories fc ON aw.category_id = fc.id
            JOIN festivals f ON fc.festival_id = f.id
            WHERE aw.campaign_id = ?
            """,
            (camp['campaign_id'],)
        ).fetchall()
        
        if awards:
            profile += "  Accolades Won:\n"
            for aw in awards:
                profile += f"    * {aw['prize_level']} in '{aw['category_name']}' at {aw['festival_name']}\n"
                
    conn.close()
    return profile

@mcp.tool()
def get_agency_profile(agency_query: str) -> str:
    """
    Retrieve campaigns produced by a creative agency and the brands they partnered with.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Simple search
    agency = cursor.execute(
        "SELECT * FROM agencies WHERE name LIKE ? OR slug LIKE ?",
        (f"%{agency_query}%", f"%{agency_query}%")
    ).fetchone()
    
    if not agency:
        conn.close()
        return f"No agency found matching: {agency_query}"
        
    campaigns = cursor.execute(
        """
        SELECT c.title, c.year, b.name as brand_name
        FROM campaigns c
        JOIN brands b ON c.brand_id = b.id
        WHERE c.agency_id = ?
        ORDER BY c.year DESC
        """,
        (agency['id'],)
    ).fetchall()
    
    conn.close()
    
    profile = f"# Agency Profile: {agency['name']}\n"
    if agency['website']:
        profile += f"Website: {agency['website']}\n"
    profile += "\n## Creative Work Portfolio:\n"
    
    if not campaigns:
        profile += "No logged campaigns found for this agency.\n"
        
    for camp in campaigns:
        profile += f"- **\"{camp['title']}\" ({camp['year']})** for brand **{camp['brand_name']}**\n"
        
    return profile

if __name__ == "__main__":
    mcp.run()
