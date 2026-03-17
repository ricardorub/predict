"""
Rutas para gestión de pacientes
"""
from flask import Blueprint, render_template, request, jsonify
from controllers.patient_controller import PatientController
from utils import login_required

patient_bp = Blueprint('patients', __name__)

@patient_bp.route('/patients')
@login_required
def index():
    """Vista principal de lista de pacientes"""
    pacientes = PatientController.get_all_patients()
    stats = PatientController.get_patients_stats()
    
    return render_template('patients.html', 
                         pacientes=pacientes,
                         total_pacientes=stats['total'],
                         pacientes_normales=stats['normales'],
                         pacientes_advertencia=stats['advertencia'],
                         pacientes_criticos=stats['criticos'])

# API Endpoints

@patient_bp.route('/api/pacientes', methods=['POST'])
@login_required
def create_patient():
    """Crear nuevo paciente"""
    try:
        data = request.json
        paciente = PatientController.create_patient(data)
        return jsonify({'message': 'Paciente creado exitosamente', 'id': paciente.id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@patient_bp.route('/api/pacientes/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_patient(id):
    """Gestionar un paciente específico (Ver, Editar, Eliminar)"""
    try:
        if request.method == 'GET':
            paciente = PatientController.get_patient_by_id(id)
            return jsonify({
                'id': paciente.id,
                'nombre': paciente.nombre,
                'edad': paciente.edad,
                'email': paciente.email,
                'telefono': paciente.telefono,
                'device_id': paciente.device_id,
                'estado': paciente.estado,
                'ultima_visita': paciente.ultima_visita.isoformat() if paciente.ultima_visita else None,
                'notas': paciente.notas,
                'foto_url': paciente.foto_url
            })
        
        elif request.method == 'PUT':
            data = request.json
            PatientController.update_patient(id, data)
            return jsonify({'message': 'Paciente actualizado exitosamente'})
        
        elif request.method == 'DELETE':
            PatientController.delete_patient(id)
            return jsonify({'message': 'Paciente eliminado exitosamente'})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@patient_bp.route('/api/pacientes/<int:id>/activar', methods=['POST'])
@login_required
def activate_patient(id):
    """Activar monitoreo para un paciente"""
    try:
        paciente = PatientController.activate_patient_monitoring(id)
        return jsonify({
            'message': f'Monitoreo activado para {paciente.nombre}',
            'paciente_id': paciente.id,
            'paciente_nombre': paciente.nombre
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400
@patient_bp.route('/api/pacientes/<int:id>/notificaciones', methods=['GET'])
@login_required
def get_notifications(id):
    """Obtener notificaciones de un paciente"""
    try:
        from models import Notificacion
        notificaciones = Notificacion.query.filter_by(paciente_id=id).order_by(Notificacion.fecha_hora).all()
        return jsonify([{
            'id': n.id,
            'fecha_hora': n.fecha_hora.isoformat(),
            'enviado': n.enviado
        } for n in notificaciones])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@patient_bp.route('/api/pacientes/<int:id>/notificaciones', methods=['POST'])
@login_required
def schedule_notification(id):
    """Programar notificación (Mensaje Pantalla)"""
    try:
        from flask import current_app
        data = request.json
        fecha_hora_str = data.get('fecha_hora')
        mensaje = data.get('mensaje') or "Recordatorio" # Mensaje para la pantalla
        
        if not fecha_hora_str:
            return jsonify({'error': 'Fecha y hora son requeridas'}), 400
            
        # Parsear fecha y hora
        from datetime import datetime
        run_date = datetime.fromisoformat(fecha_hora_str)
        
        # Obtener datos del paciente para los topicos
        paciente = PatientController.get_patient_by_id(id)
        device_id = paciente.device_id
        
        # Programar con el nuevo scheduler que maneja ambos y actualiza BD
        from scheduler_service import schedule_notification_event
        
        # Crear registro en BD primero para tener el ID
        from models import db, Notificacion
        notificacion = Notificacion(
            paciente_id=id,
            fecha_hora=run_date,
            enviado=False
            # No guardamos 'mensaje' en BD para no romper esquema, 
            # pero se pasa al job scheduler
        )
        db.session.add(notificacion)
        db.session.commit()
        
        # Ahora programar el job pasándole el ID de la notificación
        # Los tópicos se resuelven dinámicamente al ejecutar
        job_id = schedule_notification_event(
            current_app._get_current_object(), # Pasar app real para contexto
            run_date, 
            notificacion.id,
            mensaje
        )
        
        # Actualizar job_id
        notificacion.job_id = job_id
        db.session.commit()
        
        return jsonify({
            'message': 'Notificación programada exitosamente',
            'id': notificacion.id,
            'scheduled_for': run_date.isoformat()
        })
    except ValueError as e:
        return jsonify({'error': 'Formato de fecha inválido'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@patient_bp.route('/api/pacientes/<int:patient_id>/notificaciones/<int:id>', methods=['DELETE'])
@login_required
def delete_notification(patient_id, id):
    """Eliminar una notificación programada"""
    try:
        from models import db, Notificacion
        from scheduler_service import cancel_job
        
        notificacion = Notificacion.query.get_or_404(id)
        
        # Cancelar job si existe
        if notificacion.job_id:
            cancel_job(notificacion.job_id)
            
        db.session.delete(notificacion)
        db.session.commit()
        
        return jsonify({'message': 'Notificación eliminada exitosamente'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@patient_bp.route('/api/pacientes/<int:id>/enviar-mqtt', methods=['POST'])
@login_required
def send_mqtt_message(id):
    """Enviar mensaje MQTT inmediato a un paciente (OLED)"""
    try:
        data = request.json
        message = data.get('message', 'Hola') 
        
        paciente = PatientController.get_patient_by_id(id)
        
        from mqtt_service import publish_message
        success_count = 0
        
        # 1. Enviar mensaje a Pantallas (Personal + Broadcast)
        if paciente.device_id:
            if publish_message(f"healthmonitor/display/{paciente.device_id}", message):
                success_count += 1
        
        if publish_message("healthmonitor/display", message): # Broadcast
             success_count += 1
        
        if success_count > 0:
            return jsonify({'message': f'Mensaje enviado ({success_count} acciones)'})
        else:
            return jsonify({'error': 'Error al enviar mensajes MQTT'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400
