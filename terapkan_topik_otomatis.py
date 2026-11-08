import os, re, math, random
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(host="localhost", port=5432, dbname="jdih", user="postgres", password=os.getenv("DB_PASSWORD"), cursor_factory=RealDictCursor)
cur = conn.cursor()

cur.execute("SELECT id, judul FROM documents")
docs = cur.fetchall()
corpus = [(r["id"], (r["judul"] or "").lower()) for r in docs]

STOP = {"banyumas","tahun","nomor","tentang","peraturan","bupati","kabupaten","daerah","atas","perubahan","kedua","ketiga","keempat","pertama","dan","di","yang","untuk","dalam","pada","dengan","kepada","lingkungan","pemerintah"}

def bersihkan(j):
    j = re.sub(r'[^\w\s]', ' ', j)
    j = re.sub(r'\d+', ' ', j)
    return ' '.join(j.split())

def tokens(t):
    w = t.split()
    toks = list(w)
    for i in range(len(w)-1):
        toks.append(w[i]+" "+w[i+1])
    return [x for x in toks if x not in STOP and all(p not in STOP for p in x.split())]

cleaned = [(did, bersihkan(j)) for did, j in corpus]
df = {}
for did, c in cleaned:
    for t in set(tokens(c)):
        df[t] = df.get(t,0)+1
N = len(cleaned)
vocab = [t for t,c in df.items() if c >= 2]
vindex = {t:i for i,t in enumerate(vocab)}

def vec(c):
    toks = tokens(c)
    tf = {}
    for t in toks:
        tf[t] = tf.get(t,0)+1
    v = [0.0]*len(vocab)
    for t, cnt in tf.items():
        if t in vindex:
            tfval = 1+math.log(cnt)
            idf = math.log((1+N)/(1+df[t]))+1
            v[vindex[t]] = tfval*idf
    norm = math.sqrt(sum(x*x for x in v)) or 1.0
    return [x/norm for x in v]

X = [vec(c) for _, c in cleaned]
random.seed(42)
k = 10
centroids = [list(X[i]) for i in random.sample(range(len(X)), k)]
labels = [0]*len(X)
for _ in range(50):
    new = []
    for x in X:
        dists = [sum((x[i]-c[i])**2 for i in range(len(x))) for c in centroids]
        new.append(min(range(k), key=lambda i: dists[i]))
    if new == labels:
        break
    labels = new
    for c in range(k):
        pts = [X[i] for i in range(len(X)) if labels[i]==c]
        if pts:
            centroids[c] = [sum(p[i] for p in pts)/len(pts) for i in range(len(X[0]))]

cluster_labels = {}
for c in range(k):
    ranked = sorted(range(len(vocab)), key=lambda i: -centroids[c][i])
    chosen = []
    used_words = set()
    for i in ranked:
        t = vocab[i]
        words = t.split()
        if any(w in used_words for w in words):
            continue
        chosen.append(t)
        used_words.update(words)
        if len(chosen) >= 3:
            break
    cluster_labels[c] = " ".join(chosen)

doc_cluster = {cleaned[i][0]: labels[i] for i in range(len(cleaned))}

try:
    cur.execute("BEGIN")
    cur.execute("DELETE FROM document_topics")
    cur.execute("DELETE FROM topics")
    topic_ids = {}
    for c in range(k):
        cur.execute("INSERT INTO topics (label_topik, top_keywords) VALUES (%s, %s) RETURNING id",
                    (cluster_labels[c], ", ".join(cluster_labels[c].split())))
        topic_ids[c] = cur.fetchone()["id"]
    for did, cl in doc_cluster.items():
        cur.execute("INSERT INTO document_topics (document_id, topic_id) VALUES (%s, %s)", (did, topic_ids[cl]))
    conn.commit()
    print("OK, clusters:", k, "docs:", len(docs))
    for c in range(k):
        print(cluster_labels[c])
except Exception as e:
    conn.rollback()
    print("FAILED:", e)
finally:
    cur.close(); conn.close()