# Rally Data Scraper for vMix

A Python 3.12 async application for scraping rally data from HauserResults API and exporting to CSV files.

## Features

- **Async API Client**: Performant HTTP client for HauserResults API
- **HTTP Trigger API**: On-demand data fetching via HTTP requests
- **CSV & Excel Export**: Configurable CSV export and Excel workbook with multiple tabs
- **xlwings Integration**: Automatic Excel export with each dataset in separate tabs

## Quick Start

### 1. Setup Environment
```bash
# Copy and configure environment file
copy config.env.example .env
# Edit .env with your API credentials
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Application
```bash
python run.py
```

## Configuration

Key environment variables in `.env`:

```bash
# Required API Configuration
API_BASE_URL=https://hauserresults.hu
API_ERROR_CODE=your_error_code
API_EVENT_ID=event_id
USER_AGENT=your_user_agent

# Optional Settings
HTTP_SERVER_HOST=localhost
HTTP_SERVER_PORT=8000
CSV_OUTPUT_DIR=./output
CSV_DELIMITER=,
CSV_EXPORT_ENABLED=true
EXCEL_EXPORT_ENABLED=true
EXCEL_FILENAME=rally_data.xlsx
LOG_LEVEL=INFO
```

## Usage

### Trigger Data Export
```bash
# Export all data types for rally class 1 (ORB+Int/ERC)
curl -X POST http://localhost:8000/trigger \
  -H "Content-Type: application/json" \
  -d '{"rally_class": 1}'

# Rally classes: 1=ORB+Int/ERC, 2=Rallye2, 3=Historic
```

### Output Files

**CSV Files:**
- `entry_list.csv` - Entry list data
- `start_list.csv` - Start list data  
- `route_sheet.csv` - Route sheet data
- `stage_results_{stage}.csv` - Stage results
- `current_stage.csv` - Current stage info
- `enhanced_current_{stage}.csv` - Enhanced stage data with GPS

**Excel File:**
- `rally_data.xlsx` - All datasets in separate tabs (Entry_List, Start_List, Route_Sheet, Stage_Results_{stage}, etc.)

## API Endpoints

- `GET /` - Application info
- `POST /trigger` - Trigger data export with rally class

## Architecture

- **`src/api_client.py`** - HauserResults API client
- **`src/data_store.py`** - Data processing and callbacks
- **`src/csv_exporter.py`** - CSV export with configurable delimiter
- **`src/http_handler.py`** - FastAPI HTTP server
- **`src/config.py`** - Environment configuration
- **`src/main.py`** - Application entry point

## Logging

Logs show timestamp with milliseconds, level, filename, and message:
```
2024-01-15 14:30:25.123 - INFO - api_client.py - Fetching entry list data
2024-01-15 14:30:25.456 - INFO - csv_exporter.py - Exported 50 records to ./output/entry_list.csv
```

## Requirements

- Python 3.12+
- Microsoft Excel (for xlwings functionality)
- Dependencies listed in `requirements.txt`
- Valid HauserResults API credentials

## Excel Export Features

- **Automatic Excel Export**: When `EXCEL_EXPORT_ENABLED=true`, all CSV data is also exported to a single Excel file
- **Multiple Tabs**: Each data type gets its own worksheet tab (Entry_List, Start_List, Route_Sheet, etc.)
- **Auto-formatting**: Columns are auto-fitted and headers are included
- **Configurable Filename**: Set via `EXCEL_FILENAME` environment variable
- **xlwings Integration**: Uses xlwings for robust Excel file creation and manipulation