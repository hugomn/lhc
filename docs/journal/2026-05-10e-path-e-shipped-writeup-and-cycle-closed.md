# 2026-05-10e · Path E artifact #3 shipped; v0.2 cycle closed

**Status at end of session:** Path E is complete. The methodology writeup is live on hugo.im in both English and Portuguese, the LHC repo README links to it, and the v0.2 cycle is formally closed. No further work is planned in this cycle. Next cycle will be a v0.3 design conversation, framed by what we learned here.

## What we did

1. **Drafted the long-form writeup** for hugo.im. First pass was theatrical and asymmetric (over-focused on the failed model). Hugo flagged the framing as wrong: the post should lead with the artifacts (benchmark + parser + methodology trail) and treat the failed model as one example in the trail, not the spine. Rewrote end-to-end with a contribution-first lead and prose-paragraph voice (real paragraphs with beginning/middle/end, not staccato single-line beats). 3,438 words.

2. **Submitted the EN draft to the same external reviewer who has been challenging this work since round 1.** The reviewer flagged six factual/precision issues:
   - "Every fine-tuned 8B model" was inaccurate — only Ember is the fine-tune; Qwen, Ministral, Llama are comparison models. Changed to "every 8B-class LLM."
   - "Round 1 caught six issues, then listed contamination + hash bug + three more = five." Recounted. There were four more, not three.
   - The Round 4 explanation overclaimed mechanism ("the cache is warm and the KV state is the same") when the round-4 discipline had been "we did not isolate the source." Replaced with the disciplined non-explanation.
   - "Two months ago" / "two months earlier" was false for a 2026-05-10 post — all of this happened within days. Changed to "earlier in the rebuild" and "throughout the rebuild."
   - LHC could be misread as evaluating actual multi-week agent persistence; it doesn't. Added one sentence clarifying it is a controlled prompt-level proxy, not a multi-week runtime benchmark.
   - "A schema validator and parser get you deterministic 2/2" slightly overgeneralized from two task structures. Added "On these two structured-state task shapes" qualifier.

   All six fixes applied. Reviewer endorsed publish. This is round 6 of external review; same pattern as previous five rounds (each catches things the prior didn't).

3. **Translated the post to Portuguese** as a mirror, matching the existing pt/ post conventions: technical terms (LHC, fine-tune, parser, harness, scorecard, gap, sweep, baseline, prompt) kept in English; voice in conversational Portuguese; closing footer matches the bootstrap-phase post pattern. 3,782 words.

4. **Selected and saved a kintsugi image** as the OG card asset. The visual maps cleanly to the post's thesis: cracks repaired with gold, where the repair is the value. Saved at `public/images/blog/lhc-v02-long-horizon-coherence-benchmark.jpg` (381 KB JPG, converted from a ChatGPT-generated PNG).

5. **Rotated the featured set on hugo.im.** The blog had 8 featured posts before; adding the LHC post would have made 9. Un-featured the 2026-01-03 year-review post (the oldest in the featured rail). Both languages updated, both at 8 featured each.

6. **Committed and pushed both posts** to `hugomn/hugo.im` as commit `0d70ce7`. Posts are live at:
   - [hugo.im/posts/lhc-v02-long-horizon-coherence-benchmark](https://hugo.im/posts/lhc-v02-long-horizon-coherence-benchmark/)
   - [hugo.im/pt/posts/lhc-v02-long-horizon-coherence-benchmark](https://hugo.im/pt/posts/lhc-v02-long-horizon-coherence-benchmark/)

7. **Cross-linked from this repo's README** to the writeup. Added a writeup badge under the HF dataset badge and a callout link before the contents list.

## What we learned

- **The write-it-for-an-outside-audience effect is real.** When I extracted the parser to its standalone repo (Path E #2), the act of building a comparison table for a different audience surfaced the "beats every fine-tuned model" overclaim that five review rounds had not flagged. The same effect applied again with the writeup: writing the post forced a chronological narrative which made the "two months" / counting / mechanism-overclaiming errors visible to the round-6 reviewer (and likely to the post's readers if I had shipped without that round). The lesson holds: structured comparisons against different consumers catch different errors than holistic-correctness review does. Each artifact format is its own audit.

- **The first-pass draft was wrong about voice.** The instinct to write "I did X. Then Y. Then Z." in a confessional register is wrong for hugo.im. Hugo writes in real paragraphs with topic sentence, body, resolution, and the LHC story should match that register. Worth remembering: the venue's voice constrains the post's voice, not the other way around.

- **The v0.2 cycle's value is not the model.** It's the benchmark, the parser, the methodology. The model not shipping is the load-bearing example for why the methodology is honest. By any definition I would have used three months ago, this cycle "failed" — I did not ship a model. By the definition I would use now, this cycle succeeded — I shipped what was actually publishable, and the trail of why is open.

## Decisions

- **D-25.** Path E is closed. The benchmark, parser, and methodology writeup are live. The v0.2 cycle is formally complete. No more v0.2 work.

- **D-26.** Next cycle (v0.3, if there is one) is a design conversation, not an implementation push. The v0.2 budget cap was $50 + 5 days; we ran roughly 3 days and well under budget. The remaining slack is for thinking, not for building.

- **D-27.** Future cycle scoping principle: build the floor first (parser baseline), commit to a pre-registered decision matrix, design for *consumption* artifacts (HF dataset card, comparative tables) from day one. The errors that survived five rounds of review are the ones that do not show up under holistic check; build the consumption surface early to surface them.

## What's open

These are not blockers; they are open questions for whenever the v0.3 conversation starts.

- **OQ-10:** What is the actual source of the within-session-vs-restart difference in MLX-LM on Apple Silicon? Could be cache, sampling defaults, warmup, Metal kernels, process init. A controlled experiment (one variable at a time) would isolate it. Useful for any future MLX-served benchmark, not just LHC.

- **OQ-11:** If I ran a v0.3 benchmark with more tasks (say, 60 instead of 24), would the per-task variance characterization change? The current 6/24 score-flipping rate may be an artifact of the small task count.

- **OQ-12:** Is there a v0.3 fine-tuning experiment worth doing on a different base (Ministral, or a 14B-class model that fits the M5 Pro envelope), or is the answer to keep building on top of base Qwen3-8B with a parser/harness layer? The matched-inference v0.2 result tied Ember with its base; that does not falsify the "fine-tune the base" hypothesis, it just doesn't support v0.1.5's specific recipe.

- **OQ-13:** Path E artifact #2 (the parser) sets a useful floor. Is it worth packaging it as a small PyPI module so it's `pip install`-able rather than just `git clone`? Low cost, modest reach increase.

- **OQ-14:** The methodology arc is now public. Does it pick up readers? Track it for a few weeks via hugo.im analytics + HF dataset downloads + GitHub stars on `hugomn/lhc` and `hugomn/lhc-resume-state-parser`. The point is not vanity metrics; the point is whether the methodology gets used by someone else, which is the actual test of whether this cycle was worth doing.

## Pointers

- **Live writeup (EN):** https://hugo.im/posts/lhc-v02-long-horizon-coherence-benchmark/
- **Live writeup (PT):** https://hugo.im/pt/posts/lhc-v02-long-horizon-coherence-benchmark/
- **Blog repo commit:** `0d70ce7` on `hugomn/hugo.im`
- **HF dataset:** https://huggingface.co/datasets/hugonogueira/lhc-v0.2 (commits `fd9aa7f` initial, `bb461a6` Parquet companions, `8f58585` viewer-ready dataset card, `8e05f30` parser-overclaim correction)
- **Standalone parser repo:** https://github.com/hugomn/lhc-resume-state-parser (commit `86efd78`)
- **This repo:** https://github.com/hugomn/lhc (latest: this commit)
