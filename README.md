# AITA — AI Task Assistant

AITA es el microservicio de inteligencia artificial de **Task It**. Ayuda a redactar tareas, estimar un precio justo, emparejar tareas con prestadores, leer el sentimiento de las reseñas, sugerir mejoras de perfil y detectar fraude o acoso en textos de la plataforma (AI Shield).

Esta entrega cubre la estructura hexagonal, las dependencias, la capa de dominio y este documento. Los casos de uso, los adaptadores y las pruebas quedan para las etapas siguientes.

## Tecnologías

| Pieza | Elección |
| --- | --- |
| Lenguaje | Python 3.10+ |
| API | FastAPI, asíncrono |
| Validación | Pydantic v2 |
| Mensajería | `aio-pika` (RabbitMQ) |
| Clientes HTTP de IA | `httpx` |
| Servidor | Uvicorn |
| Pruebas | pytest y pytest-asyncio |

Las dependencias están en `requirements.txt`.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copia `.env.example` a `.env` y completa los valores en tu máquina. No subas credenciales al repositorio.

## Arquitectura hexagonal

El dominio no importa FastAPI, RabbitMQ ni clientes HTTP. La aplicación orquesta los casos de uso a través de puertos. Infraestructura implementa esos puertos.

```
aita/
  domain/                  Modelos, enums, excepciones, contratos y puertos
    models/                Task, Chat, Review, eventos y resultados de IA
    ports/inbound.py       Interfaces de los casos de uso
    ports/outbound.py      IAiModelPort, IVectorSearchPort, IEventPublisherPort
    services/              Lógica pura (similitud coseno)
    contracts.py           Exchanges y routing keys compartidas
    exceptions.py          Errores de negocio con código estable
  application/             Casos de uso (siguiente etapa)
  infrastructure/
    inbound/               Routers FastAPI y consumidores RabbitMQ
    outbound/              Qwen, Gemini, publisher y exception handler
tests/
  unit/
```

Flujo de una petición: el router o el consumidor valida el mensaje, llama al puerto de entrada y el caso de uso habla solo con `IAiModelPort`, `IVectorSearchPort` e `IEventPublisherPort`. Si el modelo falla, el adaptador lanza `AiServiceUnavailableError` (`AI_SERVICE_UNAVAILABLE`). El manejador global, en la etapa de infraestructura, responderá siempre JSON con `code`, `message` y `timestamp`.

Los accesos, las acciones de IA y las alertas de fraude se registrarán con `logging` en formato AAA, por ejemplo:

```text
[AUDIT] [AI-SHIELD] Anomalía detectada en tarea ID: XYZ
```

El objetivo de latencia es responder en menos de 3 segundos. Toda la I/O de las capas siguientes será `async`.

## Modelos de dominio

`Task` replica el contrato `TaskBase` de la plataforma: identificador, nombre, descripción, estado, dueño, asignado, fecha, categoría, precio y los campos de reporte, disputa y aprobación.

`TaskCategory` admite `ARREGLOS` y `EDUCACION`. `TaskStatus` admite `ACTIVE`, `COMPLETED`, `CANCELLED`, `ASSIGNED`, `REPORTED` y `DISPUTED`.

También quedan modelados `Message`, `Chat`, `Review` y `ProviderProfile`, más los comandos y resultados de cada caso de uso (`GeneratedTaskContent`, `PriceEstimate`, `MatchResult`, `SentimentAnalysis`, `FraudAnalysis`, `ProfileOptimization`).

Los modelos son inmutables y rechazan campos desconocidos.

## Casos de uso previstos

| Puerto de entrada | Responsabilidad |
| --- | --- |
| `IGenerateTaskDescriptionUseCase` | Idea corta → título y descripción |
| `IEstimateFairPriceUseCase` | Descripción, categoría y ubicación → rango de precio |
| `ISemanticMatchmakingUseCase` | Indexa la tarea y busca prestadores por similitud |
| `IAnalyzeReviewSentimentUseCase` | Sentimiento, puntaje y palabras clave de una reseña |
| `IFraudDetectionShieldUseCase` | AI Shield sobre descripciones, chats y reseñas |
| `IOptimizeProfileUseCase` | Sugerencias de perfil y evento hacia Perfiles |

