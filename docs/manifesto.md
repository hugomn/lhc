# Why long-horizon coherence

Most agent models are trained on chat data and post-trained for tool use as an afterthought. They behave well for one turn, well for ten turns, and deteriorate predictably after that.

The strongest open agent models today (Kimi K2.6, DeepSeek V4 Pro, Qwen 3, GLM 4.6) demonstrate sustained autonomous operation in the order of *hours*. This is genuine progress. Twelve-hour bursts with thousands of tool calls were science fiction eighteen months ago.

But the agents that matter — the ones that operate a company, run a research program, manage long-lived infrastructure — do not work for hours. They work for weeks. Months. Years.

The unsolved problem is not how to make a single autonomous run longer. The unsolved problem is how to make an agent that is **the same agent** when it wakes up tomorrow as it was when it slept tonight. An agent that remembers a decision it made on Monday when a contradictory request comes in on Friday. An agent that picks up a half-finished workflow after a two-week pause and recovers state without prompting.

That is what LHC measures. That is what this work is for.

## The thesis in one paragraph

A frontier-tier open model, post-trained specifically on the failure modes of long-life autonomous operation. Not a new pretraining run — the field has done that work and we will not waste capital re-doing it. We start from the best open agent base available and we try to make it measurably better at a single, narrowly defined, genuinely hard problem: **coherence across long context gaps**. We have not yet succeeded; the v0.1.5 attempt did not measurably beat its base. The benchmark and methodology that made that finding honest are this repo's actual contribution.

## What this is not

This is not a chatbot. This is not a coding assistant. This is not racing GPT-5 or Claude on general intelligence benchmarks.

This is the measurement infrastructure for the model that would eventually power the agent that runs the company.

## Patient fire

This work is built for endurance, not speed. While the field races to ship the next model in the next quarter, this is research on agents that work at week 12. Solo, currently. Long horizons. Patient fire.

— Hugo Nogueira

> Long-term destination: a research lab focused on long-horizon agent reliability, currently working name *Slow Lit Labs*. The lab is not yet incorporated; this repo lives under my personal username until it is.
