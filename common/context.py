from contextvars import ContextVar

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")
user_id_context: ContextVar[str] = ContextVar("user_id", default="-")
