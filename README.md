# 🏍️ Simulador de Experiencia de Cliente — MotoKaizen

Bienvenido al **Simulador Interactivo de Experiencia del Cliente** de **MotoKaizen**.

Este simulador fue diseñado especialmente para **personas no técnicas** (clientes, directivos, inversionistas, asesores comerciales) con el objetivo de demostrar, paso a paso y de manera visual e interactiva, cómo funciona el modelo de **autofinanciamiento colectivo (tandas de 30 personas)** frente a un crédito bancario tradicional.

---

## 🚀 Cómo abrir el Simulador (Fácil y Rápido)

### Opción 1: Con un solo clic en Windows (Recomendada para no técnicos)
1. Ve a la carpeta `simulador-cliente/`.
2. Haz **doble clic** en el archivo **`abrir-simulador.bat`** (o directamente en `index.html`).
3. ¡Listo! Se abrirá instantáneamente en tu navegador web predeterminado (Google Chrome, Microsoft Edge, etc.) sin necesidad de instalar Java, Docker o bases de datos.
   - **Nota:** abriéndolo como archivo (`file://`) no se puede usar la cámara ni el análisis de identidad; abre el servidor local para ejecutar las validaciones reales.

### Opción 2: Con cámara real (Python + OpenCV) — Recomendada para la demo
1. Asegúrate de tener **Python 3** instalado y ejecuta `python -m pip install -r requirements.txt`. Copia `.env.example` como `.env` y reemplaza `sk-proj-reemplazar` por tu clave real. El servidor carga `.env` automáticamente; la clave solo se usa en el backend y no se envía al navegador.
2. Haz **doble clic** en **`servidor-local.bat`**.
3. Se abre `http://localhost:5000` y la **verificación biométrica usa la cámara real** del computador: Python detecta el rostro en cada cuadro con OpenCV (`servidor-simulador.py`).
4. En el paso de documento, el botón **Abrir cámara** usa `getUserMedia()` y mantiene la cámara dentro de la aplicación cuando el sitio está en HTTPS o `localhost`. Los navegadores bloquean la cámara embebida en una IP LAN con `http://`; en ese caso la interfaz muestra que se requiere un contexto seguro y no abre una cámara externa.
   - Para probarlo desde iPhone en la misma WiFi, ejecuta `compartir-celular.bat`. Este inicia HTTPS en `https://<IP-LOCAL>:5000`; Safari mostrará una advertencia por el certificado local, que debes aceptar para permitir la cámara.
5. La primera vez que se abre el escáner aparece un tutorial de tres pasos sobre iluminación, estabilidad y encuadre. Al terminarlo u omitirlo, la preferencia se guarda en el navegador y las siguientes capturas abren directamente la cámara.
   - Además, la **foto del documento de identidad se clasifica en el backend** mediante OpenAI Decisions API. Solo se aceptan `cedula_colombiana` y `pasaporte` por encima del umbral configurado; la clasificación visual no afirma autenticidad ni pertenencia al usuario.
   - El OCR procesa varias versiones de la captura (contraste, umbral, perspectiva y modos de lectura) para tolerar reflejos, inclinación y fotos tomadas desde iPhone.
   - Si la cámara no está disponible o el navegador la bloquea, el flujo queda detenido con un mensaje de recuperación; no se confirma una identidad sin una respuesta real del servidor.

