# ScrapeFlow
**Note: This project is currently under heavy development. The examples provided are for demonstration purposes only and are subject to change**

## Overview
The No-Code JSON Web Scraper is a powerful and flexible tool designed to scrape data from websites without writing any code. It allows users to specify the scraping behavior using JSON configuration files, making it accessible to users with minimal programming knowledge.

## Features
* Scrapes data from target URLs based on user-defined configurations.
* Supports multiple target URLs for batch scraping.
* Configurable element selectors (tags, attributes, attribute search hierarchies, and CSS selectors) to target specific data on web pages.
* Advanced data parsing options (e.g., text collection, attribute extraction).
* Provides page navigation options to handle multiple pages or domains.

## Getting Started
* Clone the repository to your local machine.
* Install the required dependencies by running pip install -r requirements.txt.
* Create your JSON configuration file with the desired scraping behavior, see the examples below for example configurations.

##  Example 1: Scraping country names
```json
{
  "target_urls": [
    {
      "url": "https://www.scrapethissite.com/pages/simple/",
      "options": {
        "only_scrape_sub_pages": false,
        "render_pages": false
      }
    }
  ],
  "elements": [
    {
      "name": "country_name",
      "css_selector": ".h3, h3",
      "data_parsing": {
        "collect_text": true
      }
    }
  ],
  "data_saving": {
    "csv": {
      "enabled": true,
      "file_path": "output.csv",
      "delimiter": ","
    }
  },
  "data_order": []
}

```

## Example 2: Scraping Book names and prices

```json
{
  "target_urls": [
    {
      "url": "https://books.toscrape.com/",
      "options": {
        "only_scrape_sub_pages": true,
        "render_pages": false
      }
    }
  ],
  "elements": [
    {
      "name": "Book Price",
      "css_selector": ".product_main p.price_color",
      "data_parsing": {
        "collect_text": true
      }
    },
    {
      "name": "Book Name",
      "css_selector": "h1",
      "data_parsing": {
        "collect_text": true
      }
    }
  ],
  "page_navigator": {
    "allowed_domains": ["books.toscrape.com"],
    "sleep_time": 0.5,
    "url_pattern": "catalogue\\/(?!.*\\bcategory\\b).*",
    "base_url": "https://books.toscrape.com/"
  },
  "data_saving": {
    "csv": {
      "enabled": true,
      "file_path": "output.csv",
      "delimiter": ","
    },
    "database": {
      "enabled": true,
      "type": "mysql",
      "host": "localhost",
      "port": 3306,
      "username": "your_username",
      "password": "your_password",
      "database_name": "your_database"
    }
  },
  "data_order": ["Book Name", "Book Price"]
}
```
## Usage
1. Prepare your JSON configuration file.
2. Run the web scraper using the command python scraper.py your_configuration.json.

## Contributions
Contributions to the No-Code JSON Web Scraper project are welcome! Please open an issue or submit a pull request for bug fixes, improvements, or new features.
