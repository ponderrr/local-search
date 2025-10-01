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

# Import our utility modules
from utils import ScraperConfig, APIQuotaTracker, setup_logging, ScraperConstants, save_checkpoint, load_checkpoint, fuzzy_match

# ───── 1. LOAD CONFIGURATION ─────
try:
    config = ScraperConfig.from_env()
    config.validate()
    logger = setup_logging(config.log_level)
    quota_tracker = APIQuotaTracker(config.max_requests_per_day)
    logger.info("Configuration loaded and validated successfully")
except Exception as e:
    print(f"❌ Configuration Error: {e}")
    print("Please check your .env file and ensure all required settings are present.")
    exit(1)

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

# ───── 2. INIT GOOGLE CLIENT ─────
gmaps = googlemaps.Client(key=config.api_key)

# Create output directory if it doesn't exist
os.makedirs(config.output_dir, exist_ok=True)

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

def text_search_all_pages(query: str, max_pages: int = None) -> List[str]:
    """Get all place IDs from text search (up to 60 results)."""
    if max_pages is None:
        max_pages = config.max_pages
        
    place_ids = []
    page_token = None
    
    for page_num in range(max_pages):
        try:
            # Check API quota before making request
            if not quota_tracker.can_make_request():
                logger.warning("API quota exceeded. Stopping search.")
                break
                
            if page_token:
                time.sleep(2)  # Wait for token to be ready
            
            resp = gmaps.places(query, page_token=page_token)
            quota_tracker.increment()
            
            for result in resp.get("results", []):
                place_ids.append(result["place_id"])
            
            page_token = resp.get("next_page_token")
            if not page_token:
                break
                
        except Exception as e:
            logger.error(f"Error fetching page {page_num + 1}: {e}")
            break
    
    return place_ids

def get_businesses_no_site(city: str, keyword: str) -> List[OrderedDict]:
    """Get detailed info for businesses without websites."""
    query = f"{keyword} in {city}"
    leads = []
    
    logger.info(f"Searching for '{keyword}' in {city}")
    place_ids = text_search_all_pages(query)
    if not place_ids:
        logger.info(f"No places found for '{keyword}' in {city}")
        return leads
    
    logger.info(f"Found {len(place_ids)} places to check for '{keyword}' in {city}")
    
    for i, pid in enumerate(place_ids, 1):
        if i % 10 == 0:
            logger.info(f"Processed {i}/{len(place_ids)} places for '{keyword}' in {city}")
        
        # Check API quota before each request
        if not quota_tracker.can_make_request():
            logger.warning("API quota exceeded. Stopping place details requests.")
            break
        
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
        time.sleep(config.api_delay)
    
    logger.info(f"Found {len(leads)} businesses without websites for '{keyword}' in {city}")
    return leads

def save_leads_to_csv(leads: List[OrderedDict], filename: str) -> int:
    """Save leads to CSV file with enhanced deduplication using fuzzy matching."""
    if not leads:
        return 0
    
    # Enhanced deduplication with fuzzy matching
    unique_leads = []
    seen_names = set()
    
    for lead in leads:
        business_name = lead["name"].lower().strip()
        is_duplicate = False
        
        # Check against all previously seen names using fuzzy matching
        for seen_name in seen_names:
            if fuzzy_match(business_name, seen_name, threshold=0.85):
                logger.debug(f"Fuzzy duplicate found: '{lead['name']}' matches '{seen_name}'")
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_leads.append(lead)
            seen_names.add(business_name)
    
    filepath = os.path.join(config.output_dir, filename)
    
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(next(iter(unique_leads)).keys()))
        writer.writeheader()
        writer.writerows(unique_leads)
    
    logger.info(f"Saved {len(unique_leads)} unique leads to {filename} (removed {len(leads) - len(unique_leads)} duplicates)")
    return len(unique_leads)

