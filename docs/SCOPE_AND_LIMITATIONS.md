# Scope and limitations

ParcelProof is a deliberately small browser-based proof of concept for comparing a packing-list PDF with delivery photos. It demonstrates extraction, structured vision output, deterministic comparison, and source-linked results. It is not a production receiving or warehouse system.

## Supported workflow

- One **single-page text PDF**, at most **five distinct SKU rows**, and **one to three photos**.
- New uploaded files; sample filenames do not select predefined answers.
- Official OpenAI tooling: local Codex CLI with the evaluator's ChatGPT sign-in, or an evaluator-provided OpenAI API key. The BYOK key is masked in the UI and used only for the request; no usable credential is included in the repo.
- `matched`, `identity_mismatch`, `quantity_mismatch`, and `unverified` results with expected quantity, confirmed quantity, PDF row/source line, photo references, and evidence descriptions.
- Cross-photo deduplication under a controlled capture convention: every physical unit has a readable stable marker such as `ITEM-01`, reused in every view.

## Interpretation limits

A similar product name cannot establish an exact SKU match. A visible wrong SKU may support an identity-disagreement result; it does not prove that the requested product is absent. An unreadable or obscured label remains unverified. An item outside the submitted views cannot be declared certainly missing.

Stable markers simplify deduplication; this is not general multi-view tracking. Unreadable, conflicting, or absent markers can leave quantities unverified. Descriptive evidence regions are model-generated and approximate. They are not independently calibrated bounding boxes or proof that every OCR claim is correct. Schema and source-reference validation check structure and traceability, not ground-truth visual accuracy.

Scanned/image-only PDFs, multi-page documents, more than five SKUs, batch orders, and unconstrained photo sets are outside this PoC. Complex table layouts, tiny print, glare, blur, occlusion, duplicate markers, and ambiguous packaging may fail or require clearer inputs.

## Disclosed validation set

The owner requested synthetic materials. Two generated one-page text PDFs and a small set of ChatGPT ImageGen product photos cover a correct manifest, an intentionally incorrect manifest, similar-name wrong SKU, an extra unit, an obscured label, repeated views, and a corrected delivery. The incorrect PDF is valid PDF syntax with deliberately wrong order contents.

`sample-data/expected_results.json` records expectations before live inference. It is separate from the application and is never supplied as a model answer. PDF pages were rendered and visually inspected; extracted text was checked for SKU rows and quantities. Generated-image inspection and actual outcomes of three successful live synthetic cases are recorded in the README, provenance, and test log. The BYOK route remains live-untested.

This tiny synthetic set does not support a general accuracy percentage, a real-world reliability claim, or a cross-model comparison. There has been no real delivery photography or broad benchmark in this submission.

## Operational boundaries

The ChatGPT adapter is for a trusted **local evaluator session**. Each evaluator supplies their own sign-in and available usage; it is not a public shared-account service. Treat uploaded files as data, not executable instructions. Model refusal, authentication problems, invalid structured output, and upload validation errors must be shown as understandable failures.

Production hosting, enterprise authentication, billing, multi-tenancy, long-term file storage, formal security/compliance assessment, warehouse/ERP integrations, fine-tuning, model benchmarking, and production monitoring are outside scope. Further work can be scoped separately.

## Repository license

At the owner's explicit request this repository is public and uses the **MIT License**, superseding the handoff document's more restrictive publication suggestion. MIT permits use, modification, distribution, and commercial use subject to retaining the copyright and license notice; the license also supplies its warranty disclaimer. See the repository's `LICENSE` for the complete terms.
