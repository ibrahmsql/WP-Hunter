"""
WP-Hunter CLI

Command-line interface and main entry point.
"""

import argparse
import webbrowser
import threading
from typing import List, Dict, Any

from wp_hunter.config import Colors
from wp_hunter.models import ScanConfig, PluginResult
from wp_hunter.scanners.plugin_scanner import PluginScanner, close_session
from wp_hunter.scanners.theme_scanner import ThemeScanner
from wp_hunter.downloaders.plugin_downloader import PluginDownloader
from wp_hunter.reports.html_report import save_results
from wp_hunter.ui.console import (
    print_banner, 
    display_plugin_console, 
    display_theme_console,
    print_summary
)


def get_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='WP Hunter - WordPress Plugin & Theme Security Scanner'
    )
    
    # Basic scanning options
    parser.add_argument('--pages', type=int, default=5, 
                        help='Maximum number of pages to scan (Default: 5)')
    parser.add_argument('--limit', type=int, default=0, 
                        help='Maximum number of targets to list (0 = Unlimited)')
    parser.add_argument('--min', type=int, default=1000, 
                        help='Minimum active installations')
    parser.add_argument('--max', type=int, default=0, 
                        help='Maximum active installations (0 = Unlimited)')
    parser.add_argument('--sort', type=str, default='updated', 
                        choices=['new', 'updated', 'popular'])
    parser.add_argument('--smart', action='store_true', 
                        help='Show only risky categories')
    parser.add_argument('--abandoned', action='store_true', 
                        help='Show only plugins not updated for > 2 years')
    
    # Output options
    parser.add_argument('--output', type=str, 
                        help='Output file name (e.g., results.json)')
    parser.add_argument('--format', type=str, default='json', 
                        choices=['json', 'csv', 'html'], help='Output format')
    parser.add_argument('--download', type=int, default=0, metavar='N', 
                        help='Download top N plugins (sorted by VPS score) to ./Plugins/')
    
    # Time filtering
    parser.add_argument('--min-days', type=int, default=0, 
                        help='Minimum days since last update')
    parser.add_argument('--max-days', type=int, default=0, 
                        help='Maximum days since last update')
    
    # Enhanced features
    parser.add_argument('--deep-analysis', action='store_true', 
                        help='Download and analyze plugin code (slower but more accurate)')
    parser.add_argument('--themes', action='store_true', 
                        help='Scan WordPress themes instead of plugins')
    parser.add_argument('--ajax-scan', action='store_true', 
                        help='Focus on plugins with AJAX functionality')
    parser.add_argument('--dangerous-functions', action='store_true', 
                        help='Look for plugins using dangerous PHP functions')
    parser.add_argument('--user-facing', action='store_true', 
                        help='Focus on plugins that interact directly with end-users (high risk)')
    parser.add_argument('--auto-download-risky', type=int, default=0, metavar='N', 
                        help='Auto-download top N riskiest plugins for analysis')
    parser.add_argument('--aggressive', action='store_true',
                        help='AGGRESSIVE MODE: Scan everything, no limits, high concurrency.')
    
    # GUI mode
    parser.add_argument('--gui', action='store_true',
                        help='Launch web dashboard on localhost:8080')
    parser.add_argument('--port', type=int, default=8080,
                        help='Port for web dashboard (default: 8080)')
    
    return parser.parse_args()


def args_to_config(args: argparse.Namespace) -> ScanConfig:
    """Convert argparse namespace to ScanConfig."""
    return ScanConfig(
        pages=args.pages,
        limit=args.limit,
        min_installs=args.min,
        max_installs=args.max,
        sort=args.sort,
        smart=args.smart,
        abandoned=args.abandoned,
        user_facing=args.user_facing,
        themes=args.themes,
        min_days=args.min_days,
        max_days=args.max_days,
        deep_analysis=args.deep_analysis,
        ajax_scan=args.ajax_scan,
        dangerous_functions=args.dangerous_functions,
        output=args.output,
        format=args.format,
        download=args.download,
        auto_download_risky=args.auto_download_risky,
        aggressive=args.aggressive,
    )


def run_theme_scan(args: argparse.Namespace) -> None:
    """Run theme scanning mode."""
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}=== WordPress Theme Scanner ==={Colors.RESET}")
    print(f"Scanning {args.pages} pages of themes...\n")
    
    found_count = [0]
    
    def on_result(result: Dict[str, Any]):
        found_count[0] += 1
        display_theme_console(found_count[0], result)
    
    scanner = ThemeScanner(
        pages=args.pages,
        limit=args.limit,
        on_result=on_result
    )
    
    scanner.scan()
    
    print(f"{Colors.GREEN}[✓] Theme scan complete: {found_count[0]} themes analyzed{Colors.RESET}")


