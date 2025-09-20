This is a project to scrape text from the web and analyse it using an LLM. 
Implementation proceeds in iterations. We'll use Git branches for new features.

Initial idea for tech stack:
- Python for logic
- scrapy for web scraping
- CrewAI for AI agent coordination, when needed
- Git for version control
- Hosted LLMs connected through OpenRouter
- Chroma for local vector db


First use case:
User enters web address.
Program proceeds to scrape text data from the page. If there are several elements of text > 300 characters (configurable), the program shows the 50 words of each in turn and asks user if it should be included.
The ones that the user selects will be chunked and indexed in Chroma for RAG.
The user is then prompted to ask questions about the content.