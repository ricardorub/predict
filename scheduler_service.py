from apscheduler.schedulers.background import BackgroundScheduler
from mqtt_service import publish_message
from datetime import datetime
from models import db, Notificacion

scheduler = BackgroundScheduler()

def init_scheduler(app):
    """Inicializa el planificador de tareas"""
    if not scheduler.running:
        scheduler.start()
    
    # Tarea de limpieza de datos antiguos
    from models import SensorData
    from datetime import timedelta

    def clean_old_data():
        with app.app_context():
            days = app.config.get('OLD_DATA_RETENTION_DAYS', 30)
            try:
                old_records = SensorData.query.filter(
                    SensorData.fecha < datetime.now() - timedelta(days=days)
                ).delete()
                db.session.commit()
                # print(f"Deleted {old_records} old records")
            except Exception as e:
                print(f"Error cleaning data: {e}")

    scheduler.add_job(func=clean_old_data, trigger="interval", hours=24, id='clean_old_data', replace_existing=True)

def execute_notification_job(app, notification_id, display_msg):
    """
    Ejecuta la notificación:
    1. Busca la notificación y el paciente en BD
    2. Resuelve el Device ID actual
    3. Envia mensaje a pantalla (OLED)
    4. Actualiza estado en BD
    """
    with app.app_context():
        try:
            # Recuperar Notificacion y Paciente
            notificacion = Notificacion.query.get(notification_id)
            if not notificacion:
                print(f"Error: Notification {notification_id} not found at execution time")
                return

            paciente = notificacion.paciente
            if not paciente:
                 print(f"Error: Patient not found for notification {notification_id}")
                 return
            
            device_id = paciente.device_id
            
            # Construir topicos al momento de la ejecución
            display_topic = None
            if device_id:
                display_topic = f"healthmonitor/display/{device_id}"
                print(f"Executing notification for device: {device_id}")
            else:
                 print(f"Warning: Patient {paciente.nombre} (ID: {paciente.id}) has no device_id.")
            
            # 1. Enviar mensaje a Pantalla
            if display_topic and display_msg:
                publish_message(display_topic, display_msg)
            
            
            # 3. Actualizar BD
            notificacion.enviado = True
            db.session.commit()
            print(f"Notificación {notification_id} marcada como enviada")
                
        except Exception as e:
            print(f"Error executing notification job {notification_id}: {e}")

def schedule_notification_event(app, run_date, notification_id, display_msg):
    """Programa el evento de notificación completo"""
    job = scheduler.add_job(
        func=execute_notification_job,
        trigger='date',
        run_date=run_date,
        args=[app, notification_id, display_msg]
    )
    return job.id

def cancel_job(job_id):
    """Cancela un trabajo programado"""
    try:
        scheduler.remove_job(job_id)
        return True
    except Exception as e:
        print(f"Error cancelling job {job_id}: {e}")
        return False
