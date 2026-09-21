"""
LSTM model for sequential pattern learning in financial time series.
Uses PyTorch — runs on CPU or GPU automatically.
"""
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import joblib
import os
from typing import Dict, Tuple, List
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score
import logging

logger = logging.getLogger(__name__)

MODELS_DIR = "/app/app/services/ml/saved_models"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
SEQUENCE_LENGTH = 30  # look-back window


# ------------------------------------------------------------------ #
#  Dataset                                                             #
# ------------------------------------------------------------------ #

class TimeSeriesDataset(Dataset):
    def __init__(self, X: np.ndarray, y: np.ndarray):
        self.X = torch.FloatTensor(X)
        self.y = torch.FloatTensor(y)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


# ------------------------------------------------------------------ #
#  Architecture                                                        #
# ------------------------------------------------------------------ #

class LSTMNet(nn.Module):
    def __init__(self, input_size: int, hidden_size: int = 128, num_layers: int = 2,
                 dropout: float = 0.3):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
        )
        self.attention = nn.Linear(hidden_size, 1)
        self.dropout = nn.Dropout(dropout)
        self.bn = nn.BatchNorm1d(hidden_size)

        # Classification head
        self.clf_head = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )
        # Regression head
        self.reg_head = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 1),
        )

    def forward(self, x):
        lstm_out, _ = self.lstm(x)  # (batch, seq, hidden)

        # Attention pooling
        attn_weights = torch.softmax(self.attention(lstm_out), dim=1)  # (batch, seq, 1)
        context = (attn_weights * lstm_out).sum(dim=1)  # (batch, hidden)

        context = self.dropout(self.bn(context))

        clf_out = self.clf_head(context).squeeze(-1)
        reg_out = self.reg_head(context).squeeze(-1)
        return clf_out, reg_out


# ------------------------------------------------------------------ #
#  Predictor                                                           #
# ------------------------------------------------------------------ #

