import os

files_to_update = {
    "reference/PUP-ATLAN_TECHNICAL ROADMAP TEMPLATE _ AAIH 2026.md": [
        ("Gemini CLI", "Azure OpenAI CLI"),
        ("Gemini API", "Azure OpenAI API"),
    ],
    "MATRIX_Iloilo_Data_Sources.md": [
        ("Gemini 3.1 Flash-Lite", "Azure OpenAI GPT-5.4"),
    ],
    "MATRIX.md": [
        ("Gemini 2.0", "Azure OpenAI 2.0"),
        ("Gemini 1.5", "Azure OpenAI 1.5"),
        ("gemini-models/gemini-3-1-pro/", "openai/azure-openai/"),
    ],
    "data/INVENTORY.md": [
        ("| GEMINI |", "| LLM |"),
    ],
    "AGENTS.md": [
        ("Gemini 3.1 Pro", "Azure OpenAI GPT-5.4"),
        ("Gemini 3.1 Flash-Lite", "Azure OpenAI GPT-5.4"),
        ("Gemini 1.5 or 2.0", "Azure OpenAI 1.5 or 2.0"),
    ],
    "app/AGENTS.md": [
        ("Gemini 1.5/2.0/3.1", "Azure OpenAI"),
    ],
    "app/README.md": [
        ("Gemini", "Azure OpenAI"),
    ],
    "app/packages/kernel/pyproject.toml": [
        ("Gemini 1.5/2.0", "Azure OpenAI 1.5/2.0"),
    ],
    "app/packages/kernel/matrix_kernel/synthesis.py": [
        ("Gemini 3.1 Pro", "Azure OpenAI GPT-5.4"),
        ("Gemini unavailable", "Azure OpenAI unavailable"),
    ],
    "app/packages/kernel/matrix_kernel/scenario.py": [
        ("Gemini orchestrator", "Azure OpenAI orchestrator"),
    ],
    "app/packages/kernel/matrix_kernel/personas.py": [
        ("Gemini 3.1 Flash-Lite", "Azure OpenAI GPT-5.4"),
    ],
    "app/packages/kernel/matrix_kernel/orchestrator.py": [
        ("Gemini", "Azure OpenAI"),
    ],
}

def replace_in_file(filepath, replacements):
    full_path = os.path.join(r"d:\PROJECTS\matrix", filepath)
    if not os.path.exists(full_path):
        print(f"File not found: {full_path}")
        return
    
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    original = content
    for old, new in replacements:
        content = content.replace(old, new)
        
    if content != original:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {filepath}")
    else:
        print(f"No changes needed in {filepath}")

for filepath, replacements in files_to_update.items():
    replace_in_file(filepath, replacements)

# Now, we also want to do a mass replace for `gemini_ms` to `llm_ms` in the ts/tsx and py files.
import glob
def mass_replace(pattern, old_str, new_str):
    for filepath in glob.glob(os.path.join(r"d:\PROJECTS\matrix", pattern), recursive=True):
        if not os.path.isfile(filepath):
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        if old_str in content:
            content = content.replace(old_str, new_str)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Replaced {old_str} -> {new_str} in {filepath}")

mass_replace("app/apps/web/src/**/*.ts", "gemini_ms", "llm_ms")
mass_replace("app/apps/web/src/**/*.tsx", "gemini_ms", "llm_ms")
mass_replace("app/apps/web/tests/**/*.ts", "gemini_ms", "llm_ms")
mass_replace("app/apps/web/tests/**/*.tsx", "gemini_ms", "llm_ms")
mass_replace("app/apps/api/**/*.py", "gemini_ms", "llm_ms")

# In web ui test files, the text "Gemini" is also asserted:
mass_replace("app/apps/web/tests/unit/ProgressiveRunUi.test.tsx", "Gemini", "Azure OpenAI")
mass_replace("app/apps/web/src/components/RunProgress.tsx", "Gemini", "Azure OpenAI")

# Fix tests
mass_replace("app/packages/kernel/tests/test_llm.py", "gemini-3.1-pro", "gpt-5.4")
mass_replace("app/packages/kernel/tests/test_llm.py", "Gemini", "Azure OpenAI")
mass_replace("app/packages/kernel/tests/test_orchestrator_parse.py", "Gemini", "Azure OpenAI")

