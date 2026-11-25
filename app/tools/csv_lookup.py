import os
import pandas as pd
from typing import List, Any, Dict, Optional
from app.tools.registry import BaseTool, ToolParameter

class CSVLookupTool(BaseTool):
    """
    Search catalog CSV files by query or filter by column values.
    Guarantees:
    - Path traversal prevention
    - File extension validation (.csv only)
    - Restricted to authorized document directories and files
    """

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

    def execute(
        self,
        file_path: str,
        query: str = "",
        column: str = "",
        max_results: int = 5,
        authorized_directory: Optional[str] = None,
        authorized_files: Optional[List[str]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        raw_path = str(file_path).strip()

        # 1. Reject path traversal attempts and dangerous extensions
        if ".." in raw_path or raw_path.startswith("/etc") or raw_path.startswith("/var") or raw_path.startswith("/proc"):
            raise PermissionError(f"Security violation: Path traversal or unauthorized system access attempt: '{file_path}'")

        if not raw_path.lower().endswith(".csv"):
            raise PermissionError(f"Security violation: CSV lookup is strictly restricted to .csv files: '{file_path}'")

        # 2. Resolve target file path
        resolved_path = os.path.abspath(raw_path)

        # If file not found at raw_path, check in authorized_directory or cwd
        if not os.path.exists(resolved_path):
            if authorized_directory and os.path.exists(os.path.join(authorized_directory, os.path.basename(raw_path))):
                resolved_path = os.path.abspath(os.path.join(authorized_directory, os.path.basename(raw_path)))
            elif os.path.exists(os.path.join(os.getcwd(), raw_path)):
                resolved_path = os.path.abspath(os.path.join(os.getcwd(), raw_path))
            else:
                return {"error": f"File not found: {file_path}", "results": []}

        # 3. Restrict to authorized directory if specified
        if authorized_directory:
            abs_auth_dir = os.path.abspath(authorized_directory)
            common = os.path.commonpath([resolved_path, abs_auth_dir])
            if common != abs_auth_dir:
                raise PermissionError(
                    f"Security violation: Access denied: '{file_path}' is outside authorized directory: '{authorized_directory}'"
                )

        # 4. Restrict to authorized filenames if specified
        if authorized_files:
            allowed_basenames = [os.path.basename(f) for f in authorized_files]
            if os.path.basename(resolved_path) not in allowed_basenames:
                raise PermissionError(
                    f"Security violation: Access denied: '{os.path.basename(resolved_path)}' is not in authorized file list: {allowed_basenames}"
                )

        try:
            df = pd.read_csv(resolved_path)
            if not query:
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
