import torch

from s2st.train import masked_unit_loss


def test_masked_unit_loss_uses_vocabulary_as_class_dimension() -> None:
    logits = torch.full((1, 2, 3, 5), -10.0)
    codes = torch.tensor([[[1, 2, 3], [4, 3, 2]]])
    for codebook in range(2):
        for frame in range(3):
            logits[0, codebook, frame, codes[0, codebook, frame]] = 10.0

    loss = masked_unit_loss(logits, codes, torch.tensor([3]))
    assert loss.item() < 0.001
