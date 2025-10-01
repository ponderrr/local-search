"""
Utility functions and logging configuration for the Local Business Lead Generator.
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ScraperConfig:
    """Configuration class for the scraper with validation."""
    
    # Required settings
    api_key: str
    cities: List[str]
    
    # Optional settings with defaults
    api_delay: float = 0.2
    output_dir: str = "leads_output"
    max_pages: int = 3
    concurrent_browsers: int = 3
    search_delay_min: float = 1.0
    search_delay_max: float = 3.0
    headless: bool = True
    max_requests_per_day: int = 25000
    batch_size: int = 1000
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> 'ScraperConfig':
        """Load configuration from environment variables."""
        from dotenv import load_dotenv
        load_dotenv()
        
        # Required settings
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment or .env file")
        
        cities_env = os.getenv("SEARCH_CITIES")
        if not cities_env:
            raise ValueError(
                "SEARCH_CITIES not found in .env file. "
                "Please add: SEARCH_CITIES=City1 State, City2 State, City3 State"
            )
        cities = [city.strip() for city in cities_env.split(",")]
        
        # Optional settings
        return cls(
            api_key=api_key,
            cities=cities,
            api_delay=float(os.getenv("API_DELAY", "0.2")),
            output_dir=os.getenv("OUTPUT_DIR", "leads_output"),
            max_pages=int(os.getenv("MAX_PAGES", "3")),
            concurrent_browsers=int(os.getenv("CONCURRENT_BROWSERS", "3")),
            search_delay_min=float(os.getenv("SEARCH_DELAY_MIN", "1.0")),
            search_delay_max=float(os.getenv("SEARCH_DELAY_MAX", "3.0")),
            headless=os.getenv("HEADLESS", "true").lower() == "true",
            max_requests_per_day=int(os.getenv("MAX_REQUESTS_PER_DAY", "25000")),
            batch_size=int(os.getenv("BATCH_SIZE", "1000")),
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )
    
    def validate(self) -> None:
        """Validate configuration settings."""
        if not self.api_key or len(self.api_key) < 10:
            raise ValueError("Invalid API key format")
        
        if not self.cities:
            raise ValueError("No cities specified")
        
        if self.api_delay < 0.1:
            raise ValueError("API delay too low (minimum 0.1 seconds)")
        
        if self.max_pages < 1 or self.max_pages > 10:
            raise ValueError("Max pages must be between 1 and 10")
        
        if self.concurrent_browsers < 1 or self.concurrent_browsers > 10:
            raise ValueError("Concurrent browsers must be between 1 and 10")


class APIQuotaTracker:
    """Track Google API usage to prevent quota exceeded errors."""
    
    def __init__(self, max_requests_per_day: int = 25000, checkpoint_file: str = "api_quota.json"):
        self.max_requests = max_requests_per_day
        self.requests_made = 0
        self.checkpoint_file = checkpoint_file
        self.load_checkpoint()
    
    def load_checkpoint(self) -> None:
        """Load quota usage from checkpoint file."""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    data = json.load(f)
                    # Reset if it's a new day
                    if data.get('date') == datetime.now().strftime('%Y-%m-%d'):
                        self.requests_made = data.get('requests_made', 0)
                    else:
                        self.requests_made = 0
            except (json.JSONDecodeError, KeyError):
                self.requests_made = 0
    
    def save_checkpoint(self) -> None:
        """Save current quota usage to checkpoint file."""
        data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'requests_made': self.requests_made,
            'max_requests': self.max_requests
        }
        with open(self.checkpoint_file, 'w') as f:
            json.dump(data, f)
    
    def can_make_request(self) -> bool:
        """Check if we can make another API request."""
        return self.requests_made < self.max_requests
    
    def increment(self) -> None:
        """Increment request counter and save checkpoint."""
        self.requests_made += 1
        self.save_checkpoint()
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        return {
            'requests_made': self.requests_made,
            'max_requests': self.max_requests,
            'remaining': self.max_requests - self.requests_made,
            'usage_percentage': (self.requests_made / self.max_requests) * 100
        }


def setup_logging(log_level: str = "INFO", log_dir: str = "logs") -> logging.Logger:
    """
    Set up structured logging with both file and console output.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to save log files
        
    Returns:
        Configured logger instance
    """
    # Create logs directory
    os.makedirs(log_dir, exist_ok=True)
    
    # Create timestamp for log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"scraper_{timestamp}.log")
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger('lead_scraper')
    logger.info(f"Logging initialized. Log file: {log_file}")
    
    return logger


def validate_city_format(city: str) -> bool:
    """
    Validate city name format.
    
    Args:
        city: City name to validate
        
    Returns:
        True if valid format, False otherwise
    """
    # Basic validation: should contain at least city and state
    parts = city.strip().split()
    return len(parts) >= 2 and all(part.isalpha() for part in parts)


def validate_api_key(api_key: str) -> bool:
    """
    Validate Google API key format.
    
    Args:
        api_key: API key to validate
        
    Returns:
        True if valid format, False otherwise
    """
    # Google API keys are typically 39 characters and start with 'AIza'
    return len(api_key) >= 30 and api_key.startswith('AIza')


def save_checkpoint(processed_items: List[Dict], checkpoint_file: str) -> None:
    """
    Save progress checkpoint to resume later.
    
    Args:
        processed_items: List of processed business items
        checkpoint_file: Path to checkpoint file
    """
    checkpoint_data = {
        'timestamp': datetime.now().isoformat(),
        'processed_count': len(processed_items),
        'processed_items': processed_items
    }
    
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint_data, f, indent=2)


def load_checkpoint(checkpoint_file: str) -> Dict[str, Any]:
    """
    Load progress checkpoint.
    
    Args:
        checkpoint_file: Path to checkpoint file
        
    Returns:
        Checkpoint data or empty dict if file doesn't exist
    """
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {'processed_items': []}
    return {'processed_items': []}


def extract_domain(url: str) -> str:
    """
    Extract the base domain from a URL.
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Clean domain name
    """
    from urllib.parse import urlparse
    
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


def fuzzy_match(a: str, b: str, threshold: float = 0.85) -> bool:
    """
    Check if two strings are similar using fuzzy matching.
    
    Args:
        a: First string
        b: Second string
        threshold: Similarity threshold (0.0 to 1.0)
        
    Returns:
        True if strings are similar enough
    """
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() > threshold


# Constants for magic numbers
class ScraperConstants:
    """Constants to replace magic numbers throughout the codebase."""
    
    # API and rate limiting
    MIN_API_DELAY = 0.1
    DEFAULT_API_DELAY = 0.2
    MAX_API_DELAY = 5.0
    
    # Search pagination
    MIN_PAGES = 1
    DEFAULT_PAGES = 3
    MAX_PAGES = 10
    
    # Browser settings
    MIN_BROWSERS = 1
    DEFAULT_BROWSERS = 3
    MAX_BROWSERS = 10
    
    # Delays
    MIN_SEARCH_DELAY = 0.5
    DEFAULT_SEARCH_DELAY_MIN = 1.0
    DEFAULT_SEARCH_DELAY_MAX = 3.0
    MAX_SEARCH_DELAY = 10.0
    
    # Memory management
    DEFAULT_BATCH_SIZE = 1000
    MIN_BATCH_SIZE = 100
    MAX_BATCH_SIZE = 10000
    
    # Business name validation
    MIN_BUSINESS_NAME_LENGTH = 4
    
    # API quotas
    GOOGLE_PLACES_FREE_QUOTA = 25000
    GOOGLE_PLACES_PAID_QUOTA = 100000
    
    # File paths
    DEFAULT_OUTPUT_DIR = "leads_output"
    DEFAULT_LOG_DIR = "logs"
    DEFAULT_CHECKPOINT_DIR = "checkpoints"
