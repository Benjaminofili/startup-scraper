# scraper/utils/storage.py

import os
import json
import csv
from datetime import datetime
from typing import Dict, List, Optional


DATA_DIR = "data"


def ensure_data_dir():
    """Create data directory if it doesn't exist"""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Create subdirectories for organization
    os.makedirs(f"{DATA_DIR}/json", exist_ok=True)
    os.makedirs(f"{DATA_DIR}/ideas", exist_ok=True)
    os.makedirs(f"{DATA_DIR}/csv", exist_ok=True)


def get_timestamp() -> str:
    """Get formatted timestamp for filenames"""
    return datetime.now().strftime('%Y%m%d_%H%M')


def save_results(
    problems: List[Dict],
    ai_analysis: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> Dict[str, str]:
    """
    Save all results to multiple formats.
    Returns dict of saved file paths.
    """
    
    ensure_data_dir()
    timestamp = get_timestamp()
    saved_files = {}
    
    # Prepare full results object
    results = {
        "metadata": {
            "timestamp": timestamp,
            "generated_at": datetime.now().isoformat(),
            "total_problems": len(problems),
            **(metadata or {})
        },
        "ai_analysis": ai_analysis,
        "problems": problems
    }
    
    # 1. Save full JSON (timestamped)
    json_path = f"{DATA_DIR}/json/results_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    saved_files['json'] = json_path
    
    # 2. Save latest JSON (always overwritten)
    latest_path = f"{DATA_DIR}/latest.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    saved_files['latest'] = latest_path
    
    # 3. Save AI analysis as Markdown
    if ai_analysis:
        ideas_path = f"{DATA_DIR}/ideas/ideas_{timestamp}.md"
        with open(ideas_path, "w", encoding="utf-8") as f:
            f.write(f"# Startup Ideas Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"**Problems Analyzed:** {len(problems)}\n\n")
            f.write("---\n\n")
            f.write(ai_analysis)
        saved_files['ideas'] = ideas_path
        
        # Latest ideas
        with open(f"{DATA_DIR}/latest_ideas.md", "w", encoding="utf-8") as f:
            f.write(ai_analysis)
    
    # 4. Save CSV for spreadsheet analysis
    csv_path = f"{DATA_DIR}/csv/problems_{timestamp}.csv"
    save_problems_csv(problems, csv_path)
    saved_files['csv'] = csv_path
    
    # 5. Save summary text file
    summary_path = f"{DATA_DIR}/summary_{timestamp}.txt"
    save_summary(problems, ai_analysis, summary_path)
    saved_files['summary'] = summary_path
    
    return saved_files


def save_problems_csv(problems: List[Dict], filepath: str):
    """Save problems to CSV format"""
    
    if not problems:
        return
    
    # Define columns
    columns = ['source', 'subsource', 'title', 'content', 'score', 'url', 'date', 'cross_validated']
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        
        for problem in problems:
            # Clean content for CSV
            row = {
                'source': problem.get('source', ''),
                'subsource': problem.get('subsource', ''),
                'title': problem.get('title', '')[:200].replace('\n', ' '),
                'content': problem.get('content', '')[:500].replace('\n', ' '),
                'score': problem.get('score', 0),
                'url': problem.get('url', ''),
                'date': problem.get('date', ''),
                'cross_validated': problem.get('cross_validated', False)
            }
            writer.writerow(row)


def save_summary(problems: List[Dict], ai_analysis: Optional[str], filepath: str):
    """Save a human-readable summary"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("STARTUP PROBLEM SCRAPER - SUMMARY REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 60 + "\n\n")
        
        # Stats by source
        f.write("PROBLEMS BY SOURCE:\n")
        f.write("-" * 40 + "\n")
        
        source_counts = {}
        for p in problems:
            src = p.get('source', 'Unknown')
            source_counts[src] = source_counts.get(src, 0) + 1
        
        for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
            f.write(f"  {src}: {count}\n")
        
        f.write(f"\n  TOTAL: {len(problems)}\n")
        
        # Top problems by score
        f.write("\n\nTOP 20 PROBLEMS (by engagement):\n")
        f.write("-" * 40 + "\n")
        
        sorted_problems = sorted(problems, key=lambda x: x.get('score', 0), reverse=True)
        for i, p in enumerate(sorted_problems[:20], 1):
            f.write(f"\n{i}. [{p.get('source')}] (score: {p.get('score', 0)})\n")
            f.write(f"   {p.get('title', '')[:100]}\n")
        
        # AI Analysis
        if ai_analysis:
            f.write("\n\n" + "=" * 60 + "\n")
            f.write("AI-GENERATED OPPORTUNITIES:\n")
            f.write("=" * 60 + "\n\n")
            f.write(ai_analysis)


def load_latest_results() -> Optional[Dict]:
    """Load the most recent results"""
    
    latest_path = f"{DATA_DIR}/latest.json"
    
    if os.path.exists(latest_path):
        with open(latest_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return None


def load_historical_results(days: int = 7) -> List[Dict]:
    """Load results from the past N days"""
    
    json_dir = f"{DATA_DIR}/json"
    
    if not os.path.exists(json_dir):
        return []
    
    results = []
    
    for filename in os.listdir(json_dir):
        if filename.startswith('results_') and filename.endswith('.json'):
            filepath = os.path.join(json_dir, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results.append(data)
            except Exception:
                continue
    
    # Sort by timestamp (newest first)
    results.sort(key=lambda x: x.get('metadata', {}).get('timestamp', ''), reverse=True)
    
    return results[:days * 3]  # Assuming ~3 runs per day


def cleanup_old_files(keep_days: int = 30):
    """Remove files older than N days to save space"""
    
    import time
    
    cutoff_time = time.time() - (keep_days * 24 * 60 * 60)
    
    for subdir in ['json', 'ideas', 'csv']:
        dir_path = f"{DATA_DIR}/{subdir}"
        
        if not os.path.exists(dir_path):
            continue
        
        for filename in os.listdir(dir_path):
            filepath = os.path.join(dir_path, filename)
            
            if os.path.getmtime(filepath) < cutoff_time:
                try:
                    os.remove(filepath)
                    print(f"   🗑️ Removed old file: {filename}")
                except Exception:
                    pass