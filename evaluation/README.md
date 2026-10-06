# Evaluation

`python -m evaluation.run` measures the job pipeline against a small hand-labelled test set.
The latest numbers are in [`results/latest.json`](results/latest.json) and summarised in the main README.

```powershell
python -m evaluation.run                         # rule filter + red flags (offline, no API keys)
python -m evaluation.run --llm --runs 3          # + LLM scoring, 3 repetitions (~12 LLM calls)
python -m evaluation.run --briefs Groww Postman  # + company briefs (4 LLM calls each)
```

## Test set

`data/jobs.jsonl` holds 126 real postings fetched on 2026-10-06 from the app's own sources. The
public job boards (Remotive, Remote OK, We Work Remotely, Himalayas, Arbeitnow) and the
Greenhouse/Lever/Ashby boards in the committed `config/companies.yaml` were all included. The
postings are stored as fetched, without editing.

It is **not** a random sample. Fresher roles that suit the profile are rare (well under 1% of the
~3,700 postings fetched), so a random sample would contain almost no positives. Instead it contains:

- every posting that passed the rule filter (40),
- postings the filter rejected that look like near-misses: developer titles without a seniority
  word, junior/intern titles, and India-located developer roles,
- a handful of random rejects (obvious negatives).

So precision and recall here describe behaviour on hard cases. They are not a population
estimate. With 11 relevant postings, each one moves recall by about 9 points, so treat the
numbers as rough.

## Labelling rubric

Each posting was labelled against the public example profile
([`config/profile.example.yaml`](../config/profile.example.yaml)): a fresher full-stack developer
(Python, FastAPI, React, TypeScript), graduating in 2026, at most 2 years of experience, in India
or open to worldwide remote work.

`label: 1` (relevant) only if **all** of these hold:

1. **Software development role.** The main work is writing software: software, backend,
   frontend, full-stack or product engineer, or SDE intern. Support, analytics, FinOps,
   consulting and security-testing roles are 0.
2. **Open to a fresher.** No stated requirement above 2 years. No "deep/seasoned/senior-level"
   scope. No graduation-batch or degree restriction the profile fails. "Intermediate" levels
   count as mid-level and get 0.
3. **Location fits.** The job is in India, or is remote and open worldwide (or India is listed as
   eligible). When the location field and the description disagree, the description wins.

`label: null` means there wasn't enough information to judge. These postings are kept for
transparency but excluded from the metrics. Five Remote OK descriptions were truncated to about
600 characters by the API. One posting stated no location eligibility, and one was a talent-pool
form rather than a real opening.

The `note` field records the reason for any non-obvious label, and marks low-confidence calls.
Two labels (Rubrik winter internships, which require 2027 graduates) were first marked relevant.
They were corrected after the LLM scorer pointed out the graduation-batch restriction; the
correction was checked against the posting text.

## Metrics

| Stage | Metric | Meaning |
|---|---|---|
| Rule filter | recall | share of relevant postings that survive the filter, which is the number it is tuned for |
| Rule filter | precision | share of surviving postings that are relevant; the LLM scorer cleans these up |
| LLM scorer | AUC | chance a random relevant posting outscores a random irrelevant one (among filter survivors) |
| LLM scorer | precision@50 | share of postings scored 50 or more ("worth applying") that are relevant |
| Digest | precision | share of the top 10 (score at least `DIGEST_MIN_SCORE`) that are relevant |
| Digest | end-to-end recall | share of all relevant postings that reach the top 10, filter misses included |
| Red flags | flag rate | share of these real postings that get a warning. None of them are scams, so every flag is a false alarm |
| Briefs | citation coverage | share of factual lines (6+ words, outside Sources/Verification) that carry a `[n]` citation |
| Briefs | invalid citations | `[n]` numbers that don't match a gathered source |

The brief checks are structural. They confirm that claims are cited and that the citations point
at real sources. They do not check that a source actually supports the claim.