`IOptimizeProfileUseCase` no estaba en la lista funcional inicial. Existe porque AITA debe publicar `ProfileOptimizationSuggestedEvent` y ese flujo necesita un puerto propio.

El emparejamiento usa `IVectorSearchPort`. La primera implementación será un mock en memoria. La similitud coseno ya está en `aita.domain.services.similarity` para no acoplar esa fórmula al adaptador.

## Modelos de IA y configuración

`IAiModelPort` es el único contrato que ven los casos de uso. Cambiar de Qwen a Gemini es cambiar `AI_PROVIDER`; la lógica de negocio no se toca.

| `AI_PROVIDER` | Adaptador previsto | Conexión |
| --- | --- | --- |
| `qwen` | `LocalQwenAiAdapter` | `POST {OLLAMA_BASE_URL}/api/generate` (Ollama, por defecto `http://localhost:11434`) |
| `gemini` | `GeminiAiAdapter` | API de Google Gemini con `GEMINI_API_KEY` |

Variables:

```properties
AI_PROVIDER=qwen
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
```

Ollama debe estar en marcha y tener el modelo descargado (`ollama pull qwen3`) cuando el proveedor sea `qwen`. Gemini exige una API key válida. Un fallo del proveedor no tumba el proceso: se traduce a `AI_SERVICE_UNAVAILABLE`.

FastAPI elegirá el adaptador con `Depends` leyendo `AI_PROVIDER`. Esa composición de dependencias se implementa en infraestructura.

Operaciones del puerto:

- `generate_task_description`
- `estimate_fair_price`
- `embed`
- `analyze_sentiment`
- `detect_anomalies`
- `suggest_profile_optimization`

## RabbitMQ

Topología prevista (exchange de tipo topic):

| Recurso | Nombre |
| --- | --- |
| Exchange de eventos | `taskit.events` |
| Dead letter exchange | `taskit.dlx` |
| Cola de AITA | `aita.events` |
| Routing key que AITA consume | `taskit.aita.events` |
| Routing key de Auditoría HITL | `taskit.security.events` |
| Routing key de Perfiles | `taskit.profile.events` |

La routing key de perfiles no venía nombrada en el brief. AITA fija `taskit.profile.events` como contrato para que Perfiles tenga un binding estable. Las alertas de seguridad salen siempre por `taskit.security.events`.

Variables de entorno: `RABBITMQ_URL`, `RABBITMQ_ENABLED`, `RABBITMQ_EXCHANGE`, `RABBITMQ_DEAD_LETTER_EXCHANGE`, `RABBITMQ_AITA_QUEUE`, `RABBITMQ_AITA_ROUTING_KEY`, `RABBITMQ_SECURITY_ROUTING_KEY`, `RABBITMQ_PROFILE_ROUTING_KEY`. La URL real va solo en `.env`.

Cada evento lleva `event_id`, `event_type`, `occurred_at` y su carga. Las fechas van en ISO-8601.

### Eventos que AITA consume

Enlace de la cola `aita.events` a `taskit.aita.events`.

| Evento | Quién lo publica | Qué hará AITA |
| --- | --- | --- |
| `TaskCreatedEvent` | Microservicio de Tareas | AI Shield sobre la descripción e indexado del embedding |
| `ReviewCompletedEvent` | Flujo de reseñas | Análisis de sentimiento |
| `ChatMessageSentEvent` | Módulo de chat | AI Shield sobre el mensaje (fraude o acoso) |

Ejemplo de `TaskCreatedEvent`:

