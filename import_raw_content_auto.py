import os, io, fitz, psycopg2, requests
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(host="localhost", port=5432, dbname="jdih", user="postgres", password=os.getenv("DB_PASSWORD"), cursor_factory=RealDictCursor)
cur = conn.cursor()
cur.execute("SELECT id, url_pdf FROM documents WHERE konten_text_asli IS NULL AND url_pdf IS NOT NULL")
rows = cur.fetchall()

for r in rows:
    did = r["id"]
    url = r["url_pdf"]
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        doc = fitz.open(stream=io.BytesIO(resp.content), filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        cur.execute("UPDATE documents SET konten_text_asli = %s WHERE id = %s", (text, did))
        conn.commit()
        print("OK", did, len(text))
    except Exception as e:
        print("FAIL", did, e)

cur.close(); conn.close()