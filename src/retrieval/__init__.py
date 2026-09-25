from .embeddings import MiniLMEmbeddings
from .index import LocalEmbeddingIndex, SearchResult
from .qa import AnswerResult, answer_question

_LAZY_EXPORTS = {
    "build_agent": (".agent", "build_agent"),
    "run_agent_question": (".agent", "run_agent_question"),
    "build_llm": (".llm", "build_llm"),
}


def __getattr__(name: str):
    import importlib

    if name in _LAZY_EXPORTS:
        module_path, attribute = _LAZY_EXPORTS[name]
        module = importlib.import_module(module_path, __name__)
        value = getattr(module, attribute)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
