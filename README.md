<div align="center">
  <img src="banner.png" alt="WP-Hunter Banner" width="600"/>
</div>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.6%2B-blue?logo=python&logoColor=white" alt="Python 3.6+">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License MIT">
  <img src="https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey" alt="Platform">
</p>

WP-Hunter is a **WordPress plugin reconnaissance and reconnaissance tool**. It is designed for **security exploration** and evaluates the **probability** of potential vulnerabilities or outdated plugins by analyzing metadata, installation patterns, and update histories from the WordPress plugin repository.

> [!IMPORTANT]
> This is an **exploration tool**. It does not guarantee the existence of a vulnerability; instead, it provides a "Vulnerability Probability Score" (VPS) based on heuristics to help researchers prioritize their findings.

## Demo

<div align="center">
  <img src="demo.jpeg" alt="WP-Hunter Demo" width="800"/>
</div>

*WP-Hunter tool in action, showing plugin reconnaissance and probability scoring*

## Report Example

<div align="center">
  <img src="html.png" alt="HTML Report Example" width="800"/>
</div>

*Generated HTML report showing vulnerability risks*

## Core Concept: Discovery, Not Exploitation

WP-Hunter follows a "passive-first" reconnaissance approach:
- **Heuristic Scoring**: Uses weighted algorithms to estimate the likelihood of security risks.
- **Changelog Analysis**: Scans recent updates for security-related keywords.
- **Contextual Awareness**: Flags plugins handling sensitive data (e.g., payments, user roles).
- **No Active Scanning**: Performs data gathering from official APIs without intrusive probes against live sites.

## Installation

### Prerequisites
- Python 3.6 or higher
- pip (Python package installer)

### Setup
1. Clone or download the repository
2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
3. Install required dependencies:
```bash
pip install requests
```

## Usage

Run the tool to start the exploration:
```bash
python3 wp-hunter.py
```

### Command Line Options

- `--pages`: Maximum number of pages to scan (default: 5)
- `--limit`: Maximum number of targets to list (0 = Unlimited, default: 0)
- `--min`: Minimum active installations (default: 1000)
- `--max`: Maximum active installations (0 = Unlimited, default: 0)
- `--sort`: Sort method (choices: new, updated, popular, default: updated)
- `--smart`: Show only plugins in risky categories
- `--abandoned`: Show only plugins that haven't been updated in over 2 years
- `--output`: Save results to a file (e.g., `results.json`)
- `--format`: Output format (choices: `json`, `csv`, `html`, default: `json`)

### Example Commands

Focus on high-risk categories with installation limits:
```bash
python3 wp-hunter.py --limit 10 --min 1000 --max 5000 --smart
```

Review probability scores for recently updated plugins:
```bash
python3 wp-hunter.py --sort updated --pages 3 --limit 20
```

Find "zombie" plugins (abandoned > 2 years) and save report:
```bash
python3 wp-hunter.py --abandoned --limit 50 --output zombie_plugins.json
```

## Features

- **VPS Scoring**: Generates a risk probability score (0-100) based on multiple factors.
- **Security Signal Detection**: Flags potential security patches in changelogs.
- **Risk Identification**: Automatically categorizes plugins by their functional sensitivity.
- **WP Version Compatibility**: Checks if plugins are tested against the latest WordPress releases.
- **Direct Research Links**: Provides quick access to Trac logs, **CVE database**, and **WPScan** for deeper manual analysis.
- **Data Export**: Save reconnaissance results to **JSON**, **CSV**, or **HTML** for reporting.
- **Author Reputation**: Highlights trusted authors (Automattic/WordPress) to help focus on less-known sources.
- **High Performance**: Uses **multi-threaded** scanning to process multiple pages concurrently.

## Risk Categories

The tool identifies plugins in sensitive functional areas where vulnerabilities often carry higher impact:
- E-commerce and Payment Gateways
- Form Builders and Input Systems
- Media Uploaders and Managers
- Authentication and User Management
- Database and API Connectors

## Score Interpretation

- **CRITICAL (80-100)**: Very high probability of relevance; manual audit highly recommended.
- **HIGH (50-79)**: Significant risk indicators; worth further investigation.
- **LOW (0-49)**: Lower probability of immediate interest; routine monitoring.

## Legal Disclaimer

This tool is designed for **security research and authorized reconnaissance** purposes only. It is intended to assist security professionals and developers in assessing attack surfaces and evaluating plugin health. The authors are not responsible for any misuse. Always ensure you have appropriate authorization before performing any security-related activities.
