from typing import Dict, Any, Optional

import strawberry
from strawberry.fastapi import GraphQLRouter
from fastapi import Request
from loguru import logger

from app.bff.resolvers import Query


schema = strawberry.Schema(query=Query)


def get_context(request: Request) -> Dict[str, Any]:
    return {"request": request}


def create_bff_router() -> GraphQLRouter:
    router = GraphQLRouter(schema, context_getter=get_context, path="/")
    return router
