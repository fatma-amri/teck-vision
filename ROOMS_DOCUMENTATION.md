# Système de Rooms - Teck-Vision CTF

## Architecture

### Modèles de données

**RoomInstances** - Suit l'état actif des machines pour les rooms
- `user_id` / `team_id` : Propriétaire de l'instance
- `category` : Catégorie du challenge (correspond au room_id)
- `machine_ip` : Adresse IP statique (15.237.60.47)
- `is_active` : True si la machine est active
- `started_at` / `expires_at` : Timestamps de démarrage et expiration
- `duration_minutes` : Durée de vie (par défaut 30 min)

### Routes API

#### Machine Control (`/api/room-instances/`)

**POST /api/room-instances/start/<room_category>**
- Démarre une instance de machine pour une room
- Réponse: `{ machine_ip, started_at, expires_at, time_remaining, duration_minutes }`

**POST /api/room-instances/terminate/<room_category>**
- Arrête une instance active
- Réponse: `{ success: true/false }`

**GET /api/room-instances/status/<room_category>**
- Vérifie l'état d'une machine
- Réponse: `{ is_active, machine_ip, time_remaining, ... }`

#### Flag Submission (`/api/challenges/`)

**POST /api/challenges/<challenge_id>/submit-flag**
- Valide un flag pour un challenge
- Body: `{ flag: "user_submitted_flag" }`
- Réponse (succès): `{ success: true, message: "Correct flag!", points: 100 }`
- Réponse (erreur): `{ success: false, message: "Wrong flag, try again" }`

### Template HTML

**room_detail.html** - Page de détail d'une room
- Affiche les détails de la room
- **Boutons de contrôle:**
  - "Demarrer le challenge" - Lance la machine
  - "Arreter la machine" - Arrête la machine
  - "Copier l'IP" - Copie l'IP dans le presse-papiers
- **Timer en compte à rebours** - Affiche le temps restant
- **Liste des challenges** avec:
  - Titre et description
  - Points et difficulté
  - Champ input pour le flag
  - Bouton "Valider" pour soumettre
- **Indicateur de progression** - Barre remplissante au fur et à mesure

### Fonctionnalités JavaScript

- ✅ Démarrage/arrêt de la machine avec API
- ✅ Timer en temps réel avec mise à jour chaque seconde
- ✅ Copy-to-clipboard pour l'adresse IP
- ✅ Soumission de flags avec validation case-insensitive
- ✅ Indicateur visuel de l'état de la machine (point vert animé)
- ✅ Feedback utilisateur (messages d'erreur, état de chargement)

## Utilisation

### 1. Créer des challenges dans une room

Les challenges doivent avoir:
- Une `category` commune (ex: "Web Security Challenge")
- Une ou plusieurs `Flags` avec le contenu correcte
- Un `value` (points)
- Un `position` (ordre d'affichage)

### 2. Accéder à une room

```
/rooms/<room-slug>
```

Par exemple: `/rooms/web-security-challenge`

### 3. Soumettre un flag

1. Cliquer "Demarrer le challenge" pour activer la machine
2. L'adresse IP s'affiche
3. Entrer le flag pour chaque challenge
4. Cliquer "Valider"
5. Si correct → le challenge passe en vert, points ajoutés
6. Si incorrect → message d'erreur "Wrong flag, try again"

## Configuration

### Adresse IP statique

L'IP est définie à: `15.237.60.47` (modifiable dans `room_instances.py`)

### Durée de la machine

Par défaut: 30 minutes (modifiable dans `room_instances.py`)

### Validation des flags

- **Case-insensitive** : "BEN" = "ben" = "BeN"
- Whitespace trimé automatiquement
- Comparaison exacte du contenu

## Intégration avec le système existant

- ✅ Utilise le modèle `Challenges` existant
- ✅ Utilise le modèle `Solves` existant pour tracker les victoires
- ✅ Intégré avec l'authentification (`@authed_only`)
- ✅ Support mode teams et mode users
- ✅ Logging des accès et soumissions
- ✅ Rate limiting sur les routes

## Fichiers créés/modifiés

**Créés:**
- `CTF/room_instances.py` - API de contrôle des machines
- `CTF/challenges_api.py` - API de soumission des flags
- `CTF/management/create_room.py` - Utilitaire pour créer des rooms de test
- `CTF/models/RoomInstances` - Modèle de base de données (ajout à `__init__.py`)

**Modifiés:**
- `CTF/__init__.py` - Enregistrement des blueprints
- `CTF/themes/core/templates/room_detail.html` - Nouveau template avec TryHackMe design
- `CTF/challenges.py` - Routes existantes (pas de modification majeure)

## Déploiement

1. Exécuter les migrations de base de données:
```bash
python manage.py db migrate
python manage.py db upgrade
```

2. (Optionnel) Créer des challenges de test:
```bash
python -c "from CTF.management.create_room import create_room_with_challenges; from CTF import create_app; app = create_app(); app.app_context().push(); create_room_with_challenges()"
```

3. Redémarrer l'application Flask
