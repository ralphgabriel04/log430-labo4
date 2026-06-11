"""Convertit RAPPORT.md en RAPPORT.pdf (markdown -> HTML -> PDF via xhtml2pdf)."""
import os, markdown
from xhtml2pdf import pisa

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(ROOT, "RAPPORT.md")
PDF = os.path.join(ROOT, "RAPPORT.pdf")

with open(MD, encoding="utf-8") as f:
    text = f.read()

html_body = markdown.markdown(
    text, extensions=["tables", "fenced_code", "toc"]
)

CSS = """
@page { size: A4; margin: 1.6cm 1.4cm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 10pt; color: #1a1a1a; line-height: 1.45; }
h1 { font-size: 19pt; color: #1a3a5c; border-bottom: 2px solid #1a3a5c; padding-bottom: 4px; }
h2 { font-size: 14pt; color: #1a3a5c; margin-top: 16px; border-bottom: 1px solid #ccc; padding-bottom: 2px; }
h3 { font-size: 11.5pt; color: #2c3e50; margin-top: 12px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 8.5pt; }
th { background-color: #1a3a5c; color: #ffffff; padding: 4px 6px; text-align: left; }
td { border: 1px solid #bbb; padding: 3px 6px; }
tr:nth-child(even) td { background-color: #f2f5f8; }
code { font-family: Courier, monospace; font-size: 8.5pt; background-color: #f0f0f0; }
pre { background-color: #f5f5f5; border: 1px solid #ddd; padding: 6px; font-size: 8pt;
      font-family: Courier, monospace; }
img { width: 17cm; }
blockquote { border-left: 3px solid #1a3a5c; margin-left: 0; padding-left: 10px; color: #444; }
"""

html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>{CSS}</style></head><body>{html_body}</body></html>"""

def link_callback(uri, rel):
    # Resolve relative image paths against project root
    path = os.path.join(ROOT, uri.replace("/", os.sep))
    return path if os.path.isfile(path) else uri

with open(PDF, "wb") as out:
    status = pisa.CreatePDF(html, dest=out, link_callback=link_callback, encoding="utf-8")

print("PDF error" if status.err else f"PDF OK -> {PDF}")
print("size:", round(os.path.getsize(PDF)/1024, 1), "KB")
