import os
import json
import uuid
import boto3
from fastapi import FastAPI, UploadFile, File, Form, HTTPException

expediente = "740652"
nombre_completo = "Jorge Antonio Flores Burgos"

# ---------- Configuración AWS ----------
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET  = os.getenv("S3_BUCKET", f"practica-4-{expediente}")
SQS_URL    = os.getenv("SQS_QUEUE_URL")  # URL completa de la cola cola-boletines

s3  = boto3.client("s3",  region_name=AWS_REGION)
sqs = boto3.client("sqs", region_name=AWS_REGION)

app = FastAPI(title="Practica 4 - Emisor")


@app.post("/boletines")
async def crear_boletin(
    file: UploadFile = File(...),
    contenido: str = Form(...),
    correo: str = Form(...)
):
    # ---------- Validaciones ----------
    if not file:
        raise HTTPException(status_code=400, detail="Archivo requerido")

    if not file.filename or file.filename.strip() == "":
        raise HTTPException(status_code=400, detail="El archivo debe tener nombre")

    if not contenido or contenido.strip() == "":
        raise HTTPException(status_code=400, detail="Contenido vacío")

    if not correo or correo.strip() == "":
        raise HTTPException(status_code=400, detail="Correo requerido")

    if "@" not in correo or "." not in correo:
        raise HTTPException(status_code=400, detail="Correo inválido")

    contenido_archivo = await file.read()
    if not contenido_archivo:
        raise HTTPException(status_code=400, detail="El archivo está vacío")

    if not SQS_URL:
        raise HTTPException(status_code=500, detail="SQS_QUEUE_URL no configurada")

    # ---------- Subir imagen a S3 ----------
    key = f"boletines/{uuid.uuid4()}-{file.filename}"
    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=contenido_archivo,
            ContentType=file.content_type or "application/octet-stream",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error subiendo a S3: {e}")

    s3_url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"

    # ---------- Publicar mensaje en SQS ----------
    mensaje = {
        "contenido": contenido,
        "correo": correo,
        "imagen_url": s3_url,
    }
    try:
        sqs.send_message(QueueUrl=SQS_URL, MessageBody=json.dumps(mensaje))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enviando a SQS: {e}")

    return {
        "mensaje": "Boletín recibido correctamente",
        "archivo": file.filename,
        "tipo_contenido": file.content_type,
        "tamano_bytes": len(contenido_archivo),
        "contenido": contenido,
        "correo": correo,
        "imagen_url": s3_url,
    }


if __name__ == "__main__":
    print("Servicio emisor listo")
    print(f"Alumno: {nombre_completo} | Expediente: {expediente}")