### Opción 3: Desde el Servidor Backend Spring Boot
Si levantas el backend (`docker compose up` o `mvnw spring-boot:run`):
1. Abre tu navegador en: [http://localhost:8080/](http://localhost:8080/)
2. El simulador está integrado en los recursos estáticos públicos del servidor; las comprobaciones dependen de los servicios reales disponibles.

---

## 🎯 ¿Qué demuestra este simulador de principio a fin?

El recorrido sigue las **4 etapas clave** del viaje de un cliente en MotoKaizen, desde que escanea el producto en la tienda hasta su asignación formal al grupo:

### 1. Producto Escaneado en Tienda (Código QR) 📱
- Simula el flujo real de tienda: el cliente toma la foto al producto y **escanea su código QR** en un establecimiento con convenio.
- Ficha del producto escaneado: marca, modelo, especificaciones (cilindraje, potencia, rendimiento) y **valor comercial**.
- **Métodos de pago disponibles:**
  - **Convenio de Financiamiento MotoKaizen** (🏪 Tienda Aliada): autofinanciamiento colectivo en tandas de 30, cuota fija en 30 pagos, sin crédito bancario ni consultas de Datacrédito.
  - **Pago de contado en tienda**.
- Botón **"Sí, quiero pagar con el Plan de Moto Kaizen →"** para aceptar el convenio.
- Selector **"Elegir otro producto de la tienda"**: catálogo interactivo con los 6 modelos (**Yamaha NMAX 155**, **Bajaj Pulsar NS200**, **Suzuki Gixxer 150**, **KTM Duke 200**, **Honda CB 125F**, **Yamaha MT-03**), fichas técnicas y precio de contado.

### 2. Configuración del Plan & Comparativa vs Banco Tradicional ⚙️
- **Elección de frecuencia:**
  - **Plan Quincenal (Cada 15 días):** 30 cuotas en 15 meses de plazo. ¡Entregas más rápidas!
  - **Plan Mensual (Cada 30 días):** 30 cuotas en 30 meses de plazo. Cuota más baja y cómoda.
- **Comparativa Financiera en Vivo:**
  - Muestra la cuota fija justa de MotoKaizen (**0% tasa de interés usurera**).
  - Compara con un crédito bancario tradicional (38% E.A.), revelando el ahorro en intereses.

### 3. Validación de Datos, Documentos y Biometría 🔐
- Formulario del titular: nombres, **correo electrónico**, número móvil/WhatsApp, ciudad y actividad económica.
- **Documento de identidad:** tipo, número y **foto del documento** clasificada en el backend mediante OpenAI Decisions API. En este entorno de pruebas solo se aceptan visualmente cédula colombiana o pasaporte; la clasificación no afirma autenticidad ni pertenencia al usuario.
- **Verificación de presencia con cámara real:** accede a la cámara del dispositivo y detecta que haya un rostro frente al marco mediante **OpenCV (Python)** en el servidor. Tras una animación breve de escaneo, habilita el avance; no compara el rostro con el documento ni afirma identidad.
- Aceptación del tratamiento de datos.
- Confirmación de **disponibilidad garantizada de grupo** (entorno de prueba).

### 4. Asignación de Grupo + Confirmación por Correo 📧
- Asignación **aleatoria de cupo (1–30)** dentro de un grupo formal de 30 integrantes, con código de grupo único.
- Visualización de la comunidad en mosaico: tu cupo resaltado como "¡Tú!" junto a 29 compañeros de distintas ciudades de Colombia.
- Comprobación del fondo común: **30 de 30 cuotas pagadas a tiempo** = Monto exacto para adquirir 1 moto de contado.
- **Notificación por correo:** se simula el envío al correo del titular con su código de grupo y cupo asignado.

---

## 💡 Ventajas Técnicas del Simulador
- **Biometría con OpenCV:** `servidor-simulador.py` expone `GET /api/status` y `POST /api/validate-face` (Haar cascade `haarcascade_frontalface_default.xml`); el navegador envía cuadros de la cámara cada 500 ms. Cuando se detecta un rostro, ejecuta una animación breve de escaneo y habilita el avance. No compara la cara con el documento.
- **Captura documental móvil:** la cámara trasera preferida se muestra dentro de la aplicación y la foto se envía al endpoint OCR antes de habilitar el paso facial. Para usarla desde un celular en la red local, sirve el proyecto mediante HTTPS; `http://IP:5000` no permite cámara embebida por las políticas del navegador.
- **Resultado documental:** el botón `Continuar al reconocimiento facial` solo aparece después de que el servidor responde con un documento válido. Si OCR falla, se muestra el motivo, se permite repetir el escaneo y no se habilita el avance.
- **Clasificación documental:** `POST /api/verificar-documento` envía la imagen al SDK oficial de OpenAI y usa una pregunta `choice` de Decisions API. Requiere `OPENAI_API_KEY`; si la API falla no se aprueba la imagen.
- **Autónomo y Portátil:** Funciona tanto abriéndolo directamente en el explorador como desplegado en el backend.
- **Diseño Formal Bancario & Responsive:** Tema institucional claro (fondo blanco, tarjetas blancas, azul marino/naranja), optimizado para celulares, tablets y computadoras de escritorio.
- **Pantallas de Procesamiento:** Overlays de carga con pasos progresivos que recrean la validación digital del consorcio.
- **Accesible:** Anillos de foco visibles, objetivos táctiles de 44px y soporte de `prefers-reduced-motion`.
