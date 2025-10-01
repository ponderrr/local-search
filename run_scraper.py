#!/usr/bin/env python3
"""
Command-line interface for the Local Business Lead Generator.
Provides easy access to all scraper functionality with command-line options.
"""

import argparse
import sys
import os
from pathlib import Path

# Add current directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import ScraperConfig, setup_logging
from scrape_no_website import main as run_scraper
from verify_no_website import main as run_verifier


def create_parser():
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Local Business Lead Generator - Find businesses without websites",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic scraping
  python run_scraper.py --cities "Austin TX" "Portland OR"
  
  # Scrape and verify in one command
  python run_scraper.py --cities "New York NY" --verify
  
  # Custom configuration
  python run_scraper.py --cities "Chicago IL" --delay 0.5 --max-pages 2
  
  # Resume interrupted scrape
  python run_scraper.py --resume
  
  # Verify existing leads
  python run_scraper.py --verify-only
        """
    )
    
    # Main action
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        '--cities', 
        nargs='+', 
        help='Cities to search (format: "City State")'
    )
    action_group.add_argument(
        '--resume', 
        action='store_true', 
        help='Resume interrupted scrape from checkpoint'
    )
    action_group.add_argument(
        '--verify-only', 
        action='store_true', 
        help='Only run verification on existing leads'
    )
    
    # Scraping options
    scraping_group = parser.add_argument_group('Scraping Options')
    scraping_group.add_argument(
        '--delay', 
        type=float, 
        default=0.2, 
        help='Delay between API calls in seconds (default: 0.2)'
    )
    scraping_group.add_argument(
        '--max-pages', 
        type=int, 
        default=3, 
        help='Maximum pages to scrape per search (default: 3)'
    )
    scraping_group.add_argument(
        '--output-dir', 
        default='leads_output', 
        help='Output directory for CSV files (default: leads_output)'
    )
    
    # Verification options
    verification_group = parser.add_argument_group('Verification Options')
    verification_group.add_argument(
        '--verify', 
        action='store_true', 
        help='Run verification after scraping'
    )
    verification_group.add_argument(
        '--browsers', 
        type=int, 
        default=3, 
        help='Number of concurrent browsers for verification (default: 3)'
    )
    verification_group.add_argument(
        '--headless', 
        action='store_true', 
        default=True, 
        help='Run browsers in headless mode (default: True)'
    )
    verification_group.add_argument(
        '--no-headless', 
        action='store_true', 
        help='Show browser windows during verification'
    )
    
    # Advanced options
    advanced_group = parser.add_argument_group('Advanced Options')
    advanced_group.add_argument(
        '--log-level', 
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], 
        default='INFO', 
        help='Logging level (default: INFO)'
    )
    advanced_group.add_argument(
        '--api-key', 
        help='Google Places API key (overrides .env file)'
    )
    advanced_group.add_argument(
        '--quota-limit', 
        type=int, 
        default=25000, 
        help='Maximum API requests per day (default: 25000)'
    )
    
    return parser


def update_env_file(args):
    """Update .env file with command-line arguments."""
    env_file = Path('.env')
    
    # Read existing .env content
    env_content = {}
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_content[key] = value
    
    # Update with command-line arguments
    if args.cities:
        env_content['SEARCH_CITIES'] = ', '.join(args.cities)
    if args.api_key:
        env_content['GOOGLE_API_KEY'] = args.api_key
    if args.delay:
        env_content['API_DELAY'] = str(args.delay)
    if args.max_pages:
        env_content['MAX_PAGES'] = str(args.max_pages)
    if args.output_dir:
        env_content['OUTPUT_DIR'] = args.output_dir
    if args.browsers:
        env_content['CONCURRENT_BROWSERS'] = str(args.browsers)
    if args.headless and not args.no_headless:
        env_content['HEADLESS'] = 'true'
    elif args.no_headless:
        env_content['HEADLESS'] = 'false'
    if args.log_level:
        env_content['LOG_LEVEL'] = args.log_level
    if args.quota_limit:
        env_content['MAX_REQUESTS_PER_DAY'] = str(args.quota_limit)
    
    # Write updated .env file
    with open(env_file, 'w') as f:
        for key, value in env_content.items():
            f.write(f"{key}={value}\n")


def main():
    """Main CLI function."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Update .env file with command-line arguments
    update_env_file(args)
    
    # Setup logging
    logger = setup_logging(args.log_level)
    
    try:
        if args.verify_only:
            logger.info("Running verification only...")
            run_verifier()
            
        elif args.resume:
            logger.info("Resuming interrupted scrape...")
            run_scraper()
            
        else:
            logger.info(f"Starting scrape for cities: {', '.join(args.cities)}")
            run_scraper()
            
            if args.verify:
                logger.info("Starting verification...")
                run_verifier()
                
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    
    logger.info("Operation completed successfully!")


if __name__ == "__main__":
    main()
