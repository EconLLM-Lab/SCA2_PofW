"""Hand-computed fixture for the DPO loss in train_dpo.py.

beta = 0.1. Each log-prob is a summed completion log-prob (nats).

Pair 1 (policy moved the right way):
    pi_c = -10, ref_c = -12   -> chosen log-ratio   = -10 - (-12) = +2
    pi_r = -15, ref_r = -14   -> rejected log-ratio = -15 - (-14) = -1
    chosen reward   = 0.1 * 2    = +0.2
    rejected reward = 0.1 * (-1) = -0.1
    margin z        = 0.2 - (-0.1) = +0.3
    loss = -logsigmoid(0.3) = log(1 + e^-0.3)
         = log(1 + 0.7408182207) = log(1.7408182207) = 0.5543552444

Pair 2 (policy moved the wrong way):
    pi_c = -20, ref_c = -18   -> chosen log-ratio   = -2
    pi_r =  -9, ref_r = -10   -> rejected log-ratio = +1
    chosen reward   = -0.2, rejected reward = +0.1
    margin z        = -0.3
    loss = -logsigmoid(-0.3) = log(1 + e^0.3)
         = log(1 + 1.3498588076) = log(2.3498588076) = 0.8543552444

Check: loss2 - loss1 = softplus(0.3) - softplus(-0.3) = 0.3 exactly.
Mean loss = (0.5543552444 + 0.8543552444) / 2 = 0.7043552444
Mean margin = (0.3 + -0.3) / 2 = 0.0
Reward accuracy (margin > 0) = 1 / 2 = 0.5
"""

from __future__ import annotations

import pytest
import torch

from sca2_workbench.train_dpo import dpo_loss, pair_ids


def test_dpo_loss_hand_fixture():
    pi_c = torch.tensor([-10.0, -20.0], dtype=torch.float64)
    ref_c = torch.tensor([-12.0, -18.0], dtype=torch.float64)
    pi_r = torch.tensor([-15.0, -9.0], dtype=torch.float64)
    ref_r = torch.tensor([-14.0, -10.0], dtype=torch.float64)

    out = dpo_loss(pi_c, pi_r, ref_c, ref_r, beta=0.1)

    assert out["losses"].tolist() == pytest.approx([0.5543552444, 0.8543552444], abs=1e-9)
    assert out["loss"].item() == pytest.approx(0.7043552444, abs=1e-9)
    assert out["chosen_rewards"].tolist() == pytest.approx([0.2, -0.2], abs=1e-12)
    assert out["rejected_rewards"].tolist() == pytest.approx([-0.1, 0.1], abs=1e-12)
    assert out["margins"].tolist() == pytest.approx([0.3, -0.3], abs=1e-12)
    assert out["accuracy"].item() == pytest.approx(0.5)
    # the closed-form identity from the docstring
    assert (out["losses"][1] - out["losses"][0]).item() == pytest.approx(0.3, abs=1e-12)


def test_dpo_loss_gradient_flows_only_through_policy():
    pi_c = torch.tensor([-10.0], requires_grad=True)
    pi_r = torch.tensor([-15.0], requires_grad=True)
    ref_c = torch.tensor([-12.0])
    ref_r = torch.tensor([-14.0])
    dpo_loss(pi_c, pi_r, ref_c, ref_r, beta=0.1)["loss"].backward()
    # d/dz softplus(-z) = -sigmoid(-z); dz/dpi_c = beta, dz/dpi_r = -beta
    s = torch.sigmoid(torch.tensor(-0.3)).item()  # 0.4255574832
    assert pi_c.grad.item() == pytest.approx(-0.1 * s, abs=1e-7)
    assert pi_r.grad.item() == pytest.approx(+0.1 * s, abs=1e-7)


def test_pair_ids_keeps_the_end_by_cutting_the_prompt_from_the_left():
    prompt = list(range(10))      # 10 prompt tokens: 0..9
    completion = [100, 101, 102]  # 3 completion tokens
    ids, n_prompt, n_cut = pair_ids(prompt, completion, max_length=8)
    # 13 tokens > 8: cut 5 from the LEFT of the prompt, keep the completion whole
    assert ids == [5, 6, 7, 8, 9, 100, 101, 102]
    assert n_prompt == 5
    assert n_cut == 5

    ids, n_prompt, n_cut = pair_ids(prompt, completion, max_length=768)
    assert ids == prompt + completion
    assert n_prompt == 10
    assert n_cut == 0
