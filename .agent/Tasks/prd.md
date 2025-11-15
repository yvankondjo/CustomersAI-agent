# Product Requirements Document (PRD)

**AI Customer Support & Automation Platform (Instagram + Web)**

**Version:** 1.0 — Hackathon Edition
**Related docs:** [project_architecture.md](../System/project_architecture.md), [hackathon_roadmap.md](./hackathon_roadmap.md)

---

## 1️⃣ Vision

Créer une plateforme d'assistance client intelligente capable d'automatiser 70-90% des interactions support sur :
- **Instagram DM** (canal principal)
- **Widget Web** (chat embarqué)
- Futurs canaux : WhatsApp, Messenger, email

La plateforme utilise un **RAG hybride multi-sources** pour répondre avec précision en se basant sur :
- FAQ internes
- Documents uploadés (PDF, Word)
- Contenu du site web (crawlé automatiquement)
- Historique des conversations

**Différenciation clé :** Onboarding zero-code — il suffit de connecter Instagram + fournir l'URL du site web.

---

## 2️⃣ Objectifs Généraux

### Objectifs Business
1. **Automatiser 70-90%** des réponses client
2. **Réduire le temps de réponse** de 24h à <2 minutes
3. **Améliorer la satisfaction client** (CSAT >4.5/5)
4. **Libérer du temps** pour les équipes support (focus sur cas complexes)

### Objectifs Produit
1. Réponses précises basées sur données réelles de l'entreprise
2. Escalade intelligente vers humains pour cas complexes
3. Prise de rendez-vous automatisée (Cal.com)
4. Insights automatiques via clustering (BERTopic)

### Objectifs Techniques
1. Latence <3s pour 95% des réponses
2. Multi-tenant avec isolation stricte (RLS)
3. Scalable jusqu'à 10,000 conversations/jour
4. 99.9% uptime

---

## 3️⃣ Utilisateurs Cibles

### Persona 1 : PME E-commerce
- **Profil :** Boutique en ligne (vêtements, cosmétiques, tech)
- **Volume :** 50-500 DM Instagram/jour
- **Pain Points :**
  - Équipe support débordée
  - Questions répétitives (livraison, retours)
  - Pas de support 24/7
- **Besoins :**
  - Automatisation FAQ
  - Escalade pour remboursements
  - Intégration facile (no-code)

### Persona 2 : Agence de Services
- **Profil :** Coaching, consulting, événementiel
- **Volume :** 20-100 DM/jour
- **Pain Points :**
  - Beaucoup de demandes de rendez-vous
  - Qualification leads chronophage
  - Informations éparpillées (site, docs internes)
- **Besoins :**
  - Prise de RDV automatique
  - RAG sur site web + documents
  - Qualification automatique

### Persona 3 : Influenceur / Creator
- **Profil :** Influenceur avec boutique/produits
- **Volume :** 100-1000 DM/jour
- **Pain Points :**
  - Impossible de répondre à tous
  - Questions répétitives sur produits
- **Besoins :**
  - Réponses automatiques 24/7
  - Personnalisation
  - Analytics sur sujets principaux

---

## 4️⃣ Fonctionnalités Détaillées

### 4.1 — Intégration Instagram DM ⭐

**Priority:** P0 (Must-Have)

**Description:**
Recevoir et répondre automatiquement aux messages Instagram Direct.

**User Flow:**
1. Utilisateur envoie DM à `@ma_boutique_paris`
2. Webhook Instagram → Backend `/webhooks/instagram`
3. Backend route vers LangGraph
4. Agent détermine intent → génère réponse
5. Backend envoie réponse via Instagram Graph API
6. Conversation stockée dans Supabase

**Technical Requirements:**
- Webhook verification (HMAC)
- Support messages texte uniquement (MVP)
- Gestion rate limits Instagram API
- Retry logic pour messages échoués

**Acceptance Criteria:**
- [ ] Webhook reçoit messages Instagram
- [ ] Réponse envoyée <5s après réception
- [ ] Conversations stockées dans DB
- [ ] Gestion erreurs Instagram API

---

### 4.2 — Widget Web Embed ⭐

