from uuid import UUID


def format_uuid(id_: str | UUID, with_curly=False) -> str:
    if isinstance(id_, str):
        template = str(UUID(id_))
    elif isinstance(id_, UUID):
        template = str(id_)
    else:
        raise RuntimeError("Unsupported ID data type")
    if with_curly:
        return '{' + template + '}'
    return template
