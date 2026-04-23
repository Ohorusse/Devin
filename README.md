# SAE - Système d'information de billetterie & sécurité

## 1) Objectif
Mettre en place un **MVP de billetterie de spectacles** et définir une **stratégie de défense** face aux attaques (SQL injection, vol de session, malware/ransomware, fuite de données, DoS).

## 2) Organisation des équipes
- **Équipe SI (création/gestion)** : conçoit, développe, déploie et maintient le système.
- **Équipe Pirate** : simule des attaques techniques et sociales pour identifier les failles.
- Répartition équilibrée, puis sous-groupes de **3 à 4 personnes**.

## 3) Périmètre MVP (équipe SI)
### Fonctionnel
- Création de compte utilisateur.
- Achat de tickets (maximum **4 tickets par spectacle et par compte**).
- Dépôt d’avis et de notes sur les spectacles.
- Gestion des événements (date, prix, illustration).
- Édition de facture.

### Données minimales
- **Compte** : email (unique), mot de passe hashé, prénom, nom, date de création, consentements.
- **Spectacle** : titre, description, date/heure, prix, image (optionnelle), stock.
- **Commande** : utilisateur, spectacle, quantité (1..4), total, horodatage, statut.
- **Avis** : utilisateur, spectacle, note (1..5), commentaire, date.

## 4) Exigences sécurité (défense)
- **Authentification**
  - Mot de passe fort (longueur minimale + complexité), hash Argon2/bcrypt + sel.
  - Procédure “mot de passe oublié” avec jeton unique, expiration courte.
  - Limitation des tentatives de connexion (anti brute-force).
- **Protection applicative**
  - Requêtes SQL paramétrées (anti injection).
  - Validation stricte des entrées côté serveur.
  - Protection CSRF sur formulaires sensibles.
  - En-têtes de sécurité (CSP, X-Frame-Options, HSTS, etc.).
- **Session**
  - Cookies `HttpOnly`, `Secure`, `SameSite`.
  - Rotation de session après authentification.
  - Expiration de session et invalidation à la déconnexion.
- **Données & confidentialité**
  - Chiffrement TLS en transit.
  - Chiffrement des sauvegardes.
  - Journalisation des accès administratifs et actions sensibles.
- **Disponibilité**
  - Limitation de débit (rate limiting).
  - Stratégie anti-DoS de base (reverse proxy/WAF, seuils d’alerte).
- **Poste utilisateur**
  - Sensibilisation phishing/malware.
  - Procédure de réponse en cas de suspicion de ransomware.

## 5) Plan par phases
### Phase 1 — Analyse des besoins et des risques
- Cartographier actifs, menaces, impacts, priorités.
- Définir les exigences sécurité et conformité.

### Phase 2 — Conception
- **SI** : architecture (Flask/Node.js + SQLite/MySQL), modèle de données, règles métier.
- **Pirate** : plan de tests d’intrusion (SQLi, XSS, session hijacking, DoS, social engineering).

### Phase 3 — Déploiement
- **SI** : déploiement MVP, paramètres sécurisés, sauvegardes.
- **Pirate** : exécution des tests, pièges, collecte de preuves.

### Phase 4 — Formation
- Formation développeurs, hébergeurs, utilisatrices/utilisateurs.
- Restitution des scénarios d’attaque et des contre-mesures.

### Phase 5 — Maintenance & suivi sécurité
- Correctifs, mises à jour dépendances, revue de logs, tests récurrents.
- Suivi d’indicateurs : incidents, temps de correction, taux de réussite des attaques simulées.

## 6) Livrables attendus
- Spécifications MVP + schéma de données.
- Procédures de développement sécurisé et d’hébergement.
- Recommandations pour les clientes et clients.
- Rapport de tests de sécurité (équipe pirate) + plan d’amélioration continue.
