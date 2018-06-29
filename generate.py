#!/usr/bin/python

import sqlite3, requests, zipfile, io, os
import jinja2
import markdown

KOA_GITHUB_ARCHIVE_URL = "https://github.com/koajs/koa/archive/master.zip"
KOA_RESOURCES_PATH = "koa.docset/Contents/Resources/"
TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <link href="default.css" rel="stylesheet">
    <link href="github.css" rel="stylesheet">
    <link href="http://netdna.bootstrapcdn.com/twitter-bootstrap/2.3.0/css/bootstrap-combined.min.css" rel="stylesheet">
    <style>
        body {
            font-family: sans-serif;
        }
        code, pre {
            font-family: monospace;
        }
        h1 code,
        h2 code,
        h3 code,
        h4 code,
        h5 code,
        h6 code {
            font-size: inherit;
        }
    </style>
</head>
<body>
<div class="container">
{{content}}
</div>
</body>
</html>
"""
MARKDOWN_EXTENSIONS = [
    "markdown.extensions.extra",
    "markdown.extensions.toc",
    "markdown.extensions.codehilite",
    "markdown.extensions.fenced_code",
]
MARKDOWN_EXTENSION_CONFIGS = {"markdown.extensions.toc": {"anchorlink": True}}


def setup_db():
    conn = sqlite3.connect(os.path.join(KOA_RESOURCES_PATH, "docSet.dsidx"))
    cur = conn.cursor()

    try:
        cur.execute("DROP TABLE searchIndex;")
    except:
        pass

    cur.execute(
        "CREATE TABLE searchIndex(id INTEGER PRIMARY KEY, name TEXT, type TEXT, path TEXT);"
    )
    cur.execute("CREATE UNIQUE INDEX anchor ON searchIndex (name, type, path);")

    return conn, cur


def get_document():
    documents = []
    r = requests.get(KOA_GITHUB_ARCHIVE_URL)
    if r.ok:
        z = zipfile.ZipFile(io.BytesIO(r.content))
        infos = z.infolist()
        for info in infos:
            if "docs/" in info.filename and info.filename.endswith(".md"):
                info.filename = info.filename[
                    info.filename.index("docs/") + len("docs/") :
                ]
                extracted_file = z.extract(
                    info, path=os.path.join(KOA_RESOURCES_PATH, "Documents/raw_md/")
                )
                documents.append(extracted_file)
    r.raise_for_status()
    return documents


def render2html(md_path):
    assert os.path.exists(md_path)
    html_path = os.path.join(
        KOA_RESOURCES_PATH,
        "Documents",
        os.path.basename(md_path).replace(".md", ".html"),
    )
    with open(md_path, "rt", encoding="utf-8") as mf, open(
        html_path, "wt", encoding="utf-8"
    ) as hf:
        md_content = mf.read()
        html_content = markdown.markdown(
            md_content,
            extensions=MARKDOWN_EXTENSIONS,
            extension_configs=MARKDOWN_EXTENSION_CONFIGS,
            output_format="html5",
        )
        doc = jinja2.Template(TEMPLATE).render(content=html_content)
        hf.write(doc)


def main():
    try:
        conn, cur = setup_db()

        if not os.path.exists(os.path.join(KOA_RESOURCES_PATH, "Documents/raw_md/api")):
            documents = get_document()
            for document in documents:
                render2html(document)

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