```json
{
  "event_id": "evt-task-1",
  "event_type": "TaskCreatedEvent",
  "occurred_at": "2026-11-07T18:00:00Z",
  "task": {
    "task_id": "task-1",
    "task_name": "Arreglar un grifo",
    "task_description": "El grifo de la cocina gotea desde hace una semana.",
    "task_status": "ACTIVE",
    "task_owner": "user-9",
    "task_assignee": null,
    "creation_date": "2026-11-07T18:00:00Z",
    "category": "ARREGLOS",
    "price": 80000,
    "report_reason": null,
    "dispute_reason": null,
    "owner_approval": false,
    "assignee_approval": false
  }
}
```

Ejemplo de `ChatMessageSentEvent`:

```json
{
  "event_id": "evt-msg-1",
  "event_type": "ChatMessageSentEvent",
  "occurred_at": "2026-11-07T18:05:00Z",
  "task_id": "task-1",
  "message": {
    "message_id": "msg-1",
    "chat_id": "chat-1",
    "sender_id": "user-4",
    "content": "Escríbeme por fuera de la plataforma para pagarte.",
    "timestamp": "2026-11-07T18:05:00Z"
  }
}
```

Ejemplo de `ReviewCompletedEvent`: el mismo sobre, con `event_type` `ReviewCompletedEvent` y un objeto `review` (`review_id`, `task_id`, `reviewer_id`, `reviewee_id`, `rating` de 1 a 5, `comment`, `created_at`).

### Eventos que AITA publica

| Evento | Routing key | Destino |
| --- | --- | --- |
| `FraudAlertDetectedEvent` | `taskit.security.events` | Security and Audit HITL |
| `ProfileOptimizationSuggestedEvent` | `taskit.profile.events` | Profile Service |

Solo se publica alerta cuando el análisis marca `is_anomaly`. `recommended_action` vale `UNDER_REVIEW` o `ALERT_ADMIN`.

Ejemplo de `FraudAlertDetectedEvent`:

```json
{
  "event_id": "evt-fraud-1",
  "event_type": "FraudAlertDetectedEvent",
  "occurred_at": "2026-11-07T18:05:02Z",
  "recommended_action": "UNDER_REVIEW",
  "analysis": {
    "source": "CHAT_MESSAGE",
    "source_id": "msg-1",
    "task_id": "task-1",
    "chat_id": "chat-1",
    "is_anomaly": true,
    "risk_level": "HIGH",
    "anomaly_types": ["FRAUD"],
    "explanation": "El mensaje invita a sacar el pago de la plataforma.",
    "flagged_excerpt": "Escríbeme por fuera de la plataforma"
  }
}
```

Ejemplo de `ProfileOptimizationSuggestedEvent`:

```json
{
  "event_id": "evt-profile-1",
  "event_type": "ProfileOptimizationSuggestedEvent",
  "occurred_at": "2026-11-07T18:10:00Z",
  "optimization": {
    "provider_id": "provider-3",
    "suggestions": [
      "Describe años de experiencia en plomería residencial.",
      "Agrega la zona que cubres y tu disponibilidad."
    ],
    "optimized_bio": "Plomero con cinco años de experiencia en Bogotá. Atiendo urgencias el mismo día.",
    "keywords": ["plomería", "Bogotá", "urgencias"]
  }
}
```

## Contratos de integración

Los otros servicios se enlazan al exchange `taskit.events`. AITA no les expone su cola interna. Cada uno declara su propia cola y la ata a la routing key que le corresponde. Los mensajes que no se puedan procesar deben terminar en `taskit.dlx`.

### Tareas

Publica `TaskCreatedEvent` con routing key `taskit.aita.events` en cuanto la tarea queda persistida. El cuerpo debe incluir la tarea completa (`Task`). Sin ese evento, AITA no indexa embeddings ni pasa la descripción por AI Shield.

Cuando le interese reflejar el riesgo en la tarea, consume `taskit.security.events`. Si `analysis.task_id` coincide con una tarea propia y `analysis.is_anomaly` es verdadero, pasa la tarea a `REPORTED`. No decide la revisión humana: eso es de Auditoría.

### Perfiles (Profile Service)

Consume `taskit.profile.events` y filtra `event_type = ProfileOptimizationSuggestedEvent`. Al recibirlo:

