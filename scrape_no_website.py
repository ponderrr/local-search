"""
scrape_no_website_enhanced.py
Enhanced version: Find businesses without websites with expanded data collection
"""

import os
import time
import csv
from datetime import datetime
from collections import OrderedDict
from typing import List, Dict
import itertools

from dotenv import load_dotenv
import googlemaps
from googlemaps.exceptions import ApiError, TransportError

# ───── 1. LOAD CONFIGURATION ─────
load_dotenv()

# API Configuration
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not found in environment or .env file")

# Cities Configuration (REQUIRED in env)
CITIES_ENV = os.getenv("SEARCH_CITIES")
if not CITIES_ENV:
    raise RuntimeError(
        "SEARCH_CITIES not found in .env file. "
        "Please add: SEARCH_CITIES=City1 State, City2 State, City3 State"
    )
CITIES = [city.strip() for city in CITIES_ENV.split(",")]

# Comprehensive Business Categories - Cast a wide net!
BUSINESS_CATEGORIES = {
    "food_beverage": [
        "restaurant", "cafe", "coffee shop", "bakery", "bar", "pub",
        "ice cream shop", "frozen yogurt", "juice bar", "smoothie shop",
        "food truck", "catering", "deli", "pizza place", "brewery",
        "winery", "dessert shop", "bubble tea", "donut shop", "bagel shop",
        "sandwich shop", "burger joint", "taco shop", "sushi", "buffet",
        "steakhouse", "seafood restaurant", "breakfast spot", "brunch",
        "fast food", "food delivery", "meal prep", "ghost kitchen"
    ],
    "retail": [
        "clothing store", "boutique", "fashion boutique", "jewelry store",
        "gift shop", "bookstore", "antique store", "furniture store",
        "home decor", "flower shop", "pet store", "toy store",
        "sporting goods", "electronics store", "shoe store", "thrift store",
        "vintage shop", "consignment shop", "specialty store", "hobby shop",
        "art supply store", "music store", "bike shop", "outdoor gear",
        "department store", "convenience store", "liquor store", "smoke shop",
        "cbd store", "nutrition store", "vitamin shop", "beauty supply"
    ],
    "health_wellness": [
        "fitness center", "gym", "yoga studio", "pilates studio",
        "spa", "massage", "nail salon", "hair salon", "barber shop",
        "beauty salon", "med spa", "chiropractor", "physical therapy",
        "acupuncture", "wellness center", "martial arts", "dance studio",
        "crossfit", "boxing gym", "climbing gym", "meditation center",
        "tanning salon", "eyebrow threading", "lash extensions", "waxing",
        "tattoo parlor", "piercing shop", "float spa", "cryotherapy"
    ],
    "professional_services": [
        "dentist", "orthodontist", "optometrist", "veterinarian", "law firm",
        "accounting firm", "insurance agency", "real estate agency",
        "financial advisor", "tax preparation", "tutoring center",
        "consulting firm", "marketing agency", "travel agency",
        "employment agency", "property management", "title company",
        "mortgage broker", "investment firm", "architect", "engineer",
        "psychologist", "counselor", "psychiatrist", "pediatrician"
    ],
    "home_services": [
        "plumber", "electrician", "hvac", "landscaping", "roofing",
        "painting contractor", "home cleaning", "pest control",
        "handyman", "flooring", "window installation", "garage door",
        "carpet cleaning", "pressure washing", "pool service", "fence contractor",
        "concrete contractor", "tree service", "gutter cleaning", "locksmith",
        "appliance repair", "furniture repair", "home inspection", "renovation",
        "kitchen remodeling", "bathroom remodeling", "deck builder"
    ],
    "automotive": [
        "auto repair", "car dealership", "auto detailing", "tire shop",
        "oil change", "car wash", "auto parts", "motorcycle dealer",
        "transmission repair", "brake repair", "muffler shop", "auto glass",
        "body shop", "paint shop", "car rental", "towing service",
        "diesel repair", "rv dealer", "boat dealer", "auto upholstery"
    ],
    "entertainment_recreation": [
        "bowling alley", "arcade", "escape room", "mini golf",
        "movie theater", "music venue", "comedy club", "art gallery",
        "museum", "dance studio", "music lessons", "art studio",
        "karaoke", "billiards", "go kart", "laser tag", "trampoline park",
        "skating rink", "rock climbing", "paintball", "axe throwing",
        "golf course", "country club", "tennis club", "sports complex"
    ],
    "education_childcare": [
        "daycare", "preschool", "private school", "tutoring center",
        "music school", "art school", "driving school", "language school",
        "after school program", "summer camp", "childcare center",
        "montessori school", "test prep", "college prep", "trade school"
    ],
    "events_hospitality": [
        "event venue", "wedding venue", "party rental", "event planning",
        "photographer", "videographer", "dj service", "catering",
        "hotel", "motel", "bed and breakfast", "airbnb", "vacation rental",
        "banquet hall", "conference center", "coworking space"
    ],
    "manufacturing_wholesale": [
        "manufacturer", "wholesaler", "distributor", "warehouse",
        "industrial supply", "equipment rental", "machine shop",
        "metal fabrication", "woodworking", "printing service",
        "embroidery", "screen printing", "sign shop", "packaging"
    ],
    "agriculture_pets": [
        "farm", "ranch", "nursery", "garden center", "pet grooming",
        "dog training", "pet boarding", "pet daycare", "animal shelter",
        "horse stable", "feed store", "agricultural supply"
    ],
    "transportation_logistics": [
        "trucking company", "logistics", "freight", "moving company",
        "storage facility", "shipping", "courier service", "taxi service",
        "limo service", "bus company", "delivery service"
    ]
}