def run_plugin_scan(args: argparse.Namespace) -> None:
    """Run plugin scanning mode."""
    config = args_to_config(args)
    
    # Override defaults for Abandoned Mode to be effective
    if args.abandoned:
        if config.sort == 'updated':
            config.sort = 'popular'
            print(f"{Colors.YELLOW}[!] Mode switched to POPULAR to find abandoned plugins effectively.{Colors.RESET}")
        
        if args.pages == 5:  # If user didn't change default
            config.pages = 100
            print(f"{Colors.YELLOW}[!] Increased page scan limit to 100 to dig deeper for abandoned plugins.{Colors.RESET}")
    
    # Increase scan depth for date filtering
    # Increased page scan limit to 50 to find plugins older than {args.min_days} days.{Colors.RESET}")

    # Aggressive Mode Overrides
    if config.aggressive:
        print(f"{Colors.BOLD}{Colors.RED}[!!!] AGGRESSIVE MODE ENABLED [!!!]{Colors.RESET}")
        
        # Override limits if they are at defaults
        if args.pages == 5:
            config.pages = 200
            print(f"{Colors.RED}[!] Pages increased to 200{Colors.RESET}")
        
        # In Aggressive Mode, we focus on High Value Targets (High Score OR High Popularity)
        config.min_score = 40  # Only show HIGH risk items
        print(f"{Colors.RED}[!] Filtering for High Risk (Score > 40){Colors.RESET}")
            
        config.limit = 0
        print(f"{Colors.RED}[!] Result limit removed{Colors.RESET}")
        
        # We keep min_installs default (1000) or user value to avoid junk
        if args.min == 1000:
             print(f"{Colors.RED}[!] Min installs kept at 1000 to filter low-quality plugins{Colors.RESET}")
        
        if config.smart:
            config.smart = False
            print(f"{Colors.RED}[!] Smart filter DISABLED (scanning all categories){Colors.RESET}")
            
    print(f"\n{Colors.BOLD}{Colors.WHITE}=== WP Hunter ==={Colors.RESET}")
    range_str = f"{config.min_installs}-{config.max_installs}" if config.max_installs > 0 else f"{config.min_installs}+"
    print(f"Mode: {config.sort.upper()} | Range: {range_str} installs")
    
    limit_msg = f"{config.limit} items" if config.limit > 0 else "Unlimited"
    print(f"Target Limit: {Colors.YELLOW}{limit_msg}{Colors.RESET}")

    # Mode indicators
    if config.smart: 
        print(f"{Colors.RED}[!] Smart Filter: ON{Colors.RESET}")
    if config.abandoned: 
        print(f"{Colors.RED}[!] Abandoned Filter: ON (>730 days){Colors.RESET}")
    if config.deep_analysis: 
        print(f"{Colors.CYAN}[!] Deep Code Analysis: ON (slower but more accurate){Colors.RESET}")
    if config.ajax_scan: 
        print(f"{Colors.YELLOW}[!] AJAX Focus: ON{Colors.RESET}")
    if config.user_facing: 
        print(f"{Colors.MAGENTA}[!] User-Facing Plugin Filter: ON{Colors.RESET}")
    if config.dangerous_functions: 
        print(f"{Colors.RED}[!] Dangerous Functions Detection: ON{Colors.RESET}")
    
    if config.min_days > 0 or config.max_days > 0:
        d_min = config.min_days
        d_max = config.max_days if config.max_days > 0 else "∞"
        print(f"{Colors.RED}[!] Update Age Filter: {d_min} to {d_max} days{Colors.RESET}")

    print("=" * 70)

    # Set up scanner with callbacks
    found_count = [0]
    collected_results: List[PluginResult] = []
    
    def on_result(result: PluginResult):
        found_count[0] += 1
        display_plugin_console(found_count[0], result)
        collected_results.append(result)
    
    # Create scanner
    scanner = PluginScanner(config, on_result=on_result)
    
    # Set up downloader for deep analysis
    if config.deep_analysis:
        downloader = PluginDownloader()
        scanner.set_downloader(downloader)
    
    # Run scan
    scanner.scan()
    
    # Save results
    if config.output and collected_results:
        results_dicts = [r.to_dict() for r in collected_results]
        save_results(results_dicts, config.output, config.format)

    # Download top plugins if requested
    if config.download > 0 and collected_results:
        downloader = PluginDownloader()
        results_dicts = [r.to_dict() for r in collected_results]
        downloader.download_top_plugins(results_dicts, config.download)
    
    # Auto-download riskiest plugins
    if config.auto_download_risky > 0 and collected_results:
        print(f"\n{Colors.BOLD}{Colors.RED}=== Auto-Downloading Riskiest Plugins ==={Colors.RESET}")
        sorted_results = sorted(collected_results, key=lambda x: x.score, reverse=True)
        downloader = PluginDownloader()
        results_dicts = [r.to_dict() for r in sorted_results[:config.auto_download_risky]]
        downloader.download_top_plugins(results_dicts, config.auto_download_risky)

    print(f"\n{Colors.GREEN}[✓] Scan completed. Total {found_count[0]} targets analyzed.{Colors.RESET}")
    
    # Print summary
    if collected_results:
        summary = scanner.get_summary()
        print_summary(summary)


def run_gui(port: int = 8080) -> None:
    """Start the web dashboard."""
    try:
        from wp_hunter.server.app import create_app
        import uvicorn
    except ImportError:
        print(f"{Colors.RED}[!] GUI mode requires additional dependencies.{Colors.RESET}")
        print(f"{Colors.YELLOW}Please install: pip install fastapi uvicorn websockets{Colors.RESET}")
        return
    
    print(f"{Colors.BOLD}{Colors.CYAN}=== WP-Hunter Dashboard ==={Colors.RESET}")
    print(f"Starting web server on http://localhost:{port}")
    print(f"{Colors.GRAY}Press Ctrl+C to stop{Colors.RESET}\n")
    
    # Open browser after a short delay
    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open(f"http://localhost:{port}")
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run server
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


def main() -> None:
    """Main entry point."""
    print_banner()
    args = get_args()
    
    try:
        # GUI mode
        if args.gui:
            run_gui(args.port)
            return
        
        # Theme scanning mode
        if args.themes:
            run_theme_scan(args)
            return
        
        # Plugin scanning mode (default)
        run_plugin_scan(args)
        
    finally:
        close_session()


if __name__ == "__main__":
    main()
