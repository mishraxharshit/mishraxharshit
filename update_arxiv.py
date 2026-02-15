import feedparser
import re
from datetime import datetime

def fetch_papers():
    # cs.AI (Artificial Intelligence) or cs.LG (Machine Learning)
    url = "http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG&sortBy=submittedDate&sortOrder=descending&max_results=5"
    feed = feedparser.parse(url)
    
    if not feed.entries:
        return "* ⚠️ No new papers found today."
        
    entries = []
    for entry in feed.entries:
        # Title clean up
        title = entry.title.replace('\n', ' ').replace('  ', ' ').strip()
        link = entry.link
        entries.append(f"* 📄 **[{title}]({link})**")
    
    return "\n".join(entries)

def update_readme(content):
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            readme = f.read()

        # Update Date
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
        readme = re.sub(r".*", f"**{current_date}**", readme)

        # Update Section
        pattern = r"().*?()"
        replacement = f"\\1\n{content}\n\\2"
        new_readme = re.sub(pattern, replacement, readme, flags=re.DOTALL)

        with open("README.md", "w", encoding="utf-8") as f:
            f.write(new_readme)
        print("README updated successfully!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    papers = fetch_papers()
    update_readme(papers)