import os
import re
import time
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
from datetime import datetime

# ==========================================
# 1. CONFIGURATION
# ==========================================
GITHUB_USERNAME = "MuhammadAhmed-1855"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or input("Enter your GitHub Personal Access Token: ")

START_YEAR = 2023 
CURRENT_YEAR = datetime.now().year

GENERATED_DIR = Path("personal")
CORPORATE_HISTORY_DIR = Path("corporate")

# ==========================================
# 2. GITHUB GRAPHQL API (MULTI-YEAR DATA)
# ==========================================
def fetch_year_contributions(year: int) -> dict:
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    
    start_date = f"{year}-01-01T00:00:00Z"
    end_date = f"{year}-12-31T23:59:59Z"
    
    query = """
    query {
        user(login: "%s") {
            contributionsCollection(from: "%s", to: "%s") {
                contributionCalendar {
                    totalContributions
                    weeks {
                        contributionDays {
                            contributionCount
                            date
                        }
                    }
                }
            }
        }
    }
    """ % (GITHUB_USERNAME, start_date, end_date)
    
    response = requests.post(url, json={'query': query}, headers=headers)
    if response.status_code != 200:
        raise Exception(f"API Error {response.status_code}: {response.text}")
        
    return response.json()['data']['user']['contributionsCollection']['contributionCalendar']

