"""Trusted operator CLI: python -m app.services.knowledge_cli --help."""

import argparse
import json
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.db.repositories.knowledge import PostgresKnowledgeRepository, initialize_knowledge_schema
from app.db.session import database_engine
from app.integrations.embedding.client import CompatibleEmbedder, EmbeddingUnavailable
from app.schemas.retrieval import KnowledgeDocument, RetrievalQuery
from app.services.retrieval import IngestionService, RetrievalService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Create vector extension and independent RAG v1 tables")
    ingest = commands.add_parser("ingest", help="Import a KnowledgeDocument JSON object")
    ingest.add_argument("path", type=Path)
    ingest.add_argument("--text-file", type=Path, help="Read UTF-8 text/Markdown separately")
    search = commands.add_parser("search", help="Search public approved teaching material")
    search.add_argument("query")
    delete = commands.add_parser("delete", help="Delete document and its chunks")
    delete.add_argument("document_id")
    args = parser.parse_args()
    settings = Settings()
    url = settings.database_url.get_secret_value()
    if not url:
        parser.exit(1, "Set DATABASE_URL first.\n")
    engine = database_engine(url)
    try:
        repo = PostgresKnowledgeRepository(engine)
        embedder = CompatibleEmbedder(settings)
        if args.command == "init":
            initialize_knowledge_schema(engine)
            print("RAG schema ready (version 1).")
        elif args.command == "ingest":
            payload = json.loads(args.path.read_text(encoding="utf-8"))
            if args.text_file:
                payload["text"] = args.text_file.read_text(encoding="utf-8")
            document = KnowledgeDocument.model_validate(payload)
            ids = IngestionService(repo, embedder).ingest(document)
            print(json.dumps({"document_id": document.document_id, "chunk_ids": ids}))
        elif args.command == "delete":
            print(json.dumps({"deleted": repo.delete(args.document_id)}))
        else:
            result = RetrievalService(repo, embedder).search(RetrievalQuery(query=args.query))
            print(result.model_dump_json(indent=2))
    except ValidationError:
        parser.exit(1, "Invalid document/query fields; see the RAG contract.\n")
    except SQLAlchemyError:
        parser.exit(1, "RAG database unavailable; verify pgvector installation and run init.\n")
    except (EmbeddingUnavailable, ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
