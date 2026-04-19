import streamlit as st
import re
import random

# ─── Sayfa ayarı ─────────────────────────────────────────────────────────────

st.set_page_config(page_title="Anki Test", page_icon="📚", layout="centered")

st.markdown("""
<style>
  .stApp { max-width: 720px; margin: auto; }
  div[data-testid="stVerticalBlock"] { gap: 0.4rem; }
  .opt-btn { width: 100%; text-align: left; }
</style>
""", unsafe_allow_html=True)

# ─── Ayrıştırıcı ─────────────────────────────────────────────────────────────

def parse_questions(raw):
    questions = []
    lines = raw.strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        m = re.match(r"^(\d+)[.)]\s+(.+)", line)
        if not m:
            i += 1
            continue
        q_text = m.group(2).strip()
        opt_line = ""
        j = i + 1
        while j < len(lines):
            nl = lines[j].strip()
            if not nl or re.match(r"^\d+[.)]\s", nl):
                break
            if re.search(r"[A-Ea-e][.)]\s", nl):
                opt_line += " " + nl
            j += 1
        if not opt_line and re.search(r"[A-E]\)\s", q_text, re.IGNORECASE):
            opt_line = q_text
            q_text = re.sub(r"\s*[A-E]\).*", "", q_text, flags=re.IGNORECASE).strip()
        matches = re.findall(r"([A-Ea-e])[.)]\s*(.+?)(?=[A-Ea-e][.)]|$)", opt_line)
        opts = [(k.upper(), v.strip()) for k, v in matches if v.strip()]
        if q_text and len(opts) >= 2:
            correct_text = next((v for k, v in opts if k == "A"), None)
            if correct_text:
                questions.append({
                    "text": q_text,
                    "all_texts": [v for _, v in opts],
                    "correct_text": correct_text,
                })
        i = j
    return questions

def shuffle_options(q):
    keys = ["A", "B", "C", "D", "E"]
    texts = q["all_texts"][:]
    random.shuffle(texts)
    options = list(zip(keys[:len(texts)], texts))
    correct_key = next(k for k, v in options if v == q["correct_text"])
    return options, correct_key

# ─── Session state başlat ─────────────────────────────────────────────────────

