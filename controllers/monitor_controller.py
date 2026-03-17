"""
Controlador para el monitoreo en tiempo real
"""
from models import db, Paciente, SensorData
from datetime import datetime, timedelta
import csv
import io

class MonitorController:
    """Controlador para operaciones de monitoreo en tiempo real"""
    
    @staticmethod
    def get_active_patient():
        """Obtiene el paciente activo para monitoreo"""
        return Paciente.query.filter_by(activo=True).first()
    
    @staticmethod
    def get_all_active_patients():
        """Obtiene todos los pacientes activos para el selector"""
        return Paciente.query.filter_by(activo=True).all()
    
    @staticmethod
    def get_sensor_data(time_range='5min', patient_id=None):
        """
        Obtiene datos de sensores para un rango de tiempo específico
        
        Args:
            time_range: Rango de tiempo ('5min', '15min', '30min', 'all')
            patient_id: ID del paciente (opcional, usa el activo por defecto)
        """
        now = datetime.now()
        
        # Determinar el límite de tiempo
        if time_range == '5min':
            time_limit = now - timedelta(minutes=5)
        elif time_range == '15min':
            time_limit = now - timedelta(minutes=15)
        elif time_range == '30min':
            time_limit = now - timedelta(minutes=30)
        else:
            time_limit = None
        
        # Construir query
        query = SensorData.query
        
        # Filtrar por paciente
        if patient_id:
            query = query.filter(SensorData.paciente_id == int(patient_id))
        else:
            # Usar el paciente activo por defecto
            paciente_activo = MonitorController.get_active_patient()
            if paciente_activo:
                query = query.filter(SensorData.paciente_id == paciente_activo.id)
        
        # Filtrar por tiempo
        if time_limit:
            query = query.filter(SensorData.fecha >= time_limit)
        
        records = query.order_by(SensorData.fecha.asc()).all()
        
        return records
    
    @staticmethod
    def get_csv_export(patient_id):
        """Genera CSV con todos los datos del paciente"""
        records = MonitorController.get_sensor_data(time_range='all', patient_id=patient_id)
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Fecha', 'Temperatura (°C)', 'Ritmo Cardiaco (bpm)', 'SpO2 (%)'])
        
        for r in records:
            writer.writerow([r.fecha.strftime("%Y-%m-%d %H:%M:%S"), r.valor, r.heart_rate, r.spo2])
            
        return output.getvalue()
    
    @staticmethod
    def format_sensor_data(records, current_readings):
        """
        Formatea los datos de sensores para la respuesta API
        
        Args:
            records: Lista de registros de SensorData
            current_readings: Lecturas actuales del MQTT
        """
        now = datetime.now()
        
        # Preparar datos históricos
        history_temp = [{'x': r.fecha.strftime("%H:%M:%S"), 'y': float(r.valor)} for r in records]
        history_hr = [{'x': r.fecha.strftime("%H:%M:%S"), 'y': int(r.heart_rate)} for r in records]
        history_spo2 = [{'x': r.fecha.strftime("%H:%M:%S"), 'y': int(r.spo2)} for r in records]
        
        # Determinar valores actuales
        if current_readings['last_update'] and (now - current_readings['last_update']).seconds < 30:
            temp_value = current_readings['temperature']
            hr_value = current_readings['heart_rate']
            spo2_value = current_readings['spo2']
        elif records:
            last_record = records[-1]
            temp_value = float(last_record.valor)
            hr_value = int(last_record.heart_rate)
            spo2_value = int(last_record.spo2)
        else:
            temp_value = None
            hr_value = None
            spo2_value = None
        
        return {
            'temperatura_actual': temp_value,
            'heart_rate': hr_value,
            'spo2': spo2_value,
            'historico_temperatura': history_temp,
            'historico_heart': history_hr,
            'historico_spo2': history_spo2,
            'last_update': current_readings['last_update'].isoformat() if current_readings['last_update'] else None
        }
    
    @staticmethod
    def get_stats_data(days=7, patient_id=None):
        """Obtiene datos estadísticos. Si days=7 (default dashboard), lo forzamos a 2 HORAS para que la predicción se vea bien."""
        now = datetime.now()
        
        # HACK VISUAL: Si piden 7 días (dashboard default), devolvemos solo las últimas 4 horas
        # Esto hace que la predicción (30 min) ocupe una parte significativa de la gráfica (~15-20%)
        # en lugar de ser una línea microscópica a la derecha de 7 días de datos.
        if days == 7:
             time_limit = now - timedelta(minutes=60)
        else:    
             time_limit = now - timedelta(days=days)
        
        query = SensorData.query.filter(SensorData.fecha >= time_limit)
        
        if patient_id:
            query = query.filter(SensorData.paciente_id == int(patient_id))
        else:
            # Si no se especifica paciente, usamos el activo por defecto para stats también
            # o podríamos mostrar global, pero para "Panel de Salud" suele ser individual
            paciente_activo = MonitorController.get_active_patient()
            if paciente_activo:
                query = query.filter(SensorData.paciente_id == paciente_activo.id)
            
        records = query.order_by(SensorData.fecha.asc()).all()
        
        # Preparar datos
        dias = [r.fecha.strftime("%H:%M") for r in records]
        temperatura = [float(r.valor) for r in records]
        heart_rate = [int(r.heart_rate) for r in records]
        spo2 = [int(r.spo2) for r in records]
        
        # Predicciones LSTM Reales (Historia + Futuro)
        predictions = []
        if temperatura and len(temperatura) >= 12:
            try:
                from services.prediction_service import PredictionService
                # 1. Predecir sobre los datos HISTÓRICOS (para ver el 'overlap' y comparar)
                # Generamos una predicción paso a paso para cada punto existente (simulando "qué hubiera predicho")
                # Esto es costoso si son muchos puntos, así que lo hacemos solo para los últimos 20
                
                historical_preds = [None] * len(temperatura) # Llenar con nulls al inicio
                
                # Empezamos a predecir desde el punto 12 (porque necesitamos 12 previos para el contexto)
                start_index = 12
                if len(temperatura) > start_index:
                    for i in range(start_index, len(temperatura)):
                        # Contexto: los 12 puntos anteriores a 'i'
                        context = temperatura[i-12:i]
                        # Predecir el punto 'i' (1 paso adelante)
                        pred_point = PredictionService.predict_next_steps(context, steps=1)[0]
                        historical_preds[i] = pred_point

                # 2. Predecir el FUTURO (como antes)
                future_context = temperatura[-12:]
                future_preds = PredictionService.predict_next_steps(future_context, steps=12)

                # Combinar: Historia (Overlap) + Futuro
                # Nota: 'predictions' ahora contendrá toda la serie alineada con 'temperatura' + 6 extra
                predictions = historical_preds + future_preds
                
            except Exception as e:
                print(f"Error generating predictions: {e}")
                last_temp = temperatura[-1] if temperatura else 0
                predictions = [None] * len(temperatura) + [last_temp] * 12
        
        # --- PREDICCIONES RITMO CARDÍACO ---
        heart_predictions = []
        if heart_rate and len(heart_rate) >= 12:
            try:
                from services.prediction_service import PredictionService
                
                # Historia
                hist_hr_preds = [None] * len(heart_rate)
                start_index = 12
                if len(heart_rate) > start_index:
                    for i in range(start_index, len(heart_rate)):
                        context = heart_rate[i-12:i]
                        pred_point = PredictionService.predict_heart_rate(context, steps=1)[0]
                        hist_hr_preds[i] = pred_point
                
                # Futuro (12 pasos = 60 min)
                future_context_hr = heart_rate[-12:]
                future_hr_preds = PredictionService.predict_heart_rate(future_context_hr, steps=12)
                
                heart_predictions = hist_hr_preds + future_hr_preds
            except Exception as e:
                print(f"Error generating heart predictions: {e}")
                last_hr = heart_rate[-1] if heart_rate else 70
                heart_predictions = [None] * len(heart_rate) + [last_hr] * 12

        # --- PREDICCIONES SpO2 ---
        spo2_predictions = []
        if spo2 and len(spo2) >= 12:
            try:
                from services.prediction_service import PredictionService
                
                # Historia
                hist_spo2_preds = [None] * len(spo2)
                start_index = 12
                if len(spo2) > start_index:
                    for i in range(start_index, len(spo2)):
                        context = spo2[i-12:i]
                        pred_point = PredictionService.predict_spo2(context, steps=1)[0]
                        hist_spo2_preds[i] = pred_point
                
                # Futuro (12 pasos = 60 min)
                future_context_spo2 = spo2[-12:]
                future_spo2_preds = PredictionService.predict_spo2(future_context_spo2, steps=12)
                
                spo2_predictions = hist_spo2_preds + future_spo2_preds
            except Exception as e:
                print(f"Error generating spo2 predictions: {e}")
                last_spo2 = spo2[-1] if spo2 else 98
                spo2_predictions = [None] * len(spo2) + [last_spo2] * 12

        return {
            'dias': dias,
            'temperatura': temperatura,
            'heart_rate': heart_rate,
            'spo2': spo2,
            'predictions': predictions,           # Predicciones Temperatura
            'heart_predictions': heart_predictions, # Predicciones Ritmo Cardíaco
            'spo2_predictions': spo2_predictions,   # Predicciones SpO2
            'last_prediction_update': datetime.now().isoformat()
        }

    @staticmethod
    def get_global_stats():
        """Obtiene estadísticas globales de todos los pacientes"""
        # Estadísticas de pacientes
        total_pacientes = Paciente.query.count()
        normales = Paciente.query.filter_by(estado='normal').count()
        advertencia = Paciente.query.filter_by(estado='advertencia').count()
        peligro = Paciente.query.filter(Paciente.estado.in_(['peligro', 'critico'])).count()
        
        # Pacientes que requieren atención
        pacientes_criticos = Paciente.query.filter(
            Paciente.estado.in_(['advertencia', 'peligro', 'critico'])
        ).all()
        
        # Promedios de sensores (últimas 24h)
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        
        avg_temp = db.session.query(db.func.avg(SensorData.valor)).filter(
            SensorData.fecha >= last_24h
        ).scalar() or 0
        
        avg_hr = db.session.query(db.func.avg(SensorData.heart_rate)).filter(
            SensorData.fecha >= last_24h
        ).scalar() or 0
        
        avg_spo2 = db.session.query(db.func.avg(SensorData.spo2)).filter(
            SensorData.fecha >= last_24h
        ).scalar() or 0
        
        return {
            'total_pacientes': total_pacientes,
            'estados': {
                'normal': normales,
                'advertencia': advertencia,
                'peligro': peligro
            },
            'promedios_24h': {
                'temperatura': round(avg_temp, 1),
                'heart_rate': int(avg_hr),
                'spo2': int(avg_spo2)
            },
            'pacientes_criticos': [
                {
                    'id': p.id,
                    'nombre': p.nombre,
                    'estado': p.estado,
                    'foto': p.foto_url
                } for p in pacientes_criticos
            ]
        }
