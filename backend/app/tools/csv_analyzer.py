import json
from collections.abc import Sequence

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings


def summarize_csv(file_path: str) -> dict[str, object]:
    """Load CSV, return basic stats, and generate domain insights using LLM."""
    df = pd.read_csv(file_path)
    summary: dict[str, object] = {
        "row_count": int(df.shape[0]),
        "column_count": int(df.shape[1]),
        "columns": list(df.columns),
    }
    numeric_cols: Sequence[str] = df.select_dtypes(include="number").columns
    
    stats_dict = {}
    if len(numeric_cols) > 0:
        stats_dict = df[numeric_cols].describe().to_dict()
        summary["numeric_summary"] = stats_dict

    if settings.gemini_api_key:
        try:
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=settings.gemini_api_key)
            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "You are a superhuman data analyst. You are given basic statistical summaries of a dataset (column names, row count, numeric summary like min, max, mean). "
                    "Analyze these statistics and provide 3-5 concise, high-value bullet points of insights or potential problems (e.g., obvious outliers, suspicious zeros, or general observations). "
                    "Output ONLY a raw JSON array of strings, where each string is a bullet point insight."
                ),
                (
                    "human",
                    "Dataset preview:\nRow count: {rows}\nColumns: {cols}\nNumeric stats: {stats}"
                )
            ])
            chain = prompt | llm | StrOutputParser()
            raw_response = chain.invoke({
                "rows": summary["row_count"],
                "cols": summary["columns"],
                "stats": stats_dict
            }).strip()

            import re
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw_response)
            if match:
                raw_response = match.group(1).strip()
            
            insights = json.loads(raw_response)
            if isinstance(insights, list):
                summary["ai_insights"] = insights
            else:
                summary["ai_insights"] = ["Could not generate specific insights."]
        except Exception as exc:
            summary["ai_insights"] = [f"Failed to generate insights: {exc}"]
    else:
        summary["ai_insights"] = ["No LLM configured for insights."]

    return summary
