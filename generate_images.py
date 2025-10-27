#!/usr/bin/python3

import asyncio
import os
import re

import aiohttp
import ssl
import certifi

from github_stats import Stats


################################################################################
# Helper Functions
################################################################################


def generate_output_folder() -> None:
    """
    Create the output folder if it does not already exist
    """
    if not os.path.isdir("generated"):
        os.mkdir("generated")


################################################################################
# Individual Image Generation Functions
################################################################################


async def generate_overview(s: Stats) -> None:
    """
    Generate an SVG badge with summary statistics
    :param s: Represents user's GitHub statistics
    """
    with open("templates/overview.svg", "r") as f:
        output = f.read()

    # Fetch stats with fallbacks so one failing API call doesn't prevent image generation
    try:
        name_val = await s.name
    except Exception:
        name_val = "Unknown"

    try:
        stars_val = f"{await s.stargazers:,}"
    except Exception:
        stars_val = "0"

    try:
        forks_val = f"{await s.forks:,}"
    except Exception:
        forks_val = "0"

    try:
        contributions_val = f"{await s.total_contributions:,}"
    except Exception:
        contributions_val = "0"

    try:
        lines = await s.lines_changed
        changed = lines[0] + lines[1]
        changed_val = f"{changed:,}"
    except Exception:
        changed_val = "N/A"

    try:
        views_val = f"{await s.views:,}"
    except Exception:
        views_val = "0"

    try:
        repos_val = f"{len(await s.repos):,}"
    except Exception:
        repos_val = "0"

    # New stats with fallbacks
    try:
        pull_requests_val = f"{await s.total_pull_requests:,}"
    except Exception:
        pull_requests_val = "0"

    try:
        issues_val = f"{await s.total_issues_created:,}"
    except Exception:
        issues_val = "0"

    output = re.sub("{{ name }}", name_val, output)
    output = re.sub("{{ stars }}", stars_val, output)
    output = re.sub("{{ forks }}", forks_val, output)
    output = re.sub("{{ contributions }}", contributions_val, output)
    # output = re.sub("{{ lines_changed }}", f"{changed:,}", output)
    output = re.sub("{{ views }}", views_val, output)
    output = re.sub("{{ repos }}", repos_val, output)
    # New stats
    output = re.sub("{{ pull_requests }}", pull_requests_val, output)
    output = re.sub("{{ issues }}", issues_val, output)

    generate_output_folder()
    with open("generated/overview.svg", "w") as f:
        f.write(output)


async def generate_languages(s: Stats) -> None:
    """
    Generate an SVG badge with summary languages used
    :param s: Represents user's GitHub statistics
    """
    with open("templates/languages.svg", "r") as f:
        output = f.read()

    progress = ""
    lang_list = ""
    sorted_languages = sorted(
        (await s.languages).items(), reverse=True, key=lambda t: t[1].get("size")
    )
    delay_between = 150
    for i, (lang, data) in enumerate(sorted_languages):
        color = data.get("color")
        color = color if color is not None else "#000000"
        progress += (
            f'<span style="background-color: {color};'
            f'width: {data.get("prop", 0):0.3f}%;" '
            f'class="progress-item"></span>'
        )
        lang_list += f"""
<li style="animation-delay: {i * delay_between}ms;">
<svg xmlns="http://www.w3.org/2000/svg" class="octicon" style="fill:{color};"
viewBox="0 0 16 16" version="1.1" width="16" height="16"><path
fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8z"></path></svg>
<span class="lang">{lang}</span>
<span class="percent">{data.get("prop", 0):0.2f}%</span>
</li>

"""

    output = re.sub(r"{{ progress }}", progress, output)
    output = re.sub(r"{{ lang_list }}", lang_list, output)

    generate_output_folder()
    with open("generated/languages.svg", "w") as f:
        f.write(output)


################################################################################
# Main Function
################################################################################


async def main() -> None:
    """
    Generate all badges
    """
    access_token = os.getenv("ACCESS_TOKEN")
    if not access_token:
        # access_token = os.getenv("GITHUB_TOKEN")
        raise Exception("A personal access token is required to proceed!")
    user = os.getenv("GITHUB_ACTOR")
    if user is None:
        raise RuntimeError("Environment variable GITHUB_ACTOR must be set.")
    exclude_repos = os.getenv("EXCLUDED")
    excluded_repos = (
        {x.strip() for x in exclude_repos.split(",")} if exclude_repos else None
    )
    exclude_langs = os.getenv("EXCLUDED_LANGS")
    excluded_langs = (
        {x.strip() for x in exclude_langs.split(",")} if exclude_langs else None
    )
    # Convert a truthy value to a Boolean
    raw_ignore_forked_repos = os.getenv("EXCLUDE_FORKED_REPOS")
    ignore_forked_repos = (
        not not raw_ignore_forked_repos
        and raw_ignore_forked_repos.strip().lower() != "false"
    )
    raw_ignore_contribs = os.getenv("EXCLUDE_CONTRIBS") or os.getenv("EXCLUDE_CONTRIBUTED")
    ignore_contrib_repos = (
        not not raw_ignore_contribs and str(raw_ignore_contribs).strip().lower() != "false"
    )
    # Use certifi's CA bundle for aiohttp to avoid macOS venv SSL errors
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        s = Stats(
            user,
            access_token,
            session,
            exclude_repos=excluded_repos,
            exclude_langs=excluded_langs,
            ignore_forked_repos=ignore_forked_repos,
            ignore_contrib_repos=ignore_contrib_repos,
        )
        await asyncio.gather(generate_languages(s), generate_overview(s))


if __name__ == "__main__":
    asyncio.run(main())
