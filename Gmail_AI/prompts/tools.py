from pathlib import Path
from typing import Union

BASE_DIR = Path(__file__).resolve().parent
def load_prompt(prompt_path: Union[str, Path]):
    return (BASE_DIR / prompt_path).read_text(encoding="utf-8")
