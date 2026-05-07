# Why Ember

Most agent models are trained on chat data and post-trained for tool use as
an afterthought. They behave well for one turn, well for ten turns, and
deteriorate predictably after that.

The strongest open agent models today (Kimi K2.6, DeepSeek V3.2, Qwen 3,
GLM 4.6) demonstrate sustained autonomous operation in the order of *hours*.
This is genuine progress. Twelve-hour bursts with thousands of tool calls
were science fiction eighteen months ago.

But the agents that matter — the ones that operate a company, run a
research program, manage long-lived infrastructure — do not work for hours.
They work for weeks. Months. Years.

The unsolved problem is not how to make a single autonomous run longer.
The unsolved problem is how to make an agent that is **the same agent**
when it wakes up tomorrow as it was when it slept tonight. An agent that
remembers a decision it made on Monday when a contradictory request comes
in on Friday. An agent that picks up a half-finished workflow after a
two-week pause and recovers state without prompting.

This is the work Ember is for.

## The thesis in one paragraph

A frontier-tier open model, post-trained specifically on the failure modes
of long-life autonomous operation. Not a new pretraining run — the field
has done that work and we will not waste capital re-doing it. We start
from the best open agent base available, and we make it measurably better
at a single, narrowly defined, genuinely hard problem: **coherence across
long context gaps**.

## What we are not

We are not training a chatbot. We are not training a coding assistant.
We are not racing GPT-5 or Claude on general intelligence benchmarks.

We are training the model that powers the agent that runs the company.

— Cinder Labs
