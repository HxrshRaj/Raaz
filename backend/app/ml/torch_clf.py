"""PyTorch TextCNN for clue-category classification (CPU only).

A compact 1-D CNN over a learned word embedding: Embedding -> Conv1d(k=2,3,4) -> global max-pool -> dropout -> Linear.
Training: Adam, cross-entropy, early stopping on validation loss, best-epoch checkpoint. Everything is seeded.
This is a *separate* model from the LLM used for dialogue; no language model is trained here.
"""

from __future__ import annotations

import json
import random
import re
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .data import CATEGORIES, Sample
from .text_clf import metrics

PAD, UNK = 0, 1


def normalize(text: str) -> list[str]:
    t = text.lower()
    t = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", " <time> ", t)
    t = re.sub(r"\b\d[\d,\.]*\b", " <num> ", t)
    return re.findall(r"<time>|<num>|[a-z]+", t)


class Vocab:
    def __init__(self, itos: list[str]):
        self.itos = itos
        self.stoi = {w: i for i, w in enumerate(itos)}

    @classmethod
    def build(cls, texts: list[str], min_freq: int = 1, max_size: int = 6000) -> Vocab:
        c: Counter[str] = Counter()
        for t in texts:
            c.update(normalize(t))
        words = [w for w, n in c.most_common(max_size) if n >= min_freq]
        return cls(["<pad>", "<unk>", *words])

    def encode(self, text: str, max_len: int) -> list[int]:
        ids = [self.stoi.get(w, UNK) for w in normalize(text)][:max_len]
        return ids + [PAD] * (max_len - len(ids))


@dataclass
class TorchConfig:
    seed: int = 7
    emb_dim: int = 64
    filters: int = 64
    kernels: tuple[int, ...] = (2, 3, 4)
    dropout: float = 0.4
    lr: float = 3e-3
    weight_decay: float = 1e-4
    batch_size: int = 32
    max_epochs: int = 40
    patience: int = 6
    max_len: int = 40
    min_freq: int = 1


