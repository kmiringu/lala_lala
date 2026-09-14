# RiverSentinel — 10-Minute Presentation Runsheet

**Share this with all 6 of you tonight.** Assign names to the six segments below based on who actually did that part of the work — that's what makes "collaboration" visible, not equal talk-time.

**The one rule for tonight:** if a sentence needs the words *Random Forest, geopandas, CRS, buffer, threshold, precision, recall, Streamlit, confusion matrix* — cut it or translate it. Every one of those is a plain-English sentence away from landing instead of triggering a 🤔. Technical detail lives in your backup slides for Q&A, not in the spoken story.

---

## Segment 1 — The Hook (0:00–1:00) · 1 speaker

Open on people, not data. Something like:

> "In March 2024, heavy rains flooded parts of Nairobi and people living along the rivers lost their homes. Since then, the county has been trying to clear buildings that are too close to the water — but with hundreds of kilometres of river and only so many inspectors, the real question isn't 'is this illegal,' it's **'where do we even start looking?'**"

Land on that question. Don't answer it yet — that's what the rest of the ten minutes is for.

---

## Segment 2 — The Real Problem (1:00–2:30) · 1 speaker

This is where you tell them the buffer-distance story — it's genuinely more interesting than it sounds, because it's real and current:

> "Here's what makes this hard: the rule for how close is 'too close' has actually changed. It used to be 30 metres. There's now a proposal for 60. That means a building that was fine last year might not be fine now — and some buildings that were demolished had actually been approved by the government in the first place. It's not as simple as 'legal or not.' We wanted a tool that's honest about that mess, not one that pretends it's simple."

This single beat does a lot of work: it shows you understand the *actual* problem, not just the technical task, and it's a story, not a spec.

---

## Segment 3 — What You Built, and the Mistake You Caught (2:30–5:30) · 2 speakers, tag-team

**Speaker A (30–45 sec):** plain description, no jargon.

> "We used satellite images and Google's building database to spot structures near rivers across three areas of Nairobi. One of those areas — Kasarani — has a real field survey from an organisation called Pamoja Trust, who counted about 700 structures on the ground. That let us check our work against reality instead of just trusting the computer."

**Live demo, ~60–90 sec, screen-shared, minimal narration.** Let it speak. Show: pick a region → the map flies in → point at the trust badge ("this tells you whether a number is checked against real data, or a guess") → maybe one click on a river stretch.

**Speaker B (45 sec) — the integrity story, your best material:**

> "Something important happened while we built this. Our first version told us the model was 96% accurate. When we tested it properly — checking it only on data it had never seen — the real number was 84%. We're not hiding that. We think telling you the honest number is more useful than telling you the impressive one."

This is the moment that answers "do they actually understand what they built" better than any architecture diagram could.

---

## Segment 4 — Who This Actually Helps (5:30–7:30) · 1–2 speakers

Keep this concrete and short — three sentences, not a stakeholder slide:

> "This isn't a list to hand to a demolition crew. A county team could use it to decide which stretch of river to send inspectors to first. A group like Pamoja Trust could use it to check whether people caught by that 30-to-60-metre change are being treated fairly. It's a place to start looking carefully, not a verdict."

---

## Segment 5 — What You'd Do Next, Honestly (7:30–9:00) · 1 speaker

Name two or three real limits, in plain language — this is where "understanding" gets scored, by showing you know exactly where your own tool stops being trustworthy:

> "We're honest about what this can't do yet. We only have a real field check for one of the three areas. It measures distance to the middle of the river, not the edge, so it can miss a big building whose wall reaches the water but whose centre doesn't. And it can't tell you who owns a building or whether they knew the rules when they built it. Those are the things we'd tackle next."

---

## Segment 6 — Close (9:00–10:00) · 1 speaker, ideally whoever opened

Bookend it — return to the opening image, then close on the team, in one sentence, then invite questions:

> "Six of us worked on this — the field data, the model, the map you just saw — because we wanted something a real person could actually use, not just a project to hand in. Happy to take questions."

---

## Practical notes for tomorrow, since it's online

- **One person drives the whole demo, live, on their own screen — don't pass control between presenters.** Every handoff online is a place for something to go wrong and eat your ten minutes.
- **Record a 30-second screen capture of the dashboard working, tonight, as backup.** If the live demo lags or a connection drops, you play the clip instead of losing the moment.
- **Minimal slides.** A title, maybe one image of real Nairobi flooding or river encroachment, one dashboard screenshot, one closing slide. Nothing with bullet-point walls of text — that's exactly what pulls a room back into "too technical."
- **Rehearse the handoffs specifically**, not just your own lines — the gaps between speakers are where 10 minutes quietly becomes 14.
- **Prep 2–3 likely questions in advance** with one honest sentence each ready: "why should anyone trust this," "what happens to people caught by the buffer change," "why three regions but only one field-checked." Confident, short, honest answers in Q&A score the same "understanding" box the presentation does.
