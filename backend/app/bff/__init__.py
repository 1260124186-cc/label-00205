def create_bff_router():
    from app.bff.schema import create_bff_router
    return create_bff_router()


__all__ = ["create_bff_router"]
