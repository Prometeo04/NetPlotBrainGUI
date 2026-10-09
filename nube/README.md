# Servidor de renderizado en la nube

Este servidor es **opcional**. Sirve para que un equipo con pocos recursos
pueda pedirle a otra máquina que haga los renders pesados (el estilo `filled`,
`voxel size 1`, o vistas de 360° con muchos cuadros).

La aplicación lo usa desde el botón **Nube**: se le pone la dirección del
servidor y, cuando un render es demasiado pesado para el equipo local, ofrece
mandarlo allá.

---

## Antes de nada: ¿tus datos son privados?

Si trabajas con **datos de pacientes**, esto importa más que la comodidad.

Lo que este servidor recibe son **coordenadas y pesos de conexión** — no
imágenes cerebrales ni nombres. Pero una matriz de conectividad de un paciente
sigue siendo un dato de investigación, y según el reglamento de tu institución
puede contar como dato personal, sobre todo si se puede cruzar con otra
información.

Dos cosas que conviene tener claras:

- **Subir algo a un servicio en la nube no lo hace público.** Un servidor
  privado en Cloud Run o Hugging Face no queda indexado ni visible para
  cualquiera. Pero sí queda **en manos de un tercero**, en una computadora que
  no controlas, y normalmente fuera de tu país.
- **Para datos de pacientes, lo recomendable es la Opción A** (un equipo de tu
  propia red). Los datos nunca salen de la institución y no hace falta
  permiso de nadie.

Si vas a usar un proveedor externo con datos reales, consúltalo primero con el
responsable de tu laboratorio o con el comité de ética. Una alternativa
sencilla cuando solo necesitas una figura de prueba: **desplazar o barajar las
coordenadas** antes de mandarlas, de modo que lo que sale del equipo ya no
corresponda a ningún paciente.

---

## Opción A — Un equipo de tu red local (recomendado)

La mejor opción si tienes acceso a cualquier computadora con más memoria que la
tuya: otra máquina del laboratorio, una de escritorio en casa, un servidor del
instituto.

**Ventajas:** gratis, sin tarjeta de crédito, sin límites de tiempo, y los
datos nunca salen de tu red.

En el equipo que hará los renders:

```bash
cd nube
pip install "numpy>=1.24,<2.0"
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 7860
```

`--host 0.0.0.0` es lo que permite que otras máquinas de la red se conecten;
sin eso solo responde a sí mismo.

Ahora averigua la dirección IP de ese equipo:

- Windows: `ipconfig` → busca «Dirección IPv4»
- Linux / macOS: `ip addr` o `ifconfig`

Y en la aplicación, en el botón **Nube**, pon:

```
http://192.168.1.50:7860
```

(cambiando la IP por la del equipo). Usa el botón **Probar conexión** para
confirmar que responde.

Si no conecta, casi siempre es el firewall del equipo servidor. En Windows hay
que permitir el puerto 7860 para redes privadas.

Con Docker, si lo prefieres:

```bash
cd nube
docker build -t netplotbrain-servidor .
docker run -p 7860:7860 netplotbrain-servidor
```

---

## Opción B — Google Cloud Run

Buena opción técnica: escala a cero, así que **solo pagas por los segundos que
renderiza**. Para uso ocasional normalmente cae dentro de la capa gratuita.

**Requiere tarjeta de crédito** para activar la cuenta, aunque no te cobren.

```bash
# Instala gcloud y autentícate primero
gcloud run deploy netplotbrain-servidor \
  --source nube/ \
  --region us-central1 \
  --memory 4Gi \
  --cpu 2 \
  --timeout 900 \
  --allow-unauthenticated
```

Notas sobre esos valores:

- `--memory 4Gi` no es capricho: el estilo `filled` llega a usar bastante
  memoria y con menos de 2 GB el proceso muere a mitad del render.
- `--timeout 900` da 15 minutos; los renders pesados pasan de los 100 segundos.
- `--allow-unauthenticated` deja el servidor abierto a quien sepa la URL. Si
  vas a mandar datos reales, **no uses esa opción**: pon un token (ver abajo) o
  configura autenticación de verdad en Google Cloud.

Al terminar, `gcloud` te da una URL del tipo
`https://netplotbrain-servidor-xxxxx.run.app`. Esa es la que va en la
aplicación.

La primera petición después de un rato de inactividad tarda cerca de un minuto
porque el contenedor tiene que arrancar (*cold start*). La aplicación ya avisa
de esto mientras espera.

---

## Opción C — Hugging Face Spaces

Funciona, pero **los Spaces con Docker requieren una suscripción PRO**
(unos 9 USD al mes). El plan gratuito no los incluye.

Si ya tienes PRO:

1. Crea un Space nuevo con SDK **Docker**.
2. Sube `app.py`, `Dockerfile` y `requirements.txt` de esta carpeta.
3. Marca el Space como **privado** si vas a mandar datos reales.
4. La URL queda como `https://tu-usuario-tu-space.hf.space`.

---

## Qué NO funciona

- **Render.com (plan gratuito):** solo 512 MB de RAM. Medimos 530 MB para el
  render más sencillo, así que se queda corto incluso en el mejor caso.
- **Google Colab con un túnel (ngrok, Cloudflare):** técnicamente se puede,
  pero los términos de servicio de Colab prohíben expresamente usar un
  notebook a través de una interfaz web externa. Hacerlo arriesga la cuenta de
  Google. No vale la pena.

---

## Proteger el servidor con un token

Si el servidor va a estar accesible desde internet, ponle un token:

```bash
# Al arrancar el servidor
TOKEN_NETPLOTBRAIN="una-frase-larga-y-difícil" uvicorn app:app --host 0.0.0.0 --port 7860
```

En Cloud Run:

```bash
gcloud run deploy netplotbrain-servidor \
  --source nube/ \
  --set-env-vars TOKEN_NETPLOTBRAIN="una-frase-larga-y-difícil" \
  ...
```

Ese mismo token se escribe en la aplicación, en la ventana de **Nube**. Sin él,
el servidor responde `401`.

---

## Límites y variables de entorno

| Variable | Por defecto | Para qué sirve |
|---|---|---|
| `PORT` | `7860` | Puerto donde escucha |
| `TOKEN_NETPLOTBRAIN` | *(vacío)* | Si se define, exige token en cada petición |
| `MAX_NODOS` | `500` | Rechaza peticiones con más nodos |
| `MAX_ARISTAS` | `20000` | Rechaza peticiones con más aristas |

El tipo de nodo `parcels` se rechaza a propósito: necesita que el atlas esté en
el servidor y es tan lento que no encaja en una petición HTTP.

---

## Comprobar que funciona

```bash
curl https://tu-servidor/salud
```

Debe responder algo como:

```json
{"estado":"ok","version":"9.5","requiere_token":false,"max_nodos":500,"max_aristas":20000}
```
