# Inference cost estimate

Pricing checked on **2026-10-23**. All USD figures below are estimates, not invoices or measured charges.

## Default: local ChatGPT sign-in through Codex CLI

The local adapter invokes the official `codex exec` command using the evaluator's existing Codex ChatGPT sign-in. Each evaluator needs their own eligible account and available plan usage. The application does not extract login tokens, supply shared credits, or create a ChatGPT password field.

ChatGPT subscription usage cannot be converted into an actual dollar charge from API token prices. A returned token count, if available, is usage information only. Do not label this route “free” or apply the API estimate below to it. Plan limits and availability still apply.

Official references: [Codex authentication](https://learn.chatgpt.com/docs/auth), [noninteractive execution](https://learn.chatgpt.com/docs/developer-commands#codex-exec).

## Alternative: evaluator-provided OpenAI API key

The BYOK route targets **`gpt-4.1-mini-2025-04-14`**, a snapshot with text and image input and structured output support. Standard public rates:

| Usage | USD per 1 million tokens |
|---|---:|
| Input | $0.40 |
| Cached input, when eligible | $0.10 |
| Output | $1.60 |

Sources: [OpenAI API pricing](https://developers.openai.com/api/docs/pricing), [GPT-4.1 Mini model details](https://developers.openai.com/api/docs/models/gpt-4.1-mini). Rates, eligibility, and availability can change.

Illustrative single-order assumption: **6,000 total input tokens, including image tokens**, plus **2,000 output tokens**, no cached-input discount and no additional paid tools:

```text
estimated inference cost
= (6,000 × $0.40 + 2,000 × $1.60) / 1,000,000
= $0.0056 per order
```

Image input is included in the assumed input-token total, not added again as a flat image fee. Actual image-token usage depends on image dimensions and processing; file count alone does not establish cost. See [images and vision](https://developers.openai.com/api/docs/guides/images-vision).

If the API returns usage, the app may calculate an **estimated billed inference cost based on returned usage**. That is still an estimate, not a verified billing charge. If usage is unavailable, the app must label the figure as assumption-based or unavailable. The illustrative calculation above does not represent a live API test.

## Other costs and measurements

- Local development hosting has no hosted-service charge in this submission; the evaluator supplies their machine and network. Public hosting is outside scope.
- Subscription fees, generation of the synthetic test images, and any future hosting are separate from per-order API inference.
- Free credits, if an evaluator has them, do not change the underlying inference rate.
- Per-run elapsed time is measured by the server around the actual processing request. It is not a throughput or latency guarantee.
- Actual live-test status, models, timings, and any failures belong in the README and `sample-data/test_log.md`; this cost sheet makes no claim that the BYOK path has been exercised live.
