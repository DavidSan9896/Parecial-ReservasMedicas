import pika
import json
import time
import random
import redis
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conexión a Redis
try:
    redis_client = redis.Redis(host='redis', port=6379, db=0)
    redis_client.ping()
    logger.info("Conexión a Redis establecida")
except Exception as e:
    logger.error(f"Error conectando a Redis: {e}")
    raise


def process_booking(booking_data):
    """Simula el procesamiento de una reserva"""
    logger.info(f"Procesando reserva: {booking_data}")
    # Simular retraso entre 2 y 5 segundos
    time.sleep(random.uniform(2, 5))
    # Simular éxito/fallo aleatorio (80% éxito)
    return random.random() > 0.2


def update_booking_status(booking_id, status, message=None):
    """Actualiza el estado de la reserva en Redis"""
    try:
        booking_data = redis_client.get(f"booking:{booking_id}")
        if booking_data:
            booking = json.loads(booking_data)
            booking["status"] = status
            if message:
                booking["message"] = message
            redis_client.setex(f"booking:{booking_id}", 86400, json.dumps(booking))
            logger.info(f"Estado de reserva {booking_id} actualizado a: {status}")
        else:
            logger.warning(f"Reserva {booking_id} no encontrada en Redis")
    except Exception as e:
        logger.error(f"Error actualizando estado de reserva {booking_id}: {e}")
        raise


def callback(ch, method, properties, body):
    try:
        booking = json.loads(body)
        booking_id = booking["booking_id"]
        logger.info(f"Recibida nueva reserva {booking_id}")

        success = process_booking(booking)

        if success:
            status = "confirmed"
            message = "Reserva confirmada exitosamente"
        else:
            status = "rejected"
            message = "No hay disponibilidad para la fecha solicitada"

        update_booking_status(booking_id, status, message)

        # Publicar notificación
        notification = {
            "booking_id": booking_id,
            "status": status,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }

        ch.basic_publish(
            exchange='booking_notifications',
            routing_key='',
            body=json.dumps(notification),
            properties=pika.BasicProperties(
                delivery_mode=2  # mensaje persistente
            )
        )

        logger.info(f"Notificación enviada para reserva {booking_id}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except json.JSONDecodeError as e:
        logger.error(f"Error decodificando mensaje: {e}")
        ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        logger.error(f"Error procesando reserva: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main():
    while True:
        try:
            # Configurar credenciales de RabbitMQ
            credentials = pika.PlainCredentials('admin', '123')

            # Establecer conexión con retry
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host='rabbitmq',
                    credentials=credentials,
                    connection_attempts=5,
                    retry_delay=5,
                    heartbeat=600
                )
            )

            channel = connection.channel()

            # Declarar cola de trabajo
            channel.queue_declare(queue='booking_requests', durable=True)

            # Declarar exchange para notificaciones
            channel.exchange_declare(
                exchange='booking_notifications',
                exchange_type='fanout',
                durable=True
            )

            # Configurar prefetch count para distribuir la carga
            channel.basic_qos(prefetch_count=1)

            channel.basic_consume(
                queue='booking_requests',
                on_message_callback=callback
            )

            logger.info("Worker iniciado. Esperando mensajes...")
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as error:
            logger.error(f"Error de conexión a RabbitMQ: {error}")
            logger.info("Reintentando conexión en 5 segundos...")
            time.sleep(5)
        except Exception as error:
            logger.error(f"Error inesperado: {error}")
            logger.info("Reintentando en 5 segundos...")
            time.sleep(5)


if __name__ == "__main__":
    main()