# Flatten all keywords for searching
SEARCH_KEYWORDS = []
for category, keywords in BUSINESS_CATEGORIES.items():
    SEARCH_KEYWORDS.extend(keywords)

# Search settings
DELAY_BETWEEN_REQUESTS = float(os.getenv("API_DELAY", "0.2"))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "leads_output")

# ───── 2. INIT GOOGLE CLIENT ─────
gmaps = googlemaps.Client(key=API_KEY)

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ───── 3. HELPER FUNCTIONS ─────
def get_business_category(types_list: List[str]) -> str:
    """Determine the primary business category based on Google Places types."""
    for category, keywords in BUSINESS_CATEGORIES.items():
        for keyword in keywords:
            keyword_parts = keyword.lower().replace("_", " ").split()
            for place_type in types_list:
                place_type_clean = place_type.lower().replace("_", " ")
                if all(part in place_type_clean for part in keyword_parts):
                    return category
    return "other"

def format_hours(opening_hours: Dict) -> str:
    """Format opening hours into readable string."""
    if not opening_hours or "weekday_text" not in opening_hours:
        return ""
    return " | ".join(opening_hours["weekday_text"])

def safe_place_details(pid: str, fields: List[str], max_retry: int = 3) -> Dict:
    """Place Details with exponential back-off on quota/network errors."""
    delay = 1
    for attempt in range(max_retry):
        try:
            result = gmaps.place(place_id=pid, fields=fields)
            return result.get("result", {})
        except (ApiError, TransportError) as e:
            if attempt == max_retry - 1:
                print(f"    ⚠️  Skipping place after {max_retry} errors: {e}")
                return {}
            time.sleep(delay)
            delay *= 2
    return {}

def text_search_all_pages(query: str, max_pages: int = 3) -> List[str]:
    """Get all place IDs from text search (up to 60 results)."""
    place_ids = []
    page_token = None
    
    for page_num in range(max_pages):
        try:
            if page_token:
                time.sleep(2)  # Wait for token to be ready
            
            resp = gmaps.places(query, page_token=page_token)
            
            for result in resp.get("results", []):
                place_ids.append(result["place_id"])
            
            page_token = resp.get("next_page_token")
            if not page_token:
                break
                
        except Exception as e:
            print(f"    ⚠️  Error fetching page {page_num + 1}: {e}")
            break
    
    return place_ids

def get_businesses_no_site(city: str, keyword: str) -> List[OrderedDict]:
    """Get detailed info for businesses without websites."""
    query = f"{keyword} in {city}"
    leads = []
    
    place_ids = text_search_all_pages(query)
    if not place_ids:
        return leads
    
    print(f"  📍 Found {len(place_ids)} places to check...")
    
    for i, pid in enumerate(place_ids, 1):
        if i % 10 == 0:
            print(f"    Processed {i}/{len(place_ids)}...")
        
        # Get all available details
        details = safe_place_details(
            pid,
            fields=[
                "name",
                "formatted_phone_number",
                "formatted_address",
                "rating",
                "user_ratings_total",
                "type",  # Returns as "types" in response
                "website",
                "business_status",
                "opening_hours",
                "price_level",
                "place_id",
                "vicinity",
                "plus_code",
                "serves_beer",
                "serves_wine",
                "takeout",
                "delivery",
                "dine_in",
                "curbside_pickup",
                "reservable",
                "wheelchair_accessible_entrance"
            ],
        )
        
        if not details:
            continue
            
        # Skip if permanently closed
        if details.get("business_status") == "CLOSED_PERMANENTLY":
            continue
            
        # Skip if has website
        if "website" in details and details["website"]:
            continue
        
        # Extract all information
        type_list = details.get("types", [])
        category = get_business_category(type_list)
        
        opening_hours = details.get("opening_hours", {})
        hours_text = format_hours(opening_hours)
        is_open_now = opening_hours.get("open_now")
        
        # Price level: 0 = Free, 1 = $, 2 = $$, 3 = $$$, 4 = $$$$
        price_level = details.get("price_level", "")
        if price_level != "":
            price_display = "$" * (price_level + 1)
        else:
            price_display = ""
        
        # Build lead record with all available data
        lead = OrderedDict([
            ("name", details.get("name", "")),
            ("phone", details.get("formatted_phone_number", "")),
            ("address", details.get("formatted_address", "")),
            ("vicinity", details.get("vicinity", "")),  # Shorter address
            ("rating", details.get("rating", "")),
            ("review_count", details.get("user_ratings_total", 0)),
            ("price_level", price_display),
            ("business_status", details.get("business_status", "OPERATIONAL")),
            ("currently_open", is_open_now if is_open_now is not None else "Unknown"),
            ("hours", hours_text),
            ("types", "|".join(type_list)),
            ("category", category),
            ("city", city),
            ("search_keyword", keyword),
            ("place_id", details.get("place_id", "")),
            ("plus_code", details.get("plus_code", {}).get("global_code", "")),
            # Service attributes (for restaurants/food places)
            ("serves_beer", details.get("serves_beer", "")),
            ("serves_wine", details.get("serves_wine", "")),
            ("takeout", details.get("takeout", "")),
            ("delivery", details.get("delivery", "")),
            ("dine_in", details.get("dine_in", "")),
            ("curbside_pickup", details.get("curbside_pickup", "")),
            ("reservable", details.get("reservable", "")),
            ("wheelchair_accessible", details.get("wheelchair_accessible_entrance", "")),
            ("scraped_date", datetime.now().strftime("%Y-%m-%d")),
            ("scraped_time", datetime.now().strftime("%H:%M:%S"))
        ])
        
        leads.append(lead)
        time.sleep(DELAY_BETWEEN_REQUESTS)
    
    return leads

