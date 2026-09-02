import os
import requests
import xml.etree.ElementTree as ET

CORE_KWS = ["single-cell", "single cell", "sequencing", "ngs", "pcr", "dpcr", "library prep"]
BROAD_KWS = ["biology", "biomedical", "genomics", "omics", "cancer", "immunology", "genetics", "life science"]

EURAXESS_API_URL = "https://euraxess.ec.europa.eu/api/jobs/search"
ACADEMIC_TRANSFER_RSS = "https://www.academictransfer.com/en/rss/"

def fetch_euraxess_jobs():
    headers = {"User-Agent": "Mozilla/5.0"}
    payload = {
        "researcherProfiles": ["R1"],
        "sortBy": "newest",
        "pageSize": 50
    }
    jobs = []
    try:
        res = requests.post(EURAXESS_API_URL, json=payload, headers=headers, timeout=15)
        if res.status_code == 200:
            for item in res.json().get("results", []):
                jobs.append({
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "country": item.get("country", "欧洲多国"),
                    "organisation": item.get("organisation", "未标识机构"),
                    "url": item.get("url", ""),
                    "source": "EURAXESS"
                })
    except Exception as e:
        print(f"EURAXESS 异常: {e}")
    return jobs

def fetch_academic_transfer_jobs():
    headers = {"User-Agent": "Mozilla/5.0"}
    jobs = []
    try:
        res = requests.get(ACADEMIC_TRANSFER_RSS, headers=headers, timeout=15)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                description = item.findtext("description", "")
                link = item.findtext("link", "")
                if any(k in title.lower() or k in description.lower() for k in ["phd", "doctoral", "candidate"]):
                    jobs.append({
                        "title": title,
                        "description": description,
                        "country": "Netherlands",
                        "organisation": "Dutch Inst.",
                        "url": link,
                        "source": "AcademicTransfer"
                    })
    except Exception as e:
        print(f"AcademicTransfer 异常: {e}")
    return jobs

def process_and_filter(jobs):
    core_matched = []
    broad_matched = []
    seen = set()

    for j in jobs:
        url = j.get("url")
        if not url or url in seen:
            continue
        
        text = f"{j['title']} {j['description']}".lower()
        
        hit_core = [kw for kw in CORE_KWS if kw in text]
        if hit_core:
            j["hit"] = ", ".join(hit_core)
            core_matched.append(j)
            seen.add(url)
            continue
            
        hit_broad = [kw for kw in BROAD_KWS if kw in text]
        if hit_broad:
            j["hit"] = ", ".join(hit_broad[:2])
            broad_matched.append(j)
            seen.add(url)

    return core_matched, broad_matched

def send_wechat(core_jobs, broad_jobs):
    sendkey = os.environ.get("SERVERCHAN_KEY")
    if not sendkey:
        print("无 SERVERCHAN_KEY，终止推送")
        return

    total = len(core_jobs) + len(broad_jobs)
    if total == 0:
        title = "【巡检提醒】暂无最新生物类 PhD 岗位"
        content = "今日全网巡检未发现新增生物学领域岗位，系统保持定期运行中。"
    else:
        title = f"【PhD巡检】精准岗位 {len(core_jobs)} 个 | 泛生物类 {len(broad_jobs)} 个"
        lines = []
        if core_jobs:
            lines.append("## 🎯 核心技术精准匹配岗位\n")
            for i, j in enumerate(core_jobs, 1):
                lines.append(f"**{i}. [{j['source']}] {j['title']}**\n- 匹配: `{j['hit']}`\n- 地区: {j['country']} | [查看详情]({j['url']})\n")
        if broad_jobs:
            lines.append("\n## 🔬 生命科学大类相关岗位推荐\n")
            for i, j in enumerate(broad_jobs[:10], 1):
                lines.append(f"**{i}. [{j['source']}] {j['title']}**\n- 标签: `{j['hit']}`\n- 地区: {j['country']} | [查看详情]({j['url']})\n")
        content = "\n".join(lines)

    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    requests.post(url, data={"title": title, "desp": content})

if __name__ == "__main__":
    raw_jobs = fetch_euraxess_jobs() + fetch_academic_transfer_jobs()
    core_jobs, broad_jobs = process_and_filter(raw_jobs)
    send_wechat(core_jobs, broad_jobs)
