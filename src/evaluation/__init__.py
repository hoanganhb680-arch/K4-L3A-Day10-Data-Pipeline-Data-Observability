from .testset import TestSet, build_test_set, load_or_create_test_set

_LAZY_EXPORTS = {
    "EvaluationBundle": (".metrics", "EvaluationBundle"),
    "JudgeVerdict": (".metrics", "JudgeVerdict"),
    "evaluate_pipeline": (".metrics", "evaluate_pipeline"),
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
