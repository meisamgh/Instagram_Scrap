# Instagram Data Collection Toolkit

A Python toolkit for collecting public Instagram engagement data such as posts, comments, replies, likes, and follower information. The repository also contains legacy browser-automation experiments built with Selenium.

> **Status:** Legacy / research project. The project was originally built around Instagram web endpoints and page structures available at the time. Instagram changes its internal APIs and frontend frequently, so parts of the code may require modernization before they work reliably today.

## Overview

The project contains two main areas:

1. **Data collection** — scripts for extracting public engagement data and storing results as CSV files.
2. **Legacy browser automation** — Selenium-based experiments for automating browser flows.

The data-collection workflow uses a bundled `igramscraper` client that manages authentication, requests, pagination, and model conversion.

## Repository Structure

```text
Instagram_Scrap/
├── Comment_scrap.py                 # Collect comments and replies
├── Like_scrap.py                    # Collect likes and liker metadata
├── get_follwers.py                  # Collect follower information
├── Instagram_Account_Creator.py     # Legacy Selenium automation experiment
├── Instagram_Account_Creator_Proxy.py
├── igramscraper/                    # Custom Instagram client and models
├── requirements.txt                 # Python dependencies
└── README.md
```

## Core Workflow

```text
Instagram account/session
        │
        ▼
  igramscraper client
        │
        ├── profile & media discovery
        ├── comments / replies
        ├── likes
        └── followers
        │
        ▼
 pagination + checkpointing
        │
        ▼
       CSV files
```

The scraper rotates between configured sessions and periodically saves intermediate results so that long-running collection jobs can preserve progress.

## Features

- Collect profile and media metadata
- Collect post comments and threaded replies
- Collect likes and basic liker metadata
- Collect follower information
- Paginated collection for larger datasets
- Multi-session/account rotation
- Periodic CSV checkpointing
- Custom Instagram response models
- Optional proxy/browser automation experiments

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/meisamgh/Instagram_Scrap.git
cd Instagram_Scrap
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Because this is a legacy project, compatibility can depend on the Python, pandas, Selenium, and Instagram endpoint versions being used.

## Configuration

Do **not** store usernames, passwords, cookies, proxy credentials, or other secrets directly in committed source files.

For local development, keep sensitive configuration outside Git and load it from environment variables or an ignored local configuration file.

Example environment variables:

```bash
export INSTAGRAM_USERNAME="your_username"
export INSTAGRAM_PASSWORD="your_password"
export OUTPUT_PATH="./data"
```

The existing scripts contain legacy inline configuration and should be refactored to consume environment-based configuration before production use.

## Output

Depending on the script, generated data can include:

- `comments.csv`
- `replay.csv`
- `likes.csv`
- `followers_info.csv`
- `page_info.csv`
- pagination/checkpoint CSV files

Generated datasets, sessions, cookies, and local credentials should remain outside version control.

## Technical Notes

The bundled client relies on Instagram web requests and internal GraphQL-style endpoints. These endpoints are not a stable public API and can change without notice.

The Selenium scripts also use browser selectors and APIs that were valid when the project was created. Modern Selenium versions and the current Instagram UI may require updated locators and WebDriver initialization.

## Known Limitations

- Instagram internal endpoints can change or disappear.
- Login and checkpoint flows can change over time.
- Rate limiting and anti-automation controls may interrupt collection.
- Some Selenium APIs used by the legacy scripts are deprecated in modern Selenium.
- Several scripts currently combine configuration, collection, retry logic, and persistence in one module.
- There is currently no automated test suite.

## Recommended Modernization

A cleaner production-oriented architecture would separate:

```text
src/
├── client.py
├── config.py
├── comments.py
├── likes.py
├── followers.py
├── storage.py
└── cli.py
```

Recommended next steps:

- move all secrets to environment variables
- replace hard-coded local filesystem paths
- introduce structured logging
- add bounded retries with exponential backoff
- add typed configuration and CLI arguments
- add unit/integration tests
- modernize pandas and Selenium usage
- replace obsolete Instagram endpoint assumptions

## Responsible Use

Use this project only in ways that respect applicable laws, privacy requirements, platform rules, and the rights of account holders. Avoid collecting or storing personal data that you do not have a legitimate reason to process.

This project is not affiliated with, endorsed by, or maintained by Instagram or Meta.

## Author

**Meisam Ghafarlangroudi**

Data Science / Machine Learning / Data Engineering

---

If you are using this repository as a portfolio project, the strongest next improvement is to modernize the scraper client and separate configuration, collection, storage, and retry logic into testable modules.
