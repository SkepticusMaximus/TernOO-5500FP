#!/usr/bin/env python3
"""Build a frequency-ranked, PIM-boosted word list for Tmail's predictive text (g70).

Per the captain's researched plan (17-11-2026): download Peter Norvig's count_1w.txt
(Google Web Trillion Word Corpus unigrams), intersect with the LOCAL clean dictionary
(/usr/share/dict + hunspell en_AU/en_US — so we skip the second ~4MB download), boost
email/PIM/calendar vocabulary, log-normalize popularity to 0..1, and write a compact TSV
`word<TAB>popularity<TAB>is_pim`. Re-run any time a better frequency corpus turns up.

Output: FlowCode/pim_words.tsv  (loaded once into RAM by mailbox_qt)
"""
import urllib.request
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "FlowCode", "pim_words.tsv")
NORVIG = "https://norvig.com/ngrams/count_1w.txt"
MAX_WORDS = 50000
PIM_BOOST = 3.5
PIM_BASELINE = 500000

# High-priority email / calendar / task vocabulary to boost (incl. Commonwealth spellings
# and AU timezones), so completions lead with "schedule"/"attached"/"tomorrow", not "science".
PIM_VOCAB = {
    "attached", "attachment", "attachments", "forward", "forwarded", "reply", "replied",
    "regards", "sincerely", "hello", "hi", "thanks", "thank", "appreciate", "update",
    "updates", "updated", "follow", "following", "clarify", "confirm", "confirmation",
    "confirmed", "request", "requested", "urgent", "asap", "fyi", "cc", "bcc", "recipient",
    "recipients", "subject", "draft", "send", "sent", "inbox", "archive", "spam",
    "unsubscribe", "thread", "chain", "correspondence", "memo", "message", "details", "info",
    "information", "summary", "overview", "feedback", "review", "reviewed", "approve",
    "approved", "approval", "enquire", "enquiry", "please",
    "schedule", "scheduled", "reschedule", "calendar", "meeting", "invite", "invitation",
    "appointment", "availability", "available", "busy", "conflict", "agenda", "minutes",
    "attendees", "host", "organizer", "organiser", "zoom", "teams", "call", "dial", "link",
    "location", "room", "conference", "today", "tomorrow", "yesterday", "monday", "tuesday",
    "wednesday", "thursday", "friday", "saturday", "sunday", "january", "february", "march",
    "april", "may", "june", "july", "august", "september", "october", "november", "december",
    "morning", "afternoon", "evening", "noon", "midnight", "week", "weekly", "month",
    "monthly", "quarter", "quarterly", "annual", "deadline", "due", "overdue", "reminder",
    "remind", "snooze", "timezone", "aest", "acdt", "acst", "awst", "utc", "gmt", "est", "pst",
    "task", "tasks", "todo", "checklist", "priority", "high", "low", "medium", "status",
    "pending", "completed", "progress", "blocked", "milestone", "project", "folder", "tag",
    "label", "note", "notes", "journal", "contact", "contacts", "address", "phone", "mobile",
    "email", "profile", "company", "department", "title", "colleague", "client", "vendor",
    "manager", "team", "captain", "crew",
}


def local_dict():
    words = set()
    try:
        words |= {l.strip().lower() for l in open("/usr/share/dict/words", encoding="utf-8", errors="ignore")}
    except Exception:
        pass
    for p in ("/usr/share/hunspell/en_AU.dic", "/usr/share/hunspell/en_US.dic"):
        try:
            f = open(p, encoding="utf-8", errors="ignore")
            next(f, None)
            words |= {l.split("/")[0].strip().lower() for l in f}
        except Exception:
            pass
    return words


def main():
    clean = local_dict()
    clean |= PIM_VOCAB
    clean.update({"a", "i"})
    print("local clean dictionary: %d words" % len(clean))

    print("downloading Norvig count_1w.txt ...")
    req = urllib.request.Request(NORVIG, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=90).read().decode("utf-8", "ignore")
    counts = {}
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        w, cs = parts[0].strip().lower(), parts[1].strip()
        if w in clean and w.isalpha() and cs.isdigit():
            counts[w] = int(cs)
    print("clean frequency words: %d" % len(counts))

    for w in PIM_VOCAB:                                      # guarantee + boost PIM vocab
        counts[w] = int(max(counts.get(w, PIM_BASELINE), PIM_BASELINE) * PIM_BOOST)

    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:MAX_WORDS]
    max_log = math.log10(ranked[0][1])
    min_log = math.log10(ranked[-1][1])
    with open(OUT, "w", encoding="utf-8") as f:
        for w, c in ranked:
            pop = round((math.log10(c) - min_log) / (max_log - min_log), 4)
            f.write("%s\t%s\t%d\n" % (w, pop, 1 if w in PIM_VOCAB else 0))
    print("wrote %d ranked words -> %s" % (len(ranked), OUT))


if __name__ == "__main__":
    main()
