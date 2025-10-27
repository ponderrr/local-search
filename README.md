# 🎯 Local Business Lead Generator

### *Find businesses without websites. Build your client pipeline.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

---

## 🎯 What It Does

A powerful Python tool that automatically discovers local businesses without websites—perfect for:
- 🎨 Freelance Web Developers
- 🏢 Digital Agencies  
- 💼 Marketing Consultants
- 🚀 Web Design Entrepreneurs

**The Problem:** Finding businesses without websites manually takes hours.
**The Solution:** This tool automates the entire discovery process.

---

## ✨ Key Features

<table>
<tr>
<td width="50%">

### 🔍 Smart Discovery
- Searches 150+ business types
- Multi-city support
- 60+ results per search
- Automated pagination

</td>
<td width="50%">

### 🎯 Intelligent Filtering
- Removes chain businesses
- Filters out existing websites
- Excludes social media profiles
- Validates business status

</td>
</tr>
<tr>
<td width="50%">

### 📊 Rich Data Export
- Business name & category
- Phone & address
- Ratings & reviews
- Operating hours
- 15+ data points per lead

</td>
<td width="50%">

### 🛡️ Production Ready
- API quota management
- Rate limiting protection
- Checkpoint recovery
- Comprehensive logging
- Stealth anti-detection

</td>
</tr>
</table>

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Python 3.8+
- Google Places API key ([Get free key](https://developers.google.com/maps/documentation/places/web-service/get-api-key))

### Installation

```bash
# Clone and enter directory
git clone https://github.com/ponderrr/local-search.git
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

# Install browser for verification
playwright install chromium
```

### Configuration

```bash
# Copy example config
cp .env.example .env

# Edit with your settings (required: API key and cities)
nano .env  # or use your editor
```

### Run

```bash
# Scrape businesses
python scrape_no_website.py

# Verify results (removes chains/false positives)
python verify_no_website.py

# View analytics
python analytics_dashboard.py
```

**Done!** Check `leads_output/` for your CSV files.

---

## ⚙️ Configuration

### Required Settings (.env file)

```env
GOOGLE_API_KEY=your_api_key_here
SEARCH_CITIES=Austin TX, Portland OR, Denver CO
```

### Optional Settings (with defaults)

| Setting | Default | Description |
|---------|---------|-------------|
| `API_DELAY` | 0.2 | Seconds between API calls |
| `MAX_PAGES` | 3 | Pages per search (1-10) |
| `CONCURRENT_BROWSERS` | 3 | Parallel verification browsers |
| `HEADLESS` | true | Run browsers invisibly |
| `OUTPUT_DIR` | leads_output | Where to save results |

**Performance Tips:**
- **Faster:** `API_DELAY=0.15`, `MAX_PAGES=2`, `CONCURRENT_BROWSERS=5`
- **Safer:** `API_DELAY=0.3`, `MAX_PAGES=3`, `CONCURRENT_BROWSERS=2`

---

## 📊 What You Get

### Output Files

```
leads_output/
├── all_leads_no_website_TIMESTAMP.csv           # All leads
├── leads_CityName_TIMESTAMP.csv                 # By city
├── leads_category_TIMESTAMP.csv                 # By category
└── verified/
    └── verified_no_website_TIMESTAMP.csv        # ⭐ Clean leads
```

### Data Fields (15+ per business)

**Core Info:** Name, Phone, Address, City
**Engagement:** Rating, Reviews, Hours, Open Status
**Intelligence:** Category, Price Level, Services, Accessibility

### Expected Results

| City Size | Population | Expected Leads |
|-----------|-----------|----------------|
| Small | 50k | 200-500 |
| Medium | 200k | 500-1,200 |
| Large | 1M+ | 1,200-3,000 |

**Verification Rate:** 60-70% pass final verification

---

## 🏢 Business Categories (150+ Types)

The scraper searches 12 categories with 150+ specific business types:

**Food & Beverage** • **Retail** • **Health & Wellness** • **Professional Services** • **Home Services** • **Automotive** • **Entertainment** • **Education** • **Events** • **Manufacturing** • **Agriculture** • **Transportation**

Full list in `scrape_no_website.py` (easily customizable)

---

## 🛡️ Anti-Detection & Stealth Features

Built-in measures to avoid detection and rate limiting:

- ✅ Random delays between requests (0.5-3 seconds)
- ✅ Rotating user agents
- ✅ Browser fingerprint masking
- ✅ Human-like interaction patterns
- ✅ Exponential backoff on errors
- ✅ API quota tracking and limits

---

## 📈 Analytics Dashboard

Generate interactive HTML dashboards:

```bash
python analytics_dashboard.py
```

**Includes:**
- Business distribution by city
- Category breakdown charts
- Data quality metrics
- Rating statistics
- Interactive visualizations

---

## 🔧 Advanced Usage

### Custom Business Categories

Edit `BUSINESS_CATEGORIES` in `scrape_no_website.py`:

```python
BUSINESS_CATEGORIES = {
    "your_niche": [
        "specific business type",
        "another business type"
    ]
}
```

### Command Line Interface

```bash
# Quick scrape specific cities
python run_scraper.py --cities "Austin TX" "Seattle WA"

# Scrape and verify in one command
python run_scraper.py --cities "Denver CO" --verify

# Resume interrupted scrape
python run_scraper.py --resume

# Custom settings
python run_scraper.py --cities "NYC NY" --delay 0.3 --max-pages 2
```

---

## 🐛 Troubleshooting

<details>
<summary><b>❌ "GOOGLE_API_KEY not found"</b></summary>

**Fix:**
1. Ensure `.env` file exists in project root
2. Verify API key format (starts with 'AIza')
3. Enable Places API in Google Cloud Console
4. No extra spaces around the key
</details>

<details>
<summary><b>❌ "No leads found"</b></summary>

**Fix:**
1. Check API quota in Google Cloud Console
2. Verify city format: `"Austin TX"` not `"Austin, Texas"`
3. Test with one city first
4. Check logs in `logs/` directory
</details>

<details>
<summary><b>❌ Playwright errors</b></summary>

**Fix:**
```bash
playwright install chromium --force
```
</details>

<details>
<summary><b>⚠️ "API quota exceeded"</b></summary>

**Fix:**
- Wait 24 hours for quota reset
- Upgrade to paid tier (100k requests/day)
- Reduce `MAX_PAGES` in .env
- Process fewer cities at once
</details>

---

## 📝 API Limits & Costs

**Google Places API:**
- **Free Tier:** 25,000 requests/day
- **Cost After:** $17 per 1,000 requests
- **Paid Tier:** 100,000+ requests/day

**Tool automatically:**
- ✅ Tracks your usage
- ✅ Prevents quota exceeded errors
- ✅ Shows remaining quota

---

## 🔒 Security Best Practices

1. **Never commit `.env`** - Already in .gitignore
2. **Rotate API keys** every 90 days
3. **Restrict API keys** by IP (optional)
4. **Monitor usage** in Google Cloud Console
5. **Use separate keys** for dev/production

---

## 📄 License

MIT License - See LICENSE file for details.

**TL;DR:** Use commercially, modify freely, distribute openly. Just include the license.

---

## 💬 Support

- 📖 Check logs in `logs/` directory
- 🔍 Review this README thoroughly
- 🐛 Open issues on GitHub
- 💡 Suggest features

---

## 🙏 Acknowledgments

- Google Places API for business data
- Playwright for browser automation
- Python community for amazing libraries

---

<div align="center">

**Made with ❤️ for web developers and digital agencies**

⭐ Star this repo if it helps you land clients!

</div>