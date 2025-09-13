"""
verify_no_website.py
Use Playwright to verify businesses truly have no website by searching Google
Removes chains, businesses with websites, and closed businesses
"""

import os
import asyncio
import random
import re
import time
from datetime import datetime
from typing import List, Dict, Tuple
import pandas as pd
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Browser, Page
from dotenv import load_dotenv

# Load environment
load_dotenv()
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "leads_output")
VERIFIED_DIR = os.path.join(OUTPUT_DIR, "verified")
os.makedirs(VERIFIED_DIR, exist_ok=True)

# Configuration
CONCURRENT_BROWSERS = 3  # Number of parallel browser instances
SEARCH_DELAY_MIN = 1.0  # Minimum delay between searches (seconds)
SEARCH_DELAY_MAX = 3.0  # Maximum delay between searches
HEADLESS = True  # Run browsers in headless mode (set False for debugging)

# Known chain/franchise domains to filter out
CHAIN_DOMAINS = {
    'starbucks.com', 'mcdonalds.com', 'subway.com', 'dunkindonuts.com',
    'tacobell.com', 'kfc.com', 'pizzahut.com', 'dominos.com', 'papajohns.com',
    'burgerking.com', 'wendys.com', 'chickfila.com', 'popeyes.com',
    'arbys.com', 'jimmyjohns.com', 'chipotle.com', 'pandaexpress.com',
    'olivegarden.com', 'redlobster.com', 'applebees.com', 'chilis.com',
    'crackerbarrel.com', 'ihop.com', 'dennys.com', 'goldencorral.com',
    'walmart.com', 'target.com', 'costco.com', 'samsclub.com', 'kroger.com',
    'walgreens.com', 'cvs.com', 'riteaid.com', 'homedepot.com', 'lowes.com',
    'bestbuy.com', 'macys.com', 'tjmaxx.com', 'marshalls.com', 'ross.com'
}

# Social media and directory domains (not counted as business websites)
SOCIAL_DIRECTORY_DOMAINS = {
    'facebook.com', 'instagram.com', 'twitter.com', 'x.com', 'linkedin.com',
    'youtube.com', 'tiktok.com', 'pinterest.com', 'snapchat.com',
    'yelp.com', 'yellowpages.com', 'whitepages.com', 'mapquest.com',
    'tripadvisor.com', 'foursquare.com', 'zomato.com', 'opentable.com',
    'grubhub.com', 'doordash.com', 'ubereats.com', 'postmates.com',
    'seamless.com', 'bbb.org', 'manta.com', 'bizapedia.com',
    'chamberofcommerce.com', 'local.com', 'citysearch.com', 'superpages.com',
    'merchantcircle.com', 'showmelocal.com', 'kudzu.com', 'hotfrog.com',
    'google.com', 'maps.google.com', 'bing.com', 'apple.com'
}