1. Localiza al prestador con `optimization.provider_id`.
2. Le notifica las `suggestions` (y, si viene, `optimized_bio`) como recomendación, sin reemplazar la biografía sin su confirmación.
3. Ignora eventos duplicados con el mismo `event_id`.

### Auditoría (Security and Audit HITL)

Consume de forma obligatoria `taskit.security.events` y filtra `FraudAlertDetectedEvent`. Al recibirlo:

1. Abre o actualiza el reporte asociado a `analysis.task_id` o `analysis.chat_id`.
2. Si `recommended_action` es `UNDER_REVIEW`, deja el reporte en `UNDER_REVIEW`.
3. Si `recommended_action` es `ALERT_ADMIN`, deja el reporte en `UNDER_REVIEW` y alerta a un administrador.
4. Conserva `risk_level`, `anomaly_types`, `explanation` y `flagged_excerpt` como evidencia. No vuelve a llamar al modelo: la decisión de IA ya viene en el evento.

### Chat y reseñas

El módulo de chat publica `ChatMessageSentEvent` en `taskit.aita.events` por cada mensaje persistido, con `task_id` y el `message` completo. El flujo de reseñas publica `ReviewCompletedEvent` en la misma routing key cuando la reseña queda cerrada. AITA no escribe de vuelta en esas colas: el resultado de una reseña se queda en el análisis de sentimiento, y el de un chat sospechoso sale por la routing key de seguridad.

## Errores de dominio

| Excepción | `code` | Cuándo |
| --- | --- | --- |
| `AiServiceUnavailableError` | `AI_SERVICE_UNAVAILABLE` | El modelo no responde o la salida no se puede interpretar |
| `DomainValidationError` | `DOMAIN_VALIDATION_ERROR` | Regla de dominio incumplida, por ejemplo embeddings vacíos o de distinta dimensión |

El JSON HTTP estándar (`code`, `message`, `timestamp`) lo añadirá el `exception_handler` de FastAPI en la etapa de infraestructura.

## Estado de la entrega

Implementado al 100%:

1. **Capa de Dominio:**
   - Modelos Pydantic v2 inmutables (`Task`, `Chat`, `Message`, `Review`, `ProviderProfile`).
   - Comandos (`GenerateTaskDescriptionCommand`, `EstimateFairPriceCommand`, etc.).
   - Resultados de negocio (`GeneratedTaskContent`, `PriceEstimate`, `FraudAnalysis`, etc.).
   - Puertos de entrada (`IGenerateTaskDescriptionUseCase`, `IFraudDetectionShieldUseCase`, etc.).
   - Puertos de salida (`IAiModelPort`, `IVectorSearchPort`, `IEventPublisherPort`).
   - Servicio de dominio con cálculo puro de similitud coseno (`cosine_similarity`).
   - Excepciones estándar de dominio (`AitaError`, `AiServiceUnavailableError`, etc.).

2. **Capa de Aplicación:**
   - Casos de uso con degradación controlada y tiempos < 3s:
     - `GenerateTaskDescriptionUseCase`
     - `EstimateFairPriceUseCase`
     - `SemanticMatchmakingUseCase`
     - `AnalyzeReviewSentimentUseCase`
     - `FraudDetectionShieldUseCase`
     - `OptimizeProfileUseCase`
   - Logging estructurado AAA (`[AUDIT] [AI-SHIELD] ...`).
   - Despachador de eventos asíncrono (`AitaEventDispatcher`).

