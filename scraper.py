import os
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

# 1. 核心与相关技术/领域关键词
KEYWORDS = [
    # 核心技术
    "single-cell", "single cell", "sequencing", "ngs", "pcr", "dpcr", 
    "digital pcr", "library prep", "genomics", "transcriptomics", 
    "spatial transcriptomics", "omics", "microfluidics", "flow cytometry",
    
    # 领域/学科兜底关键词（防止因具体技术写在附件里而漏抓）
    "molecular biology", "cell biology", "biochemistry", "cancer research", 
    "immunology", "biomedical", "biotechnology", "genetics", "life sciences"
]

EURAXESS_API_URL = "https://euraxess.ec.europa.eu/api/jobs/search"
ACADEMIC_TRANSFER_RSS = "https://www.academictransfer.com/en/rss/"

def get_page_text(url):
    """进入岗位详情页抓取全文本，防止 API 缺失描述信息"""
    if not url:
        return ""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            return soup.get_text().lower()
    except Exception:
        pass
    return ""

def fetch_euraxess_jobs():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    payload = {
        "researcherProfiles": ["R1"],  # PhD 级别
        "sortBy": "newest",
        "pageSize": 40                 # 抓取最新 40 个，平衡运行速度
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
                    "deadline": item.get("deadline", "详见官网"),
                    "url": item.get("url", ""),
                    "source": "EURAXESS"
                })
    except Exception as e:
        print(f"EURAXESS 请求失败: {e}")
    return jobs

def fetch_academic_transfer_jobs():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    jobs = []
    try:
        res = requests.get(ACADEMIC_TRANSFER_RSS, headers=headers, timeout=15)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                description = item.findtext("description", "")
                link = item.findtext("link", "")
                
                # 筛选 PhD 相关岗位
                if any(phd_kw in title.lower() or phd_kw in description.lower() for phd_kw in ["phd", "doctoral", "candidate"]):
                    jobs.append({
                        "title": title,
                        "description": description,
                        "country": "Netherlands",
                        "organisation": "Dutch Research Inst.",
                        "deadline": "详见链接",
                        "url": link,
                        "source": "AcademicTransfer"
                    })
    except Exception as e:
        print(f"AcademicTransfer 请求失败: {e}")
    return jobs

def filter_jobs(job_list):
    matched = []
    seen_urls = set()
    
    print(f"开始深度分析 {len(job_list)} 个候选岗位...")
    
    for job in job_list:
        url = job.get("url", "")
        if not url or url in seen_urls:
            continue
            
        # 先检查已有的标题和简述
        base_text = f"{job['title']} {job['description']}".lower()
        matched_kws = [kw for kw in KEYWORDS if kw in base_text]
        
        # 如果初步匹配没命中，自动爬取详情页全文本再次搜寻
        if not matched_kws:
            detail_text = get_page_text(url)
            matched_kws = [kw for kw in KEYWORDS if kw in detail_text]
        
        if matched_kws:
            job["hit_keywords"] = matched_kws[:3]
            matched.append(job)
            seen_urls.add(url)
            
    return matched

def send_wechat(jobs):
    sendkey = os.environ.get("SERVERCHAN_KEY")
    if not sendkey:
        print("未设置 SERVERCHAN_KEY，跳过微信推送。")
        return

    if not jobs:
        title = "【巡检提醒】未发现匹配岗位"
        content = "已完成深层全网检索，暂未发现最新发布的匹配项目。"
    else:
        title = f"【PhD岗位巡检】成功为你筛选出 {len(jobs)} 个匹配岗位！"
        content_lines = []
        for i, j in enumerate(jobs[:15], 1): # 每次最多推送前 15 条最相关的
            kws = ", ".join(j.get("hit_keywords", []))
            content_lines.append(f"### {i}. [{j['source']}] {j['title']}\n")
            content_lines.append(f"- **国家**: {j['country']}")
            content_lines.append(f"- **机构**: {j['organisation']}")
            content_lines.append(f"- **匹配词**: `{kws}`")
            content_lines.append(f"- [点击查看详情/申请]({j['url']})\n\n---\n")
        content = "\n".join(content_lines)

    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    requests.post(url, data={"title": title, "desp": content})

if __name__ == "__main__":
    all_jobs = []
    all_jobs.extend(fetch_euraxess_jobs())
    all_jobs.extend(fetch_academic_transfer_jobs())
    
    final_jobs = filter_jobs(all_jobs)
    send_wechat(final_jobs)
