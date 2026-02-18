# Guide d'Administration - Teck-Vision

Guide complet pour l'administration de la plateforme CTF Teck-Vision.

## Accès au Panneau d'Administration

1. Se connecter avec un compte administrateur
2. Cliquer sur **Admin Panel** dans la barre de navigation
3. URL directe: `http://your-domain.com/admin`

## Configuration Initiale

### Premier Démarrage

Lors du premier accès à Teck-Vision, vous serez redirigé vers `/setup`:

1. **Informations de l'événement**
   - Nom du CTF: `Teck-Vision CTF 2026`
   - Description: Décrire votre compétition
   - Mode utilisateur: Individuel ou par équipes

2. **Compte administrateur**
   - Nom d'utilisateur
   - Email
   - Mot de passe (fort recommandé)

3. **Dates de la compétition**
   - Date de début (optionnel)
   - Date de fin (optionnel)

### Configuration Générale

**Admin Panel → Config → Settings**

- **CTF Name:** Nom affiché sur la plateforme
- **CTF Description:** Description visible sur la page d'accueil
- **User Mode:** `users` (individuel) ou `teams` (équipes)
- **CTF Logo:** Upload du logo personnalisé
- **CTF Theme:** Sélectionner le thème (core par défaut)

### Configuration Email

**Admin Panel → Config → Email**

Configuration SMTP pour l'envoi d'emails:

```
SMTP Server: smtp.gmail.com (exemple)
SMTP Port: 587
From Address: noreply@teck-vision.tn
Username: your-email@gmail.com
Password: your-app-password
Use TLS: ✓
```

**Test:** Envoyer un email de test pour vérifier la configuration.

## Gestion des Challenges

### Créer un Challenge

**Admin Panel → Challenges → Create**

1. **Informations de base**
   - Nom du challenge
   - Catégorie (Web, Crypto, Reverse, Forensics, etc.)
   - Description (supporte Markdown)
   - Points (statiques ou dynamiques)

2. **Type de challenge**
   - **Standard:** Challenge classique avec flag
   - **Dynamic:** Points qui diminuent avec le nombre de résolutions
   - **Custom:** Via plugins

3. **Flags**
   - Ajouter un ou plusieurs flags
   - Types: Static (exact match) ou Regex
   - Exemple flag: `TECK{th1s_1s_4_fl4g}`

4. **Hints (indices)**
   - Ajouter des hints optionnels
   - Coût en points (optionnel)
   - Contenu de l'hint

5. **Fichiers**
   - Upload de fichiers nécessaires au challenge
   - Les fichiers seront téléchargeables par les participants

6. **Paramètres avancés**
   - Nombre maximum de tentatives
   - Challenges prérequis (unlock)
   - Visibilité (visible/caché)
   - État (visible/caché)

### Catégories Recommandées

- **Web:** Exploitation web (XSS, SQLi, CSRF, etc.)
- **Crypto:** Cryptographie et cryptanalyse
- **Reverse:** Reverse engineering
- **Pwn:** Binary exploitation
- **Forensics:** Analyse forensique
- **Misc:** Challenges divers
- **OSINT:** Open Source Intelligence

### Scoring Dynamique

Pour activer le scoring dynamique:

1. Créer un challenge de type "Dynamic"
2. Configurer:
   - **Initial Value:** Points initiaux (ex: 500)
   - **Minimum Value:** Points minimum (ex: 100)
   - **Decay:** Facteur de décroissance

Formule: `Points = max(minimum, initial - decay × solves)`

## Gestion des Utilisateurs

### Voir les Utilisateurs

**Admin Panel → Users**

- Liste de tous les utilisateurs inscrits
- Recherche et filtres disponibles
- Export CSV possible

### Actions sur les Utilisateurs

Pour chaque utilisateur:

- **Voir le profil:** Détails, soumissions, scores
- **Éditer:** Modifier email, nom, mot de passe
- **Bannir:** Empêcher l'accès (ban)
- **Cacher:** Masquer du scoreboard
- **Supprimer:** Suppression définitive

### Créer un Utilisateur Manuellement

**Admin Panel → Users → Create**

Utile pour créer des comptes de test ou des comptes spéciaux.

## Gestion des Équipes

*Applicable uniquement si le mode "teams" est activé*

### Voir les Équipes

**Admin Panel → Teams**

- Liste de toutes les équipes
- Membres de chaque équipe
- Scores et statistiques

### Actions sur les Équipes

- **Voir les détails:** Membres, soumissions, challenges résolus
- **Éditer:** Modifier nom, capitaine, membres
- **Bannir/Cacher:** Comme pour les utilisateurs
- **Supprimer:** Suppression définitive

## Gestion des Soumissions

### Voir les Soumissions

**Admin Panel → Submissions**

- Toutes les soumissions de flags (correctes et incorrectes)
- Filtres par challenge, utilisateur, équipe
- Détection de triche possible (patterns suspects)

### Supprimer une Soumission

En cas d'erreur ou de triche détectée, vous pouvez supprimer des soumissions individuelles.

