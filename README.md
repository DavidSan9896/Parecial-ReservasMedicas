--David Santiago Cubuillos Méndez
Caso práctico: Una clínica en línea necesita gestionar reservas de citas médicas. Cada solicitud de cita debe pasar por 
un proceso de confirmación asíncrono (mediante simulación de disponibilidad médica), y notificar al paciente cuando la
cita es confirmada o rechazada. El sistema debe ser robusto ante fallos y permitir crecimiento horizontal.

Se usaron las siguientes Tecnologías 
Lenguaje/Framework: Python + FastAPI
Mensajería: RabbitMQ
Contenedores: Docker + Docker Compose
Almacenamiento: SQLite (ligera) para persistencia de estado

Criterios Arquitectónicos
Se usao una unica cola de trabajo booking_queue para las reservas 
Esto nos  permite mantener la lógica centralizada, facilitando 
el escalado horizontal de los workers y reduce la complejidad


para ejecutar 
use los comandos 

git clone https://github.com/DavidSan9896/Parecial-ReservasMedicas.git
cd Parecial-ReservasMedicas

luego levante 
los contenedores usado el comando en la ruta 
docker-compose up --build 
![image](https://github.com/user-attachments/assets/4a136247-b749-4305-9b78-3873711948da)

verifique con 
docker ps 
que esten levantados si todos estan asi quiere decir que funciono 

![image](https://github.com/user-attachments/assets/6af8ff0b-b451-4188-9065-a12716bf4080)

ahora ingrese al siguiente link para ver la informaccion de rabik 
http://localhost:15672/

le pedira unas credeciales las que se usaron fueron 
user : admin 
kaey: 123 
![image](https://github.com/user-attachments/assets/2c591f7d-931f-44ed-843c-1415a2327cf0)

como vemos esta funcionado 

![image](https://github.com/user-attachments/assets/7df0590e-009d-41de-ba89-ca9a8be576b5)

puedes probarlo de dos formas una usado posman o desde la terminal 

con posman usa la siguiente ruta

http://localhost:8080/book
y pon los datos que prefieras siguiendo esta estructura 

{
    "patient_id": "PAC2",
    "doctor_id": "DOC001",
    "datetime": "2024-03-25T15:30:00Z"
}

como vemos fue okey 
![image](https://github.com/user-attachments/assets/f5045e33-28b5-4571-8cb5-486c918681b7)

desde la terminal puedes usar 
el siguiente comando puedes cambiar los valores 

curl -X POST http://localhost:8080/book \
-H "Content-Type: application/json" \
-d '{
    "patient_id": "PAC001",
    "doctor_id": "DOC001",
    "datetime": "2024-03-21T15:30:00Z"
}'
y se vera asi 
![image](https://github.com/user-attachments/assets/7d2781f4-91f1-4448-a118-45d5afc56ae3)


lo cual fue recibido puedes tener el rabik a lado para ver los mensajes 

![image](https://github.com/user-attachments/assets/de904b3f-4761-422c-86b2-268d68658b85)

ahora pudes usar tambien el skip de prueba esotos paso  
1. Asegúrate de que todos los servicios estén corriendo:
2. Ejecuta el script:
     python api/test_integration.py
en la terinal como se ve  ![image](https://github.com/user-attachments/assets/0bd20677-6e7a-49d4-936c-b30b12218fc5)

y despues veras lo siguiente 
![image](https://github.com/user-attachments/assets/0f5aa1a3-d04e-43cb-acb5-e9301689b8d0)
![image](https://github.com/user-attachments/assets/98002df9-7e65-4379-912c-d6e178984ad4)


Requisitos Técnicos Cumplidos 

API REST
POST /book
Crea una nueva reserva médica con los datos del paciente y la franja horaria deseada.
{
  "patient_name": "Juan Pérez",
  "time_slot": "2025-05-13T15:00:00"
}

GET /booking/{id}
Consulta el estado actual de una reserva: pending, confirmed, rejected
para eso 
# Reemplaza BOOKING_ID con el ID que recibiste al crear la reserva ese es esta que se ve en la imagen 
en posman 
![image](https://github.com/user-attachments/assets/d597158a-d67f-49e2-8cb0-f2ecedd03e38) y en terminal 
![image](https://github.com/user-attachments/assets/e17488fd-426e-46a3-a1f7-426582de560a)

curl http://localhost:8080/booking/BOOKING_ID

RabbitMQ – Work Queues

Las reservas se procesan mediante colas de trabajo., se implementa en esta oparte del  main.py y en
 En worker.py - Consumo de la cola


![image](https://github.com/user-attachments/assets/9e823702-4dcb-46fe-aba5-e65d8a279abb)

# En worker.py 

Cada reserva pasa por una simulación de confirmación médica con un retraso aleatorio entre 2 y 5 segundos.

![image](https://github.com/user-attachments/assets/2265e9c5-89df-4071-b4a0-80aeffed3b69)

En caso de fallo, se aplica una política de reintentos (máximo 3 veces).
![image](https://github.com/user-attachments/assets/7c0b997b-8395-480b-a17c-c16c0acfe0aa)

configuraccion de la cola para los reitentos 
![image](https://github.com/user-attachments/assets/ff860f17-13a6-447f-9dcd-4c451f4144f2)

Políticas de reintentos y su justificación
Controlar los reintentos mejora la resiliencia del sistema ante errores temporales
Se mantiene la trazabilidad de fallos sin impactar la cola principal
     
Docker Compose
La aplicación se orquesta con docker-compose.yml, definiendo:
Servicios:
api: Servicio FastAPI para exponer endpoints.
worker: Encargado del procesamiento de reservas.
notifier: Suscriptor a notificaciones del exchange.
rabbitmq: Servicio de mensajería.







