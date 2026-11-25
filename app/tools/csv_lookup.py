import os
import pandas as pd
from typing import List, Any, Dict
from app.tools.registry import BaseTool, ToolParameter

class CSVLookupTool(BaseTool):
    @property
    def name(self) -> str:
        return "csv_lookup"

    @property
    def description(self) -> str:
        return "Search catalog CSV files by query or filter by column values to return matching records."

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="file_path",
                type="string",
                description="Path to the CSV file to search (relative or absolute).",
                required=True
            ),
            ToolParameter(
                name="query",
                type="string",
                description="Search query string to match across all columns (e.g., part number or keyword).",
                required=False
            ),
            ToolParameter(
                name="column",
                type="string",
                description="Optional column name to restrict the search to.",
                required=False
            ),
            ToolParameter(
                name="max_results",
                type="integer",
                description="Maximum number of rows to return (default: 5).",
                required=False
            )
        ]

    def execute(self, file_path: str, query: str = "", column: str = "", max_results: int = 5, **kwargs: Any) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            # Try searching in default directories
            alt_path = os.path.join(os.getcwd(), file_path)
            if not os.path.exists(alt_path):
                return {"error": f"File not found: {file_path}", "results": []}
            file_path = alt_path

        try:
            df = pd.read_csv(file_path)
            if not query:
                # Return top records
                results = df.head(max_results).to_dict(orient="records")
                return {"total_rows": len(df), "returned": len(results), "results": results}

            query_lower = str(query).lower().strip()

            if column and column in df.columns:
                mask = df[column].astype(str).str.lower().str.contains(query_lower, regex=False, na=False)
            else:
                # Search across all columns
                mask = df.astype(str).apply(lambda row: row.str.lower().str.contains(query_lower, regex=False, na=False)).any(axis=1)

            matches = df[mask]
            results = matches.head(max_results).to_dict(orient="records")
            return {
                "query": query,
                "total_matches": len(matches),
                "returned": len(results),
                "results": results
            }
        except Exception as e:
            return {"error": f"Failed to execute CSV lookup: {str(e)}", "results": []}
