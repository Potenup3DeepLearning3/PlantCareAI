"""
Boonz Plant Care MCP Server
식물 케어 DB를 MCP 프로토콜로 노출.

실행: python mcp_server/plant_db_server.py
"""
import asyncio
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "plant_care.db"


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


async def main():
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import Tool, TextContent
    except ImportError:
        print("mcp 패키지가 없습니다. pip install mcp")
        return

    server = Server("plant-care-db")

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="query_disease",
                description="병명으로 질병 정보를 조회합니다.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "disease_name": {
                            "type": "string",
                            "description": "영문 병명 (예: Late_Blight, Healthy)"
                        }
                    },
                    "required": ["disease_name"]
                }
            ),
            Tool(
                name="query_care_tips",
                description="카테고리별 식물 케어 팁을 조회합니다.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": ["water", "light", "soil", "nutrition",
                                     "environment", "propagation", "seasonal", "trouble"],
                        },
                        "subcategory": {"type": "string"}
                    },
                    "required": ["category"]
                }
            ),
            Tool(
                name="query_species",
                description="식물 종별 관리 정보를 조회합니다.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "species": {"type": "string"}
                    },
                    "required": ["species"]
                }
            ),
            Tool(
                name="search_by_symptom",
                description="증상 키워드로 가능한 병변을 검색합니다.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symptom": {"type": "string"}
                    },
                    "required": ["symptom"]
                }
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        db = get_db()

        if name == "query_disease":
            disease_name = arguments["disease_name"]
            row = db.execute("SELECT * FROM diseases WHERE name = ?", (disease_name,)).fetchone()
            if not row:
                return [TextContent(type="text", text=json.dumps({"error": f"'{disease_name}' 정보 없음"}, ensure_ascii=False))]
            return [TextContent(type="text", text=json.dumps(dict(row), ensure_ascii=False, indent=2))]

        elif name == "query_care_tips":
            category = arguments["category"]
            subcategory = arguments.get("subcategory", "")
            if subcategory:
                rows = db.execute(
                    "SELECT subcategory, tip, detail FROM care_tips WHERE category = ? AND subcategory LIKE ?",
                    (category, f"%{subcategory}%")
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT subcategory, tip, detail FROM care_tips WHERE category = ?",
                    (category,)
                ).fetchall()
            return [TextContent(type="text", text=json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))]

        elif name == "query_species":
            species = arguments["species"]
            row = db.execute(
                "SELECT * FROM species_care WHERE species LIKE ?", (f"%{species}%",)
            ).fetchone()
            if not row:
                return [TextContent(type="text", text=json.dumps({"error": f"'{species}' 정보 없음"}, ensure_ascii=False))]
            return [TextContent(type="text", text=json.dumps(dict(row), ensure_ascii=False, indent=2))]

        elif name == "search_by_symptom":
            symptom = arguments["symptom"]
            rows = db.execute(
                "SELECT name, korean_name, symptoms, severity_levels FROM diseases WHERE symptoms LIKE ?",
                (f"%{symptom}%",)
            ).fetchall()
            return [TextContent(type="text", text=json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))]

        return [TextContent(type="text", text="알 수 없는 도구")]

    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
