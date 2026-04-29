# Predict - Smart Health Monitoring System

![Status](https://img.shields.io/badge/Status-In%20Development-yellow)
![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![Flask](https://img.shields.io/badge/Framework-Flask-lightgrey?logo=flask)
![MQTT](https://img.shields.io/badge/Protocol-MQTT-orange?logo=mqtt)
![Docker](https://img.shields.io/badge/Deployment-Docker-blue?logo=docker)

> **Predict** It´s an advanced biometric monitoring ecosystem that integrates hardware, a real-time data analysis platform, and a pre-trained AI prediction model. 

<img width="1328" height="607" alt="predict" src="https://github.com/user-attachments/assets/d35f408f-00cc-425a-91b1-242ea3b0bab0" />

---

## The Concept

This project stems from the need for non-invasive and constant clinical monitoring. The physical device, smart glasses, uses strategic anatomical points to obtain precise readings without causing discomfort to the user:


*   **Temporal Region :** contact thermal sensor for systemic temperature measurement.
*   **Earlobe:** Pulse oximeter for oxygen saturation and heart rate via photoplethysmography.

<img width="3452" height="2312" alt="smart_glass" src="https://github.com/user-attachments/assets/63627d28-54b4-463f-80c4-3a2ca3976ce1" />

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
