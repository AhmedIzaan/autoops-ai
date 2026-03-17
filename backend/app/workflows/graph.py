"""LangGraph workflow definition for AutoOps AI.

This sets up a simple planner -> router -> tool executor -> validator -> finalizer
flow. The planner uses Gemini (via langchain-google-genai) when an API key is
configured; otherwise it falls back to a deterministic stub plan.

State shape (RunState):
- run_id: unique id for the run
- prompt: user prompt
- file_refs: optional list of file paths/ids
- plan: list of steps, each {"tool": str, "args": dict}
- cursor: current index into plan
- tool_results: list of per-step results
- status: pending|running|error|completed
- message: optional human-readable message
"""

from __future__ import annotations

import json
from typing import Any, Literal, TypedDict
from uuid import uuid4

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph

from app.config import settings
from app.tools.csv_analyzer import summarize_csv
from app.tools.email_draft import draft_email
from app.tools.pdf_summarizer import extract_text
from app.tools.task_creator import create_task
from app.tools.report_generator import generate_markdown


class RunState(TypedDict, total=False):
    run_id: str
    prompt: str
    file_refs: list[str]
    plan: list[dict[str, Any]]
    cursor: int
    tool_results: list[dict[str, Any]]
    status: Literal["pending", "running", "completed", "error"]
    message: str | None
    summary: str | None


def _make_llm():
    if not settings.gemini_api_key:
        return None
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=settings.gemini_api_key)


def _extract_json(raw: str) -> list[dict[str, Any]]:
    """Extract JSON from LLM response, handling markdown code blocks."""
    import re
    # Try to extract from markdown code block first
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if match:
        raw = match.group(1)
    raw = raw.strip()
    # Handle case where LLM returns empty or non-JSON
    if not raw or not raw.startswith("["):
        return []
    return json.loads(raw)


def planner(state: RunState) -> RunState:
    plan: list[dict[str, Any]] = []
    try:
        llm = _make_llm()
        if llm:
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are a workflow planner. Given a user request and files, "
                        "produce a minimal sequence of tool calls in JSON. Allowed tools: "
                        "csv_analyzer(path), pdf_summarizer(path), report_generator(title, summary, items?), email_draft(subject, body, to?), task_creator(title, description?, owner?). "
                        'Respond ONLY with a raw JSON array like [{{\"tool\":\"csv_analyzer\",\"args\":{{\"path\":\"/tmp/file.csv\"}}}}]. No markdown, no explanation.',
                    ),
                    ("human", "Request: {prompt}\nFiles: {file_refs}"),
                ]
            )
            chain = prompt | llm | StrOutputParser()
            raw = chain.invoke({"prompt": state.get("prompt", ""), "file_refs": state.get("file_refs", [])})
            print(f"[planner] LLM raw response: {raw[:500]}")  # Debug log
            plan = _extract_json(raw)
            print(f"[planner] Parsed plan: {plan}")  # Debug log
        else:
            # Fallback deterministic plan
            plan = [{"tool": "task_creator", "args": {"title": state.get("prompt", "Task"), "description": None}}]
        
        if not plan:
            # If plan is empty, create a sensible default based on files
            file_refs = state.get("file_refs", [])
            if file_refs:
                for f in file_refs:
                    if f.lower().endswith(".csv"):
                        plan.append({"tool": "csv_analyzer", "args": {"path": f}})
                    elif f.lower().endswith(".pdf"):
                        plan.append({"tool": "pdf_summarizer", "args": {"path": f}})
            if not plan:
                plan = [{"tool": "task_creator", "args": {"title": state.get("prompt", "Task"), "description": None}}]
        
        status: Literal["pending", "running", "error", "completed"] = "running"
        return {
            **state,
            "plan": plan,
            "cursor": 0,
            "tool_results": [],
            "status": status,
            "message": None,
        }
    except Exception as exc:  # noqa: BLE001
        print(f"[planner] Error: {exc}")  # Debug log
        return {**state, "status": "error", "message": f"planner_failed: {exc}"}


def router(state: RunState) -> str:
    if state.get("status") == "error":
        return "finalizer"
    plan = state.get("plan") or []
    cursor = state.get("cursor", 0)
    if cursor >= len(plan):
        return "finalizer"
    return "tool_executor"