# ───── 4. MAIN FUNCTION ─────
def main():
    logger.info("=" * 60)
    logger.info("🚀 ENHANCED BUSINESS LEAD SCRAPER")
    logger.info("=" * 60)
    logger.info(f"📍 Target Cities: {', '.join(config.cities)}")
    logger.info(f"🔍 Search Keywords: {len(SEARCH_KEYWORDS)} total")
    logger.info(f"📁 Output Directory: {config.output_dir}/")
    logger.info(f"🔢 API Quota: {quota_tracker.get_usage_stats()}")
    logger.info("=" * 60)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    checkpoint_file = f"checkpoint_{timestamp}.json"
    
    # Try to load existing checkpoint
    checkpoint_data = load_checkpoint(checkpoint_file)
    processed_combinations = set(checkpoint_data.get('processed_combinations', []))
    
    all_leads = checkpoint_data.get('all_leads', [])
    leads_by_city = checkpoint_data.get('leads_by_city', {city: [] for city in config.cities})
    
    total_combinations = len(config.cities) * len(SEARCH_KEYWORDS)
    current = len(processed_combinations)
    
    if current > 0:
        logger.info(f"🔄 Resuming from checkpoint: {current}/{total_combinations} combinations already processed")
    
    # Main scraping loop
    for city, keyword in itertools.product(config.cities, SEARCH_KEYWORDS):
        combination_key = f"{city}|{keyword}"
        
        # Skip if already processed
        if combination_key in processed_combinations:
            continue
            
        current += 1
        logger.info(f"[{current}/{total_combinations}] Searching: '{keyword}' in {city}")
        
        try:
            leads = get_businesses_no_site(city, keyword)
            if leads:
                all_leads.extend(leads)
                leads_by_city[city].extend(leads)
                logger.info(f"✅ Found {len(leads)} businesses without websites")
            else:
                logger.info(f"➖ No results for this search")
                
        except Exception as e:
            logger.error(f"Error searching '{keyword}' in {city}: {e}")
            continue
        
        # Mark as processed and save checkpoint
        processed_combinations.add(combination_key)
        checkpoint_data = {
            'processed_combinations': list(processed_combinations),
            'all_leads': all_leads,
            'leads_by_city': leads_by_city,
            'timestamp': datetime.now().isoformat()
        }
        save_checkpoint(checkpoint_data, checkpoint_file)
        
        # Small delay between different searches
        time.sleep(0.5)
    
    # Save results
    logger.info("=" * 60)
    logger.info("💾 SAVING RESULTS...")
    logger.info("=" * 60)
    
    if not all_leads:
        logger.error("No leads found. Please check:")
        logger.error("  - API key is valid")
        logger.error("  - You have remaining quota")
        logger.error("  - Cities are spelled correctly")
        return
    
    # Save main file with all leads
    main_filename = f"all_leads_no_website_{timestamp}.csv"
    total_unique = save_leads_to_csv(all_leads, main_filename)
    logger.info(f"📊 Main File: {total_unique} unique leads → {main_filename}")
    
    # Save separate files by city
    logger.info("📂 City-Specific Files:")
    for city, city_leads in leads_by_city.items():
        if city_leads:
            city_filename = f"leads_{city.replace(', ', '_').replace(' ', '_')}_{timestamp}.csv"
            city_unique = save_leads_to_csv(city_leads, city_filename)
            logger.info(f"  • {city}: {city_unique} leads → {city_filename}")
    
    # Save by category
    logger.info("📂 Category-Specific Files:")
    for category in BUSINESS_CATEGORIES.keys():
        category_leads = [l for l in all_leads if l["category"] == category]
        if category_leads:
            cat_filename = f"leads_{category}_{timestamp}.csv"
            cat_unique = save_leads_to_csv(category_leads, cat_filename)
            logger.info(f"  • {category}: {cat_unique} leads → {cat_filename}")
    
    # Print summary statistics
    logger.info("=" * 60)
    logger.info("📈 SUMMARY STATISTICS")
    logger.info("=" * 60)
    logger.info(f"Total unique businesses found: {total_unique}")
    logger.info(f"Cities searched: {len(config.cities)}")
    logger.info(f"Keywords used: {len(SEARCH_KEYWORDS)}")
    logger.info(f"API Usage: {quota_tracker.get_usage_stats()}")
    
    # Category breakdown
    category_counts = {}
    for lead in all_leads:
        cat = lead["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    logger.info("🏢 Businesses by Category:")
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  • {cat}: {count}")
    
    logger.info("✅ Scraping complete! Check the output folder for your leads.")
    logger.info(f"📁 Location: {os.path.abspath(config.output_dir)}/")

if __name__ == "__main__":
    main()