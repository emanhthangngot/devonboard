import re
from pathlib import Path
import subprocess

def format_inline(text):
    # Bold format **text**
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # Inline code `text`
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    return text

def markdown_to_html(md_text):
    lines = md_text.split('\n')
    html_lines = []
    in_list = False
    in_quote = False
    
    for line in lines:
        stripped = line.strip()
        
        # Blockquote handling
        if stripped.startswith('>'):
            if not in_quote:
                html_lines.append('<blockquote>')
                in_quote = True
            content = stripped[1:].strip()
            html_lines.append(format_inline(content))
            continue
        else:
            if in_quote:
                html_lines.append('</blockquote>')
                in_quote = False
        
        # List handling
        if stripped.startswith('*') or stripped.startswith('-'):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            content = stripped[1:].strip()
            html_lines.append(f'<li>{format_inline(content)}</li>')
            continue
        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
        
        if not stripped:
            continue
            
        # Headers
        if stripped.startswith('### '):
            html_lines.append(f'<h3>{format_inline(stripped[4:])}</h3>')
        elif stripped.startswith('## '):
            html_lines.append(f'<h2>{format_inline(stripped[3:])}</h2>')
        elif stripped.startswith('# '):
            html_lines.append(f'<h1>{format_inline(stripped[2:])}</h1>')
        elif stripped == '---':
            html_lines.append('<hr>')
        else:
            html_lines.append(f'<p>{format_inline(stripped)}</p>')
            
    # Cleanup trailing tags
    if in_quote:
        html_lines.append('</blockquote>')
    if in_list:
        html_lines.append('</ul>')
        
    return '\n'.join(html_lines)

def main():
    root = Path(__file__).parent.parent
    docs_dir = root / "docs"
    
    # Read files
    judges_qa_path = docs_dir / "judges_qa.md"
    tech_qa_path = docs_dir / "technical_qa.md"
    
    content = ""
    if judges_qa_path.exists():
        content += judges_qa_path.read_text(encoding="utf-8") + "\n\n"
    if tech_qa_path.exists():
        content += tech_qa_path.read_text(encoding="utf-8") + "\n\n"
        
    if not content.strip():
        print("Error: No content found in Q&A files.")
        return
        
    # Convert markdown body
    body_html = markdown_to_html(content)
    
    # HTML template with print-friendly CSS style
    html_document = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>DevOnboard - Q&A Reference Guide</title>
    <style>
        body {{
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            color: #333333;
            line-height: 1.6;
            margin: 40px;
            font-size: 14px;
        }}
        h1 {{
            font-size: 24px;
            color: #1a1a1a;
            border-bottom: 2px solid #eaeaea;
            padding-bottom: 8px;
            margin-top: 30px;
            page-break-before: always;
        }}
        h1:first-of-type {{
            page-break-before: avoid;
        }}
        h2 {{
            font-size: 18px;
            color: #2c3e50;
            margin-top: 25px;
            border-bottom: 1px solid #eaeaea;
            padding-bottom: 5px;
            page-break-before: always;
        }}
        h2:first-of-type {{
            page-break-before: avoid;
        }}
        h3 {{
            font-size: 14px;
            color: #2980b9;
            margin-top: 15px;
        }}
        blockquote {{
            border-left: 4px solid #3498db;
            background-color: #f8f9fa;
            padding: 8px 12px;
            margin: 8px 0 16px 0;
            font-style: italic;
            color: #555;
            border-radius: 4px;
        }}
        code {{
            background-color: #f1f1f1;
            padding: 2px 4px;
            font-family: Courier, monospace;
            font-size: 11px;
            border-radius: 3px;
        }}
        strong {{
            color: #2c3e50;
        }}
        hr {{
            border: 0;
            border-top: 1px solid #eaeaea;
            margin: 20px 0;
        }}
        p {{
            margin-bottom: 12px;
        }}
        ul {{
            margin-bottom: 16px;
            padding-left: 20px;
        }}
        li {{
            margin-bottom: 4px;
        }}
    </style>
</head>
<body>
    {body_html}
</body>
</html>
"""
    
    html_output_path = docs_dir / "qa_combined.html"
    html_output_path.write_text(html_document, encoding="utf-8")
    
    print(f"Generated intermediate HTML at: {html_output_path}")
    
    # Run LibreOffice to convert HTML to PDF
    try:
        subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", str(docs_dir), str(html_output_path)],
            check=True,
            stdout=subprocess.DEVNULL
        )
        print("Successfully generated docs/qa_combined.pdf")
    except Exception as e:
        print(f"Error running LibreOffice conversion: {e}")
    finally:
        # Cleanup HTML file
        if html_output_path.exists():
            html_output_path.unlink()

if __name__ == "__main__":
    main()
