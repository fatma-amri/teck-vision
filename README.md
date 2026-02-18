# Teck-Vision - Plateforme CTF

![Teck-Vision](CTFd/themes/core/static/img/logo.png)

## À propos

**Teck-Vision** est une plateforme Capture The Flag (CTF) personnalisée, développée dans le cadre d'un projet DevSecOps universitaire. La plateforme est basée sur CTFd et adaptée pour une intégration complète dans un environnement cloud moderne avec Kubernetes, monitoring, et sécurité automatisée.

### Équipe Projet
- **Fatma Amri**
- **Koussay Aydi**
- **Mariem Baraket**
- **Belgacem Balti**
- **Omar Allagui**

**Encadrante:** Mme. Sahar BEN YAALA  
**Année universitaire:** 2025-2026

## Architecture du Projet

Teck-Vision s'intègre dans une architecture DevSecOps complète comprenant:

- **Plateforme CTF:** Application web pour héberger des challenges de cybersécurité
- **Infrastructure Cloud:** Déploiement sur AWS avec EKS (Kubernetes)
- **Pipeline CI/CD:** Jenkins avec intégration de sécurité (SonarQube, Trivy, Gitleaks)
- **SOC:** Supervision avec Wazuh pour la détection d'intrusions
- **Monitoring:** Prometheus et Grafana pour l'observabilité

## Fonctionnalités

- ✅ Gestion de challenges CTF (Web, Crypto, Reverse, Forensics, etc.)
- ✅ Support des compétitions individuelles et par équipes
- ✅ Scoreboard en temps réel avec graphiques
- ✅ Système de hints et flags dynamiques
- ✅ Interface d'administration complète
- ✅ API REST pour l'automatisation
- ✅ Health checks pour Kubernetes
- ✅ Logs structurés pour intégration Wazuh

## Installation

### Prérequis

- Python 3.11+
- Docker (optionnel)
- Base de données (MySQL/PostgreSQL recommandé pour production, SQLite pour dev)
- Redis (optionnel, pour cache et sessions)

### Installation Locale

1. **Cloner le repository**
   ```bash
   git clone <repository-url>
   cd CTFd-master
   ```

2. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configuration**
   
   Modifier `CTFd/config.ini` selon vos besoins:
   ```ini
   [server]
   DATABASE_URL = mysql+pymysql://user:password@localhost/teck_vision
   REDIS_URL = redis://localhost:6379
   
   [email]
   MAILFROM_ADDR = noreply@teck-vision.tn
   MAIL_SERVER = smtp.example.com
   ```

4. **Lancer l'application**
   ```bash
   python serve.py
   ```
   
   Accéder à http://localhost:4000

### Installation avec Docker

```bash
# Build de l'image
docker build -t teck-vision:latest .

# Lancer avec docker-compose
docker compose up -d
```

### Déploiement Kubernetes

Voir [DEPLOYMENT.md](DEPLOYMENT.md) pour les instructions détaillées de déploiement sur Kubernetes/EKS.

## Configuration pour DevSecOps

### Health Checks

L'application expose deux endpoints pour Kubernetes:

- **`/health`** - Liveness probe (vérifie que l'app est en cours d'exécution)
- **`/ready`** - Readiness probe (vérifie la connectivité à la base de données)

Exemple de configuration Kubernetes:
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

### Logs

Les logs sont écrits dans `/var/log/CTFd/` et peuvent être collectés par Wazuh ou tout autre agent de collecte de logs.

### Monitoring

L'application peut être monitorée via Prometheus. Les métriques système et applicatives sont disponibles pour surveillance.

## Administration

### Premier Démarrage

1. Accéder à http://localhost:8000/setup
2. Créer le compte administrateur
3. Configurer le nom du CTF et les paramètres de base

### Gestion des Challenges

1. Se connecter en tant qu'admin
2. Accéder au panneau d'administration
3. Créer des challenges, catégories, et flags
4. Gérer les équipes et utilisateurs

Voir [ADMIN_GUIDE.md](ADMIN_GUIDE.md) pour plus de détails.

## API

Teck-Vision expose une API REST complète pour l'automatisation:

- Documentation API: http://localhost:8000/api/v1/
- Authentification via tokens API
- Endpoints pour challenges, soumissions, scores, utilisateurs, etc.

## Sécurité

- 🔒 Authentification sécurisée avec hashage bcrypt
- 🔒 Protection CSRF sur tous les formulaires
- 🔒 Sessions sécurisées avec cookies HttpOnly
- 🔒 Rate limiting sur les soumissions
- 🔒 Validation et sanitization des inputs
- 🔒 Container non-root (UID 1001)

## Support

Pour toute question ou problème:
- Contacter l'équipe projet
- Consulter la documentation CTFd officielle: https://docs.ctfd.io

## Licence

Ce projet est basé sur CTFd, distribué sous licence Apache 2.0.

## Crédits

- **CTFd Original:** https://github.com/CTFd/CTFd
- **Personnalisation Teck-Vision:** Équipe projet DevSecOps 2025-2026
- **Encadrement:** Mme. Sahar BEN YAALA

---

**Teck-Vision** - Plateforme CTF pour l'apprentissage de la cybersécurité dans un environnement DevSecOps moderne.
