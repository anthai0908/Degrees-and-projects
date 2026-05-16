osascript -e 'tell application "Terminal" to do script "cd /Users/anthai/Gmail_AI/models && ./llm_server.sh"'
uvicorn backend.main:app --reload --port 8000

