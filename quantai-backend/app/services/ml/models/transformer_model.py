"""
Transformer model for financial time series.
Uses multi-head self-attention to capture long-range dependencies.
"""
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import joblib
import math
import os
from typing import Dict, Tuple, List
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score
import logging

logger = logging.getLogger(__name__)

MODELS_DIR = "/app/app/services/ml/saved_models"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
SEQUENCE_LENGTH = 60


# ------------------------------------------------------------------ #
#  Positional Encoding                                                 #
# ------------------------------------------------------------------ #

class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 512, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len).unsqueeze(1).float()
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        self.register_buffer("pe", pe)

    def forward(self, x):
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)


# ------------------------------------------------------------------ #
#  Architecture                                                        #
# ------------------------------------------------------------------ #

class FinancialTransformer(nn.Module):
    def __init__(
        self,
        input_size: int,
        d_model: int = 64,
        nhead: int = 4,
        num_encoder_layers: int = 3,
        dim_feedforward: int = 256,
        dropout: float = 0.1,
    ):
        super().__init__()
        # Input projection
        self.input_proj = nn.Linear(input_size, d_model)
        self.pos_enc = PositionalEncoding(d_model, dropout=dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            norm_first=True,  # Pre-norm (more stable)
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_encoder_layers)
        self.norm = nn.LayerNorm(d_model)

        # Global average pooling over time
        self.pool = nn.AdaptiveAvgPool1d(1)

        # Classification head
        self.clf_head = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )
        # Regression head
        self.reg_head = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(32, 1),
        )

    def forward(self, x):
        # x: (batch, seq, input_size)
        x = self.input_proj(x)           # (batch, seq, d_model)
        x = self.pos_enc(x)
        x = self.transformer(x)          # (batch, seq, d_model)
        x = self.norm(x)

        # Pool over time dimension
        x = x.transpose(1, 2)           # (batch, d_model, seq)
        x = self.pool(x).squeeze(-1)    # (batch, d_model)

        clf_out = self.clf_head(x).squeeze(-1)
        reg_out = self.reg_head(x).squeeze(-1)
        return clf_out, reg_out


# ------------------------------------------------------------------ #
#  Dataset                                                             #
# ------------------------------------------------------------------ #

class SequenceDataset(Dataset):
    def __init__(self, X: np.ndarray, y: np.ndarray):
        self.X = torch.FloatTensor(X)
        self.y = torch.FloatTensor(y)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


# ------------------------------------------------------------------ #
#  Predictor                                                           #
# ------------------------------------------------------------------ #

