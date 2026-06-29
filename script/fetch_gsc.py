"""
fetch_gsc.py — อ่าน GSC CSV export แล้วสร้าง dashboard.json
วิธีใช้: วาง CSV ไว้ใน data/exports/ แล้วรัน python scripts/fetch_gsc.py
"""
import csv, json, os, glob, datetime

EXPORTS_DIR = "data/exports"
OUTPUT_FILE = "data/dashboard.json"

def read_pages(filepath):
    rows = []
    with open(filepath, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                rows.append({
                    "url":         row["Top pages"],
                    "clicks":      int(row["Clicks"]),
                    "impressions": int(row["Impressions"]),
                    "ctr":         float(row["CTR"].replace("%", "")),
                    "position":    float(row["Position"])
                })
            except:
                pass
    return rows

def read_queries(filepath):
    rows = []
    with open(filepath, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                rows.append({
                    "keyword":     row["Top queries"],
                    "clicks":      int(row["Clicks"]),
                    "impressions": int(row["Impressions"]),
                    "ctr":         float(row["CTR"].replace("%", "")),
                    "position":    float(row["Position"])
                })
            except:
                pass
    return rows

def analyze(pages, queries):
    if not pages:
        return {}

    # Best performers
    best = sorted(pages, key=lambda x: x["clicks"], reverse=True)[:10]

    # Quick wins: อยู่อันดับ 6-15 และมี impressions สูง
    quick_wins = [
        p for p in pages
        if 6 <= p["position"] <= 15 and p["impressions"] > 2000
    ]
    quick_wins = sorted(quick_wins, key=lambda x: x["impressions"], reverse=True)[:10]

    # AI Priority: clicks ดีแต่ position ตกเกิน 10
    click_threshold = sorted(
        [p["clicks"] for p in pages], reverse=True
    )[max(1, int(len(pages) * 0.3))]
    priority = [
        p for p in pages
        if p["position"] > 10 and p["clicks"] >= click_threshold
    ]
    priority = sorted(priority, key=lambda x: x["impressions"], reverse=True)[:8]

    # Low CTR — ปรับ title/meta ได้เลย
    low_ctr = [
        p for p in pages
        if p["ctr"] < 1.5 and p["impressions"] > 3000
    ]
    low_ctr = sorted(low_ctr, key=lambda x: x["impressions"], reverse=True)[:8]

    # Keyword quick wins
    kw_wins = [
        q for q in queries
        if 4 <= q["position"] <= 10 and q["impressions"] > 500
    ]
    kw_wins = sorted(kw_wins, key=lambda x: x["impressions"], reverse=True)[:10]

    return {
        "best_performers": best,
        "quick_wins":      quick_wins,
        "ai_priority":     priority,
        "low_ctr":         low_ctr,
        "keyword_wins":    kw_wins,
    }

def main():
    # หา CSV ทุกไฟล์ใน exports/
    # รองรับทั้ง flat folder และ subfolder แยกตามเว็บ
    sites_data = {}

    # ถ้ามี subfolder (multi-site)
    subfolders = [
        d for d in glob.glob(f"{EXPORTS_DIR}/*/")
        if os.path.isdir(d)
    ]

    if subfolders:
        for folder in subfolders:
            site_name = os.path.basename(folder.rstrip("/"))
            pages_file   = glob.glob(f"{folder}Pages*.csv")
            queries_file = glob.glob(f"{folder}Queries*.csv")
            if pages_file and queries_file:
                pages   = read_pages(pages_file[0])
                queries = read_queries(queries_file[0])
                sites_data[site_name] = {
                    "pages": pages, "queries": queries
                }
    else:
        # single site — flat folder
        pages_file   = glob.glob(f"{EXPORTS_DIR}/Pages*.csv")
        queries_file = glob.glob(f"{EXPORTS_DIR}/Queries*.csv")
        if pages_file and queries_file:
            pages   = read_pages(pages_file[0])
            queries = read_queries(queries_file[0])
            # ดึง domain จากชื่อไฟล์หรือใช้ default
            site_name = "tradewithauntie.com"
            sites_data[site_name] = {
                "pages": pages, "queries": queries
            }

    if not sites_data:
        print("ERROR: ไม่พบไฟล์ Pages.csv หรือ Queries.csv ใน", EXPORTS_DIR)
        return

    # Build output
    output = {
        "generated_at": str(datetime.datetime.now()),
        "sites": {}
    }

    for site_name, data in sites_data.items():
        pages   = data["pages"]
        queries = data["queries"]
        analysis = analyze(pages, queries)

        total_clicks = sum(p["clicks"] for p in pages)
        total_imp    = sum(p["impressions"] for p in pages)
        avg_pos      = sum(p["position"] for p in pages) / len(pages) if pages else 0

        output["sites"][site_name] = {
            "summary": {
                "total_pages":       len(pages),
                "total_keywords":    len(queries),
                "total_clicks":      total_clicks,
                "total_impressions": total_imp,
                "avg_position":      round(avg_pos, 1)
            },
            **analysis
        }

        print(f"[{site_name}] {len(pages)} pages | {total_clicks:,} clicks | avg pos {avg_pos:.1f}")
        print(f"  best: {len(analysis['best_performers'])} | quick wins: {len(analysis['quick_wins'])} | priority: {len(analysis['ai_priority'])}")

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\ndashboard.json saved → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
