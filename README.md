# 🏢 Local Business Lead Generator

A powerful Python tool that finds local businesses without websites for web development outreach. Perfect for freelancers, agencies, and developers looking to identify potential clients who need websites.

## ✨ Features

- **Comprehensive Search**: Scrapes 150+ business types across multiple cities
- **Smart Verification**: Two-stage process removes chains and businesses with existing websites
- **Organized Output**: Exports clean CSV files by city and category
- **Rate Limiting**: Built-in API quota management and request throttling
- **Resume Capability**: Checkpoint system to resume interrupted scrapes
- **Stealth Mode**: Advanced anti-detection measures for reliable scraping

## 🎯 What It Does

1. **Scrapes** Google Places API for businesses in your target cities
2. **Filters** out businesses that already have websites
3. **Verifies** results using Google search to remove chains and false positives
4. **Exports** clean, organized lead lists ready for outreach

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd local-search

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

### 2. Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your settings
# Required: Add your Google Places API key
GOOGLE_API_KEY=your_actual_api_key_here
SEARCH_CITIES=New York NY, Los Angeles CA, Chicago IL
```

### 3. Run the Scraper

```bash
# Basic usage - scrape all categories
python scrape_no_website.py

# Verify the results (removes chains and false positives)
python verify_no_website.py
```

## 📋 Configuration Options

Edit your `.env` file to customize the scraper:

```env
# Required
GOOGLE_API_KEY=your_google_places_api_key
SEARCH_CITIES=City1 State, City2 State, City3 State

# Optional
API_DELAY=0.2                    # Delay between API calls (seconds)
OUTPUT_DIR=leads_output          # Output directory for CSV files
MAX_PAGES=3                      # Max pages to scrape per search
CONCURRENT_BROWSERS=3            # Number of parallel verification browsers
```

## 📊 Output Files

The scraper generates several organized CSV files:

- `all_leads_no_website_YYYYMMDD_HHMMSS.csv` - All leads combined
- `leads_CityName_YYYYMMDD_HHMMSS.csv` - Leads by city
- `leads_category_YYYYMMDD_HHMMSS.csv` - Leads by business category
- `verified/verified_no_website_YYYYMMDD_HHMMSS.csv` - Final verified leads

## 🏢 Business Categories

The scraper searches for 150+ business types across 12 categories:

- **Food & Beverage**: Restaurants, cafes, bars, food trucks
- **Retail**: Clothing stores, boutiques, gift shops
- **Health & Wellness**: Gyms, spas, salons, medical practices
- **Professional Services**: Law firms, accounting, real estate
- **Home Services**: Plumbers, electricians, contractors
- **Automotive**: Repair shops, dealerships, detailing
- **Entertainment**: Bowling alleys, arcades, venues
- **Education**: Daycares, schools, tutoring centers
- **Events**: Venues, photographers, caterers
- **Manufacturing**: Factories, wholesalers, suppliers
- **Agriculture**: Farms, nurseries, pet services
- **Transportation**: Trucking, moving, logistics

## 🔧 Advanced Usage

### Custom Search Categories

Edit `BUSINESS_CATEGORIES` in `scrape_no_website.py` to add your own business types:

```python
BUSINESS_CATEGORIES = {
    "your_category": [
        "business type 1",
        "business type 2",
        # ... add more
    ]
}
```

### Resume Interrupted Scrapes

The scraper automatically saves progress. If interrupted, it will resume from where it left off on the next run.

### Memory Optimization

For large datasets (10k+ businesses), the scraper uses batch processing to prevent memory issues.

## 🛡️ API Limits & Best Practices

- **Google Places API**: 25,000 requests/day (free tier)
- **Rate Limiting**: Built-in delays prevent quota exceeded errors
- **Quota Tracking**: Monitor your API usage in real-time
- **Stealth Mode**: Random delays and user agents to avoid detection

## 📈 Expected Results

Typical results per city:

- **Small cities** (50k population): 200-500 leads
- **Medium cities** (200k population): 500-1,200 leads
- **Large cities** (1M+ population): 1,200-3,000 leads

**Verification rate**: ~60-70% of initial leads pass verification

## 🚨 Troubleshooting

### Common Issues

**"GOOGLE_API_KEY not found"**

- Make sure you have a `.env` file with your API key
- Verify the API key is valid and has Places API enabled

**"No leads found"**

- Check your API quota hasn't been exceeded
- Verify city names are spelled correctly
- Try reducing the number of search keywords

**Playwright errors**

- Run `playwright install chromium` to install the browser
- Check your internet connection

### Getting Help

1. Check the logs in the `logs/` directory
2. Verify your `.env` configuration
3. Test with a single city first
4. Check Google Cloud Console for API quota status

## 🔒 Security & Privacy

- API keys are stored in `.env` files (never committed to git)
- No personal data is collected or stored
- All data processing happens locally
- Respects Google's Terms of Service

## 📝 License

This project is open source. Feel free to modify and distribute according to your needs.

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- Additional business categories
- Better deduplication algorithms
- Enhanced stealth measures
- New export formats

## 📞 Support

For questions or issues:

1. Check the troubleshooting section above
2. Review the logs for error details
3. Open an issue with your configuration and error details

---

**Happy Lead Hunting! 🎯**
