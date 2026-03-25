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
                        "You are a workflow planner for an automation system. Given a user request and optional files, "
                        "produce a sequence of tool calls as a JSON array.\n\n"
                        "Available tools:\n"
                        "- csv_analyzer(path): Analyze a CSV file and extract statistics + insights.\n"
                        "- pdf_summarizer(path): Extract and summarize text from a PDF.\n"
                        "- report_generator(title): Generate a formatted markdown report. "
                        "  When used AFTER csv_analyzer or pdf_summarizer, it automatically includes their output — "
                        "  you only need to provide a title.\n"
                        "- email_draft(subject, body, to?): Draft an email.\n"
                        "- task_creator(title, description?, owner?): Create a task.\n\n"
                        "RULES:\n"
                        "1. If the user mentions 'report' or 'generate report', ALWAYS include report_generator in the plan.\n"
                        "2. If a CSV or PDF file is provided and the user wants a report, run the analyzer FIRST, then report_generator.\n"
                        "3. If the user wants analysis only (no report), just use csv_analyzer or pdf_summarizer.\n"
                        "4. Chain tools in logical order — data tools before report_generator, report before email.\n\n"
                        'Respond ONLY with a raw JSON array like [{{"tool":"csv_analyzer","args":{{"path":"/tmp/file.csv"}}}}, {{"tool":"report_generator","args":{{"title":"Sales Report"}}}}]. '
                        "No markdown, no explanation.",
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


def _build_report_context(args: dict[str, Any], state: RunState) -> tuple[str, str, list, str | None]:
    """
    Dynamically build report_generator arguments from prior tool results in state.
    Falls back to args provided by the planner if already populated.
    """
    prior_results = state.get("tool_results") or []

    title = args.get("title") or "AutoOps Report"
    summary_parts: list[str] = []
    items: list[dict[str, Any]] = args.get("items") or []
    details_parts: list[str] = []

    # Inject planner-provided summary if it exists and is meaningful
    planner_summary = (args.get("summary") or "").strip()
    if planner_summary:
        summary_parts.append(planner_summary)

    for prior in prior_results:
        output = prior.get("output") or {}
        tool = prior.get("tool", "")

        if tool == "csv_analyzer" and isinstance(output, dict):
            # Build summary from AI insights
            insights = output.get("ai_insights") or []
            if insights:
                summary_parts.append("**Data Analysis Insights:**")
                summary_parts.extend(f"- {ins}" for ins in insights)
            # Build highlight items from numeric summary
            numeric = output.get("numeric_summary") or {}
            for col, stats in list(numeric.items())[:4]:
                mean_val = stats.get("mean")
                if mean_val is not None:
                    items.append({"label": f"{col} (avg)", "value": f"{mean_val:.2f}"})
            # Include row/col counts
            details_parts.append(
                f"Dataset: {output.get('row_count', '?')} rows × {output.get('column_count', '?')} columns"
            )

        elif tool == "pdf_summarizer" and isinstance(output, dict):
            pdf_summary = (output.get("summary") or "").strip()
            if pdf_summary:
                summary_parts.append(pdf_summary)
            details_parts.append(
                f"Source: {output.get('page_count', '?')} page PDF ({output.get('char_count', '?')} chars extracted)"
            )

    final_summary = "\n\n".join(summary_parts) or "Automated report generated by AutoOps AI."
    final_details = "\n\n".join(details_parts) or None
    return title, final_summary, items, final_details


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
            # Build context from prior tool results for LLM body generation
            prior_results = state.get("tool_results") or []
            context_parts: list[str] = []
            for prior in prior_results:
                out = prior.get("output") or {}
                t = prior.get("tool", "")
                if t == "report_generator" and isinstance(out, dict):
                    context_parts.append(out.get("content", ""))
                elif t == "csv_analyzer" and isinstance(out, dict):
                    insights = out.get("ai_insights") or []
                    if insights:
                        context_parts.append("\n".join(f"- {i}" for i in insights))
                elif t == "pdf_summarizer" and isinstance(out, dict):
                    context_parts.append(out.get("summary", ""))
            context = "\n\n".join(filter(None, context_parts)) or None

            # If we have real context from prior tools, discard the planner's
            # generic placeholder body and let the LLM write from actual content.
            body_arg = None if context else (args.get("body") or None)

            result = {"tool": tool_name, "output": draft_email(
                subject=args.get("subject", "AutoOps Report"),
                body=body_arg,
                to=args.get("to") or None,
                context=context,
            )}


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
            # Dynamically build context from previous tool results
            title, summary, items, details = _build_report_context(args, state)
            print(f"[tool_executor] report_generator — title='{title}', summary_len={len(summary)}, items={len(items)}")
            result = {
                "tool": tool_name,
                "output": generate_markdown(
                    title=title,
                    summary=summary,
                    items=items,
                    details=details,
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
    # Skip validation if we are already in an error state
    if state.get("status") == "error":
        return state

    tool_results = state.get("tool_results", [])
    if not tool_results:
        return state

    last_result = tool_results[-1]
    tool_name = last_result.get("tool", "unknown")

    # Check if there's already a hard tool error
    if "error" in last_result:
        return state

    # Special case: email_draft — if the email content is valid (subject + body present),
    # treat it as success even if SMTP sending failed. SMTP errors are infra issues,
    # not tool logic failures. The draft itself is the deliverable.
    if tool_name == "email_draft":
        output = last_result.get("output") or {}
        if output.get("subject") and output.get("body"):
            smtp_err = output.get("send_skipped_reason") or ""
            if "SMTP error" in smtp_err:
                print(f"[validator] email_draft: SMTP send failed but draft is valid — passing.")
            return state   # always pass email_draft if content is present


    try:
        llm = _make_llm()
        if llm:
            # Build a clean copy of output, stripping large/raw debug fields
            # that are intentionally truncated (e.g. raw_extract in pdf_summarizer)
            raw_output = last_result.get("output", "")
            if isinstance(raw_output, dict):
                SKIP_KEYS = {"raw_extract"}  # known large debug-only fields
                clean_output = {k: v for k, v in raw_output.items() if k not in SKIP_KEYS}
            else:
                clean_output = raw_output

            output_str = str(clean_output)[:2000]

            validation_prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "You are a data validation agent in an automated workflow. "
                    "Given the output of a tool, decide if it is valid and useful. "
                    "Rules:\n"
                    "- A 'summary' or 'ai_insights' field with real content means the tool succeeded.\n"
                    "- Fields named 'raw_extract' are intentionally truncated — ignore them entirely.\n"
                    "- Only flag as invalid if the core output is empty, missing, or contains an obvious error message.\n"
                    "If valid, reply ONLY with the single word: VALID\n"
                    "If invalid, reply with one short sentence explaining what is wrong."
                ),
                (
                    "human",
                    "User request: {prompt}\n\nTool: {tool}\nOutput (debug fields removed): {output}"
                ),
            ])
            chain = validation_prompt | llm | StrOutputParser()
            
            response = chain.invoke({
                "prompt": state.get("prompt", ""),
                "tool": tool_name, 
                "output": output_str
            }).strip()
            
            print(f"[validator] Tool: {tool_name} | Eval: {response}")
            
            # If the LLM doesn't explicitly return VALID, treat it as an error
            if "VALID" not in response.upper() or len(response) > 10:
                return {
                    **state,
                    "status": "error",
                    "message": f"Validation failed for '{tool_name}': {response}"
                }
    except Exception as exc:
        print(f"[validator] LLM check failed (falling back to accepting): {exc}")

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
