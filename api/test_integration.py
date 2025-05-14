import requests
import random
from datetime import datetime, timedelta
import json
import time
import sys
from typing import Dict, List
import logging

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración
API_URL = "http://localhost:8080"
NUM_REQUESTS = 5  # Número de reservas a crear por prueba

# Datos de prueba
DOCTORS = ["DOC001", "DOC002", "DOC003", "DOC004", "DOC005"]
PATIENTS = ["PAC001", "PAC002", "PAC003", "PAC004", "PAC005"]

class TestRunner:
    def __init__(self):
        self.successful_tests = 0
        self.failed_tests = 0
        self.bookings: List[Dict] = []

    def generate_datetime(self) -> str:
        """Genera una fecha aleatoria en los próximos 30 días"""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=30)
        random_date = start_date + timedelta(
            days=random.randint(0, (end_date - start_date).days),
            hours=random.randint(8, 17),
            minutes=random.choice([0, 15, 30, 45])
        )
        return random_date.isoformat()

    def test_health_endpoint(self) -> bool:
        """Prueba el endpoint de salud"""
        logger.info("Probando endpoint de salud...")
        try:
            response = requests.get(f"{API_URL}/health")
            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"Estado del sistema: {json.dumps(health_data, indent=2)}")
                return all([health_data["redis"], health_data["rabbitmq"]])
            return False
        except Exception as e:
            logger.error(f"Error en health check: {e}")
            return False

    def test_root_endpoint(self) -> bool:
        """Prueba el endpoint raíz"""
        logger.info("Probando endpoint raíz...")
        try:
            response = requests.get(API_URL)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Respuesta del endpoint raíz: {data}")
                return "message" in data
            return False
        except Exception as e:
            logger.error(f"Error en endpoint raíz: {e}")
            return False

    def create_booking(self) -> Dict:
        """Crea una reserva y retorna la respuesta"""
        data = {
            "patient_id": random.choice(PATIENTS),
            "doctor_id": random.choice(DOCTORS),
            "datetime": self.generate_datetime()
        }

        response = requests.post(f"{API_URL}/book", json=data)
        if response.status_code == 200:
            result = response.json()
            result["request_data"] = data
            return result
        raise Exception(f"Error {response.status_code}: {response.text}")

    def test_booking_creation(self) -> bool:
        """Prueba la creación de múltiples reservas"""
        logger.info(f"\nCreando {NUM_REQUESTS} reservas de prueba...")
        success = 0

        for i in range(NUM_REQUESTS):
            try:
                booking = self.create_booking()
                self.bookings.append(booking)
                logger.info(f"Reserva {i+1} creada - ID: {booking['id']}")
                logger.info(f"Datos: {json.dumps(booking['request_data'], indent=2)}")
                success += 1
                time.sleep(0.5)  # Pequeña pausa entre reservas
            except Exception as e:
                logger.error(f"Error en reserva {i+1}: {e}")

        return success == NUM_REQUESTS

    def monitor_bookings(self, timeout=30) -> bool:
        """Monitorea el estado de las reservas por un tiempo determinado"""
        logger.info(f"\nMonitoreando estado de las reservas por {timeout} segundos...")
        start_time = time.time()
        completed = set()

        while time.time() - start_time < timeout:
            for booking in self.bookings:
                if booking['id'] in completed:
                    continue

                try:
                    response = requests.get(f"{API_URL}/booking/{booking['id']}")
                    if response.status_code == 200:
                        status = response.json()
                        if status['status'] in ['confirmed', 'rejected']:
                            logger.info(f"Reserva {booking['id']} procesada - Estado: {status['status']}")
                            if 'message' in status:
                                logger.info(f"Mensaje: {status['message']}")
                            completed.add(booking['id'])
                except Exception as e:
                    logger.error(f"Error monitoreando reserva {booking['id']}: {e}")

            if len(completed) == len(self.bookings):
                logger.info("Todas las reservas han sido procesadas")
                return True

            time.sleep(2)  # Esperar antes de la siguiente verificación

        remaining = len(self.bookings) - len(completed)
        logger.warning(f"{remaining} reservas no fueron procesadas en el tiempo esperado")
        return False

    def run_all_tests(self):
        """Ejecuta todas las pruebas"""
        tests = [
            ("Health Check", self.test_health_endpoint),
            ("Root Endpoint", self.test_root_endpoint),
            ("Booking Creation", self.test_booking_creation),
            ("Booking Processing", self.monitor_bookings)
        ]

        logger.info("Iniciando pruebas de integración...")

        for test_name, test_func in tests:
            logger.info(f"\n{'='*50}")
            logger.info(f"Ejecutando prueba: {test_name}")
            try:
                result = test_func()
                if result:
                    logger.info(f"✅ {test_name}: EXITOSO")
                    self.successful_tests += 1
                else:
                    logger.error(f"❌ {test_name}: FALLIDO")
                    self.failed_tests += 1
            except Exception as e:
                logger.error(f"❌ {test_name}: ERROR - {str(e)}")
                self.failed_tests += 1

        self.print_summary()

    def print_summary(self):
        """Imprime el resumen de las pruebas"""
        logger.info("\n" + "="*50)
        logger.info("RESUMEN DE PRUEBAS")
        logger.info("="*50)
        logger.info(f"Total de pruebas: {self.successful_tests + self.failed_tests}")
        logger.info(f"Pruebas exitosas: {self.successful_tests}")
        logger.info(f"Pruebas fallidas: {self.failed_tests}")
        logger.info("="*50)

        if self.failed_tests > 0:
            sys.exit(1)

if __name__ == "__main__":
    test_runner = TestRunner()
    test_runner.run_all_tests()