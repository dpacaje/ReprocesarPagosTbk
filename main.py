import os
import time
import smtplib
import requests
from mysql.connector import pooling, Error
from dotenv import load_dotenv
from email.message import EmailMessage

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "connect_timeout": 30,
    "pool_name": "mypool",
    "pool_size": 4,
}

DATABASES = [
    "portal_calera",
    "portal_cholchol",
    "portal_curacautin",
    "portal_maipo",
    "portal_olivar",
    "portal_pichidegua",
    "portal_pirque",
    "portal_rengo"
]

API_URL = os.getenv("TBK_URL")
API_MAX_FAILURES = int(os.getenv("TBK_MAX_FAILURES"))

class ScriptProcesador:
    def __init__(self):
        self.connection_pool = None
        self.registros_pendientes = []
        self.errores_api = 0
        self.reporte_final = []
    
    def inicializar_pool(self):
        try:
            self.connection_pool = pooling.MySQLConnectionPool(**DB_CONFIG)
        except Error as e:
            self.notificar_error_critico(f"Error al crear el pool: {e}")
            exit(1)
    
    def consultar_bases_de_datos(self):
        for db_name in DATABASES:
            exito = False
            for intento in range(2):
                try:
                    conn = self.connection_pool.get_connection()
                    conn.database = db_name
                    cursor = conn.cursor(dictionary=True)

                    cursor.execute(f"USE {db_name}")

                    cursor.execute("SELECT * FROM view_intentos_de_pagos")
                    rows = cursor.fetchall()

                    for row in rows:
                        row['source_db'] = db_name
                        self.registros_pendientes.append(row)
                    
                    cursor.close()
                    conn.close()
                    exito = True
                    break
                except Error as e:
                    print(f"Intento {intento+1} fallido en {db_name}: {e}")
                    time.sleep(2)
            
            if not exito:
                mensaje = f"CRÍTICO: No se pudo acceder a la DB {db_name} tras reintentos."
                self.notificar_error_critico(mensaje)
                exit(1)
    
    def consultar_api_externa(self):
        notificacion_importantes = []

        with requests.Session() as session:
            for registro in self.registros_pendientes:
                if self.errores_api >= API_MAX_FAILURES:
                    self.notificar_error_critico("Proceso detenido: Se superó el limite de 5 fallos en la API.")
                    exit(1)
                
                exito_api = False
                for intento in range(2):
                    try:
                        token_recortado = str(registro['token'])[-64:]
                        response = session.get(f"{API_URL}?aplicacionId={registro['tbkid']}&token={token_recortado}", timeout=20)
                        response.raise_for_status()
                        data = response.json()

                        if data.get('status') == 'AUTHORIZED' and data.get('response_code') == 0:
                            notificacion_importantes.append({
                                "id": registro["id"],
                                "cliente": registro["cliente"],
                                "db": registro["source_db"],
                                "tipo": registro["tipo"]
                            })
                            print(f"Registro Pagado ID {registro['id']} | DB: {registro['source_db']} | CLIENTE: {registro['cliente']}")
                        
                        exito_api = True
                        break
                    except Error as e:
                        print(f"Error API intento {intento+1} para ID {registro['id']}: {e}")
                        time.sleep(1)
                
                if not exito_api:
                    self.errores_api += 1
                    self.reporte_final.append(f"Fallo persistente API: Registro {registro['id']} (DB: {registro['source_db']})")

        return notificacion_importantes

    def enviar_correo(self, asunto, cuerpo):
        msg = EmailMessage()
        msg.set_content(cuerpo)
        msg['Subject'] = asunto
        msg['From'] = os.getenv("EMAIL_USER")
        msg['To'] = os.getenv("EMAIL_RECEIVER")

        try:
            with smtplib.SMTP(os.getenv("EMAIL_SERVER"), int(os.getenv("EMAIL_PORT"))) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))
                smtp.send_message(msg)
            print("Correo enviado con éxito")
        except Error as e:
            print(f"Error enviando correo: {e}")
    
    def notificar_error_critico(self, mensaje):
        print(mensaje)
        self.enviar_correo("FALLO CRÍTICO SCRIPT", mensaje)
    
    def ejecutar(self):
        print("Iniciando proceso...")
        self.inicializar_pool()
        self.consultar_bases_de_datos()

        print(f"Registros encontrados: {len(self.registros_pendientes)}. Consultando API...")
        alertas = self.consultar_api_externa()

        cuerpo_correo = "Resumen de ejecución:\n"
        cuerpo_correo += f"- Total procesados: {len(self.registros_pendientes)}\n"
        cuerpo_correo += f"- Alertas detectadas: {len(alertas)}\n\n"

        if alertas:
            cuerpo_correo += "REGISTROS QUE REQUIEREN ATENCIÓN:\n"
            for a in alertas:
                cuerpo_correo += f"ID: {a['id']} | TIPO: {a['tipo']} | DB: {a['db']} | CLIENTE: {a['cliente']}\n"
        
        if self.reporte_final:
            cuerpo_correo += "\nERRORES NO BLOQUEANTES DURANTE LA EJECUCIÓN:\n"
            cuerpo_correo += "\n".join(self.reporte_final)
        
        self.enviar_correo("Reporte Proceso", cuerpo_correo)
        print("Proceso finalizado exitosamente.")

if __name__ == "__main__":
    procesador = ScriptProcesador()
    procesador.ejecutar()