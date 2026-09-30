# Instagram Scrap

Python tools for collecting public Instagram engagement data such as comments, replies, likes, and followers.

> This is a legacy/research project. It uses Instagram web/internal endpoints, so endpoint changes or anti-automation controls can break collection.

## What It Collects

- comments and replies
- post likes and liker metadata
- followers
- basic post/profile metadata

## Structure

```text
Instagram_Scrap/
├── Comment_scrap.py          # comments + replies
├── Like_scrap.py             # likes
├── get_followers.py          # followers
├── get_follwers.py           # old-name compatibility wrapper
├── scraper_runtime.py        # config, login, retries, logging, storage
├── igramscraper/             # Instagram client and response models
├── requirements.txt          # core scraper dependencies
└── requirements-legacy.txt   # old Selenium experiments
```

## Setup

```bash
git clone https://github.com/meisamgh/Instagram_Scrap.git
cd Instagram_Scrap

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
```

Add credentials to `.env`:

```env
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
OUTPUT_PATH=./data
```

For multiple accounts, use `INSTAGRAM_ACCOUNTS_JSON` as shown in `.env.example`.

Never commit `.env`, passwords, cookies, or session files.

## Usage

Comments:

```bash
python Comment_scrap.py target_username
```

Likes:

```bash
python Like_scrap.py target_username
```

Followers:

```bash
python get_followers.py target_username
```

Resume an interrupted job:

```bash
python Comment_scrap.py target_username --resume
```

Useful options:

```text
--output-dir ./data
--num-posts 100
--page-size 50
--request-attempts 4
--request-delay 0.5
--log-level INFO
```

## How It Works

```text
configured Instagram sessions
          ↓
     igramscraper
          ↓
 comments / likes / followers
          ↓
 bounded retry + pagination
          ↓
 checkpoint files + CSV output
```

Long-running jobs save checkpoint state so they can resume after interruption. CSV files are written atomically to reduce the chance of corrupted output.

## Output

Files are written under:

```text
data/Data_<username>/
```

Typical outputs include:

```text
comments.csv
replies.csv
likes.csv
followers_info.csv
page_info.csv
*_checkpoint.json
```

## Legacy Browser Automation

`Instagram_Account_Creator.py` and `Instagram_Account_Creator_Proxy.py` are historical Selenium experiments and are not part of the supported scraping path.

If you need to inspect them, install the optional legacy dependencies:

```bash
pip install -r requirements-legacy.txt
```

## Important Notes

- Instagram internal endpoints are not a stable public API.
- Use bounded request rates and respect platform rules and applicable privacy laws.
- Do not collect or retain personal data without a legitimate reason.
- This project is not affiliated with Instagram or Meta.
