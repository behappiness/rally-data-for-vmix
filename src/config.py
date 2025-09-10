"""Configuration management for Rally Data Scraper."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables using python-dotenv."""
    
    def __init__(self):
        """Initialize settings from environment variables."""
        # API Configuration - Required values, no defaults for sensitive data
        self.api_base_url = os.getenv("API_BASE_URL")
        self.api_error_code = os.getenv("API_ERROR_CODE")  # Sensitive - no default
        self.user_agent = os.getenv("USER_AGENT")
        
        # Validate required API settings
        if not all([self.api_base_url, self.api_error_code, self.user_agent]):
            missing = [k for k, v in {
                "API_BASE_URL": self.api_base_url,
                "API_ERROR_CODE": self.api_error_code,
                "USER_AGENT": self.user_agent
            }.items() if not v]
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        # HTTP Configuration - with sensible defaults
        self.request_timeout_seconds = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
        
        # Data Storage
        self.csv_output_dir = os.getenv("CSV_OUTPUT_DIR", "./output")
        self.csv_delimiter = os.getenv("CSV_DELIMITER", ",")
        
        # Export Configuration
        self.csv_export_enabled = os.getenv("CSV_EXPORT_ENABLED", "true").lower() == "true"
        self.excel_export_enabled = os.getenv("EXCEL_EXPORT_ENABLED", "true").lower() == "true"
        self.excel_filename = os.getenv("EXCEL_FILENAME", "rally_data.xlsx")
        
        # Racing Number and Stage Settings
        self.racing_number_tab = os.getenv("RACING_NUMBER_TAB", "Settings")
        self.racing_number_range = os.getenv("RACING_NUMBER_RANGE", "A1:D3")
        self.racing_speed_filename = os.getenv("RACING_SPEED_FILENAME", "racing_speed")
    
        # HTTP Server Configuration
        self.http_server_host = os.getenv("HTTP_SERVER_HOST", "localhost")
        self.http_server_port = int(os.getenv("HTTP_SERVER_PORT", "8000"))
        
        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = os.getenv("LOG_FILE", "rally_data.log")


# Global settings instance
settings = Settings()