def _build_net(vocab_size: int, n_classes: int, cfg: TorchConfig):
    import torch
    from torch import nn

    class TextCNN(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.emb = nn.Embedding(vocab_size, cfg.emb_dim, padding_idx=PAD)
            self.convs = nn.ModuleList([nn.Conv1d(cfg.emb_dim, cfg.filters, k, padding=k // 2) for k in cfg.kernels])
            self.drop = nn.Dropout(cfg.dropout)
            self.fc = nn.Linear(cfg.filters * len(cfg.kernels), n_classes)

        def forward(self, x):  # x: [B, T]
            e = self.emb(x).transpose(1, 2)  # [B, E, T]
            pooled = [torch.relu(c(e)).max(dim=2).values for c in self.convs]
            return self.fc(self.drop(torch.cat(pooled, dim=1)))

    return TextCNN()


@dataclass
class TorchResult:
    net: Any
    vocab: Vocab
    cfg: TorchConfig
    history: list[dict[str, float]] = field(default_factory=list)
    best_epoch: int = 0
    metrics: dict[str, Any] = field(default_factory=dict)
    train_seconds: float = 0.0
    n_params: int = 0


def _seed_all(seed: int) -> None:
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def train_torch(train: list[Sample], val: list[Sample], test: list[Sample], real: list[Sample],
                cfg: TorchConfig | None = None) -> TorchResult:
    import torch
    from sklearn.metrics import f1_score
    from torch import nn

    cfg = cfg or TorchConfig()
    prev_threads = torch.get_num_threads()
    torch.set_num_threads(1)  # tiny model; single thread keeps float reductions reproducible
    try:
        _seed_all(cfg.seed)
        vocab = Vocab.build([s.text for s in train], cfg.min_freq)
        label2id = {c: i for i, c in enumerate(CATEGORIES)}

        def tensors(samples: list[Sample]):
            x = torch.tensor([vocab.encode(s.text, cfg.max_len) for s in samples], dtype=torch.long)
            y = torch.tensor([label2id[s.label] for s in samples], dtype=torch.long)
            return x, y

        xt, yt = tensors(train)
        xv, yv = tensors(val)
        net = _build_net(len(vocab.itos), len(CATEGORIES), cfg)
        opt = torch.optim.Adam(net.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
        loss_fn = nn.CrossEntropyLoss()
        gen = torch.Generator().manual_seed(cfg.seed)
        best_loss, best_state, bad = float("inf"), None, 0
        history: list[dict[str, float]] = []
        res = TorchResult(net, vocab, cfg)
        t0 = time.perf_counter()
        for epoch in range(1, cfg.max_epochs + 1):
            net.train()
            perm = torch.randperm(len(xt), generator=gen)
            tl = 0.0
            for i in range(0, len(perm), cfg.batch_size):
                idx = perm[i:i + cfg.batch_size]
                opt.zero_grad()
                loss = loss_fn(net(xt[idx]), yt[idx])
                loss.backward()
                opt.step()
                tl += float(loss.detach()) * len(idx)
            net.eval()
            with torch.no_grad():
                vlogits = net(xv)
                vloss = float(loss_fn(vlogits, yv))
                vf1 = float(f1_score(yv.numpy(), vlogits.argmax(1).numpy(), average="macro", zero_division=0))
            history.append({"epoch": epoch, "train_loss": round(tl / len(xt), 5), "val_loss": round(vloss, 5), "val_macro_f1": round(vf1, 4)})
            if vloss < best_loss - 1e-4:
                best_loss, bad = vloss, 0
                best_state = {k: v.clone() for k, v in net.state_dict().items()}
                res.best_epoch = epoch
            else:
                bad += 1
                if bad >= cfg.patience:
                    break
        res.train_seconds = time.perf_counter() - t0
        if best_state is not None:
            net.load_state_dict(best_state)  # checkpoint restore
        net.eval()
        res.history = history
        res.n_params = sum(p.numel() for p in net.parameters())
        pred = TorchPredictor(net, vocab, cfg)
        res.metrics = {
            "val": metrics([s.label for s in val], [p[0] for p in pred.predict([s.text for s in val])]),
            "test": metrics([s.label for s in test], [p[0] for p in pred.predict([s.text for s in test])]),
            "real_ood": metrics([s.label for s in real], [p[0] for p in pred.predict([s.text for s in real])]),
        }
        return res
    finally:
        torch.set_num_threads(prev_threads)


class TorchPredictor:
    def __init__(self, net: Any, vocab: Vocab, cfg: TorchConfig):
        self.net, self.vocab, self.cfg = net, vocab, cfg

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        import torch

        if not texts:
            return np.zeros((0, len(CATEGORIES)))
        x = torch.tensor([self.vocab.encode(t, self.cfg.max_len) for t in texts], dtype=torch.long)
        self.net.eval()
        with torch.no_grad():
            return torch.softmax(self.net(x), dim=1).numpy()

    def predict(self, texts: list[str]) -> list[tuple[str, float]]:
        p = self.predict_proba(texts)
        return [(CATEGORIES[int(i)], float(p[k, int(i)])) for k, i in enumerate(p.argmax(1))]


# ----------------------------------------------------------------------------- artifacts
def save_artifacts(res: TorchResult, directory: Path) -> None:
    import torch

    directory.mkdir(parents=True, exist_ok=True)
    torch.save(res.net.state_dict(), directory / "model.pt")
    (directory / "vocab.json").write_text(json.dumps(res.vocab.itos))
    cfg = asdict(res.cfg)
    cfg["kernels"] = list(cfg["kernels"])
    (directory / "config.json").write_text(json.dumps(cfg))
    (directory / "metrics.json").write_text(json.dumps({"history": res.history, "best_epoch": res.best_epoch, "n_params": res.n_params,
                                                       **res.metrics}))


def load_artifacts(directory: Path) -> TorchPredictor:
    import torch

    cfg_d = json.loads((directory / "config.json").read_text())
    cfg_d["kernels"] = tuple(cfg_d["kernels"])
    cfg = TorchConfig(**cfg_d)
    vocab = Vocab(json.loads((directory / "vocab.json").read_text()))
    net = _build_net(len(vocab.itos), len(CATEGORIES), cfg)
    net.load_state_dict(torch.load(directory / "model.pt", map_location="cpu", weights_only=True))
    net.eval()
    return TorchPredictor(net, vocab, cfg)