**Priority:** P1 (Should-Have)

**Description:**
Chat widget embeddable sur le site du client.

**User Flow:**
1. Visiteur clique sur bulle de chat
2. Widget s'ouvre (iframe ou composant)
3. Utilisateur tape message
4. Appel API backend `/support/message`
5. Réponse affichée en temps réel

**Technical Requirements:**
- Script embed simple (`<script src="widget.js">`)
- Support customisation (couleurs, position)
- Responsive (mobile + desktop)
- Gestion session (localStorage)

**Acceptance Criteria:**
- [ ] Widget s'intègre en <5min
- [ ] UI propre et responsive
- [ ] Conversations persistées
- [ ] Support streaming (optionnel MVP)

---

### 4.3 — Agent Router (LangGraph) ⭐

**Priority:** P0 (Must-Have)

**Description:**
Orchestrateur intelligent qui route les demandes vers le bon handler.

**Graph Nodes:**
1. **Classifier** → Détermine l'intent
2. **FAQ Handler** → Répond via system prompt
3. **RAG Handler** → Recherche dans Qdrant
4. **Escalation** → Envoie email
5. **Scheduling** → Génère lien Cal.com

**State Management:**
- PostgresCheckpointSaver pour mémoire conversation
- Contexte utilisateur (nom, historique)
- Métadonnées (intent, sources utilisées)

**Technical Requirements:**
- LangGraph 0.2+
- Support multi-turn conversations
- Timeout handling (fallback si LLM lent)

**Acceptance Criteria:**
- [ ] Routing précis (>90% accuracy)
- [ ] Mémoire conversation fonctionne
- [ ] Latence <3s moyenne
- [ ] Gestion erreurs robuste

---

### 4.4 — FAQ Engine (System Prompt) ⭐

**Priority:** P0 (Must-Have)

**Description:**
Réponses immédiates pour questions fréquentes via system prompt enrichi.

**FAQ Examples:**
```
Q: Quel est le délai de livraison ?
A: 3 à 5 jours ouvrés en France métropolitaine. Gratuit >50€.

Q: Quelle est la politique de retour ?
A: Retours acceptés sous 30 jours, produit non utilisé avec étiquette.

Q: Comment suivre ma commande ?
A: Vous recevrez un email avec lien de tracking 24h après expédition.
```

**Technical Requirements:**
- FAQ stockées dans Supabase `tenant_settings.faq`
- Injectées dans system prompt
- Pas de RAG nécessaire (plus rapide)

**Acceptance Criteria:**
- [ ] Réponses FAQ correctes à 100%
- [ ] Latence <1s
- [ ] Admin peut éditer FAQ facilement

---

### 4.5 — RAG Hybrid Search (Qdrant) ⭐

**Priority:** P0 (Must-Have)

**Description:**
Recherche sémantique dans documents + site web pour réponses précises.

**Data Sources:**
1. Documents PDF/Word uploadés
2. Pages website crawlées
3. (Optionnel) Historique conversations

**Pipeline:**
1. Multi-query expansion (3-5 variants)
2. Dense vector search (top 5 per query)
3. Deduplication (top 12 unique)
4. Reranking (score-based ou LLM)
5. Context injection (top 3)

**Technical Requirements:**
- Qdrant Cloud (free tier)
- OpenAI embeddings (text-embedding-3-small)
- Filtering par `tenant_id` + `source_type`

**Acceptance Criteria:**
- [ ] RAG retourne contexte pertinent >80% temps
- [ ] Latence RAG <2s
- [ ] Gestion cas "no results found"
- [ ] Citations sources dans réponse

**See:** [rag_pipeline.md](../System/rag_pipeline.md)

---

### 4.6 — Website Ingestion (Crawl4AI) ⭐

**Priority:** P1 (Should-Have)

**Description:**
Crawl automatique du site web client pour alimenter RAG.

**User Flow:**
1. Admin entre URL : `https://ma-boutique.com`
2. Backend lance worker asynchrone
3. Crawl4AI crawl jusqu'à 50 pages
4. Extraction contenu (markdown)
5. Stockage dans `website_pages`
6. Chunking + embedding + Qdrant indexing
7. Notification admin "Crawl terminé"

