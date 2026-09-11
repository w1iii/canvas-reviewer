import markdown
from weasyprint import HTML as WeasyHTML


def generate_markdown(course_name: str, modules: list[dict]) -> str:
    lines = [f"# {course_name} — Study Reviewer\n", "---\n"]

    for mod in modules:
        lines.append(f"## Module: {mod['name']}\n")

        if mod.get("key_concepts"):
            lines.append("### Key Concepts\n")
            for c in mod["key_concepts"]:
                lines.append(f"- {c}")
            lines.append("")

        if mod.get("summary"):
            lines.append(f"### Summary\n{mod['summary']}\n")

        if mod.get("key_points"):
            lines.append("### Key Points\n")
            for p in mod["key_points"]:
                lines.append(f"- {p}")
            lines.append("")

        if mod.get("definitions"):
            lines.append("### Definitions\n")
            for term, defn in mod["definitions"].items():
                lines.append(f"- **{term}:** {defn}")
            lines.append("")

        if mod.get("key_takeaways"):
            lines.append("### Key Takeaways\n")
            for t in mod["key_takeaways"]:
                lines.append(f"- {t}")
            lines.append("")

        if mod.get("resources"):
            lines.append("### Resources\n")
            for r in mod["resources"]:
                lines.append(f"- [{r['title']}]({r['url']})")
            lines.append("")

        lines.append("---\n")

    return "\n".join(lines)


def generate_html(markdown_content: str) -> str:
    body = markdown.markdown(
        markdown_content, extensions=["tables", "fenced_code"]
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Study Reviewer</title>
<style>
    body {{ font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
    h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
    h2 {{ color: #2980b9; }}
    h3 {{ color: #27ae60; }}
</style>
</head>
<body>
{body}
</body>
</html>"""


def generate_pdf(html_content: str, output_path: str):
    WeasyHTML(string=html_content).write_pdf(output_path)
