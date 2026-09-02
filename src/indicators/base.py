from abc import ABC, abstractmethod
from datetime import date

import pandas as pd


class BaseIndicator(ABC):
    name: str

    @abstractmethod
    def compute(self, df: pd.DataFrame, corridor: str, cutoff_date: date) -> pd.Series:
        """
        Score series indexed by date. No data after cutoff_date allowed.
        Score range: document per subclass.
        """

    def get_signal(
        self,
        df: pd.DataFrame,
        corridor: str,
        cutoff_date: date,
        threshold: float = 0.5,
    ) -> bool:
        scores = self.compute(df, corridor, cutoff_date)
        if cutoff_date not in scores.index:
            return False
        return bool(scores[cutoff_date] >= threshold)

    def _filter(self, df: pd.DataFrame, corridor: str, cutoff_date: date) -> pd.DataFrame:
        mask = (df["corridor"] == corridor) & (df["date"] <= cutoff_date)
        return df[mask].copy()
