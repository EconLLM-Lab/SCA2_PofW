"""Relative conservation gates: ``|error| / scale <= tau``.

An absolute threshold does not survive a change of dtype or model. The residual stream of
SmolLM2-135M carries an entry of about 2.6e4 (a massive activation), and one float32 ulp
there is 1.95e-3: the brief's ``< 1e-3`` absolute closure gate is below the representation
error of the stream it is checking, so it fails on a float32 pass that is otherwise exact.
This module states every gate the same way, as an error *relative to the size of the
quantity the error is an error of*, and takes ``tau`` from the caller, so a model measures
its own numbers and passes its own thresholds.

The checks, their error and their scale
---------------------------------------
name               error                                                scale
----------------   ---------------------------------------------------   ------------------------
residual_closure   inf-norm of ``h^L - (h^0 + sum_l a^l + sum_l m^l)``   inf-norm of ``h^L``,
                                                                         floored at 1
step_closure       inf-norm over features of                             inf-norm of ``h^l_t``,
                   ``h^l_t - h^{l-1}_t - a^l_t - m^l_t``, worst over     floored at 1 (at the
                   layers l and positions t                              same (l, t))
head_closure       inf-norm of ``a^l - sum_h o^l_h``                     inf-norm of ``a^l``,
                                                                         floored at 1
readout            ``|margin - attr_sum|``  (the DLA gap)               ``|margin| + 1``
pair_attribution   ``|d_margin - (sum d_head_attr + sum d_mlp_attr     ``|d_margin| + 1``
                   + d_embed_attr)|``
logits_reference   ``max |logits_ours - logits_reference|``            ``max |logits_reference|``

Why those scales:

* **Residual closure** divides by the size of the state the pieces must add up to. The
  inf-norm (not the 2-norm) is used because the error itself is an inf-norm: it is the
  largest single entry that either closes or does not, and the largest entry of the
  stream is the one whose round-off is largest. The floor at 1 keeps a degenerate
  all-zero capture from turning the gate into 0/0; on any real pass the floor is inert.
* **Step closure** is residual closure at the grain of one addition. The global gate above
  divides by the largest entry of ``h^L``, and that entry is a massive activation (position 0,
  one feature, 4,429 in SmolLM2-135M-Instruct) that the typical position, layer and feature
  never get near. Its tau (1e-4 in float32) therefore allows an absolute error of 0.44, more
  than a 0.1% error in the MLP write of most layers (audit of ``t_1547e1a8``: a 1.001x write
  in the median layer passed the global gate at 0.1x of tau). Each step is a float32 addition
  of local quantities, so its honest error is a few ulps of the *local* magnitude
  ``||h^l_t||_inf``; the gate is that ratio, worst over (l, t). Both gates are kept: the step
  gate catches a wrong piece, the global one catches an accumulated drift.
* **Head closure** divides by the size of the attention write, for the same reason one
  level down: ``a^l`` is what the heads must sum to.
* **The readout** divides by ``|margin| + 1``. The ``+ 1`` makes the scale a margin of
  error in its own units: an error smaller than 1 logit cannot be inflated by a margin
  that happens to be near zero, and for Q43, whose margin is 0.039, the gate does not
  become an absolute 1e-2 gate in disguise.
* **The pair attribution** divides by ``|d_margin| + 1``, the same construction applied
  to the difference of two margins.
* **The reference check** is already a relative gap; its scale simply gets a name.

``TAUS_F64`` and ``TAUS_F32`` are the calibrated sets for the SmolLM2-135M family. Each
tau is 10x the largest relative error measured for that check on that model set, rounded
up to the next power of ten; the measurements are in ``plans/stage1_f32_gaps.md``. They are
defaults, not constants of nature: pass your own ``GateTaus`` for another model.

Two of the six are exceptions to that rule, stated where they sit: ``head_closure``
is exactly zero in both dtypes (the same sum computed twice), so its tau is 10x the
round-off of the same identity summed in float64; and ``pair_attribution`` keeps the value
the pair gate already had, because the script that calibrates this table exports no pair.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import torch  # noqa: F401  (type names in ``worst_step``)

#: The multiple of the observed error that a tau is set at (see ``plans/stage1_f32_gaps.md``).
TAU_MULTIPLE = 10.0

#: Floor applied to the scale of the two closure checks (see the module docstring).
SCALE_FLOOR = 1.0


@dataclass(frozen=True)
class Gate:
    """One check, in the form ``|error| / scale <= tau``."""

    name: str
    error: float
    scale: float
    scale_desc: str
    tau: float

    @property
    def rel(self) -> float:
        """The relative error the gate compares against ``tau``."""
        return self.error / self.scale if self.scale else float("inf")

    @property
    def ok(self) -> bool:
        return self.rel <= self.tau

    def as_dict(self) -> dict:
        return {"error": self.error, "scale": self.scale, "scale_desc": self.scale_desc,
                "rel": self.rel, "tau": self.tau, "pass": self.ok}


@dataclass(frozen=True)
class GateTaus:
    """The six thresholds of one calibration. Pass a different one for a different model."""

    residual_closure: float
    step_closure: float
    head_closure: float
    readout: float
    pair_attribution: float
    logits_reference: float

    def as_dict(self) -> dict:
        return {"residual_closure": self.residual_closure, "step_closure": self.step_closure,
                "head_closure": self.head_closure,
                "readout": self.readout, "pair_attribution": self.pair_attribution,
                "logits_reference": self.logits_reference}

    def scaled(self, multiple: float) -> "GateTaus":
        """The same set with every tau multiplied; for a sensitivity check, not for shipping."""
        return replace(self, **{k: v * multiple for k, v in self.as_dict().items()})


#: ``step_closure`` taus, SmolLM2-135M family (same 18 pairs). Measured max: 1.95e-15 (float64),
#: 2.85e-07 (float32); 10x, next power of ten. ``plans/scripts/step_gap.py`` ->
#: ``plans/scripts/out/step_gap.txt``. A 1.001x stored MLP write fails it by 21x (smallest layer)
#: to 100x (largest) in float32 and by 2e9x+ in float64; clean passes at 0.02x / 0.003x.
STEP_F64 = 1e-13
STEP_F32 = 1e-5

#: Calibrated on SmolLM2-135M, -135M-Instruct and -Instruct+usa_e3, float64, 18 (model, prompt)
#: pairs. Measured max: 5.45e-15 (residual closure), 0.0 (head closure, exact), 2.13e-14
#: (readout), 6.14e-15 (reference). See ``plans/stage1_f32_gaps.md``.
TAUS_F64 = GateTaus(residual_closure=1e-13, step_closure=STEP_F64, head_closure=1e-15, readout=1e-12,
                    pair_attribution=1e-6, logits_reference=1e-13)

#: Same models and prompts, float32. Measured max: 6.23e-06 (residual closure), 0.0 in the
#: shipped form (1.80e-07 when the same identity is summed in float64), 2.28e-05 (readout),
#: 4.44e-06 (reference). See ``plans/stage1_f32_gaps.md``.
TAUS_F32 = GateTaus(residual_closure=1e-4, step_closure=STEP_F32, head_closure=1e-5, readout=1e-3,
                    pair_attribution=1e-6, logits_reference=1e-4)


def floor_scale(scale: float) -> float:
    """``max(scale, SCALE_FLOOR)``: what the closure gates divide by."""
    return max(float(scale), SCALE_FLOOR)


def residual_closure(closure_inf: float, h_final_inf: float, tau: float) -> Gate:
    """``h^L = h^0 + sum a + sum m``, relative to ``||h^L||_inf``."""
    return Gate("residual_closure", float(closure_inf), floor_scale(h_final_inf),
                "max|h^L| over positions and features, floored at 1", float(tau))


def step_closure(step_err_inf: float, step_scale_inf: float, tau: float) -> Gate:
    """``h^l_t = h^{l-1}_t + a^l_t + m^l_t`` at the worst (l, t), relative to ``||h^l_t||_inf``.

    ``step_err_inf`` and ``step_scale_inf`` are the numerator and denominator of the *worst
    ratio* (the (l, t) that maximises error / scale), not the two maxima taken separately.
    """
    return Gate("step_closure", float(step_err_inf), floor_scale(step_scale_inf),
                "max|h^l_t| at the worst (layer, position), floored at 1", float(tau))


def worst_step(err: "torch.Tensor", scale: "torch.Tensor") -> tuple:
    """(error, scale) at the entry that maximises ``err / max(scale, 1)``. Both are (L, T)."""
    ratio = err / scale.clamp(min=SCALE_FLOOR)
    i = int(ratio.argmax())
    return err.flatten()[i].item(), scale.flatten()[i].item()


def head_closure(head_closure_inf: float, attn_write_inf: float, tau: float) -> Gate:
    """``a^l = sum_h o^l_h``, relative to ``max|a^l|`` over layers, positions and features."""
    return Gate("head_closure", float(head_closure_inf), floor_scale(attn_write_inf),
                "max|a^l| over layers, positions and features, floored at 1", float(tau))


def readout(margin: float, dla_gap: float, tau: float) -> Gate:
    """``|margin - attr_sum|``, relative to ``|margin| + 1``."""
    return Gate("readout", float(dla_gap), abs(float(margin)) + 1.0, "|margin| + 1", float(tau))


def pair_attribution(d_margin: float, gap: float, tau: float) -> Gate:
    """The B - A attribution sum against ``d_margin``, relative to ``|d_margin| + 1``."""
    return Gate("pair_attribution", float(gap), abs(float(d_margin)) + 1.0, "|d_margin| + 1",
                float(tau))


def logits_reference(max_abs_gap: float, logits_inf: float, tau: float) -> Gate:
    """``max|logits_ours - logits_ref|``, relative to ``max|logits_ref|``."""
    return Gate("logits_reference", float(max_abs_gap), max(float(logits_inf), SCALE_FLOOR),
                "max|logits_reference|, floored at 1", float(tau))


def check_capture(out: dict, taus: GateTaus, *, suffix: str = "") -> dict:
    """The three gates every capture can run, read off a ``llama_capture.run`` result.

    ``suffix`` sets the output keys (``""`` for the pass, ``"_clamped"`` for the clamped pass).
    """
    return {
        f"residual_closure{suffix}": residual_closure(
            out["residual_closure_inf"], out["residual_scale_inf"], taus.residual_closure),
        f"step_closure{suffix}": step_closure(
            out["step_err_inf"], out["step_scale_inf"], taus.step_closure),
        f"head_closure{suffix}": head_closure(
            out["head_closure_inf"], out["attn_scale_inf"], taus.head_closure),
        f"readout{suffix}": readout(out["margin"], out["dla_gap"], taus.readout),
    }


def all_ok(gates: dict) -> bool:
    """True when every gate in the mapping passes. An empty mapping is not a pass."""
    return bool(gates) and all(g.ok for g in gates.values())


def as_manifest(gates: dict, taus: GateTaus) -> dict:
    """The JSON block written into a run manifest: the taus, every gate, and the verdict."""
    return {"taus": taus.as_dict(), "tau_multiple": TAU_MULTIPLE,
            "checks": {k: g.as_dict() for k, g in gates.items()}, "pass": all_ok(gates)}
