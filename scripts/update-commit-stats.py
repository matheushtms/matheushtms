#!/usr/bin/env python3
"""Recalcula os badges de commits (hoje/ano/total) e atualiza o README entre os marcadores COMMIT-STATS."""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

LOGIN = "matheushtms"
README_PATH = os.path.join(os.path.dirname(__file__), "..", "README.md")
START_MARKER = "<!-- COMMIT-STATS:START -->"
END_MARKER = "<!-- COMMIT-STATS:END -->"
API_URL = "https://api.github.com/graphql"

YEARS_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionYears
    }
  }
}
"""

RANGE_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions }
    }
  }
}
"""


def graphql(query, variables, token):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": LOGIN,
        },
    )
    with urllib.request.urlopen(req) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]


def commits_in_range(token, start, end):
    data = graphql(
        RANGE_QUERY,
        {"login": LOGIN, "from": start.isoformat(), "to": end.isoformat()},
        token,
    )
    cc = data["user"]["contributionsCollection"]
    print(f"DEBUG {start.date()}..{end.date()}: {cc}", file=sys.stderr)
    return cc["totalCommitContributions"]


def main():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("defina GITHUB_TOKEN ou GH_TOKEN no ambiente")

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    hoje = commits_in_range(token, today_start, now)
    ano = commits_in_range(token, year_start, now)

    years_data = graphql(YEARS_QUERY, {"login": LOGIN}, token)
    years = years_data["user"]["contributionsCollection"]["contributionYears"]

    total = 0
    for y in years:
        if y == now.year:
            total += ano
            continue
        y_start = datetime(y, 1, 1, tzinfo=timezone.utc)
        y_end = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
        total += commits_in_range(token, y_start, y_end)

    badges = (
        f"![Commits hoje](https://img.shields.io/badge/Commits_hoje-{hoje}-2DD4BF?style=for-the-badge&logo=git&logoColor=white) "
        f"![Commits este ano](https://img.shields.io/badge/Commits_este_ano-{ano}-2DD4BF?style=for-the-badge&logo=git&logoColor=white) "
        f"![Commits no total](https://img.shields.io/badge/Commits_no_total-{total}-2DD4BF?style=for-the-badge&logo=git&logoColor=white)"
    )
    block = f"{START_MARKER}\n{badges}\n{END_MARKER}"

    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL)
    if not pattern.search(content):
        sys.exit("marcadores COMMIT-STATS não encontrados no README")

    new_content = pattern.sub(block, content)

    if new_content != content:
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"README atualizado: hoje={hoje} ano={ano} total={total}")
    else:
        print("Nenhuma mudança nos números.")


if __name__ == "__main__":
    main()
