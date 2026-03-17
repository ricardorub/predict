import torch
import torch.nn as nn
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import os

# Definición del modelo (Debe coincidir EXACTAMENTE con el de entrenamiento)
class TempPredictor(nn.Module):
    def __init__(self, input_dim=1, hidden_dim=50, num_layers=2, output_dim=1):
        super(TempPredictor, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :]) 
        return out

class PredictionService:
    _model = None
    _scaler = MinMaxScaler(feature_range=(0, 1))
    _device = torch.device('cpu') # Usar CPU para inferencia en backend web siempre
    
    _heart_model = None
    _scaler_heart = MinMaxScaler(feature_range=(0, 1))

    @classmethod
    def load_model(cls, model_path='models/temp_lstm_model.pth'):
        if cls._model is None:
            try:
                if not os.path.exists(model_path):
                    # Silently fail or warn, but don't crash
                    return False
                
                cls._model = TempPredictor().to(cls._device)
                cls._model.load_state_dict(torch.load(model_path, map_location=cls._device))
                cls._model.eval()
                return True
            except Exception as e:
                print(f"Error loading temp model: {e}")
                return False
        return True

    _spo2_model = None
    _scaler_spo2 = MinMaxScaler(feature_range=(0, 1))

    @classmethod
    def load_heart_model(cls, model_path='models/heart_lstm_model.pth'):
        if cls._heart_model is None:
            try:
                if not os.path.exists(model_path):
                    return False
                
                cls._heart_model = TempPredictor().to(cls._device)
                cls._heart_model.load_state_dict(torch.load(model_path, map_location=cls._device))
                cls._heart_model.eval()
                return True
            except Exception as e:
                print(f"Error loading heart model: {e}")
                return False
        return True

    @classmethod
    def load_spo2_model(cls, model_path='models/spo2_lstm_model.pth'):
        if cls._spo2_model is None:
            try:
                if not os.path.exists(model_path):
                    return False
                
                cls._spo2_model = TempPredictor().to(cls._device)
                cls._spo2_model.load_state_dict(torch.load(model_path, map_location=cls._device))
                cls._spo2_model.eval()
                return True
            except Exception as e:
                print(f"Error loading spo2 model: {e}")
                return False
        return True

    @classmethod
    def predict_next_steps(cls, recent_data, steps=6):
        if not cls._model:
            if not cls.load_model(): return []
        return cls._predict_generic(cls._model, cls._scaler, recent_data, steps)

    @classmethod
    def predict_heart_rate(cls, recent_data, steps=6):
        if not cls._heart_model:
            if not cls.load_heart_model(): return []
        return cls._predict_generic(cls._heart_model, cls._scaler_heart, recent_data, steps)

    @classmethod
    def predict_spo2(cls, recent_data, steps=6):
        if not cls._spo2_model:
            if not cls.load_spo2_model(): return []
        return cls._predict_generic(cls._spo2_model, cls._scaler_spo2, recent_data, steps)

    @classmethod
    def _predict_generic(cls, model, scaler, recent_data, steps):
        if len(recent_data) < 12: return []

        # Escalar usando la data reciente
        scaler.fit(np.array(recent_data).reshape(-1, 1)) 
        input_seq = np.array(recent_data[-12:]).reshape(-1, 1)
        scaled_seq = scaler.transform(input_seq)
        
        current_seq = torch.tensor(scaled_seq, dtype=torch.float32).unsqueeze(0).to(cls._device)
        
        predictions = []
        with torch.no_grad():
            for _ in range(steps):
                pred = model(current_seq)
                predictions.append(pred.item())
                pred_reshaped = pred.unsqueeze(1)
                current_seq = torch.cat((current_seq[:, 1:, :], pred_reshaped), dim=1)
        
        predictions_array = np.array(predictions).reshape(-1, 1)
        original_scale_preds = scaler.inverse_transform(predictions_array)
        return original_scale_preds.flatten().tolist()