def tool_executor(state: RunState) -> RunState:
    plan = state.get("plan") or []
    cursor = state.get("cursor", 0)
    print(f"[tool_executor] Starting, cursor={cursor}, plan_len={len(plan)}")
    if cursor >= len(plan):
        return {**state, "status": "completed", "message": "no_steps"}

    step = plan[cursor]
    tool_name = step.get("tool")
    args = step.get("args", {}) or {}
    print(f"[tool_executor] Running tool={tool_name}, args={args}")
    result: dict[str, Any]

    try:
        if tool_name == "csv_analyzer":
            path = args.get("path")
            if not path:
                raise ValueError("csv_analyzer requires 'path'")
            result = {"tool": tool_name, "output": summarize_csv(path)}
        elif tool_name == "pdf_summarizer":
            path = args.get("path")
            if not path:
                raise ValueError("pdf_summarizer requires 'path'")
            result = {"tool": tool_name, "output": extract_text(path)}
        elif tool_name == "email_draft":
            result = {"tool": tool_name, "output": draft_email(**{k: v for k, v in args.items() if k in {"subject", "body", "to"}})}
        elif tool_name == "task_creator":
            result = {
                "tool": tool_name,
                "output": create_task(
                    title=args.get("title", state.get("prompt", "Task")),
                    description=args.get("description"),
                    owner=args.get("owner"),
                ),
            }
        elif tool_name == "report_generator":
            result = {
                "tool": tool_name,
                "output": generate_markdown(
                    title=args.get("title", "Report"),
                    summary=args.get("summary", ""),
                    items=args.get("items"),
                    details=args.get("details"),
                ),
            }
        else:
            raise ValueError(f"unsupported tool: {tool_name}")

        tool_results = list(state.get("tool_results", []))
        tool_results.append(result)
        print(f"[tool_executor] Success: {tool_name}")
        return {
            **state,
            "tool_results": tool_results,
            "cursor": cursor + 1,
            "status": "running",
        }
    except Exception as exc:  # noqa: BLE001
        print(f"[tool_executor] Error in {tool_name}: {exc}")
        tool_results = list(state.get("tool_results", []))
        tool_results.append({"tool": tool_name, "error": str(exc)})
        return {**state, "status": "error", "message": f"tool_failed: {exc}", "tool_results": tool_results}

def validator(state: RunState) -> RunState:
    # Placeholder validator; could add content checks later.
    return state


def finalizer(state: RunState) -> RunState:
    if state.get("status") != "error":
        state = {**state, "status": "completed", "message": state.get("message")}
    print(f"[finalizer] status={state.get('status')}, tool_results count={len(state.get('tool_results', []))}")

    # Generate a human-readable summary using the LLM
    summary: str | None = None
    try:
        llm = _make_llm()
        if llm and state.get("tool_results"):
            results_text = json.dumps(state["tool_results"], indent=2)
            prompt_text = state.get("prompt", "")
            summarize_prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "You are a helpful assistant. Given the user's original request and the raw JSON outputs "
                    "from a set of automated tools, write a clear, concise, and friendly summary for the user. "
                    "Use plain language. Use bullet points or short paragraphs as appropriate. "
                    "Do NOT output JSON. Highlight key numbers, insights, or action items.",
                ),
                (
                    "human",
                    "Original request: {prompt}\n\nTool outputs:\n{results}",
                ),
            ])
            chain = summarize_prompt | llm | StrOutputParser()
            summary = chain.invoke({"prompt": prompt_text, "results": results_text})
            print(f"[finalizer] Summary generated ({len(summary)} chars)")
    except Exception as exc:
        print(f"[finalizer] Summary generation failed: {exc}")

    return {**state, "summary": summary}


def build_graph():
    graph = StateGraph(RunState)
    graph.add_node("planner", planner)
    graph.add_node("tool_executor", tool_executor)
    graph.add_node("validator", validator)
    graph.add_node("finalizer", finalizer)

    graph.set_entry_point("planner")
    # After planning, route to first tool or straight to finalizer if no steps
    graph.add_conditional_edges("planner", router, {"tool_executor": "tool_executor", "finalizer": "finalizer"})
    graph.add_edge("tool_executor", "validator")
    # After each tool, route to next tool or finalizer when all steps done
    graph.add_conditional_edges("validator", router, {"tool_executor": "tool_executor", "finalizer": "finalizer"})
    graph.add_edge("finalizer", END)

    return graph.compile()


app = build_graph()


def run_workflow(prompt: str, file_refs: list[str] | None = None) -> RunState:
    run_id = str(uuid4())
    initial_state: RunState = {
        "run_id": run_id,
        "prompt": prompt,
        "file_refs": file_refs or [],
        "status": "pending",
        "plan": [],
        "cursor": 0,
        "tool_results": [],
        "message": None,
        "summary": None,
    }
    result = app.invoke(initial_state)
    return result
