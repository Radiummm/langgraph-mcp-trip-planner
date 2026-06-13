"""Ingest markdown travel guides into PostgreSQL/pgvector."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.rag_service import get_rag_service  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the travel RAG knowledge base.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "travel_guides",
        help="Directory containing markdown travel guide files.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append/upsert documents without clearing the existing table.",
    )
    args = parser.parse_args()

    rag_service = get_rag_service()
    documents = rag_service.load_documents(args.data_dir)
    print(f"Loaded {len(documents)} chunks from {args.data_dir}")

    if not args.append:
        rag_service.clear_documents()
        print(f"Cleared existing rows from {rag_service.table_name}")

    inserted = rag_service.ingest_documents(documents)
    print(f"Upserted {inserted} chunks into {rag_service.table_name}")


if __name__ == "__main__":
    main()
