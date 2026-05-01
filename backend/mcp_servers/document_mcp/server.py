"""
Document Processing MCP Server — PDF/text extraction, chunking, search.
Handles: PDF parsing, table extraction, structured data extraction via LLM.
"""
import json
import base64
import logging
from pathlib import Path
from mcp.server.fastmcp import FastMCP
import fitz  # PyMuPDF
import boto3
from backend.core.config import settings

logger = logging.getLogger(__name__)
mcp = FastMCP(name="Document MCP Server", version="1.0.0")


@mcp.tool()
async def extract_text_from_pdf(pdf_path: str, page_range: str | None = None) -> str:
    """
    Extract text from a PDF file with structure preservation.

    Args:
        pdf_path: Local path or S3 URI (s3://bucket/key) to the PDF
        page_range: Optional page range like "1-5" or "2"

    Returns:
        Extracted text with page markers
    """
    try:
        # Handle S3 paths
        if pdf_path.startswith("s3://"):
            parts = pdf_path[5:].split("/", 1)
            bucket, key = parts[0], parts[1]
            s3 = boto3.client("s3",
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )
            response = s3.get_object(Bucket=bucket, Key=key)
            pdf_bytes = response["Body"].read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        else:
            doc = fitz.open(pdf_path)

        # Determine page range
        start, end = 0, len(doc)
        if page_range:
            if "-" in page_range:
                s, e = page_range.split("-")
                start, end = int(s) - 1, int(e)
            else:
                start = int(page_range) - 1
                end = start + 1

        text_parts = []
        for page_num in range(start, min(end, len(doc))):
            page = doc[page_num]
            text = page.get_text("text")
            text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

        doc.close()
        return json.dumps({
            "text": "\n\n".join(text_parts),
            "total_pages": len(doc),
            "extracted_pages": end - start,
        })

    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def extract_tables_from_pdf(pdf_path: str) -> str:
    """
    Extract tables from a PDF as structured JSON data.

    Args:
        pdf_path: Path to PDF file

    Returns:
        JSON array of extracted tables with rows and columns
    """
    try:
        doc = fitz.open(pdf_path)
        all_tables = []

        for page_num, page in enumerate(doc):
            tabs = page.find_tables()
            for tab in tabs:
                df_data = tab.extract()
                if df_data:
                    all_tables.append({
                        "page": page_num + 1,
                        "rows": df_data,
                        "row_count": len(df_data),
                        "col_count": len(df_data[0]) if df_data else 0,
                    })
        doc.close()
        return json.dumps({"tables": all_tables, "total_tables": len(all_tables)})

    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def search_document(pdf_path: str, query: str) -> str:
    """
    Search for specific text within a document.

    Args:
        pdf_path: Path to document
        query: Text to search for

    Returns:
        List of matches with page numbers and surrounding context
    """
    try:
        doc = fitz.open(pdf_path)
        matches = []
        for page_num, page in enumerate(doc):
            rects = page.search_for(query)
            if rects:
                context = page.get_text("text")
                matches.append({
                    "page": page_num + 1,
                    "match_count": len(rects),
                    "context_preview": context[:500],
                })
        doc.close()
        return json.dumps({"matches": matches, "total_matches": len(matches)})
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Mount
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

    session_manager = StreamableHTTPSessionManager(
        app=mcp._mcp_server, json_response=True, stateless=True
    )
    app = Starlette(routes=[Mount("/mcp", app=session_manager.handle_request)])
    uvicorn.run(app, host="0.0.0.0", port=settings.document_mcp_port)
