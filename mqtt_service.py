"""
Servicio MQTT para manejar la conexión y recepción de datos
"""
import paho.mqtt.client as mqtt
import json
from datetime import datetime
from models import db, SensorData, Paciente
from flask import current_app

# Variables globales para lecturas actuales
current_readings = {
    'temperature': None,
    'heart_rate': None,
    'spo2': None,
    'last_update': None,
    'device_id': None
}

def init_mqtt(app):
    """Inicializa el cliente MQTT"""
    client = mqtt.Client()
    
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("MQTT Connected successfully")
            client.subscribe(app.config['MQTT_TOPIC'])
        else:
            print(f"Failed to connect, return code {rc}")
    
    def on_message(client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8', errors='ignore')
            
            # Ignorar mensajes de nuestros propios tópicos de visualización/control
            if topic.startswith('healthmonitor/display') or topic.startswith('healthmonitor/control'):
                return

            print(f"RAW MSG on {topic}: {payload}")
            
            data = json.loads(payload)
            
            print(f"Parsed data: {data}")
            
            if not isinstance(data, dict):
                print(f"Ignored data (not a dict): {data}")
                return

            # Actualizar lecturas actuales
            # Soporte para nuevo formato: device_uuid y objeto salud
            if 'device_uuid' in data:
                current_readings['device_id'] = data['device_uuid']
                print(f"DEBUG: Updated device_id from device_uuid: {current_readings['device_id']}")
            elif 'device_id' in data:
                current_readings['device_id'] = data['device_id']
                
            if 'temperature' in data and data['temperature'] is not None:
                current_readings['temperature'] = float(data['temperature'])
            
            # Manejo de objeto salud anidado (nuevo firmware)
            if 'salud' in data:
                print(f"DEBUG: 'salud' field found. Type: {type(data['salud'])}")
                if isinstance(data['salud'], dict):
                    salud = data['salud']
                    if 'hr' in salud and salud['hr'] is not None:
                        current_readings['heart_rate'] = int(salud['hr'])
                    if 'spo2' in salud and salud['spo2'] is not None:
                        current_readings['spo2'] = int(salud['spo2'])
                else:
                    print(f"DEBUG: 'salud' is not a dict: {data['salud']}")

            # Soporte retrocompatible (formato plano)
            else:
                if 'hr' in data and data['hr'] is not None:
                    current_readings['heart_rate'] = int(data['hr'])
                if 'spo2' in data and data['spo2'] is not None:
                    current_readings['spo2'] = int(data['spo2'])
            
            print(f"DEBUG: Intermediate current_readings: {current_readings}")
            
            current_readings['last_update'] = datetime.now()
            
            # Guardar en base de datos si tenemos AL MENOS UN DATO (lenient save)
            has_data = any([current_readings['temperature'] is not None, 
                           current_readings['heart_rate'] is not None, 
                           current_readings['spo2'] is not None])
            
            if has_data:
                with app.app_context():
                    # Obtener paciente por device_id
                    device_id = current_readings.get('device_id')
                    paciente = None
                    
                    if device_id:
                        paciente = Paciente.query.filter_by(device_id=device_id).first()
                        if paciente:
                            print(f"DEBUG: Found patient by device_id: {paciente.nombre}")
                    
                    if not paciente:
                        # Fallback: buscar paciente activo (comportamiento anterior)
                        paciente = Paciente.query.filter_by(activo=True).first()
                        if paciente:
                            print(f"DEBUG: Fallback to active patient: {paciente.nombre}")
                            # Si no teníamos device_id en el mensaje, lo tomamos del paciente activo para consistencia en la UI
                            if not current_readings['device_id']:
                                current_readings['device_id'] = paciente.device_id
                    
                    # Usar valores de fallback (1.0) solo si son estrictamente necesarios para la DB (aunque SensorData suele aceptar Null)
                    # Pero para que las gráficas no se rompan, solemos preferir el último valor o 1.0
                    temp_val = current_readings['temperature'] if current_readings['temperature'] is not None else 0.0
                    hr_val = current_readings['heart_rate'] if current_readings['heart_rate'] is not None else 0
                    spo2_val = current_readings['spo2'] if current_readings['spo2'] is not None else 0

                    record = SensorData(
                        paciente_id=paciente.id if paciente else None,
                        valor=temp_val,
                        heart_rate=hr_val,
                        spo2=spo2_val
                    )
                    db.session.add(record)
                    db.session.commit()
                    print(f"DEBUG: Datos guardados para paciente: {paciente.nombre if paciente else 'Desconocido'}")
                    
        except json.JSONDecodeError:
            print(f"Error decoding JSON from payload: {payload}")
        except Exception as e:
            print(f"Error processing MQTT message: {str(e)}")
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(app.config['MQTT_BROKER'], app.config['MQTT_PORT'], 60)
        client.loop_start()
        global mqtt_client
        mqtt_client = client
        return client
    except Exception as e:
        print(f"Error connecting to MQTT broker: {e}")
        return None

def get_current_readings():
    """Retorna las lecturas actuales"""
    return current_readings

def publish_message(topic, message):
    """Publica un mensaje en el tópico especificado"""
    if mqtt_client:
        mqtt_client.publish(topic, message)
        print(f"Published message to {topic}: {message}")
        return True
    return False
