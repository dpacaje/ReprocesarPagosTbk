## 🛠️ Instalación y Configuración

Sigue estos pasos para configurar el entorno de desarrollo en tu máquina local:

### 1. Preparar el Entorno Virtual
Es fundamental usar un entorno virtual para evitar conflictos entre las librerías de distintos proyectos.

* **En Windows:**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

* **En macOS/Linux:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

### 2. Instalar Dependencias
Una vez activado el entorno (verás un `(venv)` en tu terminal), instala los paquetes necesarios:

```bash
pip install -r requirements.txt
```

### 3. Ejecución

* **En Windows:**
    ```bash
    python main.py
    ```

* **En macOS/Linux:**
    ```bash
    python3 main.py
    ```

### 4. Salir Entorno Virtual

```bash
deactivate
```
