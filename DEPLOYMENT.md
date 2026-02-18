# Guide de Déploiement Kubernetes - Teck-Vision

Ce document décrit le déploiement de la plateforme Teck-Vision sur Kubernetes/EKS dans le cadre du projet DevSecOps.

## Prérequis

- Cluster Kubernetes (EKS sur AWS)
- `kubectl` configuré
- Image Docker `teck-vision:latest` disponible dans un registry
- Base de données MySQL/PostgreSQL (RDS recommandé pour AWS)
- Redis (ElastiCache recommandé pour AWS)

## Architecture Kubernetes

```
┌─────────────────────────────────────────────┐
│           AWS Load Balancer (ALB)           │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         Ingress Controller                  │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│      Teck-Vision Service (ClusterIP)        │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│      Teck-Vision Deployment (3 replicas)    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │  Pod 1   │ │  Pod 2   │ │  Pod 3   │    │
│  └──────────┘ └──────────┘ └──────────┘    │
└─────────────────────────────────────────────┘
```

## Fichiers de Configuration Kubernetes

### 1. Namespace

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: teck-vision
  labels:
    name: teck-vision
    project: devsecops
```

### 2. ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: teck-vision-config
  namespace: teck-vision
data:
  # Configuration de base
  REVERSE_PROXY: "true"
  THEME_FALLBACK: "true"
  UPDATE_CHECK: "false"
  SERVER_SENT_EVENTS: "true"
```

### 3. Secret

```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: teck-vision-secrets
  namespace: teck-vision
type: Opaque
stringData:
  SECRET_KEY: "CHANGE_ME_TO_RANDOM_STRING"
  DATABASE_URL: "mysql+pymysql://user:password@rds-endpoint:3306/teck_vision"
  REDIS_URL: "redis://elasticache-endpoint:6379/0"
  MAIL_PASSWORD: "your-smtp-password"
```

**Important:** Ne jamais committer les secrets dans Git. Utiliser des outils comme AWS Secrets Manager ou HashiCorp Vault en production.

### 4. Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: teck-vision
  namespace: teck-vision
  labels:
    app: teck-vision
    version: "1.0.0"
spec:
  replicas: 3
  selector:
    matchLabels:
      app: teck-vision
  template:
    metadata:
      labels:
        app: teck-vision
        version: "1.0.0"
    spec:
      containers:
      - name: teck-vision
        image: <your-registry>/teck-vision:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
          name: http
          protocol: TCP
        
        # Variables d'environnement depuis ConfigMap
        envFrom:
        - configMapRef:
            name: teck-vision-config
        
        # Variables d'environnement depuis Secret
        env:
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: teck-vision-secrets
              key: SECRET_KEY
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: teck-vision-secrets
              key: DATABASE_URL
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: teck-vision-secrets
              key: REDIS_URL
        
        # Health checks
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 3
        
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        
        # Ressources
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        
        # Volumes pour logs (pour Wazuh)
        volumeMounts:
        - name: logs
          mountPath: /var/log/CTFd
      
      volumes:
      - name: logs
        emptyDir: {}
      
      # Security context
      securityContext:
        runAsNonRoot: true
        runAsUser: 1001
        fsGroup: 1001
```

### 5. Service

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: teck-vision
  namespace: teck-vision
  labels:
    app: teck-vision
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
    name: http
  selector:
    app: teck-vision
```

### 6. Ingress (ALB)

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: teck-vision
  namespace: teck-vision
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account:certificate/xxx
    alb.ingress.kubernetes.io/ssl-redirect: '443'
spec:
  rules:
  - host: teck-vision.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: teck-vision
            port:
              number: 80
```

### 7. HorizontalPodAutoscaler

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: teck-vision
  namespace: teck-vision
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: teck-vision
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Déploiement

### 1. Créer le namespace

```bash
kubectl apply -f namespace.yaml
```

### 2. Créer les secrets

```bash
# Éditer secret.yaml avec vos vraies valeurs
kubectl apply -f secret.yaml
```

### 3. Créer la ConfigMap

```bash
kubectl apply -f configmap.yaml
```

### 4. Déployer l'application

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml
kubectl apply -f hpa.yaml
```

### 5. Vérifier le déploiement

```bash
# Vérifier les pods
kubectl get pods -n teck-vision

# Vérifier les logs
kubectl logs -f deployment/teck-vision -n teck-vision

# Vérifier le service
kubectl get svc -n teck-vision

# Vérifier l'ingress
kubectl get ingress -n teck-vision
```

## Intégration avec les Autres Composants

### Wazuh (SOC)

Pour l'intégration avec Wazuh, déployer un agent Wazuh en sidecar ou DaemonSet:

```yaml
# Dans deployment.yaml, ajouter un sidecar container
- name: wazuh-agent
  image: wazuh/wazuh-agent:latest
  env:
  - name: WAZUH_MANAGER
    value: "wazuh-manager.monitoring.svc.cluster.local"
  volumeMounts:
  - name: logs
    mountPath: /var/log/CTFd
    readOnly: true
```

### Prometheus (Monitoring)

Ajouter des annotations pour Prometheus:

```yaml
# Dans deployment.yaml metadata
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

## Mise à Jour (Rolling Update)

```bash
# Mettre à jour l'image
kubectl set image deployment/teck-vision teck-vision=<registry>/teck-vision:v1.1.0 -n teck-vision

# Ou appliquer un nouveau deployment.yaml
kubectl apply -f deployment.yaml

# Vérifier le rollout
kubectl rollout status deployment/teck-vision -n teck-vision

# Rollback si nécessaire
kubectl rollout undo deployment/teck-vision -n teck-vision
```

## Troubleshooting

### Les pods ne démarrent pas

```bash
kubectl describe pod <pod-name> -n teck-vision
kubectl logs <pod-name> -n teck-vision
```

### Problèmes de base de données

```bash
# Vérifier la connectivité depuis un pod
kubectl exec -it <pod-name> -n teck-vision -- /bin/bash
# Puis tester la connexion à la base de données
```

### Health checks échouent

```bash
# Tester manuellement les endpoints
kubectl port-forward deployment/teck-vision 8000:8000 -n teck-vision
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

## Sécurité

- ✅ Pods s'exécutent en tant qu'utilisateur non-root (UID 1001)
- ✅ Network Policies pour restreindre le trafic
- ✅ Secrets stockés dans Kubernetes Secrets (ou AWS Secrets Manager)
- ✅ TLS/HTTPS via ALB
- ✅ Resource limits pour prévenir les abus

## Backup et Disaster Recovery

### Backup de la base de données

Configurer des snapshots automatiques RDS sur AWS.

### Backup des uploads

Si utilisation de S3 pour les fichiers, activer le versioning S3.

## Monitoring

- **Logs:** Collectés par Wazuh et/ou CloudWatch
- **Métriques:** Prometheus + Grafana
- **Alertes:** Alertmanager pour les incidents critiques
- **Traces:** Optionnel avec Jaeger ou AWS X-Ray

---

Pour toute question sur le déploiement, contacter l'équipe DevOps du projet.
