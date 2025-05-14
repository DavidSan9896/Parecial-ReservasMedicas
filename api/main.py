from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import pika
import json
import uuid
import redis
from typing import Optional
import logging

class BookingRequest(BaseModel):
    patient_id: str
    doctor_id: str
    datetime: datetime

class BookingResponse(BaseModel):
    id: str
    status: str
    message: Optional[str] = None


# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sistema de Reservas Médicas")

# Conexión a Redis
try:
    redis_client = redis.Redis(host='redis', port=6379, db=0)
    redis_client.ping()  # Verificar conexión
    logger.info("Conexión a Redis establecida")
except Exception as e:
    logger.error(f"Error conectando a Redis: {e}")
    raise

@app.get("/booking/{booking_id}")
async def get_booking(booking_id: str):
    """Obtiene el estado de una reserva específica"""
    try:
        booking_data = redis_client.get(f"booking:{booking_id}")
        if booking_data:
            return json.loads(booking_data)
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    except Exception as e:
        logger.error(f"Error obteniendo reserva {booking_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Configuración de coneccion RabbitMQ
def get_rabbitmq_channel():
    try:
        credentials = pika.PlainCredentials('admin', '123')
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='rabbitmq',
                credentials=credentials,
                connection_attempts=5,
                retry_delay=5
            )
        )
        channel = connection.channel()
        channel.queue_declare(queue='booking_requests', durable=True)
        return channel
    except Exception as e:
        logger.error(f"Error conectando a RabbitMQ: {e}")
        raise


@app.post("/book", response_model=BookingResponse)
async def create_booking(booking: BookingRequest):
    try:
        booking_id = str(uuid.uuid4())

        # Almacenar estado inicial en Redis
        booking_data = {
            "status": "pending",
            "patient_id": booking.patient_id,
            "doctor_id": booking.doctor_id,
            "datetime": booking.datetime.isoformat()
        }

        redis_client.setex(f"booking:{booking_id}", 86400, json.dumps(booking_data))

        # Enviar a cola de RabbitMQ
        channel = get_rabbitmq_channel()

        message = {
            "booking_id": booking_id,
            "patient_id": booking.patient_id,
            "doctor_id": booking.doctor_id,
            "datetime": booking.datetime.isoformat()
        }

        channel.basic_publish(
            exchange='',
            routing_key='booking_requests',
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,
            )
        )

        logger.info(f"Reserva creada con ID: {booking_id}")
        return BookingResponse(id=booking_id, status="pending")

    except Exception as e:
        logger.error(f"Error creando reserva: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {"message": "API de Reservas Médicas"}


@app.get("/health")
async def health_check():
    health = {
        "status": "healthy",
        "redis": False,
        "rabbitmq": False
    }

    try:
        redis_client.ping()
        health["redis"] = True
    except:
        health["status"] = "unhealthy"

    try:
        channel = get_rabbitmq_channel()
        channel.close()
        health["rabbitmq"] = True
    except:
        health["status"] = "unhealthy"

    return health
