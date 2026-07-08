import asyncio

from langchain_core.messages import HumanMessage

from reviewbot.github.diff import fetch_pr_context, parse_pr_url
from reviewbot.graph.state import ReviewState

SNIPPET_PROMPT_TEMPLATE = """Review the following code snippet. Point out bugs, security issues, \
and meaningful simplifications. Be concise and specific; skip praise and nitpicks that don't matter.

{content}
"""

PR_PROMPT_TEMPLATE = """Review the following GitHub PR diff ({source_ref}). Point out bugs, \
security issues, and meaningful simplifications. Be concise and specific; skip praise and nitpicks \
that don't matter.
{full_files_section}
Diff:
{diff}
"""

FULL_FILES_SECTION_TEMPLATE = """
For extra context, here is the full content of the changed files (the diff below shows exactly \
which lines changed within them):
{files}
"""

FILE_BLOCK_TEMPLATE = """
--- File: {path} ---
{content}
"""


def _build_full_files_section(full_files: dict[str, str]) -> str:
    if not full_files:
        return ""
    files_text = "".join(
        FILE_BLOCK_TEMPLATE.format(path=path, content=content) for path, content in full_files.items()
    )
    return FULL_FILES_SECTION_TEMPLATE.format(files=files_text)


async def intake(state: ReviewState) -> dict:
    raw_input = state["raw_input"]
    pr_ref = parse_pr_url(raw_input)

    if pr_ref:
        owner, repo, number = pr_ref
        source_ref = f"{owner}/{repo}#{number}"
        diff, full_files = await asyncio.to_thread(fetch_pr_context, owner, repo, number)

        prompt = PR_PROMPT_TEMPLATE.format(
            source_ref=source_ref,
            full_files_section=_build_full_files_section(full_files),
            diff=diff,
        )
        return {
            "source": "pr",
            "source_ref": source_ref,
            "review_target": diff,
            "messages": [HumanMessage(content=prompt)],
        }

    prompt = SNIPPET_PROMPT_TEMPLATE.format(content=raw_input)
    return {
        "source": "snippet",
        "source_ref": None,
        "review_target": raw_input,
        "messages": [HumanMessage(content=prompt)],
    }