**Technical Requirements:**
- Crawl4AI library
- Async processing (Redis worker)
- Rate limiting (respecter robots.txt)
- Exclude patterns (admin, checkout, etc.)

**Acceptance Criteria:**
- [ ] Crawl fonctionne pour 90% sites
- [ ] Extraction contenu propre (sans nav/footer)
- [ ] Pages indexées dans Qdrant
- [ ] Admin voit status crawl en temps réel

**See:** [rag_pipeline.md](../System/rag_pipeline.md)

---

### 4.7 — Document Upload & Indexing

**Priority:** P1 (Should-Have)

**Description:**
Upload PDF/Word pour enrichir knowledge base.

**User Flow:**
1. Admin upload fichier
2. Backend stocke dans Supabase Storage
3. Worker extrait texte
4. Chunking + embedding
5. Indexation Qdrant
6. Document disponible pour RAG

**Technical Requirements:**
- Support PDF + Word
- Max file size: 10MB
- Extraction via pypdf / python-docx
- Preview admin (optionnel)

**Acceptance Criteria:**
- [ ] Upload fonctionne pour PDF/Word
- [ ] Extraction texte précise >95%
- [ ] Chunks indexés dans Qdrant
- [ ] Liste documents dans admin panel

---

### 4.8 — Escalation Email

**Priority:** P1 (Should-Have)

**Description:**
Escalade automatique vers humain pour cas complexes.

**Triggers:**
- Litiges / fraude
- Remboursements complexes
- Client VIP
- Demande juridique
- Sentiment négatif détecté

**User Flow:**
1. Agent détecte besoin escalade
2. Génère résumé conversation (LLM)
3. Worker envoie email à `support@entreprise.com`
4. Stocke dans table `escalations`
5. Répond au client : "Demande transmise à équipe, réponse sous 24h"

**Email Template:**
```
Subject: [ESCALATION] Demande client - {user_name}

Conversation ID: {conversation_id}
Canal: Instagram DM
Raison: Demande remboursement produit défectueux

Résumé:
Le client a reçu un produit abîmé il y a 2 semaines.
Il demande un remboursement complet + geste commercial.

Lien conversation: https://admin.app.com/conversations/{id}
```

**Acceptance Criteria:**
- [ ] Email envoyé pour escalations
- [ ] Résumé LLM pertinent
- [ ] Client informé de l'escalade
- [ ] Traçabilité dans DB

---

### 4.9 — Scheduling (Cal.com)

**Priority:** P2 (Nice-to-Have)

**Description:**
Prise de rendez-vous automatique via Cal.com.

**User Flow:**
1. Client demande RDV
2. Agent génère lien Cal.com
3. Client clique → réserve créneau
4. Event stocké dans `meetings`
5. Confirmation auto par email

**Technical Requirements:**
- Cal.com account par tenant
- Lien statique (MVP) ou API dynamic booking
- Stockage meetings dans DB

**Acceptance Criteria:**
- [ ] Lien Cal.com généré automatiquement
- [ ] Client peut réserver créneau
- [ ] (Optionnel) Sync Google Calendar

---

### 4.10 — Conversation History & Analytics

**Priority:** P1 (Should-Have)

**Description:**
Dashboard admin pour voir conversations et métriques.

**Features:**
- Liste conversations (filtre par status, date)
- Détail conversation (timeline messages)
- Métriques :
  - Volume conversations/jour
  - Taux automatisation
  - Topics principaux
  - Temps moyen réponse

**Technical Requirements:**
- Next.js admin panel
- Supabase queries optimisées
- Charts (Recharts ou Chart.js)

**Acceptance Criteria:**
- [ ] Admin voit toutes conversations tenant
- [ ] Détail conversation lisible
- [ ] Métriques de base affichées

---

### 4.11 — BERTopic Clustering (Bonus)

**Priority:** P3 (Nice-to-Have)

**Description:**
Clustering automatique des sujets de conversation.

**User Flow:**
1. Worker quotidien (cron)
2. Récupère messages 24h
3. BERTopic clustering
4. Génère topics + labels
5. Stocke dans `topics_daily`
6. Dashboard affiche :
   - "Livraison" : 30% messages
   - "Remboursement" : 20%
   - "Produit abîmé" : 10%

