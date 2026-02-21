# 🛡️ Teck-Vision

<div align="center">

![Teck-Vision Logo](CTF/themes/core/static/img/logo.png)

**Plateforme Capture The Flag pour l'apprentissage de la cybersécurité dans un environnement DevSecOps moderne**

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.x-lightgrey?logo=flask)](https://flask.palletsprojects.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![Kubernetes](https://img.shields.io/badge/K8s-EKS-326CE5?logo=kubernetes&logoColor=white)](https://kubernetes.io)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

</div>

---

## 📋 À propos

**Teck-Vision** est une plateforme CTF (Capture The Flag) personnalisée, développée dans le cadre d'un projet DevSecOps universitaire. Basée sur CTFd, elle est adaptée pour une intégration complète dans un environnement cloud moderne avec Kubernetes, monitoring et sécurité automatisée.

### 👥 Équipe Projet

| Membre | Rôle |
|--------|------|
| **Fatma Amri** | Développeuse principale |
| **Koussay Aydi** | DevOps / Infrastructure |
| **Mariem Baraket** | Sécurité / SOC |
| **Belgacem Balti** | Backend / API |
| **Omar Allagui** | Frontend / Thème |

**Encadrante :** Mme. Sahar BEN YAALA  
**Année universitaire :** 2025-2026

---

## ✨ Fonctionnalités

- ✅ Gestion de challenges CTF (Web, Crypto, Reverse, Forensics, etc.)
- ✅ Support des compétitions individuelles et par équipes
- ✅ Scoreboard en temps réel avec graphiques
- ✅ Système de hints et flags dynamiques
- ✅ Interface d'administration complète
- ✅ API REST pour l'automatisation
- ✅ Health checks pour Kubernetes
- ✅ Logs structurés pour intégration Wazuh

---

## 🏗️ Architecture

```
teck-vision/
├── CTF/                     # Code source principal
│   ├── api/                 # API REST v1
│   ├── models/              # Modèles de données (SQLAlchemy)
│   ├── plugins/             # Plugins (challenges, flags)
│   ├── schemas/             # Schémas de sérialisation (Marshmallow)
│   ├── themes/              # Thèmes (admin, core)
│   └── utils/               # Utilitaires (auth, email, crypto)
├── migrations/              # Migrations Alembic
├── tests/                   # Tests unitaires et d'intégration
├── Dockerfile               # Image Docker production
├── docker-compose.yml       # Stack complète
└── serve.py                 # Serveur de développement
```

---

## 🚀 Installation

### Prérequis

- Python 3.11+
- Docker & Docker Compose (optionnel)

### Installation locale

```bash
# 1. Cloner le repository
git clone https://github.com/fatma-amri/teck-vision.git
cd teck-vision

# 2. Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer le serveur
python serve.py --disable-gevent --port 4000
```

Accéder à **http://localhost:4000** pour le setup initial.

### Avec Docker

```bash
# Build et lancement
docker compose up -d
```

---

## ⚙️ Configuration

### Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `DATABASE_URL` | URL de la base de données | `sqlite:///ctfd.db` |
| `REDIS_URL` | URL Redis pour cache/sessions | — |
| `SECRET_KEY` | Clé secrète Flask | Auto-générée |
| `REVERSE_PROXY` | Derrière un reverse proxy | `false` |
| `LOG_FOLDER` | Répertoire des logs | `/var/log/teck-vision` |

### Health Checks (Kubernetes)

```yaml
livenessProbe:
  httpGet:
    path: /healthcheck
    port: 8000

readinessProbe:
  httpGet:
    path: /healthcheck
    port: 8000
```

---

## 🎨 Thème Teck-Vision

| Couleur | Hex | Rôle |
|---------|-----|------|
| 🔵 Cyan | `#00d4ff` | Accent principal |
| 🟣 Violet | `#7b2ff7` | Accent secondaire |
| 🟢 Vert | `#00ff88` | Succès / Résolu |
| ⬛ Sombre | `#0a0e1a` | Arrière-plan |

---

## 🔒 Sécurité

- Authentification sécurisée (bcrypt)
- Protection CSRF sur tous les formulaires
- Sessions HttpOnly + SameSite
- Rate limiting sur les soumissions de flags
- Validation et sanitization des entrées
- Container non-root (UID 1001)

---

## 📖 Documentation

- [Guide d'administration](ADMIN_GUIDE.md)
- [Guide de déploiement Kubernetes](DEPLOYMENT.md)

---

## 📄 Licence

Ce projet est distribué sous licence **MIT**. Voir [LICENSE](LICENSE).

---

<div align="center">

**Teck-Vision** — Plateforme CTF DevSecOps Académique 🛡️

*Développé avec ❤️ par l'équipe Teck-Vision — 2025-2026*

</div>