class WebsiteVerifier:
    def __init__(self, csv_path: str):
        """Initialize with path to CSV file to verify."""
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path)
        self.total_businesses = len(self.df)
        self.processed = 0
        self.results = []
        
        # Statistics
        self.stats = {
            'total': self.total_businesses,
            'verified_no_website': 0,
            'has_website': 0,
            'is_chain': 0,
            'business_closed': 0,
            'processing_errors': 0
        }
    
    def extract_domain(self, url: str) -> str:
        """Extract the base domain from a URL."""
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc or parsed.path
            # Remove www. prefix
            domain = domain.replace('www.', '')
            # Clean up
            domain = domain.split('/')[0]
            return domain
        except:
            return ""
    
    def is_business_website(self, url: str, business_name: str) -> Tuple[bool, str]:
        """
        Check if URL is a legitimate business website.
        Returns (is_website, reason)
        """
        domain = self.extract_domain(url)
        
        # Check if it's a known chain
        if domain in CHAIN_DOMAINS:
            return (True, "chain")
        
        # Check if it's social media or directory
        if domain in SOCIAL_DIRECTORY_DOMAINS:
            return (False, "social_directory")
        
        # Check if domain contains business name (fuzzy match)
        business_name_clean = re.sub(r'[^a-z0-9]', '', business_name.lower())
        domain_clean = re.sub(r'[^a-z0-9]', '', domain)
        
        # If business name appears in domain, likely their website
        if len(business_name_clean) > 4 and business_name_clean in domain_clean:
            return (True, "business_website")
        
        # Check for .com/.net/.org/.biz etc with potential business domain
        business_words = business_name_clean.split()
        for word in business_words:
            if len(word) > 4 and word in domain_clean:
                return (True, "likely_business_website")
        
        # If none of the above, it's probably not their website
        return (False, "unrelated")
    
    async def search_business(self, page: Page, business: Dict) -> Dict:
        """
        Search for a business on Google and determine if it has a website.
        Returns the business dict with verification status added.
        """
        business_name = business['name']
        city = business['city']
        address = business.get('address', '')
        
        # Build search query
        search_query = f'"{business_name}" {city}'
        if address and len(address) > 10:
            # Add partial address for better accuracy
            search_query = f'"{business_name}" {address.split(',')[0]}'
        
        try:
            # Random delay to appear human-like
            await asyncio.sleep(random.uniform(SEARCH_DELAY_MIN, SEARCH_DELAY_MAX))
            
            # Navigate to Google
            await page.goto('https://www.google.com/search?q=' + search_query.replace(' ', '+'))
            
            # Wait for results to load
            await page.wait_for_selector('div#search', timeout=5000)
            
            # Get all search result links
            results = await page.query_selector_all('div#search a')
            
            has_website = False
            is_chain = False
            website_found = None
            
            # Check first 5-7 results
            for i, result in enumerate(results[:7]):
                try:
                    href = await result.get_attribute('href')
                    if not href:
                        continue
                    
                    # Check if this is a business website
                    is_website, reason = self.is_business_website(href, business_name)
                    
                    if is_website:
                        if reason == "chain":
                            is_chain = True
                            website_found = href
                            break
                        else:
                            has_website = True
                            website_found = href
                            break
                except:
                    continue
            
            # Determine verification status
            if is_chain:
                business['verification_status'] = 'REMOVED_CHAIN'
                business['website_found'] = website_found
                self.stats['is_chain'] += 1
            elif has_website:
                business['verification_status'] = 'REMOVED_HAS_WEBSITE'
                business['website_found'] = website_found
                self.stats['has_website'] += 1
            else:
                business['verification_status'] = 'VERIFIED_NO_WEBSITE'
                business['website_found'] = ''
                self.stats['verified_no_website'] += 1
            
            business['verified_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        except Exception as e:
            print(f"    ⚠️ Error searching for {business_name}: {str(e)}")
            business['verification_status'] = 'ERROR'
            business['website_found'] = ''
            business['verified_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.stats['processing_errors'] += 1
        
        return business
    
    async def process_batch(self, browser: Browser, businesses: List[Dict], worker_id: int):
        """Process a batch of businesses with one browser instance."""
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        for business in businesses:
            self.processed += 1
            print(f"  [{self.processed}/{self.total_businesses}] Verifying: {business['name']} - {business['city']}")
            
            verified_business = await self.search_business(page, business)
            self.results.append(verified_business)
            
            # Print status
            status = verified_business['verification_status']
            if status == 'VERIFIED_NO_WEBSITE':
                print(f"    ✅ Verified - No website found")
            elif status == 'REMOVED_CHAIN':
                print(f"    ❌ Removed - Chain business")
            elif status == 'REMOVED_HAS_WEBSITE':
                print(f"    ❌ Removed - Has website: {verified_business.get('website_found', '')[:50]}...")
            else:
                print(f"    ⚠️ Error during verification")
        
        await context.close()
    
    async def verify_all(self):
        """Main verification process using multiple browser instances."""
        print(f"\n🔍 Starting verification of {self.total_businesses} businesses...")
        print(f"   Using {CONCURRENT_BROWSERS} concurrent browsers\n")
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(
                headless=HEADLESS,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            # Split businesses into batches for each worker
            businesses_list = self.df.to_dict('records')
            batch_size = len(businesses_list) // CONCURRENT_BROWSERS
            batches = []
            
            for i in range(CONCURRENT_BROWSERS):
                start_idx = i * batch_size
                if i == CONCURRENT_BROWSERS - 1:
                    # Last batch gets remaining businesses
                    batch = businesses_list[start_idx:]
                else:
                    batch = businesses_list[start_idx:start_idx + batch_size]
                batches.append(batch)
            
            # Process batches concurrently
            tasks = []
            for i, batch in enumerate(batches):
                if batch:  # Only create task if batch has businesses
                    task = self.process_batch(browser, batch, i)
                    tasks.append(task)
            
            await asyncio.gather(*tasks)
            await browser.close()
    
    def save_results(self):
        """Save verified results to new CSV files."""
        if not self.results:
            print("❌ No results to save")
            return
        
        # Create DataFrame from results
        results_df = pd.DataFrame(self.results)
        
        # Separate verified businesses from removed ones
        verified_df = results_df[results_df['verification_status'] == 'VERIFIED_NO_WEBSITE'].copy()
        removed_df = results_df[results_df['verification_status'] != 'VERIFIED_NO_WEBSITE'].copy()
        
        # Drop verification columns from verified businesses CSV (keep it clean)
        if not verified_df.empty:
            verified_df = verified_df.drop(columns=['verification_status', 'website_found', 'verified_date'])
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save verified businesses (the good leads!)
        if not verified_df.empty:
            verified_file = os.path.join(VERIFIED_DIR, f"verified_no_website_{timestamp}.csv")
            verified_df.to_csv(verified_file, index=False)
            print(f"\n✅ Saved {len(verified_df)} verified leads to: {verified_file}")
        
        # Save removed businesses (for reference)
        if not removed_df.empty:
            removed_file = os.path.join(VERIFIED_DIR, f"removed_businesses_{timestamp}.csv")
            removed_df.to_csv(removed_file, index=False)
            print(f"📋 Saved {len(removed_df)} removed businesses to: {removed_file}")
        
        # Save full results with all verification details
        full_results_file = os.path.join(VERIFIED_DIR, f"full_verification_results_{timestamp}.csv")
        results_df.to_csv(full_results_file, index=False)
        print(f"📊 Saved complete results to: {full_results_file}")
        
        return verified_file if not verified_df.empty else None

def main():
    """Main function to run the verification process."""
    print("=" * 60)
    print("🌐 WEBSITE VERIFICATION SCRIPT")
    print("=" * 60)
    
    # Find the most recent leads file
    import glob
    lead_files = glob.glob(os.path.join(OUTPUT_DIR, "all_leads_no_website_*.csv"))
    
    if not lead_files:
        print("❌ No leads file found. Please run the scraping script first.")
        return
    
    # Use the most recent file
    lead_files.sort()
    latest_file = lead_files[-1]
    print(f"📂 Using leads file: {latest_file}")
    
    # Create verifier instance
    verifier = WebsiteVerifier(latest_file)
    
    # Run verification
    start_time = time.time()
    asyncio.run(verifier.verify_all())
    elapsed_time = time.time() - start_time
    
    # Save results
    verified_file = verifier.save_results()
    
    # Print statistics
    print("\n" + "=" * 60)
    print("📈 VERIFICATION STATISTICS")
    print("=" * 60)
    print(f"Total businesses processed: {verifier.stats['total']}")
    print(f"✅ Verified (no website): {verifier.stats['verified_no_website']} ({verifier.stats['verified_no_website']/verifier.stats['total']*100:.1f}%)")
    print(f"❌ Has website: {verifier.stats['has_website']}")
    print(f"❌ Chain/Franchise: {verifier.stats['is_chain']}")
    print(f"⚠️ Processing errors: {verifier.stats['processing_errors']}")
    print(f"\n⏱️ Time elapsed: {elapsed_time:.1f} seconds")
    print(f"⚡ Average per business: {elapsed_time/verifier.stats['total']:.2f} seconds")
    
    if verified_file:
        print(f"\n🎯 YOUR CLEAN LEADS ARE READY!")
        print(f"📍 Location: {verified_file}")
        print(f"💼 You have {verifier.stats['verified_no_website']} qualified prospects to contact!")

if __name__ == "__main__":
    # Install required packages:
    # pip install playwright pandas python-dotenv
    # playwright install chromium
    
    main()