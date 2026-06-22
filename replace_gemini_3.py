import os
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

# Kernel py files
mass_replace("app/packages/kernel/**/*.py", "gemini_ms", "llm_ms")
mass_replace("app/packages/kernel/**/*.py", "Gemini", "Azure OpenAI")
mass_replace("app/packages/kernel/**/*.py", "gemini-3.1-pro-preview", "gpt-5.4")
mass_replace("app/packages/kernel/**/*.py", "gemini-3.1-flash-lite", "gpt-5.4")

mass_replace("docs/*.md", "gemini_ms", "llm_ms")

# Just to be safe, replace Gemini with Azure OpenAI in a few remaining ones
mass_replace("docs/cr-007-close-the-loop.md", "Gemini", "Azure OpenAI")
mass_replace("docs/cr-007-close-the-loop.md", "gemini-3.1-pro", "gpt-5.4")
mass_replace("docs/cr-007-close-the-loop.md", "gemini-3.1-flash-lite", "gpt-5.4")
mass_replace("docs/cr-007-close-the-loop.md", "gemini_ms", "llm_ms")

mass_replace("docs/index.md", "Gemini", "Azure OpenAI")