**Technical Requirements:**
- BERTopic library
- Sentence embeddings
- Min messages pour clustering : 50+

**Acceptance Criteria:**
- [ ] Clustering fonctionne sur dataset test
- [ ] Topics pertinents >70% temps
- [ ] Dashboard affiche topics

---

## 5️⃣ Non-Functional Requirements

### Performance
- **Latence réponse :** <3s (p95)
- **RAG search :** <2s
- **Website crawl :** <5min pour 50 pages
- **Throughput :** 100 messages/seconde

### Security
- **Multi-tenant isolation :** RLS Supabase
- **Encryption :** At rest + in transit (TLS)
- **Auth :** Supabase Auth pour admin
- **Webhook verification :** HMAC Instagram

### Scalability
- **Horizontal scaling :** FastAPI instances derrière load balancer
- **Qdrant :** Cloud auto-scaling
- **Database :** Supabase Pro (read replicas si besoin)
- **Workers :** Redis cluster mode

### Reliability
- **Uptime :** 99.9% SLA
- **Retry logic :** Messages échoués (exponential backoff)
- **Monitoring :** Sentry (errors) + PostHog (analytics)
- **Backup :** Daily Supabase backups

---

## 6️⃣ Success Metrics

### Product Metrics
- **Automation Rate:** % messages répondus sans humain (Target: >70%)
- **Response Time:** Temps moyen première réponse (Target: <2min)
- **Resolution Rate:** % conversations résolues sans escalade (Target: >80%)
- **CSAT:** Satisfaction client (Target: >4.5/5)

### Technical Metrics
- **Uptime:** % disponibilité (Target: >99.9%)
- **Latency p95:** 95e percentile latence (Target: <3s)
- **RAG Precision:** % réponses RAG pertinentes (Target: >80%)
- **Error Rate:** % requêtes en erreur (Target: <1%)

### Business Metrics
- **Time Saved:** Heures économisées équipe support/semaine
- **Cost per Conversation:** Coût moyen par conversation automatisée
- **MRR:** Monthly Recurring Revenue (pricing TBD)
- **Churn Rate:** % clients qui partent (Target: <5%)

---

## 7️⃣ Out of Scope (MVP)

Ces features ne sont **PAS** incluses dans le MVP hackathon :

- ❌ Support WhatsApp / Messenger (futur)
- ❌ Multi-langue (focus français MVP)
- ❌ Voice messages Instagram
- ❌ Images / GIFs support
- ❌ Fine-tuning modèle custom
- ❌ A/B testing réponses
- ❌ Customer portal (self-service)
- ❌ Live chat handoff (humain prend la main)
- ❌ Payments / e-commerce integration
- ❌ CRM integration (Salesforce, HubSpot)

---

## 8️⃣ Pricing Strategy (Post-MVP)

### Free Tier
- 100 conversations/mois
- 1 social account
- FAQ + RAG basique
- Email support

### Pro ($49/mois)
- 1,000 conversations/mois
- 3 social accounts
- Website crawling
- Priority support

### Business ($149/mois)
- 10,000 conversations/mois
- Unlimited accounts
- Custom branding
- Dedicated support
- Analytics avancées

---

## 9️⃣ Timeline

**MVP Hackathon (12 heures):**
- Core features only (Instagram, FAQ, RAG, Widget)
- Focus sur démo fluide

**Post-Hackathon (4 semaines):**
- Week 1: Polish + tests
- Week 2: Admin panel complet
- Week 3: Website crawling + docs upload
- Week 4: Beta launch (10 clients)

**Version 2.0 (3 mois):**
- WhatsApp + Messenger
- Multi-langue
- Fine-tuning
- Enterprise features

---

## 🔗 Related Documentation
- [Project Architecture](../System/project_architecture.md)
- [Database Schema](../System/database_schema.md)
- [RAG Pipeline](../System/rag_pipeline.md)
- [Hackathon Roadmap](./hackathon_roadmap.md)
- [MVP Features](./mvp_features.md)
