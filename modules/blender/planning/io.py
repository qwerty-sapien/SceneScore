"""Bounded JSON/YAML input and new-directory, paired validation output."""
import json
from pathlib import Path


def load_plan(path):
    path = Path(path)
    if path.stat().st_size > 1_000_000:
        raise ValueError('plan exceeds 1 MB input limit')
    text = path.read_text()
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if not isinstance(key, str) or key in result:
                raise ValueError('duplicate or non-string mapping key')
            result[key] = value
        return result
    if path.suffix.lower() in {'.yaml', '.yml'}:
        import yaml
        if any(isinstance(token, yaml.tokens.AliasToken) for token in yaml.scan(text)):
            raise ValueError('YAML aliases are not supported in scene plans')
        class UniqueLoader(yaml.SafeLoader):
            pass
        def mapping(loader, node):
            return unique((loader.construct_object(k, deep=True), loader.construct_object(v, deep=True)) for k, v in node.value)
        UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
        try:
            result = yaml.load(text, Loader=UniqueLoader)
        except yaml.YAMLError as error:
            raise ValueError(str(error)) from error
    else:
        result = json.loads(text, object_pairs_hook=unique)
    # Catch YAML non-JSON types and NaN/Infinity before schema/geometry work.
    json.dumps(result, allow_nan=False)
    return result


def write_outputs(out, report, resolved):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    for name, value in [('plan_validation.json', report), ('resolved_constraints.json', resolved)]:
        (out/name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')
