import feedparser
import re
from datetime import datetime

def fetch_papers():
    # arXiv API for AI and ML
    url = "http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG&sortBy=submittedDate&sortOrder=descending&max_results=8"
    feed = feedparser.parse(url)
    
    if not feed.entries:
        return "⚠️ No new patterns detected today."
        
    # Saare titles ko ek line mein join karna (Divider ' | ' ke saath)
    entries = []
    for entry in feed.entries:
        title = entry.title.replace('\n', ' ').strip()
        link = entry.link
        # News ticker format: [Title] | [Title] ...
        entries.append(f"📄 <a href='{link}'>{title}</a>")
    
    # Scrolling Ticker Block
    ticker_text = " &nbsp;&nbsp;&nbsp; | &nbsp;&nbsp;&nbsp; ".join(entries)
    return f'<marquee behavior="scroll" direction="left" scrollamount="5"><b>{ticker_text}</b></marquee>'

def update_readme(content):
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            readme = f.read()

        # Update Section using markers
        # Make sure your README has and start_marker = ""
        end_marker = ""
        
        pattern = f"{start_marker}.*?{end_marker}"
        replacement = f"{start_marker}\n{content}\n{end_marker}"
        
        new_readme = re.sub(pattern, replacement, readme, flags=re.DOTALL)

        with open("README.md", "w", encoding="utf-8") as f:
            f.write(new_readme)
        print("README updated with scrolling ticker!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    papers = fetch_papers()
    update_readme(papers)