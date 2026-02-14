import feedparser
import re

def fetch_papers():
    # cs.AI = AI, cs.LG = Machine Learning
    url = "http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG&sortBy=submittedDate&sortOrder=descending&max_results=5"
    feed = feedparser.parse(url)
    
    entries = []
    for entry in feed.entries:
        title = re.sub('\s+', ' ', entry.title).strip()
        link = entry.link
        entries.append(f"* 📄 [{title}]({link})")
    
    return "\n".join(entries)

def update_readme(content):
    with open("README.md", "r", encoding="utf-8") as f:
        readme = f.read()

    # Update Date
    from datetime import datetime
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    readme = re.sub(r".*", f"**{current_date}**", readme)

    # Update Content
    pattern = r".*?"
    replacement = f"\n{content}\n"
    new_readme = re.sub(pattern, replacement, readme, flags=re.DOTALL)

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new_readme)

if __name__ == "__main__":
    papers = fetch_papers()
    update_readme(papers)