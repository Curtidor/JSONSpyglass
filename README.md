# ScrapeFlow
**Note: This project is currently under heavy development. The examples provided are for demonstration purposes only and are subject to change**

## Overview
The No-Code JSON Web Scraper is a powerful and flexible tool designed to scrape data from websites without writing any code. It allows users to specify the scraping behavior using JSON configuration files, making it accessible to users with minimal programming knowledge.

## Features
* Scrapes data from target URLs based on user-defined configurations.
* Supports multiple target URLs for batch scraping.
* Configurable element selectors (tags and attributes) to target specific data on web pages.
* Advanced data parsing options (e.g., text collection, attribute extraction).
* Provides page navigation options to handle multiple pages or domains.

## Getting Started
* Clone the repository to your local machine.
* Install the required dependencies by running pip install -r requirements.txt.
* Create your JSON configuration file with the desired scraping behavior, see the examples below example configurations.

##  Example 1: Scraping Product Prices
```json
{
  "target_urls": ["https://books.toscrape.com/"],
  "elements": [
    {
      "name": "product_price",
      "tag": "p",
      "attributes": [
        {
          "name": "class",
          "value": "price_color"
        }
      ],
      "page_navigator": "global",
      "data_parsing": {
         "collect_text": true
      }
    }
  ],
  "page_navigator":
    {
      "allowed_domains": ["books.toscrape.com"],
      "sleep_time": 0.5,
      "url_pattern": "\\/catalogue\\/.*",
      "target_elements": ["product_price"]
    }
}
```

## Example 2: Scraping Country Names and Teams

```json
{
  "target_urls": ["https://www.scrapethissite.com/pages/simple/",
    "https://www.scrapethissite.com/pages/forms/"],
  "elements": [
    {
      "tag": "h3",
      "attributes": [
        {
          "name": "class",
          "value": "country-name"
        }
      ],
      "data_parsing": {
         "collect_text": true
      }
    },
    {
      "tag": "tr",
      "attributes": [
        {
          "name": "class",
          "value": "team"
        }
        ],
      "data_parsing": {
        "collect_text": true
      }
    }
  ]
}
```
## Usage
1. Prepare your JSON configuration file.
2. Run the web scraper using the command python scraper.py your_configuration.json.

## Contributions
Contributions to the No-Code JSON Web Scraper project are welcome! Please open an issue or submit a pull request for bug fixes, improvements, or new features.