def init_state():
    defaults = {
        "screen": "input",       # input | test | done
        "deck": [],
        "queue": [],
        "current_idx": 0,
        "current_options": [],
        "current_correct_key": None,
        "answered": False,
        "chosen_key": None,
        "stats": {"correct": 0, "wrong": 0},
        "log": [],
        "raw_text": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()
s = st.session_state

# ─── Yardımcılar ─────────────────────────────────────────────────────────────

def start_test():
    deck = parse_questions(s.raw_text)
    if not deck:
        st.error("Soru bulunamadı. A) B) C) D) E) formatını kullan.")
        return
    s.deck = deck
    _restart_queue()

def _restart_queue():
    s.queue = list(range(len(s.deck)))
    random.shuffle(s.queue)
    s.stats = {"correct": 0, "wrong": 0}
    s.log = []
    s.current_idx = s.queue.pop(0)
    opts, ck = shuffle_options(s.deck[s.current_idx])
    s.current_options = opts
    s.current_correct_key = ck
    s.answered = False
    s.chosen_key = None
    s.screen = "test"

def answer(key):
    s.answered = True
    s.chosen_key = key

def do_action(action):
    q = s.deck[s.current_idx]
    is_correct = s.chosen_key == s.current_correct_key

    if action == "again":
        s.stats["wrong"] += 1
        insert_pos = min(3, len(s.queue))
        s.queue.insert(insert_pos, s.current_idx)
    elif action == "hard":
        s.stats["wrong"] += 1
        insert_pos = min(max(len(s.queue) // 2, 1), len(s.queue))
        s.queue.insert(insert_pos, s.current_idx)
    elif action in ("good", "easy"):
        s.stats["correct"] += 1
    elif action == "skip":
        s.stats["wrong"] += 1

    s.log.append({
        "q": q,
        "correct": is_correct,
        "chosen_text": next(v for k, v in s.current_options if k == s.chosen_key),
        "correct_text": q["correct_text"],
    })

    if not s.queue:
        s.screen = "done"
    else:
        s.current_idx = s.queue.pop(0)
        opts, ck = shuffle_options(s.deck[s.current_idx])
        s.current_options = opts
        s.current_correct_key = ck
        s.answered = False
        s.chosen_key = None

# ─── Ekranlar ─────────────────────────────────────────────────────────────────

# ── Giriş ekranı ──────────────────────────────────────────────────────────────
if s.screen == "input":
    st.title("📚 Anki Test")
    st.caption("5 şıklı format (A–E). A şıkkı doğru — karşına çıkarken şıklar rastgele karışır.")

    s.raw_text = st.text_area(
        "Soruları buraya yapıştır",
        value=s.raw_text or (
            "1. Türkiye'nin başkenti neresidir?\n"
            "A) Ankara  B) İstanbul  C) İzmir  D) Bursa  E) Trabzon\n\n"
            "2. Güneş sistemindeki en büyük gezegen?\n"
            "A) Jüpiter  B) Satürn  C) Mars  D) Venüs  E) Neptün"
        ),
        height=240,
        label_visibility="collapsed"
    )

    if st.button("Testi başlat →", type="primary", use_container_width=True):
        start_test()
        st.rerun()

# ── Test ekranı ───────────────────────────────────────────────────────────────
elif s.screen == "test":
    total = len(s.deck)
    done = s.stats["correct"] + s.stats["wrong"]

    # Üst bilgi
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    with c1:
        st.progress(done / total if total else 0)
    with c2:
        st.caption(f"🟣 {len([i for i in s.queue if True])} kalan")
    with c3:
        st.caption(f"✅ {s.stats['correct']} doğru")
    with c4:
        st.caption(f"❌ {s.stats['wrong']} yanlış")

    st.markdown(f"**{done + 1} / {total}**")
    st.markdown(f"### {s.deck[s.current_idx]['text']}")
    st.markdown("---")

    # Şıklar
    if not s.answered:
        for key, text in s.current_options:
            if st.button(f"{key})  {text}", key=f"opt_{key}", use_container_width=True):
                answer(key)
                st.rerun()
    else:
        correct_key = s.current_correct_key
        chosen_key  = s.chosen_key
        is_correct  = chosen_key == correct_key
        correct_text = s.deck[s.current_idx]["correct_text"]
        chosen_text  = next(v for k, v in s.current_options if k == chosen_key)

        for key, text in s.current_options:
            if key == correct_key:
                st.success(f"**{key})  {text}**  ✓")
            elif key == chosen_key and not is_correct:
                st.error(f"{key})  {text}  ✗")
            else:
                st.button(f"{key})  {text}", key=f"opt_{key}", disabled=True, use_container_width=True)

        st.markdown("---")

        if is_correct:
            st.success("Doğru!")
        else:
            st.error(f"Yanlış. Doğru cevap: **{correct_text}**")

        st.markdown("**Ne yapmak istiyorsun?**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("🔴 Tekrar\n<1dk", use_container_width=True):
                do_action("again")
                st.rerun()
        with col2:
            if st.button("🟠 Zor\nSonra", use_container_width=True):
                do_action("hard")
                st.rerun()
        with col3:
            if is_correct:
                if st.button("🟢 İyi\nGeçti", use_container_width=True):
                    do_action("good")
                    st.rerun()
            else:
                if st.button("⬜ Geç\nAtla", use_container_width=True):
                    do_action("skip")
                    st.rerun()
        with col4:
            if is_correct:
                if st.button("🔵 Kolay\nTamam", use_container_width=True):
                    do_action("easy")
                    st.rerun()

# ── Sonuç ekranı ──────────────────────────────────────────────────────────────
elif s.screen == "done":
    total = max(len(s.log), 1)
    c = sum(1 for l in s.log if l["correct"])
    w = sum(1 for l in s.log if not l["correct"])
    pct = round((c / total) * 100)

    st.title("Tur tamamlandı")
    col1, col2, col3 = st.columns(3)
    col1.metric("Doğru", c)
    col2.metric("Yanlış", w)
    col3.metric("Başarı", f"{pct}%")

    st.markdown("---")
    st.markdown("### Gözden geçir")
    for i, l in enumerate(s.log):
        icon = "✅" if l["correct"] else "❌"
        with st.expander(f"{icon} {i+1}. {l['q']['text']}"):
            if l["correct"]:
                st.success(f"Doğru: {l['correct_text']}")
            else:
                st.error(f"Senin cevabın: {l['chosen_text']}")
                st.success(f"Doğru cevap: {l['correct_text']}")

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Tekrar çöz", use_container_width=True):
            _restart_queue()
            st.rerun()
    with col_b:
        if st.button("Yeni test", type="primary", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
