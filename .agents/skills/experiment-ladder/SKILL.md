---
name: experiment-ladder
description: Spend a GPU budget on machine-learning experiments in rungs that each buy a decision — smoke test, scaling curve, matched-compute comparison, then the full run — with hyperparameters that transfer across width (μP) and a held-out benchmark that stays sealed. Use when planning, launching or judging training runs, when asked whether an idea is worth a bigger run, or before reading a benchmark's evaluation split.
---

# Experiment ladder

No large run on a hunch. The budget is spent in rungs, each about ten times the cost of the one
before, and each ends in a decision written down before it started. A rung that cannot change the
next decision is not run.

## The rungs

0. **Smoke, ~1–2% of the budget.** The whole pipeline on a handful of tasks: data, training,
   checkpoint, resume, inference, scoring, results back on the machine that asked. Overfit one batch
   to near-zero loss. Score the reference answers through your own scorer (full marks) and a trivial
   baseline (near zero). Kill a run and resume it: it must continue, not restart.
1. **Curve, ~15%.** The baseline at three or more compute scales spanning at least a factor of ten,
   on one schedule (below). Fit a power law to a continuous metric and check it extrapolates towards
   the published number, if there is one. A baseline that does not reproduce is the finding.
2. **Comparison, ~15%.** The change on the same schedule, scales, data and evaluation. The claim is
   the gap at matched compute, at every scale: a gap that grows with scale is the result, one that
   shrinks is a warning, one inside the seed spread is no gap.
3. **Decision**, with whoever owns the budget. Fund the full run only if the change's curve sits
   above the baseline's and is not flattening, and write down the number the full run should give
   before it starts.

Before any rung, write down:

- the claim, and the number that would refute it;
- the kill rule, e.g. *at 10% of the run, more than X below the projected curve: stop*;
- the cost cap, enforced by a timeout on every remote call, not by watching;
- which evaluation it reads, logged before the read.

## Curves for the price of one run

- **Warmup–stable–decay.** Train at constant learning rate and, for each point of the curve — say
  1/9, 1/3 and all of the budget — branch a cool-down over that point's last ~10–20% of steps,
  decayed to zero. Each branch is a point of the curve for the cost of its cool-down, where a
  cosine schedule costs a full run per point (Hägele et al., 2024, arXiv 2405.18392).
- **Fit continuous metrics**: validation loss, per-token or per-cell accuracy, log-probability of
  the correct answer. Exact match and multiple-choice grade jump and fake emergence (Schaeffer et
  al., 2023, arXiv 2304.15004), and pass@k thresholds the same way: report them, do not extrapolate
  them.
- **Extrapolate at most a factor of ten** past the largest point.
- **Seeds set the noise floor**: two or three at the smallest scale, before reading any gap.

## Hyperparameters that transfer: μP

Under the standard parametrization the best learning rate moves with width, so a sweep on a small
model says little about a large one. μP (Yang et al., 2022, *Tensor Programs V*, arXiv 2203.03466)
scales initialisation and per-tensor learning rate so that the optimum stays put: sweep on the
small model, then copy the hyperparameters.

The rule is per tensor, by which of its dimensions grow with width. For Adam, without multipliers
(the paper's Table 3; the `mup` package implements its equivalent Table 8, which moves the
readout's 1/fan-in into an output multiplier):

| tensor | example | init variance | learning rate |
|---|---|---|---|
| input-like: only fan-out grows | embeddings, biases, norm gains | width-independent | width-independent |
| hidden: both grow | attention and MLP matrices | ∝ 1/fan-in | ∝ 1/fan-in |
| output-like: only fan-in grows | readout, unembedding | ∝ 1/fan-in² (or zero) | ∝ 1/fan-in |

Attention logits scale by 1/d_head instead of 1/√d_head. Anchor each ∝ at a base width, and the
attention scale as √d_head,0 / d_head, and μP at the base width is the standard model, unless a
layer is initialised at zero. SGD has its own row in the paper's Table 3.

**The optimizer-independent form** is the spectral condition (Yang, Simon & Bernstein, 2023,
arXiv 2310.17813), shown there for SGD and entrywise optimizers like Adam and met by any update once
it is normalised: every weight matrix and every update to it should have spectral norm of order
√(fan-out / fan-in), fan-in read as 1 for a one-hot input such as an embedding's. Adam's table above
is one instance. For an update orthogonalised to unit spectral norm, as Muon's is, it is scaling the
update by √(fan-out / fan-in) at a width-independent learning rate; Muon's reference code uses
√max(1, fan-out / fan-in), the same up to a constant per shape on the hidden matrices it is meant
for, while Moonlight's 0.2·√max(fan-out, fan-in) matches AdamW's update size instead and does not
meet the condition as is. The modular norm (Large et al., 2024, arXiv 2405.14813, the `modula`
package) composes this rule along the network: each module carries a mass and a sensitivity, and a
composite's are computed from its parts, so a new architecture built from existing layers needs no
new table; a new kind of layer declares its norm, mass and sensitivity by hand.

**Check it in minutes.** Train a few steps at widths 128 to 2048 and plot the size of each layer's
activations: flat across widths under μP, growing or vanishing otherwise (`mup.coord_check`).

**What transfers.** Width, with theory. Depth, in μP itself, only empirically and fragile: to
transfer across depth, scale the residual branches by 1/L and Adam's ε with them (CompleteP, Dey et al., 2025, arXiv 2505.01618);
depth-μP's 1/√L is derived for one-layer blocks, not transformers. Steps and batch size transfer
only empirically (Tensor Programs V, on transformers, steps fixed when batch size varies). Weight
decay and other regularisers do not, nor a different dataset or task. If the proxy and the target
differ only in steps, μP buys nothing: the warmup–stable–decay curve is the ladder.

## Evaluation that measures the claim

- **Hold out tasks, not examples.** A dev set must stand to training as the benchmark does: a model
  that scored 84% on new examples of its training tasks scored under 3% on the benchmark's unseen
  tasks.
- **Controls at matched budget**: the trivial baseline, the unlearned search on the same compute,
  and a lookup of known solutions, so that recall is not read as generalisation.
- **Score as the benchmark scores**, e.g. two attempts per test input and credit per output.
- **A sealed split is read only to score a claim written down first**, one read per claim, logged.
  Code loads it only through an explicit argument: an environment variable survives in a warm
  container. Overlapping benchmark versions are excluded by id.
- **Review before the read**: an adversarial review of the evaluation code — leaks, the scoring
  rule, augmentations not undone, missing timeouts — since a read cannot be taken back.

## Running on rented GPUs

- Launch from a deployed app, not from a client whose death takes the run with it.
- Checkpoint often; test resume in the smoke rung.
- Put a time limit on every remote call and on every run of generated code.
- Write one result file per call: concurrent appends to one file lose lines.
- Read the bill daily against the plan, and stop a rung at its cap.

## Reporting a rung

What it cost, the curve or the gap with its seed spread, the decision taken, and the next rung's
prediction.
