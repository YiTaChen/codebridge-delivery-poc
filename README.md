# ParcelProof

A small browser PoC that compares a text packing-list PDF with delivery photos, then reports what the evidence supports. Built for the Codebridge AI-First Product Builder assessment.

**Real model calls, new file uploads, source-linked findings.** React/TypeScript + FastAPI + one OpenAI vision provider. The default local mode uses the official Codex CLI with your ChatGPT sign-in; an evaluator-provided OpenAI API key is also supported.

[Watch the short demo](walkthrough.mp4) · [Screenshots](docs/screenshots/) · [Actual test log](sample-data/test_log.md) · [Expected results](sample-data/expected_results.json) · [Actual JSON](sample-data/actual/) · [Scope](docs/SCOPE_AND_LIMITATIONS.md) · [Cost assumptions](docs/COST_ESTIMATE.md)

## Run locally

Requires Python 3.12 or 3.13, Node.js 22+, npm, and Google Chrome or another modern browser. For the default model route, install the [official Codex CLI](https://learn.chatgpt.com/docs/cli) and authenticate on your own computer:

```bash
npm install -g @openai/codex
codex login
codex login status
git clone https://github.com/YiTaChen/codebridge-delivery-poc.git
cd codebridge-delivery-poc
bash scripts/dev.sh
```

Open **http://127.0.0.1:8000**. The script creates a virtual environment, installs pinned backend packages, builds the frontend, and starts the app on localhost. It does not install Codex or purchase inference credits. ChatGPT mode needs an eligible account, access to the configured model, and available plan usage. Change the model only if needed with `CODEX_MODEL=... bash scripts/dev.sh`.

For BYOK, choose **OpenAI API · your key** and enter your own API key in the masked field. No Codex installation is needed for that route. The API key remains in browser/request memory and is never written to storage or logs by this app. The official CLI manages its own login cache outside the repo; the app does not read or extract it. Do not expose this local CLI-backed app as a public service. Uploads are sent to OpenAI for analysis; use non-sensitive evaluation data.

For frontend development, run the backend with `.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`, then run `npm run dev` inside `frontend/` and open http://127.0.0.1:5173.

## Try it

1. Load **Issue delivery**, or upload your own one-page text PDF and one to three photos.
2. Click **Analyze delivery**. Every click invokes the selected model; sample buttons only load files.
3. Review exact-SKU counts, PDF row/line references, and clickable photo evidence.
4. Load **Corrected delivery** or **Incorrect packing list**, then analyze again. Export JSON if desired.

Supported inputs: one text PDF, up to five distinct SKU rows, and 1–3 JPEG/PNG/WebP images. Each file must be at most 10 MiB; each image at most 20 megapixels. SKU and quantity should share the same visual PDF row. Multi-page, scanned, encrypted, complex/wrapped tables, and duplicate SKU rows are unsupported or may be rejected. Semantic row completeness on arbitrary PDFs is not guaranteed by schema validation alone.

Each physical unit needs a readable unique marker such as `ITEM-01`, reused across views. Exact SKU + stable marker + clear visibility are required for a confirmed count. Duplicate markers within one photo or conflicting SKU readings are excluded. This is a controlled capture convention, not general object tracking.

Results distinguish `matched`, `identity_mismatch`, `quantity_mismatch`, and `unverified`. Similar names never replace an exact SKU. A lower visible count does **not** prove missing delivery. Photo regions are model descriptions with `region_verified=false`; no calibrated bounding boxes are implied.

## What was actually verified

Three live browser-to-backend-to-model runs used **`gpt-6.1-sol` through Codex CLI 0.163.0-alpha.10.2**, authenticated with ChatGPT, on 2026-10-23. Expected results were recorded and the generated images visually inspected by the agent before inference. No human review is claimed.

| Live case | Expected and observed outcome | Measured processing time |
|---|---|---:|
| Correct PDF + issue photos | TEA-101: 2 matched after deduplication; TEA-102: 0 verified, unverified; MUG-201: 2 vs 1, quantity mismatch; TEA-103 surfaced separately; hidden ITEM-06 unverified | 19.881 s |
| Correct PDF + corrected photo | All three SKU rows matched, four unique objects | 11.066 s |
| Incorrect PDF + corrected photo | TEA-101: 2 vs 1, quantity mismatch; TEA-102 matched; MUG-202 identity mismatch; visible MUG-201 surfaced separately | 10.845 s |

All three cases met their predeclared expectations. The result checker passed **134 deterministic checks** on these saved outputs; these are consistency checks, **not 134 deliveries or an accuracy benchmark**. The third manifest's mug row can legitimately be unverified or identity mismatch; this actual run returned identity mismatch.

**33 offline backend tests passed**, covering matching/deduplication, source/schema validation, bad uploads, local-origin restrictions, credential-safe errors, image format preservation, and provider/cost boundaries. Frontend production build, desktop visual review, mobile layout/disabled-button/masked-key smoke checks, and browser recording passed with no browser page errors. GitHub Actions repeats offline tests, build, and the committed-result comparison without model calls.

```bash
.venv/bin/python -m pytest backend/tests -q
.venv/bin/python scripts/check_actual.py
cd frontend && npm ci && npm run build
```

No failed expectation was observed in the three live cases. Known failures/limits include rejected non-text/multi-page PDFs, unreadable markers excluded from counts, uncertain/missing views left unverified, approximate photo localization, and model/layout errors on other inputs. The BYOK HTTP adapter is implemented and tested with mocks; **no live BYOK request, real-delivery photography, broad accuracy test, or public hosting was performed**. See the [test log](sample-data/test_log.md) for the exact evidence and limitations.

## Fixtures, models, and generated content

- **Exactly two PDFs**: `packing_list_correct.pdf` and `packing_list_incorrect.pdf`, generated with ReportLab 4.4.9. The latter is a valid PDF with deliberately incorrect SKU/quantity facts, rather than a corrupt file. Both were rendered and visually inspected; text/source rows were checked programmatically.
- **Four synthetic product images**: three issue views and one corrected delivery, created with built-in ChatGPT ImageGen at the owner's request. Its underlying model version was not exposed; no version is invented. Every image is visibly marked synthetic. [Exact prompts](sample-data/image_prompts.json) and [provenance](sample-data/PROVENANCE.md) are included. Image labels were checked by agent visual inspection; software also checked the model outputs against the predeclared oracle.
- **Live vision model**: `gpt-6.1-sol`; PDF text extraction: PyMuPDF 1.26.7. A single structured call extracts PDF rows and per-photo observations; deterministic Python rules produce final statuses. Model output must pass strict Pydantic schema and source validation.
- **Alternative API model**: pinned `gpt-4.1-mini-2025-04-14` via official Responses API, `store=false`, structured output, no paid tools. It has not been exercised live in this submission.
- **Implementation assistance**: Codex using GPT-6.1 Sol, with parallel implementation/review agents. Generated code was checked by tests/build, and the UI was inspected. No production-quality claim is made.

The application never reads `expected_results.json` or saved actual results to construct answers. They are evaluation artifacts only. New uploads use the same extraction/model/matching path.

## Cost and elapsed time

The three live runs consumed the logged-in evaluator's ChatGPT/Codex plan usage. Returned tokens and server elapsed times are saved in each actual JSON. There is **no per-run dollar invoice available** for that route, and plan usage is not described as free.

For BYOK planning only, public GPT-4.1 Mini rates checked on 2026-10-23 are $0.40/M input, $0.10/M cached input, and $1.60/M output. An explicit assumption of 6,000 total input tokens including images + 2,000 output tokens gives **$0.0056/order estimated**, with no cache discount. This is not a measured charge or the cost of the Codex runs. [Pricing, formulas, and source links](docs/COST_ESTIMATE.md).

**Measured task wall time: 8 minutes 43 seconds (about 9 minutes)** from first document review at **2026-10-23 15:09:19 America/Vancouver (22:09:19 UTC)** through verified public publication and successful GitHub Actions at **15:18:02 (22:18:02 UTC)**. This includes implementation, parallel agent review, image/PDF creation, tests, recording/editing, documentation, and initial publication/CI; the final bookkeeping commit is outside that timing checkpoint. This is elapsed wall time, not summed parallel-agent labor or a claim of eight hours' work.

The initial published code passed [GitHub Actions](https://github.com/YiTaChen/codebridge-delivery-poc/actions/runs/40032647036) on a fresh Linux runner: 33 backend tests, frontend install/build, and saved-result comparison. The video is **43.71 seconds**, from 72.133 seconds of source recording. This is a basic PoC, with no warehouse integration, accounts/billing, model benchmark, or production deployment.

## Demo and reproduction

`walkthrough.mp4` is a **43.71-second** silent, captioned recording of the actual browser workflow and the three real model responses. Only waiting intervals are accelerated; captions disclose this and the UI shows real measured duration. No responses are intercepted or replaced. The full MP4 was decoded successfully and sampled frames were visually inspected. [Recording/edit timeline](docs/demo_timeline.json).

Optional reproduction (with Chrome and the app already running): install `playwright` in a temporary local Node environment, make it resolvable through `NODE_PATH`, then run `node scripts/record_demo.cjs`. The script consumes real model usage. To edit waiting intervals, install `imageio-ffmpeg` or a system FFmpeg and run `.venv/bin/python scripts/edit_demo.py`. To regenerate the PDFs, install `reportlab` and run `.venv/bin/python scripts/generate_pdfs.py`.

## License

Public **MIT License**, as explicitly requested by the owner. Copyright retained by YiTa Chen; retain the copyright and license notice when reusing the software. See [LICENSE](LICENSE). Synthetic validation remains limited to the disclosed fixtures.