class TransformerPredictor:
    def __init__(self, ticker: str, sequence_length: int = SEQUENCE_LENGTH):
        self.ticker = ticker
        self.seq_len = sequence_length
        self.model: FinancialTransformer = None
        self.scaler = StandardScaler()
        self.feature_cols: List[str] = []
        self.is_trained = False

    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        df = df.copy().sort_values("date").reset_index(drop=True)

        df["future_return"] = df["close"].pct_change(1).shift(-1)
        df["direction"] = (df["future_return"] > 0).astype(float)

        # Price features
        for lag in [1, 2, 3, 5, 10, 20]:
            df[f"ret_{lag}d"] = df["close"].pct_change(lag)

        df["hl_ratio"] = (df["high"] - df["low"]) / df["close"]
        df["co_ratio"] = (df["close"] - df["open"]) / df["open"]
        df["vol_norm"] = df["volume"] / (df["volume"].rolling(20).mean() + 1e-9)

        # Volatility regime
        df["vol_10"] = df["ret_1d"].rolling(10).std()
        df["vol_30"] = df["ret_1d"].rolling(30).std()
        df["vol_regime"] = df["vol_10"] / (df["vol_30"] + 1e-9)

        indicator_cols = [
            c for c in df.columns
            if any(c.startswith(p) for p in [
                "rsi", "macd", "bb_", "atr", "adx", "ema", "sma", "obv", "stoch"
            ])
        ]

        base = [
            f"ret_{l}d" for l in [1, 2, 3, 5, 10, 20]
        ] + ["hl_ratio", "co_ratio", "vol_norm", "vol_10", "vol_30", "vol_regime"]

        self.feature_cols = base + indicator_cols
        self.feature_cols = [c for c in self.feature_cols if c in df.columns]

        df.dropna(subset=self.feature_cols + ["direction", "future_return"], inplace=True)

        return df[self.feature_cols].values, df["direction"].values, df["future_return"].values

    def _build_sequences(self, X, y_clf, y_reg):
        Xs, ycs, yrs = [], [], []
        for i in range(self.seq_len, len(X)):
            Xs.append(X[i - self.seq_len:i])
            ycs.append(y_clf[i])
            yrs.append(y_reg[i])
        return np.array(Xs), np.array(ycs), np.array(yrs)

    def train(self, df: pd.DataFrame, epochs: int = 40, batch_size: int = 32) -> Dict:
        logger.info(f"[Transformer] Training on {self.ticker}")

        X_raw, y_clf, y_reg = self.prepare_features(df)

        if len(X_raw) < self.seq_len + 50:
            raise ValueError(f"Not enough data: {len(X_raw)} rows")

        X_scaled = self.scaler.fit_transform(X_raw)
        X_seq, y_c_seq, y_r_seq = self._build_sequences(X_scaled, y_clf, y_reg)

        split = int(len(X_seq) * 0.8)
        X_tr, X_val = X_seq[:split], X_seq[split:]
        yc_tr, yc_val = y_c_seq[:split], y_c_seq[split:]

        train_loader = DataLoader(SequenceDataset(X_tr, yc_tr), batch_size=batch_size, shuffle=False)
        val_loader = DataLoader(SequenceDataset(X_val, yc_val), batch_size=batch_size, shuffle=False)

        input_size = X_seq.shape[2]
        self.model = FinancialTransformer(input_size=input_size).to(DEVICE)

        optimizer = torch.optim.AdamW(self.model.parameters(), lr=1e-3, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        loss_fn = nn.BCELoss()

        best_val_loss = float("inf")
        best_state = None

        for epoch in range(epochs):
            self.model.train()
            for X_b, y_b in train_loader:
                X_b, y_b = X_b.to(DEVICE), y_b.to(DEVICE)
                optimizer.zero_grad()
                clf_out, _ = self.model(X_b)
                loss = loss_fn(clf_out, y_b)
                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), 0.5)
                optimizer.step()
            scheduler.step()

            self.model.eval()
            val_loss = 0.0
            all_proba, all_labels = [], []
            with torch.no_grad():
                for X_b, y_b in val_loader:
                    X_b, y_b = X_b.to(DEVICE), y_b.to(DEVICE)
                    clf_out, _ = self.model(X_b)
                    val_loss += loss_fn(clf_out, y_b).item()
                    all_proba.extend(clf_out.cpu().numpy())
                    all_labels.extend(y_b.cpu().numpy())

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = {k: v.clone() for k, v in self.model.state_dict().items()}

        self.model.load_state_dict(best_state)
        self.is_trained = True

        preds = [1 if p > 0.5 else 0 for p in all_proba]
        metrics = {
            "model": "transformer",
            "ticker": self.ticker,
            "epochs": epochs,
            "accuracy": float(accuracy_score(all_labels, preds)),
            "auc_roc": float(roc_auc_score(all_labels, all_proba)),
            "val_loss": float(best_val_loss),
            "input_size": input_size,
            "sequence_length": self.seq_len,
        }
        logger.info(f"[Transformer] {self.ticker} — accuracy={metrics['accuracy']:.3f}")
        return metrics

    def predict(self, df: pd.DataFrame) -> Dict:
        if not self.is_trained:
            raise RuntimeError("Model not trained.")

        X_raw, _, _ = self.prepare_features(df)
        X_scaled = self.scaler.transform(X_raw)

        if len(X_scaled) < self.seq_len:
            raise ValueError(f"Need at least {self.seq_len} rows")

        X_seq = X_scaled[-self.seq_len:][np.newaxis, :, :]
        X_tensor = torch.FloatTensor(X_seq).to(DEVICE)

        self.model.eval()
        with torch.no_grad():
            clf_out, reg_out = self.model(X_tensor)

        direction_proba = float(clf_out.cpu().item())
        predicted_return = float(reg_out.cpu().item())

        return {
            "model": "transformer",
            "ticker": self.ticker,
            "direction": "up" if direction_proba > 0.5 else "down",
            "direction_probability": direction_proba,
            "predicted_return_pct": predicted_return * 100,
            "confidence": abs(direction_proba - 0.5) * 2,
            "sequence_length": self.seq_len,
        }

    def save(self):
        os.makedirs(MODELS_DIR, exist_ok=True)
        path = f"{MODELS_DIR}/transformer_{self.ticker}"
        torch.save(self.model.state_dict(), f"{path}_weights.pt")
        joblib.dump({
            "scaler": self.scaler,
            "feature_cols": self.feature_cols,
            "ticker": self.ticker,
            "seq_len": self.seq_len,
            "input_size": len(self.feature_cols),
        }, f"{path}_meta.pkl")

    def load(self) -> bool:
        path = f"{MODELS_DIR}/transformer_{self.ticker}"
        if not os.path.exists(f"{path}_weights.pt"):
            return False
        meta = joblib.load(f"{path}_meta.pkl")
        self.scaler = meta["scaler"]
        self.feature_cols = meta["feature_cols"]
        self.seq_len = meta["seq_len"]
        self.model = FinancialTransformer(input_size=meta["input_size"]).to(DEVICE)
        self.model.load_state_dict(torch.load(f"{path}_weights.pt", map_location=DEVICE))
        self.is_trained = True
        return True