# ==========================================
# 3. HEATMAP RENDERER
# ==========================================
def render_personal_heatmap(calendar_data: dict, year: int):
    GENERATED_DIR.mkdir(exist_ok=True)
    output_path = GENERATED_DIR / f"personal_heatmap_{year}.png"
    
    weeks = calendar_data['weeks']
    total_contribs = calendar_data['totalContributions']
    
    bg_color = "#0d1117"
    empty_color = "#161b22"
    colors = ["#0e4429", "#006d32", "#26a641", "#39d353"] 
    
    fig, ax = plt.subplots(figsize=(10, 1.8))
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    
    for w, week in enumerate(weeks):
        for d, day in enumerate(week['contributionDays']):
            count = day['contributionCount']
            color = empty_color if count == 0 else (colors[count - 1] if count < 5 else colors[3])
            rect = patches.Rectangle((w, 6 - d), 0.8, 0.8, linewidth=1, edgecolor=bg_color, facecolor=color)
            ax.add_patch(rect)
            
    ax.set_xlim(-0.5, len(weeks))
    ax.set_ylim(-0.5, 7.5)
    ax.invert_yaxis()
    ax.axis('off')
    
    plt.title(f"📊 {total_contribs} contributions in {year}", 
              color="white", fontsize=12, pad=10, loc='left', fontweight='bold')
              
    plt.tight_layout()
    plt.savefig(output_path, facecolor=bg_color, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ {year} heatmap saved to {output_path}")

# ==========================================
# 4. HELPER FUNCTIONS
# ==========================================
def extract_year_from_filename(filename: str) -> str:
    match = re.search(r'(20\d{2})', filename)
    return match.group(1) if match else ""

def get_image_caption(img_path: Path, is_personal: bool = False) -> str:
    year = extract_year_from_filename(img_path.stem)
    if is_personal:
        return f"Personal Contributions ({year})" if year else "Personal Contributions"
    
    name_parts = img_path.stem.replace(year, '').strip('_').split('_')
    project_type = ' '.join(name_parts[:-1]).title() if name_parts[:-1] else 'Contribution'
    return f"{project_type} ({year})" if year else project_type

# ==========================================
# 5. MARKDOWN ASSEMBLER
# ==========================================
# ==========================================
# 5. MARKDOWN ASSEMBLER (FIXED WINDOWS PATHS)
# ==========================================
def generate_readme() -> str:
    
    # --- CORPORATE SECTION ---
    company_dirs = [d for d in CORPORATE_HISTORY_DIR.iterdir() if d.is_dir() and not d.name.startswith('.')]
    company_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    corporate_section = ""
    for company_dir in company_dirs:
        company_name = company_dir.name.replace("_", " ").title()
        
        # FIX: Use .as_posix() to force forward slashes instead of Windows backslashes
        deep_dive_link = f"{company_dir.as_posix()}/README.md" if (company_dir / "README.md").exists() else "#"
        root_images = sorted(list(company_dir.glob("*.png")))
        
        corporate_section += f"### 🏢 {company_name}\n\n"
        
        if len(root_images) == 0:
            corporate_section += f'<p align="left"><a href="{deep_dive_link}"><img src="https://img.shields.io/badge/_View_{company_name}_Deep_Dive-0d1117?style=for-the-badge&logo=github&logoColor=white" /></a></p>\n\n'
        else:
            years_list = [extract_year_from_filename(img.stem) for img in root_images]
            years_range = f"{min(years_list)}-{max(years_list)}" if years_list else ""
            
            corporate_section += f'<details>\n'
            corporate_section += f'  <summary><strong>📊 View {len(root_images)} Contribution Heatmaps {f"({years_range})" if years_range else ""}</strong></summary>\n'
            corporate_section += f'  <br>\n\n'
            
            for img in root_images:
                caption = get_image_caption(img, is_personal=False)
                # FIX: Ensure image src also uses .as_posix()
                corporate_section += f'  **{caption}**\n\n'
                corporate_section += f'  <img src="{img.as_posix()}" alt="{caption}" width="100%" />\n\n'
                
            corporate_section += f'</details>\n\n'

        corporate_section += f"👉 **[View Technical Deep-Dive, Architecture & Full Commit History]({deep_dive_link})**\n\n"
        corporate_section += "---\n\n"

    if not corporate_section:
        corporate_section = "*Corporate deep-dives are being compiled.*\n\n---\n\n"

    # --- PERSONAL SECTION ---
    personal_heatmaps = sorted(list(GENERATED_DIR.glob("personal_heatmap_*.png")), reverse=True)
    
    personal_section = ""
    if len(personal_heatmaps) > 0:
        years_list = [extract_year_from_filename(img.stem) for img in personal_heatmaps]
        years_range = f"{min(years_list)}-{max(years_list)}" if years_list else ""
        
        personal_section += f'<details>\n'
        personal_section += f'  <summary><strong>📊 View {len(personal_heatmaps)} Personal Contribution Heatmaps {f"({years_range})" if years_range else ""}</strong></summary>\n'
        personal_section += f'  <br>\n\n'
        
        for img in personal_heatmaps:
            caption = get_image_caption(img, is_personal=True)
            personal_section += f'  **{caption}**\n\n'
            personal_section += f'  <img src="{img.as_posix()}" alt="{caption}" width="100%" />\n\n'
            
        personal_section += f'</details>\n\n'
    else:
        personal_section = "*Personal contribution heatmaps are being generated.*\n\n"

    # --- TECH ARSENAL BADGES ---
    tech_arsenal = """
<p align="left">
  <img src="https://img.shields.io/badge/Angular-DD0031?style=for-the-badge&logo=angular&logoColor=white" alt="Angular" />
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" />
  <img src="https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" alt="Tailwind" />
  <img src="https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/D3.js-F9A03C?style=for-the-badge&logo=d3.js&logoColor=white" alt="D3.js" />
</p>

<p align="left">
  <img src="https://img.shields.io/badge/Node.js-43853D?style=for-the-badge&logo=node.js&logoColor=white" alt="Node.js" />
  <img src="https://img.shields.io/badge/Express.js-404D59?style=for-the-badge&logo=express&logoColor=white" alt="Express" />
  <img src="https://img.shields.io/badge/NestJS-E0234E?style=for-the-badge&logo=nestjs&logoColor=white" alt="NestJS" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
</p>

<p align="left">
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/MySQL-005C84?style=for-the-badge&logo=mysql&logoColor=white" alt="MySQL" />
  <img src="https://img.shields.io/badge/MongoDB-4EA94B?style=for-the-badge&logo=mongodb&logoColor=white" alt="MongoDB" />
  <img src="https://img.shields.io/badge/Sequelize-52B0E7?style=for-the-badge&logo=sequelize&logoColor=white" alt="Sequelize" />
</p>

<p align="left">
  <img src="https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white" alt="AWS" />
  <img src="https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black" alt="Linux" />
  <img src="https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white" alt="Git" />
  <img src="https://img.shields.io/badge/Jira-0052CC?style=for-the-badge&logo=jira&logoColor=white" alt="Jira" />
</p>
"""

    # --- ASSEMBLE FINAL CV ---
    md = f"""# Muhammad Ahmed
### Full-Stack Engineer | Multi-Tenant Architecture Specialist

<p align="left">
  <a href="https://linkedin.com/in/muhammad-ahmed-403212237" target="_blank">
    <img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn" />
  </a>
  <a href="https://github.com/MuhammadAhmed-1855" target="_blank">
    <img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white" alt="GitHub" />
  </a>
  <a href="mailto:falconahmed7023@gmail.com" target="_blank">
    <img src="https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white" alt="Email" />
  </a>
  <img src="https://img.shields.io/badge/Location-Pakistan-2ea043?style=for-the-badge&logo=googlemaps&logoColor=white" alt="Location" />
</p>

---

## 🎯 Professional Summary
Full-Stack Engineer with 2.5+ years of experience engineering high-performance, multi-tenant enterprise applications across healthcare and tax-benefit domains. Expertise in **Angular, React.js, Node.js/Express, and PostgreSQL**. Proven track record of accelerating API performance by 60%, architecting multi-tenant data isolation systems, and driving technical execution alongside CTOs while reviewing code for junior developers.

## 🛠️ Technical Arsenal
{tech_arsenal}

---

##  Corporate Experience & Impact
*Sorted by most recently updated. Click to expand contribution heatmaps.*

{corporate_section}

## 🟢 Personal Contributions & Open Source
{personal_section}

---

## 📄 Full Work History (Text Summary)
**Tangent Tech** | *Full Stack Developer* | `Jan 2026 – Present`
- Developing end-to-end multi-tenant data isolation across Express.js REST APIs and Angular components.
- Mentored 2 junior engineers, enforcing linting rules, and managing 120+ technical tickets in Odoo.

**Beyond Solutions** | *Full Stack Engineer* | `Nov 2024 – Dec 2025`
- Delivered a high-throughput multi-tenant AMR surveillance system adopted across 4 government sectors.
- Engineered database connection pooling, reducing API latency by 60% and handling 25,000+ row reports.

**NESL-IT** | *Technical Project Coordinator* | `Jun 2024 – Nov 2024`
- Orchestrated Agile/Scrum workflows and developed Selenium test automation scripts.

**AB-Matrix** | *Software Engineer (Contract)* | `Sep 2023 – May 2024`
- Migrated legacy cloud infrastructure to AWS, cutting system downtime by 25%.

**Eden Spell** | *Software Engineer Intern* | `Jun 2023 – Aug 2023`
- Developed custom full-stack web applications using PHP, JavaScript, and MySQL.

---

## 🎓 Education & Certifications
- **BS in Software Engineering** | FAST – National University of Computer and Emerging Sciences (2024)
- **Certifications:** Google Project Management Specialization (Coursera) | IBM Web Development Fundamentals

---
*🤖 Portfolio compiled on **{datetime.now().strftime('%Y-%m-%d')}**. Personal stats fetched live via GitHub GraphQL API.*
"""
    return md
  
# ==========================================
# 6. MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    print("🚀 Starting Portfolio Build Pipeline...")
    
    for year in range(START_YEAR, CURRENT_YEAR + 1):
        print(f"📡 Fetching personal data for {year}...")
        try:
            calendar_data = fetch_year_contributions(year)
            render_personal_heatmap(calendar_data, year)
            time.sleep(1) 
        except Exception as e:
            print(f"⚠️ Warning: Could not fetch data for {year}. Error: {e}")
    
    print("📝 Assembling README.md...")
    readme_content = generate_readme()
    Path("README.md").write_text(readme_content, encoding="utf-8")
    
    print("🎉 Build complete! Open README.md to view your portfolio.")