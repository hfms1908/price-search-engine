"""Persistência atômica dos artefatos do índice."""
import json
import os
import tempfile
from pathlib import Path

def save_json(path: Path, value, *, sort_keys: bool = True) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    
    descriptor, temp = tempfile.mkstemp(prefix='.index-', suffix='.tmp', dir=path.parent)
    
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=sort_keys)
        
        os.replace(temp, path)
    finally:
        if os.path.exists(temp): os.unlink(temp)
    
    return path.stat().st_size
