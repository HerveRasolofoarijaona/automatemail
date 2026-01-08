# 📧 Send Report – Automated Report Sender

**Send Report** est un outil Python packagé en exécutable Windows (`.exe`) permettant de générer et d'envoyer automatiquement des rapports Oracle par email.

## 🚀 Fonctionnalités

- **Connexion Oracle sécurisée** (mode THIN par défaut)
- **Génération automatique de rapports** :
  - 📄 CSV
  - 📄 PDF (format paysage)
- **Envoi d'emails automatisés** :
  - Corps HTML (template Jinja2)
  - Pièces jointes multiples
  - Destinataires CC / CCI
- **Configuration externe** via `.env`
- **Logs applicatifs** détaillés
- **Exécutable Windows autonome** (`.exe`)

---

## 📦 Structure des fichiers

Dans le dossier d'exécution, vous devez avoir :

```
📁 send_report/
├── send_report.exe          # Exécutable principal
├── report.csv               # Fichier de configuration des rapports
├── .env                     # Variables d'environnement (OBLIGATOIRE)
├── 📁 logs/                 # Logs générés automatiquement
└── 📁 outputs/              # Rapports CSV/PDF générés
```

---

## 🧾 Fichier `report.csv` (pilotage)

Ce fichier CSV définit les rapports à générer et envoyer.

### Exemple

```csv
to_email,subject,template_name,context,cc,bcc,attachments,report_type,nd,date_debut,date_fin,partition
user@test.com,Rapport journalier,report.html,{},cc@test.com,bcc@test.com,,remit,ND001,2026-01-01,2026-01-01,P202601
manager@test.com,Analyse UP,report.html,{},,,extra.pdf,up,ND002,2026-01-01,2026-01-07,P202601
```

### Description des colonnes

| Champ           | Description                                      | Exemple                     |
|-----------------|--------------------------------------------------|-----------------------------|
| `to_email`      | Email(s) destinataire(s) (séparés par `;`)       | `user@test.com`             |
| `subject`       | Sujet de l'email                                 | `Rapport journalier`        |
| `template_name` | Nom du template HTML Jinja2                      | `report.html`               |
| `context`       | Contexte JSON pour le template (optionnel)       | `{}`                        |
| `cc`            | Email(s) en copie (séparés par `;`)              | `cc@test.com`               |
| `bcc`           | Email(s) en copie cachée (séparés par `;`)       | `bcc@test.com`              |
| `attachments`   | Pièces jointes supplémentaires (séparées par `;`)| `extra.pdf`                 |
| `report_type`   | Type de rapport : `remit` ou `up`                | `remit`                     |
| `nd`            | Identifiant ND                                   | `ND001`                     |
| `date_debut`    | Date de début (format `YYYY-MM-DD`)              | `2026-01-01`                |
| `date_fin`      | Date de fin (format `YYYY-MM-DD`)                | `2026-01-01`                |
| `partition`     | Partition Oracle                                 | `P202601`                   |

---

## 🔐 Fichier `.env` (obligatoire)

Le fichier `.env` contient les variables de configuration sensibles. **Il doit être créé manuellement** et ne doit **jamais être versionné**.

### Exemple de configuration

```env
# Configuration Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=example@gmail.com
EMAIL_PASSWORD=your_app_password

# Configuration Oracle (mode THIN par défaut)
ORACLE_USER=your_oracle_user
ORACLE_PASSWORD=your_oracle_password
ORACLE_DSN=hostname:1521/service_name

# Niveau de logs (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

### 📝 Notes importantes

- **Gmail** : Utilisez un [mot de passe d'application](https://support.google.com/accounts/answer/185833)
- **Outlook/O365** : Vérifiez les paramètres SMTP de votre organisation
- Le fichier `.env` n'est **pas inclus** dans l'exécutable

---

## 🧠 Base de données Oracle – Prérequis

### ✅ Mode THIN (recommandé – par défaut)

- **Aucun client Oracle à installer**
- Connexion TCP standard
- Compatible Oracle Database ≥ 12c

### ⚠️ Mode THICK (optionnel)

Nécessite **Oracle Instant Client** si vous utilisez :
- Wallet (authentification avancée)
- TCPS / SSL
- Configuration réseau complexe

---

## ▶️ Utilisation

### Lancement sous Windows

1. Placez-vous dans le dossier contenant `send_report.exe`
2. Assurez-vous que `report.csv` et `.env` sont présents
3. Double-cliquez sur `send_report.exe` ou exécutez en ligne de commande :

```cmd
send_report.exe
```

### Processus d'exécution

Le programme effectue les étapes suivantes :

1. ✅ Lecture du fichier `report.csv`
2. 🔍 Connexion à la base Oracle
3. 📊 Exécution des requêtes SQL
4. 📄 Génération des fichiers CSV et PDF
5. 📧 Envoi des emails avec pièces jointes
6. 📝 Écriture des logs

---

## 📂 Logs

Les logs sont automatiquement générés dans :

```
logs/send_report.log
```

Le niveau de logs est configurable via `LOG_LEVEL` dans `.env` :
- `DEBUG` : Informations détaillées
- `INFO` : Informations générales (par défaut)
- `WARNING` : Avertissements uniquement
- `ERROR` : Erreurs uniquement

---

## 🛠️ Build de l'exécutable (développeurs)

Pour reconstruire l'exécutable à partir du code source :

### Prérequis

```bash
pip install pyinstaller oracledb jinja2 python-dotenv reportlab pandas
```

### Commande de build

```bash
pyinstaller \
  --onefile \
  --name send_report \
  --add-data "src/templates:templates" \
  --hidden-import=oracledb \
  src/main.py
```

### Résultat

L'exécutable sera généré dans :

```
dist/send_report.exe
```

---

## 🧪 Compatibilité

- **OS** : Windows 10 / 11 (64-bit)
- **Base de données** : Oracle Database 12c ou supérieur
- **SMTP** : Gmail, Outlook, Office 365, serveurs SMTP personnalisés

---

## 🔒 Sécurité

- ✅ Le fichier `.env` est **externe** et ne doit **jamais être versionné**
- ✅ L'exécutable `.exe` ne contient **aucun credential**
- ✅ Les logs ne contiennent **jamais de mots de passe**
- ✅ Utilisez des **mots de passe d'application** pour les services email

### Recommandations

- Stockez le fichier `.env` dans un emplacement sécurisé
- Limitez les droits d'accès au dossier d'exécution
- Utilisez des comptes de service dédiés pour Oracle et SMTP

---

## 🆘 Dépannage

### Erreur de connexion Oracle

```
Vérifiez :
- Le paramètre ORACLE_DSN dans .env
- La connectivité réseau vers la base
- Les credentials (ORACLE_USER / ORACLE_PASSWORD)
```

### Erreur d'envoi d'email

```
Vérifiez :
- Les paramètres EMAIL_HOST et EMAIL_PORT
- Le mot de passe d'application (Gmail)
- Les paramètres de sécurité de votre compte email
```

### Logs introuvables

```
Le dossier logs/ est créé automatiquement.
Vérifiez les droits d'écriture dans le dossier d'exécution.
```

---

## 📄 Licence

Projet interne – Usage contrôlé.

---

## 🧑‍💻 Auteur

**Send Report** – Automatisation & Reporting Oracle / Email

Pour toute question ou support, contactez Moi.

---

## 📌 Changelog

### Version 1.0.0
- 🎉 Première version
- ✅ Support Oracle mode THIN
- ✅ Génération CSV/PDF
- ✅ Envoi d'emails avec templates HTML
- ✅ Configuration via .env
- ✅ Logs applicatifs