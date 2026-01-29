# scraper/utils/storage.py

import os
import json
from datetime import datetime
from typing import Dict, List, Optional


DATA_DIR = "data"


def ensure_data_dir():
    """Create data directories"""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(f"{DATA_DIR}/json", exist_ok=True)
    os.makedirs(f"{DATA_DIR}/ideas", exist_ok=True)


def get_timestamp() -> str:
    """Get timestamp for filenames"""
    return datetime.now().strftime('%Y%m%d_%H%M')


def save_results(
    problems: List[Dict],
    ai_analysis: Optional[str] = None,
    feasibility_report: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> Dict[str, str]:
    """Save results to files"""
    
    ensure_data_dir()
    timestamp = get_timestamp()
    saved_files = {}
    
    results = {
        "metadata": {
            "timestamp": timestamp,
            "total_problems": len(problems),
            **(metadata or {})
        },
        "ai_analysis": ai_analysis,
        "problems": problems
    }
    
    # JSON file
    json_path = f"{DATA_DIR}/json/results_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    saved_files['json'] = json_path
    
    # Latest JSON
    with open(f"{DATA_DIR}/latest.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Ideas markdown
    if ai_analysis:
        ideas_path = f"{DATA_DIR}/ideas/ideas_{timestamp}.md"
        with open(ideas_path, "w", encoding="utf-8") as f:
            f.write(f"# Startup Ideas - {timestamp}\n\n")
            f.write(f"**Problems Analyzed:** {len(problems)}\n\n---\n\n")
            f.write(ai_analysis)
        saved_files['ideas'] = ideas_path
        
        with open(f"{DATA_DIR}/latest_ideas.md", "w", encoding="utf-8") as f:
            f.write(ai_analysis)
    
    # Feasibility report
    if feasibility_report:
        feasibility_path = f"{DATA_DIR}/ideas/feasible_{timestamp}.md"
        with open(feasibility_path, "w", encoding="utf-8") as f:
            f.write(f"# Feasible Startup Ideas - {timestamp}\n\n")
            f.write(feasibility_report)
        saved_files['feasibility'] = feasibility_path
        
        with open(f"{DATA_DIR}/feasible_ideas.md", "w", encoding="utf-8") as f:
            f.write(f"# Feasible Startup Ideas - {timestamp}\n\n")
            f.write(feasibility_report)
    
    return saved_files


def load_latest_results() -> Optional[Dict]:
    """Load the latest results from the data directory"""
    latest_path = f"{DATA_DIR}/latest.json"
    
    if not os.path.exists(latest_path):
        return None
    
    try:
        with open(latest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading latest results: {e}")
        return None