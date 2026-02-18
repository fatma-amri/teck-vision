# 🛡️ Teck-Vision — Plateforme CTF DevSecOps# Teck-Vision - Plateforme CTF



<div align="center">![Teck-Vision](CTFd/themes/core/static/img/logo.png)



**Plateforme Capture The Flag pour l'apprentissage de la cybersécurité dans un environnement DevSecOps moderne.**## À propos



![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)**Teck-Vision** est une plateforme Capture The Flag (CTF) personnalisée, développée dans le cadre d'un projet DevSecOps universitaire. La plateforme est basée sur CTFd et adaptée pour une intégration complète dans un environnement cloud moderne avec Kubernetes, monitoring, et sécurité automatisée.

![Flask](https://img.shields.io/badge/Flask-2.x-lightgrey?logo=flask)

![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)### Équipe Projet

![Kubernetes](https://img.shields.io/badge/K8s-EKS-326CE5?logo=kubernetes&logoColor=white)- **Fatma Amri**

![License](https://img.shields.io/badge/Licence-MIT-green)- **Koussay Aydi**

- **Mariem Baraket**

</div>- **Belgacem Balti**

- **Omar Allagui**

---

**Encadrante:** Mme. Sahar BEN YAALA  

## 📋 À propos**Année universitaire:** 2025-2026



**Teck-Vision** est une plateforme CTF (Capture The Flag) conçue pour héberger des compétitions de cybersécurité dans un cadre académique DevSecOps. Elle propose un thème cyberpunk personnalisé, un système de scoring en temps réel, et une architecture cloud-native prête pour la production.## Architecture du Projet



### 🎨 Thème Teck-VisionTeck-Vision s'intègre dans une architecture DevSecOps complète comprenant:



| Couleur | Hex | Rôle |- **Plateforme CTF:** Application web pour héberger des challenges de cybersécurité

|---------|-----|------|- **Infrastructure Cloud:** Déploiement sur AWS avec EKS (Kubernetes)

| 🔵 Cyan | `#00d4ff` | Accent principal |- **Pipeline CI/CD:** Jenkins avec intégration de sécurité (SonarQube, Trivy, Gitleaks)

| 🟣 Violet | `#7b2ff7` | Accent secondaire |- **SOC:** Supervision avec Wazuh pour la détection d'intrusions

| 🟢 Vert | `#00ff88` | Succès / Résolu |- **Monitoring:** Prometheus et Grafana pour l'observabilité

| ⬛ Sombre | `#0a0e1a` | Arrière-plan |

## Fonctionnalités

### 📂 Catégories de challenges DevSecOps

- ✅ Gestion de challenges CTF (Web, Crypto, Reverse, Forensics, etc.)

| # | Catégorie | Description |- ✅ Support des compétitions individuelles et par équipes

|---|-----------|-------------|- ✅ Scoreboard en temps réel avec graphiques

| 1 | **CI/CD Security** | Sécurisation des pipelines Jenkins, GitLab CI |- ✅ Système de hints et flags dynamiques

| 2 | **Container Security** | Docker, Kubernetes, analyse d'images |- ✅ Interface d'administration complète

| 3 | **Secrets Management** | Vault, gestion des credentials, détection de fuites |- ✅ API REST pour l'automatisation

| 4 | **IaC Security** | Terraform, CloudFormation, misconfigurations |- ✅ Health checks pour Kubernetes

| 5 | **SAST/DAST** | Analyse statique et dynamique du code |- ✅ Logs structurés pour intégration Wazuh



---## Installation



## 👥 Équipe Projet### Prérequis



| Membre | Rôle |- Python 3.11+

|--------|------|- Docker (optionnel)

| **Fatma Amri** | Développeuse principale |- Base de données (MySQL/PostgreSQL recommandé pour production, SQLite pour dev)

| **Koussay Aydi** | DevOps / Infrastructure |- Redis (optionnel, pour cache et sessions)

| **Mariem Baraket** | Sécurité / SOC |

| **Belgacem Balti** | Backend / API |### Installation Locale

| **Omar Allagui** | Frontend / Thème |

1. **Cloner le repository**

**Encadrante :** Mme. Sahar BEN YAALA   ```bash

**Année universitaire :** 2025–2026   git clone <repository-url>

   cd CTFd-master

---   ```



## 🚀 Installation2. **Installer les dépendances**

   ```bash

### Prérequis   pip install -r requirements.txt

   ```

- Python 3.11+

- Node.js 18+ (pour la compilation du thème)3. **Configuration**

- Docker & Docker Compose (optionnel)   

   Modifier `CTFd/config.ini` selon vos besoins:

### Installation locale   ```ini

   [server]

```bash   DATABASE_URL = mysql+pymysql://user:password@localhost/teck_vision

# 1. Cloner le repository   REDIS_URL = redis://localhost:6379

git clone https://github.com/fatma-amri/teck-vision.git   

cd teck-vision   [email]

   MAILFROM_ADDR = noreply@teck-vision.tn

# 2. Créer l'environnement virtuel   MAIL_SERVER = smtp.example.com

python -m venv .venv   ```

source .venv/bin/activate

4. **Lancer l'application**

# 3. Installer les dépendances   ```bash

pip install -r requirements.txt   python serve.py

   ```

# 4. Lancer le serveur   

python serve.py --disable-gevent --port 4000   Accéder à http://localhost:4000

```

### Installation avec Docker

Accéder à **http://localhost:4000** pour le setup initial.

```bash

### Avec Docker# Build de l'image

docker build -t teck-vision:latest .

```bash

docker compose up -d# Lancer avec docker-compose

```docker compose up -d

```

---

### Déploiement Kubernetes

## 🏗️ Architecture

Voir [DEPLOYMENT.md](DEPLOYMENT.md) pour les instructions détaillées de déploiement sur Kubernetes/EKS.

```

teck-vision/## Configuration pour DevSecOps

├── CTFd/                    # Code source principal

│   ├── api/                 # API REST v1### Health Checks

│   ├── models/              # Modèles de données (SQLAlchemy)

│   ├── plugins/             # Plugins (challenges, flags)L'application expose deux endpoints pour Kubernetes:

│   ├── schemas/             # Schémas de sérialisation (Marshmallow)

│   ├── themes/- **`/health`** - Liveness probe (vérifie que l'app est en cours d'exécution)

│   │   ├── teck-vision/     # 🎨 Thème principal- **`/ready`** - Readiness probe (vérifie la connectivité à la base de données)

│   │   │   ├── assets/      # Sources SCSS + JS

│   │   │   ├── static/      # Assets compilés (Vite)Exemple de configuration Kubernetes:

│   │   │   └── templates/   # Templates Jinja2```yaml

│   │   ├── admin/           # Thème d'administrationlivenessProbe:

│   │   └── core/            # Thème par défaut  httpGet:

│   └── utils/               # Utilitaires (auth, email, crypto)    path: /health

├── migrations/              # Migrations de base de données (Alembic)    port: 8000

├── tests/                   # Tests unitaires et d'intégration  initialDelaySeconds: 30

├── Dockerfile               # Image Docker production  periodSeconds: 10

├── docker-compose.yml       # Stack complète (app + DB + cache)

└── serve.py                 # Serveur de développementreadinessProbe:

```  httpGet:

    path: /ready

## 🔧 Compilation du thème    port: 8000

  initialDelaySeconds: 10

```bash  periodSeconds: 5

cd CTFd/themes/teck-vision```

npm install

npm run build### Logs

```

Les logs sont écrits dans `/var/log/CTFd/` et peuvent être collectés par Wazuh ou tout autre agent de collecte de logs.

Assets générés dans `static/` :

- CSS compilé (Bootstrap 5 + SCSS custom)### Monitoring

- JS bundlé (Alpine.js + ECharts + modules)

- Polices FontAwesome 6.5L'application peut être monitorée via Prometheus. Les métriques système et applicatives sont disponibles pour surveillance.

- Scripts standalone (particles, cursor, typewriter)

## Administration

---

### Premier Démarrage

## ⚙️ Configuration DevSecOps

1. Accéder à http://localhost:8000/setup

### Health Checks (Kubernetes)2. Créer le compte administrateur

3. Configurer le nom du CTF et les paramètres de base

```yaml

livenessProbe:### Gestion des Challenges

  httpGet:

    path: /healthcheck1. Se connecter en tant qu'admin

    port: 80002. Accéder au panneau d'administration

readinessProbe:3. Créer des challenges, catégories, et flags

  httpGet:4. Gérer les équipes et utilisateurs

    path: /healthcheck

    port: 8000Voir [ADMIN_GUIDE.md](ADMIN_GUIDE.md) pour plus de détails.

```

## API

### Variables d'environnement

Teck-Vision expose une API REST complète pour l'automatisation:

| Variable | Description | Défaut |

|----------|-------------|--------|- Documentation API: http://localhost:8000/api/v1/

| `DATABASE_URL` | URL de la base de données | `sqlite:///ctfd.db` |- Authentification via tokens API

| `REDIS_URL` | URL Redis pour cache/sessions | — |- Endpoints pour challenges, soumissions, scores, utilisateurs, etc.

| `SECRET_KEY` | Clé secrète Flask | Auto-générée |

| `REVERSE_PROXY` | Derrière un reverse proxy | `false` |## Sécurité

| `LOG_FOLDER` | Répertoire des logs | `/var/log/teck-vision` |

- 🔒 Authentification sécurisée avec hashage bcrypt

---- 🔒 Protection CSRF sur tous les formulaires

- 🔒 Sessions sécurisées avec cookies HttpOnly

## 🔒 Sécurité- 🔒 Rate limiting sur les soumissions

- 🔒 Validation et sanitization des inputs

- Authentification sécurisée (bcrypt)- 🔒 Container non-root (UID 1001)

- Protection CSRF sur tous les formulaires

- Sessions HttpOnly + SameSite## Support

- Rate limiting sur les soumissions de flags

- Validation et sanitization des entréesPour toute question ou problème:

- Container non-root (UID 1001)- Contacter l'équipe projet

- Consulter la documentation CTFd officielle: https://docs.ctfd.io

---

## Licence

## 📖 Documentation

Ce projet est basé sur CTFd, distribué sous licence Apache 2.0.

- [Guide d'administration](ADMIN_GUIDE.md)

- [Guide de déploiement Kubernetes](DEPLOYMENT.md)## Crédits



---- **CTFd Original:** https://github.com/CTFd/CTFd

- **Personnalisation Teck-Vision:** Équipe projet DevSecOps 2025-2026

## 📄 Licence- **Encadrement:** Mme. Sahar BEN YAALA



Ce projet est distribué sous licence **MIT**. Voir [LICENSE](LICENSE).---



---**Teck-Vision** - Plateforme CTF pour l'apprentissage de la cybersécurité dans un environnement DevSecOps moderne.


<div align="center">

**Teck-Vision** — Plateforme CTF DevSecOps Académique 🛡️

*Développé avec ❤️ par l'équipe Teck-Vision — 2025-2026*

</div>