class LSTMPredictor:
    def __init__(self, ticker: str, sequence_length: int = SEQUENCE_LENGTH):
        self.ticker = ticker
        self.seq_len = sequence_length
        self.model: LSTMNet = None
        self.scaler = StandardScaler()
        self.feature_cols: List[str] = []
        self.is_trained = False

    # ---------------------------------------------------------------- #

    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        df = df.copy().sort_values("date").reset_index(drop=True)

        df["future_return"] = df["close"].pct_change(1).shift(-1)
        df["direction"] = (df["future_return"] > 0).astype(float)

        df["return_1d"] = df["close"].pct_change(1)
        df["return_3d"] = df["close"].pct_change(3)
        df["return_5d"] = df["close"].pct_change(5)
        df["hl_ratio"] = (df["high"] - df["low"]) / df["close"]
        df["co_ratio"] = (df["close"] - df["open"]) / df["open"]
        df["vol_norm"] = df["volume"] / df["volume"].rolling(20).mean()

        indicator_cols = [
            c for c in df.columns
            if any(c.startswith(p) for p in [
                "rsi", "macd", "bb_", "atr", "adx", "ema", "sma", "obv"
            ])
        ]

        base_features = [
            "return_1d", "return_3d", "return_5d",
            "hl_ratio", "co_ratio", "vol_norm",
        ]
        self.feature_cols = base_features + indicator_cols
        self.feature_cols = [c for c in self.feature_cols if c in df.columns]

        df.dropna(subset=self.feature_cols + ["direction", "future_return"], inplace=True)

        X_raw = df[self.feature_cols].values
        y_clf = df["direction"].values
        y_reg = df["future_return"].values

        return X_raw, y_clf, y_reg

    def _build_sequences(self, X: np.ndarray, y_clf: np.ndarray, y_reg: np.ndarray):
        Xs, ycs, yrs = [], [], []
        for i in range(self.seq_len, len(X)):
            Xs.append(X[i - self.seq_len:i])
            ycs.append(y_clf[i])
            yrs.append(y_reg[i])
        return np.array(Xs), np.array(ycs), np.array(yrs)

    # ---------------------------------------------------------------- #

    def train(self, df: pd.DataFrame, epochs: int = 50, batch_size: int = 32) -> Dict:
        logger.info(f"[LSTM] Training on {self.ticker}")

        X_raw, y_clf, y_reg = self.prepare_features(df)

        if len(X_raw) < self.seq_len + 50:
            raise ValueError(f"Not enough data for LSTM: {len(X_raw)} rows")

        X_scaled = self.scaler.fit_transform(X_raw)
        X_seq, y_c_seq, y_r_seq = self._build_sequences(X_scaled, y_clf, y_reg)

        # Train/val split (80/20, no shuffle — time series)
        split = int(len(X_seq) * 0.8)
        X_tr, X_val = X_seq[:split], X_seq[split:]
        yc_tr, yc_val = y_c_seq[:split], y_c_seq[split:]
        yr_tr, yr_val = y_r_seq[:split], y_r_seq[split:]

        train_ds = TimeSeriesDataset(X_tr, yc_tr)
        val_ds = TimeSeriesDataset(X_val, yc_val)
        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=False)
        val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

        input_size = X_seq.shape[2]
        self.model = LSTMNet(input_size=input_size).to(DEVICE)

        optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-3, weight_decay=1e-5)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)
        clf_loss_fn = nn.BCELoss()
        reg_loss_fn = nn.MSELoss()

        best_val_loss = float("inf")
        best_state = None

        for epoch in range(epochs):
            self.model.train()
            train_loss = 0.0
            for X_b, y_b in train_loader:
                X_b, y_b = X_b.to(DEVICE), y_b.to(DEVICE)
                optimizer.zero_grad()
                clf_out, _ = self.model(X_b)
                loss = clf_loss_fn(clf_out, y_b)
                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()
                train_loss += loss.item()

            # Validation
            self.model.eval()
            val_loss = 0.0
            all_proba, all_labels = [], []
            with torch.no_grad():
                for X_b, y_b in val_loader:
                    X_b, y_b = X_b.to(DEVICE), y_b.to(DEVICE)
                    clf_out, _ = self.model(X_b)
                    val_loss += clf_loss_fn(clf_out, y_b).item()
                    all_proba.extend(clf_out.cpu().numpy())
                    all_labels.extend(y_b.cpu().numpy())

            scheduler.step(val_loss)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = {k: v.clone() for k, v in self.model.state_dict().items()}

        # Load best weights
        self.model.load_state_dict(best_state)
        self.is_trained = True

        preds = [1 if p > 0.5 else 0 for p in all_proba]
        metrics = {
            "model": "lstm",
            "ticker": self.ticker,
            "epochs": epochs,
            "accuracy": float(accuracy_score(all_labels, preds)),
            "auc_roc": float(roc_auc_score(all_labels, all_proba)),
            "val_loss": float(best_val_loss),
            "input_size": input_size,
            "sequence_length": self.seq_len,
        }
        logger.info(f"[LSTM] {self.ticker} — accuracy={metrics['accuracy']:.3f}")
        return metrics

    # ---------------------------------------------------------------- #

    def predict(self, df: pd.DataFrame) -> Dict:
        if not self.is_trained:
            raise RuntimeError("Model not trained.")

        X_raw, _, _ = self.prepare_features(df)
        X_scaled = self.scaler.transform(X_raw)

        if len(X_scaled) < self.seq_len:
            raise ValueError(f"Need at least {self.seq_len} rows for prediction")

        X_seq = X_scaled[-self.seq_len:][np.newaxis, :, :]  # (1, seq, features)
        X_tensor = torch.FloatTensor(X_seq).to(DEVICE)

        self.model.eval()
        with torch.no_grad():
            clf_out, reg_out = self.model(X_tensor)

        direction_proba = float(clf_out.cpu().item())
        predicted_return = float(reg_out.cpu().item())

        return {
            "model": "lstm",
            "ticker": self.ticker,
            "direction": "up" if direction_proba > 0.5 else "down",
            "direction_probability": direction_proba,
            "predicted_return_pct": predicted_return * 100,
            "confidence": abs(direction_proba - 0.5) * 2,
            "sequence_length": self.seq_len,
        }

    # ---------------------------------------------------------------- #

    def save(self):
        os.makedirs(MODELS_DIR, exist_ok=True)
        path = f"{MODELS_DIR}/lstm_{self.ticker}"
        torch.save(self.model.state_dict(), f"{path}_weights.pt")
        joblib.dump({
            "scaler": self.scaler,
            "feature_cols": self.feature_cols,
            "ticker": self.ticker,
            "seq_len": self.seq_len,
            "input_size": len(self.feature_cols),
        }, f"{path}_meta.pkl")

    def load(self) -> bool:
        path = f"{MODELS_DIR}/lstm_{self.ticker}"
        if not os.path.exists(f"{path}_weights.pt"):
            return False
        meta = joblib.load(f"{path}_meta.pkl")
        self.scaler = meta["scaler"]
        self.feature_cols = meta["feature_cols"]
        self.seq_len = meta["seq_len"]
        self.model = LSTMNet(input_size=meta["input_size"]).to(DEVICE)
        self.model.load_state_dict(torch.load(f"{path}_weights.pt", map_location=DEVICE))
        self.is_trained = True
        return True
