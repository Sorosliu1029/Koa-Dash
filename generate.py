#!/usr/bin/python

import sqlite3, requests, zipfile, io, os, re
import jinja2
import markdown
from bs4 import BeautifulSoup

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
ANY = re.compile(r".*")


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
    assert os.path.exists(md_path), md_path
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


def extract_link(cursor, html_path):
    html_path = os.path.join(KOA_RESOURCES_PATH, "Documents", html_path)
    assert os.path.exists(html_path), html_path
    basename = os.path.basename(html_path)
    with open(html_path, "rt", encoding="utf-8") as f:
        content = f.read()
        soup = BeautifulSoup(content, "lxml")
        for tag in soup.find_all("a", {"href": ANY}, class_="toclink"):
            name = tag.text.strip()
            toclink = tag.attrs["href"].strip()
            if "(" in name:
                type = "Method"
            elif "." in name:
                type = "Attribute"
            else:
                type = "Guide"
            cursor.execute(
                "INSERT OR IGNORE INTO searchIndex(name, type, path) VALUES (?,?,?)",
                (name, type, basename + toclink),
            )
            print("name: {}, type: {}, link: {}".format(name, type, basename + toclink))


def main():
    try:
        conn, cur = setup_db()

        if not os.path.exists(os.path.join(KOA_RESOURCES_PATH, "Documents/raw_md/api")):
            documents = get_document()
            for document in documents:
                render2html(document)

        api_files = set()
        for _, _, filenames in os.walk(
            os.path.join(KOA_RESOURCES_PATH, "Documents/raw_md/api")
        ):
            for file in filter(lambda f: f.endswith(".md"), filenames):
                html_file = file.replace(".md", ".html")
                api_files.add(html_file)
                extract_link(cur, html_file)

        html_files = set()
        for _, _, filenames in os.walk(os.path.join(KOA_RESOURCES_PATH, "Documents")):
            html_files.update(filter(lambda f: f.endswith(".html"), filenames))

        no_api_files = html_files - api_files
        for file in no_api_files:
            file_name = file.replace(".html", "")
            cur.execute(
                "INSERT OR IGNORE INTO searchIndex(name, type, path) VALUES (?,?,?)",
                (file_name, "Guide", file),
            )

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
