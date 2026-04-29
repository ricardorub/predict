# Predict - Smart Health Monitoring System

![Status](https://img.shields.io/badge/Status-In%20Development-yellow)
![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![Flask](https://img.shields.io/badge/Framework-Flask-lightgrey?logo=flask)
![MQTT](https://img.shields.io/badge/Protocol-MQTT-orange?logo=mqtt)
![Docker](https://img.shields.io/badge/Deployment-Docker-blue?logo=docker)

> **Predict** is an advanced biometric monitoring ecosystem that integrates wearable hardware (smart glasses) with a real-time data analysis platform.

---

## The Concept

This project stems from the need for non-invasive and constant clinical monitoring. The physical device (glasses) uses strategic anatomical points to obtain precise readings without causing discomfort to the user:

*   **Temporal Region (Temple):** contact thermal sensor for systemic temperature measurement.
*   **Earlobe:** Pulse oximeter for oxygen saturation (SpO2) and heart rate via photoplethysmography.

---

## Key Features

-    **Real-Time Monitoring:** Data transmission via MQTT with ultra-low latency.
-    **Intelligent Dashboard:** Dynamic visualization of vital signs.
-    **Alert System:** Automatic notifications when physiological levels move outside the normal range.
-    **Patient Management:** Centralized database for longitudinal tracking.
-    **Containerized:** Ready to deploy with Docker and Docker Compose.

---

##  Tech Stack

| Component | Technology |
| :--- | :--- |
| **Backend** | Python / Flask |
| **Database** | SQLAlchemy (SQLite/PostgreSQL) |
| **Communication** | MQTT Protocol (Mosquitto) |
| **Frontend** | HTML5 / CSS3 / Jinja2 |
| **Tasks** | APScheduler (Log cleanup) |

---

##  System Architecture

```mermaid
graph LR
    A[Smart Glasses] -- "Sensor Data" --> B((MQTT Broker))
    B -- "Publish/Subscribe" --> C[Flask Backend]
    C -- "Store" --> D[(Database)]
    C -- "Stream" --> E[Web Dashboard]
    E -- "Alerts" --> F[User/Doctor]
```

---

##  Installation & Usage

### Prerequisites
*   Python 3.9+
*   Docker & Docker Compose (optional)
*   MQTT Broker (e.g., Eclipse Mosquitto)

### Option 1: Docker (Recommended)
```bash
docker-compose up -d
```

### Option 2: Local
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure environment variables in `.env`:
   ```env
   MQTT_BROKER=localhost
   MQTT_PORT=1883
   SECRET_KEY=your_secret_key
   ```
3. Run the application:
   ```bash
   python app.py
   ```

---

##  Author

**Ricardo Gutierrez**
*   [GitHub](https://github.com/ricardorub)
*   [LinkedIn](https://linkedin.com/in/ricardo-gutierrez-9ba3b11b2/)

---

*Developed with feelings for health innovation.*
