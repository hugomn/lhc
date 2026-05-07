# Changelog

All notable changes to Ember are documented here.

## [Unreleased]

### Added
- Initial repository scaffold
- LHC (Long-Horizon Coherence) eval suite v0.1 — task spec and runner skeleton
- Training pipeline scaffold (Axolotl-based LoRA on top of the strongest
  available open agent base model)
- Inference scaffold (vLLM-backed OpenAI-compatible API)

### Planned for v0.1
- LHC v0.1 baseline run against Kimi K2.6, DeepSeek V3.2, Claude Sonnet,
  GPT-5 — published as a Cinder Labs research note
- ~50k SFT examples generated from real and synthetic agent traces
- LoRA fine-tune released as `cinderlabs/ember-v0.1`
- Public OpenAI-compatible API at `api.cinderlabs.ai/v1`

## How releases work

Ember follows a simple `vMAJOR.MINOR` scheme.

- `MINOR` releases improve LHC scores or add capability without breaking
  the API surface.
- `MAJOR` releases change the base model, the API, or the eval suite version.

Every release ships with: weights on Hugging Face, an LHC scorecard,
release notes here.
