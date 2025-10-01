"""
Utility functions and logging configuration for the Local Business Lead Generator.
"""

import os
import logging
import json
import re
import time
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
        # Validate max_requests_per_day is positive
        if max_requests_per_day <= 0:
            raise ValueError(f"max_requests_per_day must be a positive integer, got {max_requests_per_day}")
        
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
        """Save current quota usage to checkpoint file with atomic write and error handling."""
        data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'requests_made': self.requests_made,
            'max_requests': self.max_requests
        }
        
        # Get logger for error reporting
        logger = logging.getLogger('lead_scraper')
        
        # Ensure directory exists
        checkpoint_dir = os.path.dirname(self.checkpoint_file)
        if checkpoint_dir:
            os.makedirs(checkpoint_dir, exist_ok=True)
        
        # Atomic write with retry logic
        max_retries = 1
        for attempt in range(max_retries + 1):
            try:
                # Create temporary file in same directory
                temp_file = f"{self.checkpoint_file}.tmp"
                
                with open(temp_file, 'w') as f:
                    json.dump(data, f)
                    f.flush()  # Ensure data is written to disk
                    os.fsync(f.fileno())  # Force OS to flush buffers
                
                # Atomic move
                os.replace(temp_file, self.checkpoint_file)
                return  # Success, exit function
                
            except (OSError, IOError, json.JSONEncodeError) as e:
                error_msg = f"Failed to save checkpoint (attempt {attempt + 1}/{max_retries + 1}): {type(e).__name__}: {e}"
                logger.error(error_msg)
                
                # Clean up temp file if it exists
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except OSError:
                    pass  # Ignore cleanup errors
                
                # If this was the last attempt, fail gracefully
                if attempt == max_retries:
                    logger.error("Checkpoint save failed after all retries. Continuing without saving checkpoint.")
                    return  # Fail gracefully instead of raising
                
                # Brief delay before retry
                time.sleep(0.1)
    
    def can_make_request(self) -> bool:
        """Check if we can make another API request."""
        return self.requests_made < self.max_requests
    
    def increment(self) -> None:
        """Increment request counter and save checkpoint."""
        self.requests_made += 1
        self.save_checkpoint()
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        # Guard against division by zero
        usage_percentage = 0.0
        if self.max_requests > 0:
            usage_percentage = (self.requests_made / self.max_requests) * 100
        
        return {
            'requests_made': self.requests_made,
            'max_requests': self.max_requests,
            'remaining': self.max_requests - self.requests_made,
            'usage_percentage': usage_percentage
        }


def setup_logging(log_level: str = "INFO", log_dir: str = "logs") -> logging.Logger:
    """
    Set up structured logging with both file and console output.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to save log files
        
    Returns:
        Configured logger instance
        
    Raises:
        ValueError: If log_level is not a valid logging level
    """
    # Validate log_level against known logging levels
    valid_levels = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
    log_level_upper = log_level.upper()
    
    if log_level_upper not in valid_levels:
        raise ValueError(f"Invalid log_level '{log_level}'. Must be one of: {', '.join(valid_levels)}")
    
    # Get the named logger first
    logger = logging.getLogger('lead_scraper')
    
    # Clear existing handlers to prevent duplicates
    logger.handlers.clear()
    
    # Prevent propagation to root logger to avoid duplicate messages
    logger.propagate = False
    
    # Create logs directory
    os.makedirs(log_dir, exist_ok=True)
    
    # Create timestamp for log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"scraper_{timestamp}.log")
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create and add file handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Create and add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Set logger level using the validated level
    logger.setLevel(getattr(logging, log_level_upper))
    
    logger.info(f"Logging initialized. Log file: {log_file}")
    
    return logger


def validate_city_format(city: str) -> bool:
    """
    Validate city name format using regex-based validation.
    
    Validates that the city string:
    - Contains at least two space-separated parts
    - Allows letters, digits, spaces, hyphens, apostrophes, and periods
    - Has a final token that is either a valid state code or alphabetic
    
    Args:
        city: City name to validate
        
    Returns:
        True if valid format, False otherwise
    """
    if not city or not isinstance(city, str):
        return False
    
    # Trim and collapse whitespace
    city = re.sub(r'\s+', ' ', city.strip())
    
    # Split into parts
    parts = city.split()
    
    # Must have at least two parts
    if len(parts) < 2:
        return False
    
    # Compiled regex for valid characters in city tokens
    # Allows letters, digits, spaces, hyphens, apostrophes, and periods
    city_pattern = re.compile(r'^[A-Za-z0-9 .\'-]+$')
    
    # Check if the full city string matches the allowed character pattern
    if not city_pattern.match(city):
        return False
    
    # Validate the last token (state code or alphabetic token)
    last_token = parts[-1]
    
    # Check if it's a valid state code (2 letters, optionally with periods)
    state_code_pattern = re.compile(r'^[A-Za-z]{2}\.?$')
    if state_code_pattern.match(last_token):
        return True
    
    # If not a state code, check if it's at least alphabetic
    if last_token.isalpha():
        return True
    
    return False


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


def save_checkpoint(processed_items: List[Dict], checkpoint_file: str) -> bool:
    """
    Save progress checkpoint to resume later with atomic write and error handling.
    
    Args:
        processed_items: List of processed business items
        checkpoint_file: Path to checkpoint file
        
    Returns:
        True if checkpoint saved successfully, False otherwise
    """
    checkpoint_data = {
        'timestamp': datetime.now().isoformat(),
        'processed_count': len(processed_items),
        'processed_items': processed_items
    }
    
    # Get logger for error reporting
    logger = logging.getLogger('lead_scraper')
    
    # Ensure directory exists
    checkpoint_dir = os.path.dirname(checkpoint_file)
    if checkpoint_dir:
        try:
            os.makedirs(checkpoint_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create checkpoint directory '{checkpoint_dir}': {e}")
            return False
    
    # Atomic write using temporary file
    temp_file = f"{checkpoint_file}.tmp"
    
    try:
        with open(temp_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
            f.flush()  # Ensure data is written to disk
            os.fsync(f.fileno())  # Force OS to write to disk
        
        # Atomic move - this is atomic on most filesystems
        os.replace(temp_file, checkpoint_file)
        logger.debug(f"Checkpoint saved successfully to '{checkpoint_file}'")
        return True
        
    except (OSError, IOError) as e:
        logger.error(f"Failed to save checkpoint to '{checkpoint_file}': {e}")
        # Clean up temporary file if it exists
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except OSError:
            pass  # Ignore cleanup errors
        return False
        
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to serialize checkpoint data for '{checkpoint_file}': {e}")
        # Clean up temporary file if it exists
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except OSError:
            pass  # Ignore cleanup errors
        return False


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
    except Exception as e:
        logger = logging.getLogger('lead_scraper')
        logger.error(f"Error extracting domain from URL '{url}': {e}")
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