## Pages et Contenu

### Créer des Pages Personnalisées

**Admin Panel → Pages → Create**

Créer des pages statiques (règles, FAQ, sponsors, etc.):

- **Title:** Titre de la page
- **Route:** URL (ex: `/rules`)
- **Content:** Contenu en Markdown ou HTML
- **Draft:** Brouillon (non publié)
- **Hidden:** Caché de la navigation
- **Auth Required:** Nécessite authentification

### Pages Recommandées

- `/rules` - Règles de la compétition
- `/faq` - Questions fréquentes
- `/sponsors` - Sponsors et partenaires
- `/about` - À propos du projet

## Notifications

### Envoyer une Notification

**Admin Panel → Notifications → Create**

Envoyer des annonces à tous les participants:

- **Title:** Titre de la notification
- **Content:** Message (Markdown supporté)
- **Type:** Info, Warning, Success, Error

Les notifications apparaissent en temps réel pour les utilisateurs connectés.

## Import/Export

### Exporter les Données

**Admin Panel → Config → Backup**

- **Export CTF:** Télécharge toutes les données (challenges, users, submissions)
- Format: ZIP contenant des fichiers JSON
- Utile pour backup ou migration

### Importer des Données

**Admin Panel → Config → Backup → Import**

- Upload d'un fichier ZIP d'export
- Restaure challenges, pages, et configuration
- ⚠️ Attention: peut écraser des données existantes

## Sécurité et Modération

### Détection de Triche

Surveiller les comportements suspects:

- Soumissions trop rapides
- Patterns de soumissions identiques
- Partage de flags entre équipes

**Admin Panel → Submissions** permet de voir toutes les soumissions.

### Bannir un Utilisateur

Si triche détectée:

1. **Admin Panel → Users**
2. Sélectionner l'utilisateur
3. Cliquer **Ban**
4. L'utilisateur ne pourra plus se connecter

### Rate Limiting

CTFd inclut une protection contre le bruteforce:

- Limite automatique des tentatives de soumission
- Configurable dans le code si nécessaire

## Monitoring et Logs

### Logs de l'Application

Les logs sont écrits dans `/var/log/CTFd/`:

- `ctfd.log` - Logs généraux
- `logins.log` - Connexions
- `submissions.log` - Soumissions de flags
- `registrations.log` - Inscriptions

### Surveiller l'Activité

**Admin Panel → Statistics**

- Graphiques de soumissions
- Activité par challenge
- Progression des équipes/utilisateurs

## API Administration

### Générer un Token API

**Admin Panel → Settings → Access Tokens**

1. Créer un nouveau token
2. Définir les permissions
3. Utiliser le token pour l'automatisation

### Utiliser l'API

```bash
# Exemple: Lister les challenges
curl -H "Authorization: Token YOUR_TOKEN" \
     https://teck-vision.example.com/api/v1/challenges

# Créer un challenge via API
curl -X POST \
     -H "Authorization: Token YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"name":"Test","category":"Web","value":100}' \
     https://teck-vision.example.com/api/v1/challenges
```

Documentation complète: `/api/v1/` (si Swagger activé)

## Maintenance

### Nettoyer les Sessions

Si problèmes de performance:

```bash
# Depuis le container
flask cache clear
```

### Réinitialiser un Mot de Passe Admin

Si mot de passe admin perdu:

```bash
# Depuis le container
flask users create --admin --name admin --email admin@teck-vision.tn --password newpassword
```

### Backup Réguliers

Recommandations:

- **Base de données:** Snapshot quotidien (RDS automated backups)
- **Fichiers uploadés:** Backup S3 ou volume persistence
- **Export CTF:** Export hebdomadaire via l'interface admin

## Dépannage

### Les utilisateurs ne reçoivent pas d'emails

1. Vérifier la configuration SMTP
2. Tester l'envoi d'email depuis Admin Panel
3. Vérifier les logs: `/var/log/CTFd/ctfd.log`

### Un challenge ne s'affiche pas

1. Vérifier que le challenge est "Visible"
2. Vérifier les prérequis (unlock requirements)
3. Vérifier la date de début du CTF

### Problèmes de performance

1. Vérifier les ressources (CPU, RAM) dans Kubernetes
2. Augmenter le nombre de replicas (HPA)
3. Vérifier la connexion Redis/Database

## Bonnes Pratiques

✅ **Tester les challenges** avant publication  
✅ **Backup réguliers** de la base de données  
✅ **Surveiller les logs** pour détecter les problèmes  
✅ **Communiquer** avec les participants via notifications  
✅ **Documenter** les règles clairement  
✅ **Préparer** des hints pour les challenges difficiles  
✅ **Monitorer** le scoreboard pour détecter la triche  

## Support

Pour toute question technique:
- Consulter la documentation CTFd: https://docs.ctfd.io
- Contacter l'équipe projet Teck-Vision

---

**Teck-Vision** - Administration simplifiée pour une expérience CTF optimale.
