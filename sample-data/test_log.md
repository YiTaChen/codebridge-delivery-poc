# Limited test log

**Test date:** 2026-10-23. These are three actual browser submissions against the local backend, using the disclosed synthetic fixtures. All three returned HTTP 200. Raw responses are preserved in [`actual/`](actual/); the predeclared oracle is [`expected_results.json`](expected_results.json), and post-run consistency checks are in [`actual/comparison.json`](actual/comparison.json).

## Environment and procedure

- Live provider: official local **Codex CLI `0.163.0-alpha.10.2`**, authenticated with **ChatGPT sign-in**. Returned model identifier: **`gpt-6.1-sol`** for all three runs. No more precise immutable model snapshot was exposed by these responses.
- Browser selected the PDF and generated images, submitted Analyze to the real backend, and displayed the returned results. The model received numbered extracted PDF text plus the submitted images; the application did not receive the expected-results file as an answer source.
- The parent agent visually inspected all four generated images before the first live inference. Both one-page PDFs were rendered, visually inspected, and text-extracted; backend source-line references were confirmed. No human inspection is claimed.
- Images were generated using the **built-in ChatGPT ImageGen tool**. Its underlying image-model version was not exposed. Exact prompts are in [`image_prompts.json`](image_prompts.json).
- Backend elapsed times below are actual measured processing durations, including the model invocation; they are not estimates or performance guarantees. Token figures are returned CLI usage and include CLI/model context, not just visible packing-list text.

## Live runs and returned usage

The timestamps below are recorded response timestamps from [`docs/demo_timeline.json`](../docs/demo_timeline.json), in UTC. Vancouver local time was 15:14 on the same date.

| Case | Recorded at UTC | HTTP | Measured seconds | Input tokens | Output tokens | Cached input tokens |
|---|---|---:|---:|---:|---:|---:|
| Issue delivery | 22:14:01.935 | 200 | 19.881 | 18,069 | 790 | 0 |
| Corrected delivery | 22:14:25.472 | 200 | 11.066 | 14,271 | 384 | 0 |
| Incorrect manifest | 22:14:41.035 | 200 | 10.845 | 14,274 | 383 | 0 |

Actual per-run dollar charges are **unavailable** for ChatGPT subscription usage; `estimated_usd` is null in all three responses. The separate BYOK API estimate in [`COST_ESTIMATE.md`](../docs/COST_ESTIMATE.md) is illustrative and was not used to price these runs.

## Expected versus actual

Each expected cell gives the allowed quantity/status recorded before inference. “Unverified or identity mismatch” was predeclared because a clear different SKU may or may not receive an explicit related-row association. Neither status permits counting that SKU as the requested one or declaring absent stock.

| Case / input | PDF line / SKU | PDF quantity | Expected confirmed / status | Actual confirmed / status |
|---|---|---:|---|---|
| Issue: correct PDF + photos 1–3 | 7 / TEA-101 | 2 | 2 / matched | 2 / matched |
| Issue: correct PDF + photos 1–3 | 8 / TEA-102 | 1 | 0 / unverified or identity mismatch | 0 / unverified |
| Issue: correct PDF + photos 1–3 | 9 / MUG-201 | 1 | 2 / quantity mismatch | 2 / quantity mismatch |
| Corrected: correct PDF + corrected image | 7 / TEA-101 | 2 | 2 / matched | 2 / matched |
| Corrected: correct PDF + corrected image | 8 / TEA-102 | 1 | 1 / matched | 1 / matched |
| Corrected: correct PDF + corrected image | 9 / MUG-201 | 1 | 1 / matched | 1 / matched |
| Incorrect manifest + corrected image | 7 / TEA-101 | 1 | 2 / quantity mismatch | 2 / quantity mismatch |
| Incorrect manifest + corrected image | 8 / TEA-102 | 1 | 1 / matched | 1 / matched |
| Incorrect manifest + corrected image | 9 / MUG-202 | 1 | 0 / unverified or identity mismatch | 0 / identity mismatch |

Observed details:

- In the issue case, ITEM-01, ITEM-03, and ITEM-04 appeared in multiple photos and were counted once per distinct stable marker. Two visible TEA-101 units remained two, rather than becoming three photo appearances.
- Visible TEA-103 / Green Tea Jasmine was reported as an unexpected SKU and did not count as TEA-102 / Green Tea Decaf. The model supplied no unique related-row association, so TEA-102 stayed `unverified`.
- The two visible MUG-201 units produced a quantity mismatch against one expected unit.
- ITEM-06 had a readable object marker and an obscured SKU/name in both relevant views. Its SKU was not guessed; it remained `unverified` and excluded from confirmed counts. The system did not declare it or any unseen requested unit certainly missing.
- The corrected image matched all three rows of the correct manifest. Changing only the PDF to the intentionally incorrect manifest exposed both the TEA-101 quantity disagreement and visible MUG-201 versus requested MUG-202 identity disagreement.
- Photo evidence cited uploaded photo IDs and descriptive regions; every returned region remained `region_verified=false`. No precise calibrated location is claimed.

## Checks, failures, and untested work

**134/134 consistency assertions passed** across these three saved live results: 51 for issue delivery, 41 for corrected delivery, and 42 for incorrect manifest. These assertions check quantities, accepted statuses, source references, expected observations, deduplication, obscured-label handling, and metrics. They are not 134 independent deliveries, a benchmark, or an accuracy percentage. The comparison checker makes no additional model calls.

**33 offline backend tests passed**, covering deterministic behavior and validation paths, including format preservation for JPEG/PNG/WebP uploads. Provider calls in these tests are mocked; this count is distinct from the three live inferences above.

No live case failed its predeclared expectations in this run. The recording reported no browser errors. This does not establish reliability beyond these inputs. The OpenAI BYOK Responses path (`gpt-4.1-mini-2025-04-14`) was tested with mocks only and **was not exercised against the live API**. No inference payment was made for a live BYOK test.

Real photographs, broad OCR/layout compatibility, authentication/rate-limit behavior under other accounts, throughput, production hosting, and general multi-view tracking were not validated. All visual inputs here are synthetic. See [`SCOPE_AND_LIMITATIONS.md`](../docs/SCOPE_AND_LIMITATIONS.md).

## Demo recording

The silent, captioned demo records the real browser actions and the actual responses from these three submissions. Only model-wait intervals were accelerated, to three seconds per wait, with the acceleration disclosed in captions; no result was replaced. The saved edit timeline reports **43.71 seconds**, from **72.133 seconds** of source recording. The final video is below the requested two-minute limit.

ChatGPT sign-in was already present before recording, so no API key or login credential was entered or revealed in the demo. The recording covers the input flow, issue results, corrected delivery, and incorrect-manifest comparison. The JSON responses and timeline retain the original measured processing times even though waits are shorter in the video.
