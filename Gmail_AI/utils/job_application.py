from dotenv import load_dotenv
import os
import httpx
import asyncio
import base64
from typing import Optional
from database.db import dbservice

load_dotenv("../.env")
user = os.getenv("GITHUB_USER")
repo = os.getenv("GITHUB_REPO")
token = os.getenv("GITHUB_ACCESS_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {token}"
}


async def compare_commit(last_processed_commit: Optional[str] = None) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{user}/{repo}/git/trees/main?recursive=1",
            headers=HEADERS
        )
        response.raise_for_status()
        latest_commit = response.json()["sha"]

        if latest_commit == last_processed_commit:
            return "No changes"
        elif last_processed_commit is None:
            try:
                await dbservice.add_commit(repo_name=repo, commit=latest_commit)
                tasks = []
                for item in response.json()["tree"]:
                    if item["type"] != "blob":
                        continue
                    path = item["path"]
                    task = asyncio.create_task(
                        get_file_content(client, user, repo, path, latest_commit)
                    )
                    tasks.append(task)
                result = await asyncio.gather(*tasks)
                return "\n\n".join(res for res in result if res)
            except Exception as e:
                return f"Error during compare commit {str(e)}"
        else:
            try:
                response = await client.get(
                    f"https://api.github.com/repos/{user}/{repo}/compare/{last_processed_commit}...{latest_commit}",
                    headers=HEADERS
                )
                response.raise_for_status()
                result = ""
                for item in response.json()["files"]:
                    filename = item.get("filename")
                    status = item.get("status")
                    if status != "added":
                        patch = item.get("patch", "")
                        result += f"{filename} - {status} - {patch}\n"
                    else:
                        decoded_content = await get_file_content(
                            client, user, repo, filename, latest_commit
                        )
                        result += f"{filename} - {status} - {decoded_content}\n"
                await dbservice.add_commit(repo_name=repo, commit=latest_commit)
                return result
            except Exception as e:
                return f"Error during compare commit {str(e)}"


def chunk_result_by_tokens(
    text: str,
    target_tokens: int = 8500,
    max_tokens: int = 9000,
    overlap_tokens: int = 200,
) -> list[str]:
    if not text:
        return []

    target_chars = target_tokens * 4
    max_chars = max_tokens * 4
    overlap_chars = overlap_tokens * 4

    lines = text.split("\n")
    chunks: list[str] = []
    current = ""

    for line in lines:
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) <= target_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
            tail = current[-overlap_chars:] if overlap_chars > 0 else ""
            current = f"{tail}\n{line}" if tail else line
        else:
            start = 0
            while start < len(line):
                end = min(start + max_chars, len(line))
                chunks.append(line[start:end])
                start = end
            current = ""

    if current:
        chunks.append(current)

    final_chunks: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            final_chunks.append(chunk)
            continue
        start = 0
        while start < len(chunk):
            end = min(start + max_chars, len(chunk))
            final_chunks.append(chunk[start:end])
            start = end

    return final_chunks


async def compare_commit_chunked(last_processed_commit: Optional[str] = None) -> list[str]:
    result = await compare_commit(last_processed_commit)
    return chunk_result_by_tokens(result)


async def get_file_content(
    client: httpx.AsyncClient, user: str, repo: str, path: str, ref: str
) -> str:
    response = await client.get(
        f"https://api.github.com/repos/{user}/{repo}/contents/{path}?ref={ref}",
        headers=HEADERS
    )
    response.raise_for_status()
    content = response.json().get("content", "").replace("\n", "")
    return base64.b64decode(content).decode("utf-8", errors="replace")