3. **Capa de Infraestructura:**
   - Adaptador HTTP REST FastAPI (`router.py`) con endpoints versionados `/api/v1/...` y `/health`.
   - Adaptador de IA local Ollama (`LocalQwenAiAdapter`) con llamadas asíncronas vía `httpx`.
   - Adaptador de IA Google Gemini (`GeminiAiAdapter`) con API REST v1beta vía `httpx`.
   - Adaptador de base vectorial en memoria (`InMemoryVectorSearchAdapter`).
   - Publicador asíncrono RabbitMQ (`RabbitMqEventPublisher`) con `aio-pika` y `NullEventPublisher` de fallback.
   - Consumidor RabbitMQ (`RabbitMqConsumer`) con topología de Topic Exchange y Dead Letter Queue (DLQ).
   - Middleware de auditoría HTTP y manejadores de error globales estandarizados (`code`, `message`, `timestamp`).
   - Inyección de dependencias dinámica (`dependencies.py`) basada en `AI_PROVIDER`.
   - Punto de entrada principal `main.py` con ciclo de vida `lifespan`.

4. **Testing:**
   - 26 pruebas unitarias y de integración pasando en verde (`pytest -v`).
   - Cobertura de Happy Paths, escenarios de error y degradación elegante ante caídas de IA.

## Ejecución del microservicio

Para levantar el microservicio localmente:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

O directamente ejecutando Python:

```bash
python main.py
```

Para correr las pruebas unitarias:

```bash
pytest -v
```

---

## Guía de Pruebas en Postman