def save_leads_to_csv(leads: List[OrderedDict], filename: str) -> int:
    """Save leads to CSV file with deduplication."""
    if not leads:
        return 0
    
    # Deduplicate by (name, address) - some businesses might not have phone
    unique_leads = {}
    for lead in leads:
        key = (lead["name"], lead["address"])
        if key not in unique_leads:
            unique_leads[key] = lead
    
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(next(iter(unique_leads.values())).keys()))
        writer.writeheader()
        writer.writerows(unique_leads.values())
    
    return len(unique_leads)

# ───── 4. MAIN FUNCTION ─────
def main():
    print("=" * 60)
    print("🚀 ENHANCED BUSINESS LEAD SCRAPER")
    print("=" * 60)
    print(f"📍 Target Cities: {', '.join(CITIES)}")
    print(f"🔍 Search Keywords: {len(SEARCH_KEYWORDS)} total")
    print(f"📁 Output Directory: {OUTPUT_DIR}/")
    print("=" * 60)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_leads = []
    leads_by_city = {city: [] for city in CITIES}
    
    total_combinations = len(CITIES) * len(SEARCH_KEYWORDS)
    current = 0
    
    # Main scraping loop
    for city, keyword in itertools.product(CITIES, SEARCH_KEYWORDS):
        current += 1
        print(f"\n[{current}/{total_combinations}] Searching: '{keyword}' in {city}")
        
        try:
            leads = get_businesses_no_site(city, keyword)
            if leads:
                all_leads.extend(leads)
                leads_by_city[city].extend(leads)
                print(f"  ✅ Found {len(leads)} businesses without websites")
            else:
                print(f"  ➖ No results for this search")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue
        
        # Small delay between different searches
        time.sleep(0.5)
    
    # Save results
    print("\n" + "=" * 60)
    print("💾 SAVING RESULTS...")
    print("=" * 60)
    
    if not all_leads:
        print("❌ No leads found. Please check:")
        print("  - API key is valid")
        print("  - You have remaining quota")
        print("  - Cities are spelled correctly")
        return
    
    # Save main file with all leads
    main_filename = f"all_leads_no_website_{timestamp}.csv"
    total_unique = save_leads_to_csv(all_leads, main_filename)
    print(f"\n📊 Main File: {total_unique} unique leads → {main_filename}")
    
    # Save separate files by city
    print("\n📂 City-Specific Files:")
    for city, city_leads in leads_by_city.items():
        if city_leads:
            city_filename = f"leads_{city.replace(', ', '_').replace(' ', '_')}_{timestamp}.csv"
            city_unique = save_leads_to_csv(city_leads, city_filename)
            print(f"  • {city}: {city_unique} leads → {city_filename}")
    
    # Save by category
    print("\n📂 Category-Specific Files:")
    for category in BUSINESS_CATEGORIES.keys():
        category_leads = [l for l in all_leads if l["category"] == category]
        if category_leads:
            cat_filename = f"leads_{category}_{timestamp}.csv"
            cat_unique = save_leads_to_csv(category_leads, cat_filename)
            print(f"  • {category}: {cat_unique} leads → {cat_filename}")
    
    # Print summary statistics
    print("\n" + "=" * 60)
    print("📈 SUMMARY STATISTICS")
    print("=" * 60)
    print(f"Total unique businesses found: {total_unique}")
    print(f"Cities searched: {len(CITIES)}")
    print(f"Keywords used: {len(SEARCH_KEYWORDS)}")
    
    # Category breakdown
    category_counts = {}
    for lead in all_leads:
        cat = lead["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    print("\n🏢 Businesses by Category:")
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {cat}: {count}")
    
    print("\n✅ Scraping complete! Check the output folder for your leads.")
    print(f"📁 Location: {os.path.abspath(OUTPUT_DIR)}/")

if __name__ == "__main__":
    main()