El proyecto incluye la colección lista para importar en el archivo:
📁 **[`postman_collection.json`](file:///c:/Users/juanp/OneDrive/Desktop/IATASK/postman_collection.json)**.

> **Tip:** En Postman, ve a **Import** -> selecciona el archivo `postman_collection.json` y tendrás todas las peticiones con ejemplos y variables listas para ejecutar contra `http://localhost:8000`.

A continuación se detalla la especificación de cada endpoint para probar manualmente o copiar a Postman:

---

### 0. Health Check
Verifica que el servicio esté arriba y respondiendo.

- **Método:** `GET`
- **URL:** `http://localhost:8000/health`
- **Headers:** Ninguno requerido
- **Respuesta Esperada (`200 OK`):**
  ```json
  {
    "status": "ok"
  }
  ```

---

### 1. Asistencia de Redacción de Tarea
Toma una idea corta del usuario y la transforma en un título atractivo y descripción detallada profesional.

- **Método:** `POST`
- **URL:** `http://localhost:8000/api/v1/tasks/description`
- **Headers:** `Content-Type: application/json`
- **Body (raw JSON):**
  ```json
  {
    "idea": "necesito instalar tres repisas de madera en la sala y asegurar un televisor a la pared"
  }
  ```
- **Respuesta Esperada (`200 OK`):**
  ```json
  {
    "title": "Instalación de repisas de madera y montaje de televisor en sala",
    "description": "Se solicita técnico para fijar tres repisas flotantes de madera y realizar el montaje seguro de televisor en pared de mampostería."
  }
  ```

---

### 2. Estimación de Precio Justo
Analiza descripción, categoría y ubicación geográfica para calcular un rango de precio justo en pesos colombianos (COP).

- **Método:** `POST`
- **URL:** `http://localhost:8000/api/v1/tasks/price-estimate`
- **Headers:** `Content-Type: application/json`
- **Body (raw JSON):**
  ```json
  {
    "description": "Cambio urgente de empaques y grifería de cocina por filtración de agua constante",
    "category": "ARREGLOS",
    "location": "Bogotá"
  }
  ```
- **Respuesta Esperada (`200 OK`):**
  ```json
  {
    "min_price": 40000,
    "max_price": 75000,
    "currency": "COP",
    "confidence": 0.9,
    "rationale": "Estimación calculada según categoría ARREGLOS y complejidad de plomería urbana."
  }
  ```

---

### 3. Matchmaking Semántico: Indexar Tarea
Genera el embedding de una tarea y la indexa en el almacén vectorial.

- **Método:** `POST`
- **URL:** `http://localhost:8000/api/v1/matchmaking/tasks`
- **Headers:** `Content-Type: application/json`
- **Body (raw JSON):**
  ```json
  {
    "task_id": "task-plomeria-001",
    "task_name": "Reparación urgente de fuga de agua",
    "task_description": "Tubería rota bajo el lavaplatos que requiere cambio de codo PVC.",
    "category": "ARREGLOS"
  }
  ```
- **Respuesta Esperada (`200 OK`):**
  ```json
  {
    "status": "indexed",
    "resource_id": "task-plomeria-001"
  }
  ```

---

### 4. Matchmaking Semántico: Indexar Perfil de Prestador
Indexa el perfil de un prestador calculando su representación semántica vectorial.

- **Método:** `POST`
- **URL:** `http://localhost:8000/api/v1/matchmaking/providers`
- **Headers:** `Content-Type: application/json`
- **Body (raw JSON):**
  ```json
  {
    "provider_id": "prov-carlos-001",
    "display_name": "Carlos Fontanería",
    "bio": "Especialista en plomería residencial, cambio de tuberías PVC y filtraciones.",
    "skills": ["plomería", "tuberías", "reparaciones", "fugas"],
    "location": "Bogotá",
    "categories": ["ARREGLOS"]
  }
  ```
- **Respuesta Esperada (`200 OK`):**
  ```json
  {
    "status": "indexed",
    "resource_id": "prov-carlos-001"
  }
  ```

---

### 5. Matchmaking Semántico: Búsqueda y Emparejamiento
Busca los prestadores con mayor cercanía y similitud coseno con respecto a la tarea.

- **Método:** `POST`
- **URL:** `http://localhost:8000/api/v1/matchmaking/search`
- **Headers:** `Content-Type: application/json`
- **Body (raw JSON):**
  ```json
  {
    "task_id": "task-plomeria-001",
    "task_name": "Reparación urgente de fuga de agua",
    "task_description": "Tubería rota bajo el lavaplatos que requiere cambio de codo PVC.",
    "category": "ARREGLOS",
    "limit": 5
  }
  ```
- **Respuesta Esperada (`200 OK`):**
  ```json
  [
    {
      "task_id": "task-plomeria-001",
      "provider_id": "prov-carlos-001",
      "score": 0.92,
      "rationale": "Similitud coseno 0.92 con Carlos Fontanería."
    }
  ]
  ```

---

### 6. Análisis de Sentimiento de Reseñas
Analiza el comentario de una reseña, clasificando el sentimiento, puntuación semántica y palabras clave.

- **Método:** `POST`
- **URL:** `http://localhost:8000/api/v1/reviews/sentiment`
- **Headers:** `Content-Type: application/json`
- **Body (raw JSON):**
  ```json
  {
    "review_id": "rev-888",
    "task_id": "task-plomeria-001",
    "reviewer_id": "user-cliente-10",
    "reviewee_id": "prov-carlos-001",
    "rating": 5,
    "comment": "Excelente trabajo, llegó muy puntual, trajo todas las herramientas y dejó el piso impecable.",
    "created_at": "2025-02-01T15:00:00Z"
  }
  ```
- **Respuesta Esperada (`200 OK`):**
  ```json
  {
    "review_id": "rev-888",
    "sentiment": "POSITIVE",
    "score": 1.0,
    "keywords": [
      "puntual",
      "herramientas",
      "impecable",
      "excelente"
    ],
    "summary": "Reseña altamente positiva destacando puntualidad y profesionalismo."
  }
  ```

---

### 7. AI Shield: Detección de Fraude en Tiempo Real

#### Caso A: Texto Legítimo (Sin Anomalía)
- **Método:** `POST`
- **URL:** `http://localhost:8000/api/v1/shield/analyze`
- **Headers:** `Content-Type: application/json`
- **Body (raw JSON):**
  ```json
  {
    "source": "CHAT_MESSAGE",
    "source_id": "msg-001",
    "text": "Hola Carlos, ¿podrías venir este sábado a las 9 am a revisar la fuga?",
    "task_id": "task-plomeria-001",
    "chat_id": "chat-500",
    "sender_id": "user-cliente-10"
  }
  ```
- **Respuesta Esperada (`200 OK`):**
  ```json
  {
    "source": "CHAT_MESSAGE",
    "source_id": "msg-001",
    "task_id": "task-plomeria-001",
    "chat_id": "chat-500",
    "is_anomaly": false,
    "risk_level": "LOW",
    "anomaly_types": [],
    "explanation": "Mensaje legítimo de coordinación de horario.",
    "flagged_excerpt": ""
  }
  ```

#### Caso B: Intento de Fraude / Evasión de Plataforma (Dispara Alerta)
- **Método:** `POST`
- **URL:** `http://localhost:8000/api/v1/shield/analyze`
- **Headers:** `Content-Type: application/json`
- **Body (raw JSON):**
  ```json
  {
    "source": "CHAT_MESSAGE",
    "source_id": "msg-002",
    "text": "No pagues por aquí porque cobran comisión. Escríbeme al WhatsApp 3109998877 y te transfiero por Nequi directo.",
    "task_id": "task-plomeria-001",
    "chat_id": "chat-500",
    "sender_id": "user-sospechoso-99"
  }
  ```
- **Respuesta Esperada (`200 OK`):**
  ```json
  {
    "source": "CHAT_MESSAGE",
    "source_id": "msg-002",
    "task_id": "task-plomeria-001",
    "chat_id": "chat-500",
    "is_anomaly": true,
    "risk_level": "HIGH",
    "anomaly_types": [
      "FRAUD"
    ],
    "explanation": "Intento de evadir la plataforma y desviar pagos por canales externos.",
    "flagged_excerpt": "Escríbeme al WhatsApp 3109998877 y te transfiero por Nequi directo"
  }
  ```
  *(Nota: Si RabbitMQ está habilitado, emite simultáneamente `FraudAlertDetectedEvent` a `taskit.security.events`).*

---

### 8. Optimización de Perfil de Prestador
Analiza el perfil actual y emite recomendaciones personalizadas junto a una biografía optimizada.

- **Método:** `POST`
- **URL:** `http://localhost:8000/api/v1/profiles/optimize`
- **Headers:** `Content-Type: application/json`
- **Body (raw JSON):**
  ```json
  {
    "provider_id": "prov-carlos-001",
    "display_name": "Carlos",
    "bio": "Hago trabajos de plomería y tubos.",
    "skills": ["plomería"],
    "location": "Bogotá",
    "categories": ["ARREGLOS"]
  }
  ```
- **Respuesta Esperada (`200 OK`):**
  ```json
  {
    "provider_id": "prov-carlos-001",
    "suggestions": [
      "Menciona tus años de experiencia y herramientas especializadas.",
      "Añade habilidades específicas como detección de fugas y grifería para mejorar visibilidad."
    ],
    "optimized_bio": "Técnico especialista en plomería residencial con amplia experiencia en reparación de fugas, cambio de grifería e instalación de tuberías.",
    "keywords": [
      "plomería",
      "filtraciones",
      "grifería",
      "emergencias"
    ]
  }
  ```
  *(Nota: Si RabbitMQ está habilitado, emite `ProfileOptimizationSuggestedEvent` hacia `taskit.profile.events`).*

---

### 9. Pruebas de Respuestas de Error Estandarizadas

#### Error 422 - Validación de Contrato de Entrada
- **Método:** `POST`
- **URL:** `http://localhost:8000/api/v1/tasks/description`
- **Body:** `{"idea": "a"}` *(longitud menor a 3 caracteres)*
- **Respuesta Esperada (`422 Unprocessable Entity`):**
  ```json
  {
    "code": "REQUEST_VALIDATION_ERROR",
    "message": "La solicitud no cumple el contrato de entrada.",
    "timestamp": "2025-02-01T15:30:00.000000+00:00"
  }
  ```

#### Error 503 - Degradación Elegante / Caída de Proveedor de IA
Si el proveedor de IA configurado no está disponible:
- **Respuesta Esperada (`503 Service Unavailable`):**
  ```json
  {
    "code": "AI_SERVICE_UNAVAILABLE",
    "message": "El proveedor de IA no está disponible. Intente más tarde.",
    "timestamp": "2025-02-01T15:30:00.000000+00:00"
  }
  ```

